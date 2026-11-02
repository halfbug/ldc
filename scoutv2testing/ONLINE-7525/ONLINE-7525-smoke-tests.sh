#!/usr/bin/env bash
# ONLINE-7525 smoke checks for the shared Bedrock cache, cost meter and batch helper (rag experiments/_shared).
# This ticket has no page and no API, so this replaces the usual -api-tests.sh: it runs against your rag checkout.
#
# By default only offline checks run (no AWS, no cost). SMOKE_LIVE=1 adds 4 real Haiku calls of ~30 tokens each
# (well under $0.01) to prove the record / re-run / replay / record / off / corrupt-entry behaviour end to end.
# Everything is written to a temp dir; your harness caches and .ledger/ are not touched.
#
# Usage (in your own terminal):
#   export AWS_PROFILE=StudiesWeekly AWS_DEFAULT_REGION=us-west-2   # only for SMOKE_LIVE=1 (not AWS_REGION)
#   export SMOKE_LIVE=1                       # optional: run the live checks
#   export SMOKE_MODEL='us.anthropic...'      # optional: model for the live checks (default: product's Haiku 4.5)
#   export RAG_DIR=/home/lenovo/rag           # optional: the rag checkout to test
#   export KEEP_WORK=1                        # optional: keep the temp dir (cache files, ledger) to look at
#   bash ONLINE-7525-smoke-tests.sh

set -u
RAG="${RAG_DIR:-/home/lenovo/rag}"
PASS=0; FAIL=0; SKIP=0

if [ ! -f "$RAG/experiments/_shared/bedrock_cache.py" ]; then
    echo "RAG_DIR must be a rag checkout with experiments/_shared/bedrock_cache.py (ONLINE-7525). Got: $RAG"
    exit 2
fi
if ! command -v uv >/dev/null; then echo "uv is not installed (run 'make install-dev' in rag first)."; exit 2; fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/online7525-smoke.XXXXXX")
if [ -n "${KEEP_WORK:-}" ]; then echo "Temp dir kept: $WORK"; else trap 'rm -rf "$WORK"' EXIT; fi
unset BEDROCK_CACHE_MODE          # a mode left in your shell would change every check below
export SMOKE_WORK="$WORK" PYTHONPATH="$RAG:$WORK" AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-west-2}"
PY=(uv run -q --project "$RAG/lambdas/ai_assistant" python)

# Shared helpers for the Python checks. Real Bedrock calls are counted in calls.txt, across processes, so a check
# can prove "no call was made" instead of trusting the cache's own counters.
cat > "$WORK/smoke_lib.py" <<'PYLIB'
import json
import os
from pathlib import Path

from experiments._shared.bedrock_cache import CachedBedrockClient, CacheMissError  # noqa: F401

WORK = Path(os.environ["SMOKE_WORK"])
CACHE = WORK / "cache"
CALLS = WORK / "calls.txt"
MODEL = os.environ.get("SMOKE_MODEL") or "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def calls():
    return int(CALLS.read_text()) if CALLS.exists() else 0


class Counting:
    def __init__(self, real):
        self.real = real

    def converse(self, **kwargs):
        CALLS.write_text(str(calls() + 1))
        return self.real.converse(**kwargs)


def client(mode=None):
    import boto3
    real = boto3.client("bedrock-runtime", region_name=os.environ["AWS_DEFAULT_REGION"])
    return CachedBedrockClient(Counting(real), cache_dir=CACHE, mode=mode)


def request(text="Reply with the single word OK.", temperature=0, model=None):
    return {"modelId": model or MODEL,
            "messages": [{"role": "user", "content": [{"text": text}]}],
            "inferenceConfig": {"maxTokens": 5, "temperature": temperature}}


def files():
    return sorted(CACHE.glob("*/*/*.json"))


def text(resp):
    return resp["output"]["message"]["content"][0]["text"]


def expect(ok, why):
    if not ok:
        raise SystemExit(f"not as expected: {why}")
PYLIB

