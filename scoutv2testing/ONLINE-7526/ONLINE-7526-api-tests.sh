#!/usr/bin/env bash
# ONLINE-7526 checks against dev2. Nothing here calls the model or spends AI credits: chat checks send a blank
# message, which rag refuses with 400 after the auth, daily-cap and throttle checks and before any model call.
# The AWS section only reads (describe / get-item / Logs Insights); it never writes to the daily-usage table.
#
# Usage (in your own terminal):
#   export SWO_TOKEN='eyJ...'              # teacher token (Authorization header, without "Bearer ")
#   export TURN_URL='https://<id>.lambda-url.us-west-2.on.aws/assistant/v2/turn?host=dev2-online.studiesweekly.com'
#                                          # optional: copied from the Network tab after asking Scout anything
#   export THREADS_URL='https://.../assistant/thread/listing?host=...'   # optional: from the Network tab
#                                          # (opening Scout's chat list sends it)
#   export NOFLAG_TOKEN='eyJ...'           # optional: a teacher without feature_frontend_ai_assistant
#   export EXPECT_CAPPED=1                 # optional: your daily row was set to $5 (test 13); expect the cap's 429
#   export THROTTLE=1                      # optional: 11 blank chat messages in a row to hit the 10-a-minute
#                                          # throttle (locks your chat for up to a minute)
#   export AWS_CHECKS=1 AWS_PROFILE=StudiesWeekly AWS_DEFAULT_REGION=us-west-2   # optional: read-only AWS checks
#   export SWO_USER_ID='<id>'              # optional, with AWS_CHECKS: your Laravel user id, to read today's row
#   bash ONLINE-7526-api-tests.sh

set -u
PASS=0; FAIL=0; SKIP=0
ENVNAME="${ENVNAME:-dev}"
TABLE="${TABLE:-swo-ai-daily-usage}"
V2_FN="swo-genai-pov-ai-assistant-v2-$ENVNAME"
GW_FN="swo-genai-pov-ai-assistant-$ENVNAME"

if [ -z "${SWO_TOKEN:-}" ]; then echo "Set SWO_TOKEN first (see the top of this file)."; exit 2; fi

# check <name> <expected status, or alternatives like 401|403> <token or ""> <url> <body> [text the response must contain]
check() {
    local name="$1" want="$2" token="$3" url="$4" body="$5" expect="${6:-}"
    local auth=()
    [ -n "$token" ] && auth=(-H "Authorization: Bearer ${token#Bearer }")
    local out code secs
    out=$(curl -s -m 60 -w $'\n%{http_code} %{time_total}' -X POST "$url" "${auth[@]}" \
        -H 'Accept: application/json' -H 'Content-Type: application/json' \
        -H 'Origin: https://dev2-online.studiesweekly.com' --data-raw "$body")
    secs="${out##* }"; out="${out% *}"
    code="${out##*$'\n'}"; out="${out%$'\n'*}"
    LAST_BODY="$out"
    if [[ "$code" =~ ^($want)$ ]] && { [ -z "$expect" ] || printf '%s' "$out" | grep -qF -- "$expect"; }; then
        PASS=$((PASS + 1)); printf 'PASS  %-58s %s  %ss\n' "$name" "$code" "$secs"
    else
        FAIL=$((FAIL + 1)); printf 'FAIL  %-58s got %s, want %s %s\n' "$name" "$code" "$want" "${expect:+containing \"$expect\"}"
    fi
    printf '      %s\n' "$(printf '%s' "$out" | head -c 300)"
    [ -n "${RAG_PAUSE:-}" ] && sleep "$RAG_PAUSE"
    return 0
}

# absent <name> <text>: the last response must NOT contain <text>
absent() {
    if printf '%s' "${LAST_BODY:-}" | grep -qF -- "$2"; then
        FAIL=$((FAIL + 1)); printf 'FAIL  %-58s response contains "%s"\n' "$1" "$2"
    else
        PASS=$((PASS + 1)); printf 'PASS  %-58s\n' "$1"
    fi
}

skip() { SKIP=$((SKIP + 1)); printf 'SKIP  %-58s (set %s)\n' "$1" "$2"; }
ok()   { PASS=$((PASS + 1)); printf 'PASS  %-58s %s\n' "$1" "${2:-}"; }
bad()  { FAIL=$((FAIL + 1)); printf 'FAIL  %-58s %s\n' "$1" "${2:-}"; }

# ---------------------------------------------------------------------------------------------------------
echo "== rag chat door (Function URL)"
if [ -n "${TURN_URL:-}" ] && [[ "$TURN_URL" != *"/assistant/v2/turn"* ]]; then
    echo "TURN_URL must be the chat request (…/assistant/v2/turn?host=…), copied from the Network tab after"
    echo "asking Scout anything. Got: ${TURN_URL%%\?*}"
    FAIL=$((FAIL + 1))