# check <name> <text the output must contain> <command...>   (passes on exit 0 AND the text)
check() {
    local name="$1" expect="$2"; shift 2
    local out code
    out=$(cd "$RAG" && "$@" 2>&1); code=$?
    if [ "$code" -eq 0 ] && { [ -z "$expect" ] || printf '%s' "$out" | grep -qF -- "$expect"; }; then
        PASS=$((PASS + 1)); printf 'PASS  %-62s\n' "$name"
    else
        FAIL=$((FAIL + 1)); printf 'FAIL  %-62s exit %s%s\n' "$name" "$code" "${expect:+, want output containing \"$expect\"}"
    fi
    printf '%s\n' "$out" | tail -n 6 | head -c 900 | sed 's/^/      /'
    return 0
}

# pycheck <name> <text> <<'PY' ... PY   (Python code on stdin, run in the ai_assistant venv)
pycheck() { local code; code=$(cat); check "$1" "$2" "${PY[@]}" -c "$code"; }

skip() { SKIP=$((SKIP + 1)); printf 'SKIP  %-62s (set %s)\n' "$1" "$2"; }

echo "== Offline: rag at $RAG ($(git -C "$RAG" rev-parse --abbrev-ref HEAD 2>/dev/null) $(git -C "$RAG" rev-parse --short HEAD 2>/dev/null))"

# Test 1: the ticket's own check scripts
check "T1  check_bedrock_cache.py"                  "14 passed, 0 failed" "${PY[@]}" experiments/_shared/check_bedrock_cache.py
check "T1  check_cost_meter.py"                     "11 passed, 0 failed" "${PY[@]}" experiments/_shared/check_cost_meter.py
check "T1  check_bedrock_batch.py"                  "5 passed, 0 failed"  "${PY[@]}" experiments/_shared/check_bedrock_batch.py

# Test 4a: key ignores dict order, sees content
pycheck "T4a key ignores key order, changes with content" "key checks ok" <<'PY'
from smoke_lib import *
c = CachedBedrockClient(None, cache_dir=WORK / "keys", mode="off")
a = request()
b = {"inferenceConfig": {"temperature": 0, "maxTokens": 5}, "messages": a["messages"], "modelId": a["modelId"]}
k = lambda r: c.key(model=r["modelId"], request={"op": "converse", **r})
expect(k(a) == k(b), "same request in another key order got a different key")
expect(k(a) != k(request(text="Reply with the single word NO.")), "a changed prompt kept the key")
expect(k(a) != k(request(temperature=0.5)), "a changed temperature kept the key")
expect(k(a) != k(request(model="us.anthropic.claude-sonnet-5")), "a changed model kept the key")
print("key checks ok")
PY

# Test 5 (bad mode) and test 7 (cache dir is gitignored)
check "T5  bad BEDROCK_CACHE_MODE is refused"       "bad BEDROCK_CACHE_MODE 'foo'" \
    env BEDROCK_CACHE_MODE=foo "${PY[@]}" -c '
from smoke_lib import *
try:
    CachedBedrockClient(None, cache_dir=WORK / "bad")
except ValueError as e:
    print(e)
else:
    raise SystemExit("mode foo was accepted")'
pycheck "T7  cache dir gets its own .gitignore"      "gitignore ok" <<'PY'
from smoke_lib import *
CachedBedrockClient(None, cache_dir=WORK / "gi", mode="off")
body = (WORK / "gi" / ".gitignore").read_text()
expect(body == "*\n!.gitignore\n", f".gitignore is {body!r}")
print("gitignore ok")
PY

# Test 8: estimate (on-demand and batch)
pycheck "T8  estimate: 40 Sonnet calls 1000 in / 200 out" "0.176000 0.088000" <<'PY'
from experiments._shared.cost_meter import estimate
print(f"{estimate('claude-sonnet-5', 40, 1000, 200):.6f} {estimate('claude-sonnet-5', 40, 1000, 200, batch=True):.6f}")
PY