elif [ -n "${TURN_URL:-}" ]; then
    echo "   (7s between calls: chat allows 10 a minute and counts these blank messages too)"
    RAG_PAUSE=7
    BLANK='{"message":"   "}'
    check "401: guest"                                       401 ""           "$TURN_URL" "$BLANK" '"not_signed_in"'
    if [ -n "${EXPECT_CAPPED:-}" ]; then
        check "429: over the \$5 cap (row set by hand)"     429 "$SWO_TOKEN" "$TURN_URL" "$BLANK" 'DAILY_LIMIT_EXCEEDED'
        printf '%s' "$LAST_BODY" | grep -qF "You've reached today's limit for Scout. You can continue in about" \
            && ok "429 carries the teacher-facing message" \
            || bad "429 carries the teacher-facing message" "missing \"You've reached today's limit for Scout…\""
    else
        check "400: blank message (under the cap, no model call)" 400 "$SWO_TOKEN" "$TURN_URL" "$BLANK" 'Message cannot be empty.'
        absent "not refused by the daily cap"                'DAILY_LIMIT_EXCEEDED'
    fi
    if [ -n "${NOFLAG_TOKEN:-}" ]; then
        check "403: AI flag off"                             403 "$NOFLAG_TOKEN" "$TURN_URL" "$BLANK" '"scout_off"'
    else skip "403: AI flag off" NOFLAG_TOKEN; fi
    if [ -n "${THROTTLE:-}" ] && [ -z "${EXPECT_CAPPED:-}" ]; then
        echo "   waiting 61s for a fresh minute window, then 11 blank messages with no pause"
        sleep 61; RAG_PAUSE=
        for i in $(seq 1 10); do
            curl -s -o /dev/null -m 30 -X POST "$TURN_URL" -H "Authorization: Bearer ${SWO_TOKEN#Bearer }" \
                -H 'Content-Type: application/json' --data-raw "$BLANK"
        done
        check "429: 11th chat message in a minute (throttle)" 429 "$SWO_TOKEN" "$TURN_URL" "$BLANK" 'Scout can take 10 messages a minute'
        absent "the throttle, not the dollar cap"            'DAILY_LIMIT_EXCEEDED'
    else
        skip "429: throttle (10 chat messages a minute)" "THROTTLE=1 (not with EXPECT_CAPPED)"
    fi
    RAG_PAUSE=
else
    skip "rag chat door checks (4-6)" TURN_URL
fi

# ---------------------------------------------------------------------------------------------------------
echo
echo "== rag gateway door (thread listing, a light route)"
if [ -n "${THREADS_URL:-}" ] && [[ "$THREADS_URL" != *"/thread/listing"* ]]; then
    echo "THREADS_URL must be the chat-list request (…/assistant/thread/listing?host=…). Got: ${THREADS_URL%%\?*}"
    FAIL=$((FAIL + 1))
elif [ -n "${THREADS_URL:-}" ]; then
    check "401/403: guest"                                   "401|403" ""           "$THREADS_URL" '{"limit":1,"offset":0}'
    check "200: listing, first call (note the time)"        200 "$SWO_TOKEN" "$THREADS_URL" '{"limit":1,"offset":0}'
    absent "no internal usage record in the response"       '"_usage"'
    absent "no daily-row fields in the response"            'cost_microusd'
    check "200: listing, warm (compare with the guest 401 time)"       200 "$SWO_TOKEN" "$THREADS_URL" '{"limit":1,"offset":0}'
else
    skip "rag gateway door checks (5)" THREADS_URL
fi

# ---------------------------------------------------------------------------------------------------------
echo
echo "== AWS (read-only): tables, Lambda config, today's row, CloudWatch"
if [ -z "${AWS_CHECKS:-}" ]; then
    skip "AWS checks (off by default, even with AWS configured)" "export AWS_CHECKS=1"
elif ! command -v aws >/dev/null; then
    bad "aws CLI installed" "not found"
elif ! aws sts get-caller-identity >/dev/null 2>&1; then
    bad "AWS session" "aws sts get-caller-identity failed (aws sso login?)"