# Test 9: per-day ledger (temp dir, not the real .ledger/)
pycheck "T9  ledger keeps a per-day total"           "\$0.3000 across 2 recorded run(s)" <<'PY'
from datetime import date
from smoke_lib import *
from experiments._shared.cost_meter import Ledger
ledger = Ledger(root=WORK / "ledger")
ledger.record(harness="smoke_a", model="claude-haiku-4-5", usd=0.1, calls=3, note="smoke")
ledger.record(harness="smoke_b", model="claude-sonnet-5", usd=0.2, calls=1, note="smoke")
expect((WORK / "ledger" / f"{date.today().isoformat()}.jsonl").exists(), "no <today>.jsonl file")
expect("$0.0000 across 0 recorded run(s)" in Ledger(root=WORK / "empty").today(), "an empty day isn't $0")
print(ledger.today())
PY

# Test 10: batch refuses without infra
check "T10 batch refuses with no bucket / role"     "BEDROCK_BATCH_S3_BUCKET and BEDROCK_BATCH_ROLE_ARN must both be set" \
    env -u BEDROCK_BATCH_S3_BUCKET -u BEDROCK_BATCH_ROLE_ARN "${PY[@]}" -c '
from experiments._shared.bedrock_batch import BatchConfig, BatchInfraMissing
try:
    BatchConfig.from_env()
except BatchInfraMissing as e:
    print(e)
else:
    raise SystemExit("from_env() returned a config with nothing set")'

# Test 12: every harness that calls Bedrock goes through the shared cache (AC2)
check "T12 no harness calls Bedrock outside the cache" "all harnesses use the shared cache" bash -c '
cd experiments
left=$(for f in $(grep -rlE "bedrock-runtime|ChatBedrock" --include=*.py . | grep -v _shared/); do
    grep -q "_shared" "$f" || echo "$f"; done)
if [ -z "$left" ]; then echo "all harnesses use the shared cache"; exit 0; fi
echo "$(printf "%s\n" "$left" | wc -l) scripts call Bedrock without experiments._shared, e.g.:"
printf "%s\n" "$left" | sort | head -n 5; exit 1'

# Test 15: the deployed Lambda doesn't depend on any of this
check "T15 the Lambda imports nothing from experiments/" "no imports" bash -c '
if grep -rnE "from experiments|import experiments" lambdas/ai_assistant/src; then exit 1; fi; echo "no imports"'

echo
if [ "${SMOKE_LIVE:-}" != "1" ]; then
    skip "Live checks T2-T6, T8 actual cost (4 Haiku calls, < \$0.01)" SMOKE_LIVE=1
else
    echo "== Live: ${SMOKE_MODEL:-us.anthropic.claude-haiku-4-5-20251001-v1:0} in $AWS_DEFAULT_REGION"
    (cd "$RAG" && "${PY[@]}" -c '
from experiments._shared.cost_meter import estimate
est = estimate("claude-haiku-4-5", 4, 30, 5)
print(f"   estimated ${est:.6f} for 4 live calls (printed before any call)")')
    if ! (cd "$RAG" && "${PY[@]}" -c 'import boto3; boto3.client("sts").get_caller_identity()' >/dev/null 2>&1); then
        echo "   No AWS credentials (set AWS_PROFILE, or run 'aws sso login'). Live checks not run."
        FAIL=$((FAIL + 1))
    else
        pycheck "T2  first call is recorded (1 miss, 1 file)" "0 hits, 1 misses" <<'PY'
from smoke_lib import *
c = client("auto")
r = c.converse(**request())
expect(calls() == 1, f"{calls()} Bedrock calls, want 1")
expect(len(files()) == 1, f"{len(files())} cache files, want 1")
entry = json.loads(files()[0].read_text())
for field in ("op", "model_id", "recorded_at", "response"):
    expect(field in entry, f"cache entry has no {field}")
expect("usage" in entry["response"], "cached response has no usage block")
(WORK / "first.txt").write_text(text(r))
(WORK / "first_recorded_at.txt").write_text(str(entry["recorded_at"]))
print(f"answer {text(r)!r}, usage {entry['response']['usage']}")
print(c.report())
PY
        pycheck "T3  unchanged re-run (auto) makes no call"      "1 hits, 0 misses" <<'PY'
from smoke_lib import *
c = client("auto")
r = c.converse(**request())
expect(calls() == 1, f"{calls()} Bedrock calls, want still 1")
expect(text(r) == (WORK / "first.txt").read_text(), "a different answer came back")
print(c.report())
PY
        pycheck "T3  unchanged re-run (replay, via env) makes no call" "1 hits, 0 misses" <<'PY'
import os
os.environ["BEDROCK_CACHE_MODE"] = "replay"
from smoke_lib import *
c = client()
expect(c.mode == "replay", f"mode is {c.mode}")
c.converse(**request())
expect(calls() == 1, f"{calls()} Bedrock calls, want still 1")
print(c.report())
PY
        pycheck "T4b changed prompt / temperature / model in replay: no call" "3 misses raised, 0 calls" <<'PY'
from smoke_lib import *
c = client("replay")
raised = 0
for r in (request(text="Reply with the single word NO."), request(temperature=0.5),
          request(model="us.anthropic.claude-sonnet-5")):
    try:
        c.converse(**r)
    except CacheMissError as e:
        expect("in replay mode -- the request changed" in str(e), f"message is {e}")
        raised += 1
expect(calls() == 1, f"{calls()} Bedrock calls, want still 1")
print(f"{raised} misses raised, {calls() - 1} calls")
PY
        pycheck "T5  record always calls and overwrites"         "record ok" <<'PY'
from smoke_lib import *
client("record").converse(**request())
expect(calls() == 2, f"{calls()} Bedrock calls, want 2")
expect(len(files()) == 1, f"{len(files())} cache files, want 1")
entry = json.loads(files()[0].read_text())
expect(str(entry["recorded_at"]) != (WORK / "first_recorded_at.txt").read_text(), "recorded_at didn't change")
print("record ok")
PY
        pycheck "T5  off calls through, reads and writes nothing" "off ok" <<'PY'
from smoke_lib import *
before = files()[0].stat().st_mtime_ns
c = client("off")
c.converse(**request())
expect(calls() == 3, f"{calls()} Bedrock calls, want 3")
expect(len(files()) == 1 and files()[0].stat().st_mtime_ns == before, "off mode touched the cache")
print(c.report())   # note: off-mode calls don't appear in the hit/miss report
print("off ok")
PY
        pycheck "T6  corrupt entry: replay misses, auto re-fetches" "corrupt ok" <<'PY'
from smoke_lib import *
path = files()[0]
path.write_text(path.read_text()[:40])
try:
    client("replay").converse(**request())
    raise SystemExit("replay returned something for a corrupt entry")
except CacheMissError:
    pass
expect(calls() == 3, f"{calls()} Bedrock calls after replay, want still 3")
client("auto").converse(**request())
expect(calls() == 4, f"{calls()} Bedrock calls, want 4")
json.loads(path.read_text())
print("corrupt ok")
PY
        pycheck "T8  actual cost from usage = cost from cache"  "actual cost ok" <<'PY'
from smoke_lib import *
from experiments._shared.cost_meter import actual_cost, actual_cost_from_cache, PRICES
usage = json.loads(files()[0].read_text())["response"]["usage"]
p = PRICES["claude-haiku-4-5"]
by_hand = usage["inputTokens"] / 1e6 * p["input"] + usage["outputTokens"] / 1e6 * p["output"]
one = actual_cost("claude-haiku-4-5", usage)
from_cache = actual_cost_from_cache(CachedBedrockClient(None, cache_dir=CACHE, mode="off"))
expect(abs(one - by_hand) < 1e-12, f"actual_cost {one} vs by hand {by_hand}")
expect(abs(from_cache - one) < 1e-12, f"from cache {from_cache} vs {one}")
print(f"one call ${one:.6f}; 4 live calls about ${4 * one:.6f}")
print("actual cost ok")
PY
    fi
fi

echo
echo "PASS $PASS  FAIL $FAIL  SKIP $SKIP"
[ "$FAIL" -eq 0 ]