else
    # The deployed name is <project>-content-cache-<env> (infra/swo/output.txt), not the module's old default.
    CACHE_TABLE="swo-genai-pov-content-cache-$ENVNAME"
    out=$(aws dynamodb describe-table --table-name "$CACHE_TABLE" 2>&1)
    printf '%s' "$out" | grep -q ResourceNotFoundException \
        && ok "$CACHE_TABLE removed" "ResourceNotFoundException" \
        || bad "$CACHE_TABLE removed" "$(printf '%s' "$out" | head -c 120)"
    alarms=$(aws cloudwatch describe-alarms --alarm-name-prefix "$CACHE_TABLE" --query 'length(MetricAlarms)' --output text 2>&1)
    [ "$alarms" = "0" ] && ok "its alarms removed" "0 left" || bad "its alarms removed" "$alarms left"

    created=$(aws dynamodb describe-table --table-name "$TABLE" --query 'Table.CreationDateTime' --output text 2>&1)
    [[ "$created" == 20* ]] \
        && ok "$TABLE still exists" "created $created (must predate the deploy: moved, not recreated)" \
        || bad "$TABLE still exists" "$created"

    for fn in "$V2_FN" "$GW_FN"; do
        envs=$(aws lambda get-function-configuration --function-name "$fn" --query 'Environment.Variables' --output json 2>&1)
        if ! printf '%s' "$envs" | grep -q '{'; then bad "$fn config readable" "$(printf '%s' "$envs" | head -c 120)"; continue; fi
        printf '%s' "$envs" | grep -q "\"DAILY_USAGE_TABLE_NAME\": \"$TABLE\"" \
            && ok "$fn: DAILY_USAGE_TABLE_NAME=$TABLE" || bad "$fn: DAILY_USAGE_TABLE_NAME=$TABLE" "not set to $TABLE"
        printf '%s' "$envs" | grep -qE 'CONTENT_CACHE_TABLE_NAME|DAILY_COST|DAILY_TOKEN' \
            && bad "$fn: no cache-table or cap env var" "$(printf '%s' "$envs" | grep -oE '"(CONTENT_CACHE|DAILY_COST|DAILY_TOKEN)[A-Z_]*"')" \
            || ok "$fn: no cache-table or cap env var"
        mod=$(aws lambda get-function-configuration --function-name "$fn" --query 'LastModified' --output text 2>/dev/null)
        printf '      %s last deployed %s (must be after 83ec2cc0, 2026-10-01)\n' "$fn" "$mod"
    done

    if [ -n "${SWO_USER_ID:-}" ]; then
        today=$(date -u +%F)
        row=$(aws dynamodb get-item --table-name "$TABLE" \
            --key "{\"user_id\":{\"S\":\"$SWO_USER_ID\"},\"date\":{\"S\":\"$today\"}}" --output json 2>&1)
        if printf '%s' "$row" | grep -q '"cost_microusd"'; then
            ok "today's row has dollars and cached tokens" "$today"
            for f in cost_microusd input_tokens output_tokens cache_read_tokens cache_write_tokens total_tokens; do
                printf '      %-20s %s\n' "$f" "$(printf '%s' "$row" | python3 -c "import json,sys;d=json.load(sys.stdin).get('Item',{});print(d.get('$f',{}).get('N','-'))")"
            done
            printf '%s' "$row" | grep -q '"cache_read_tokens"' || bad "row carries cache_read_tokens" "missing"
        elif printf '%s' "$row" | grep -q '"Item"'; then
            bad "today's row has dollars" "row exists but has no cost_microusd (old code still writing?)"
        else
            printf 'INFO  no row for %s on %s yet: ask Scout one question, then run again\n' "$SWO_USER_ID" "$today"
        fi
    else
        skip "today's daily-usage row" SWO_USER_ID
    fi

    # Logs Insights over the last 24h of chat turns: are the new fields there, and what do turns cost?
    q='fields @timestamp | filter message = "core_turn" and outcome = "complete"
       | stats count(*) as turns, count(model_ms) as with_stage_split, avg(cost_usd) as mean_cost,
               pct(first_content_ms, 50) as fc_p50, pct(first_content_ms, 95) as fc_p95,
               pct(total_ms, 50) as total_p50, pct(total_ms, 95) as total_p95,
               sum(cache_read_tokens) as cache_read, sum(input_tokens) as input, sum(cache_write_tokens) as cache_write'
    qid=$(aws logs start-query --log-group-name "/aws/lambda/$V2_FN" --start-time $(( $(date +%s) - 86400 )) \
        --end-time "$(date +%s)" --query-string "$q" --query queryId --output text 2>&1)
    if [[ "$qid" =~ ^[0-9a-f-]{36}$ ]]; then
        tmpq=$(mktemp)
        for _ in $(seq 1 30); do
            res=$(aws logs get-query-results --query-id "$qid" --output json)
            printf '%s' "$res" | grep -q '"status": "Complete"' && break; sleep 2
        done
        printf '%s' "$res" | python3 -c '
import json, sys
rows = json.load(sys.stdin).get("results") or []
row = {c["field"]: c["value"] for c in rows[0]} if rows else {}
for k, v in row.items(): print(f"      {k:18} {v}")
turns = float(row.get("turns", 0)); split = float(row.get("with_stage_split", 0))
print("RESULT", "none" if turns == 0 else ("ok" if split > 0 else "nosplit"))' > "$tmpq" 2>&1
        grep -v '^RESULT' "$tmpq"
        case "$(grep '^RESULT' "$tmpq")" in
            "RESULT ok")      ok "core_turn lines carry the stage split (model_ms…)" ;;
            "RESULT nosplit") bad "core_turn lines carry the stage split (model_ms…)" "no line in 24h has model_ms" ;;
            *)                printf 'INFO  no completed chat turn on %s in the last 24h\n' "$V2_FN" ;;
        esac
        rm -f "$tmpq"
    else
        bad "Logs Insights query on /aws/lambda/$V2_FN" "$(printf '%s' "$qid" | head -c 160)"
    fi
fi

echo
echo "PASS $PASS  FAIL $FAIL  SKIP $SKIP"
[ "$FAIL" -eq 0 ]
