# ONLINE-7525 test-results report content. Built by ../make_test_results_docx.py ONLINE-7525

title = doc.add_paragraph()
run = title.add_run("ONLINE-7525: Shared Response Cache — QA Test Results")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("Record-and-replay Bedrock cache, cost meter and batch helper for Scout evaluation runs")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Ticket", "ONLINE-7525 (SCOUT-C)"],
    ["Environment", "Local rag checkout, branch ONLINE-5385_scout_ai_integration (35b99fba); live calls to Bedrock in "
                    "us-west-2. No swo-3.0 change, so there is nothing to test on dev2"],
    ["Account", "Tester's AWS SSO session (AWSAdminAccess role)"],
    ["Page", "None: no UI and no API. Code under rag/experiments/_shared (bedrock_cache.py, cost_meter.py, "
             "bedrock_batch.py)"],
    ["Date", "1 Oct 2026"],
    ["Overall result", "PASS 18/19 with ONLINE-7525-smoke-tests.sh: an unchanged re-run makes no Bedrock call, the "
                       "estimate is printed before the run, actual cost and a per-day total are kept. 1 FAIL: 33 "
                       "scripts still call Bedrock without the shared cache (AC2). Batch jobs (AC4) can't run yet: no "
                       "S3 bucket or role exists. Total spend for the run: about $0.00015."],
])

doc.add_heading("Smoke test results", level=1)
doc.add_heading("How the tests were run", level=2)
doc.add_paragraph(
    "Tested on 1 Oct 2026 from a terminal (WSL2), not in a browser: this ticket has no page or API. (1) The rag "
    "repo was on branch ONLINE-5385_scout_ai_integration at 35b99fba, which contains the ONLINE-7525 commits "
    "9d11e0d2 and d3c400f8, with its Python dependencies installed (make install-dev). (2) AWS access was confirmed "
    "with aws sts get-caller-identity (SSO session, AWSAdminAccess role, region us-west-2). (3) From the ticket "
    "folder, the script was run with SMOKE_LIVE=1 AWS_DEFAULT_REGION=us-west-2 bash ONLINE-7525-smoke-tests.sh. "
    "It first runs the developer's three check scripts (T1), then its own offline checks, then prints a cost "
    "estimate and makes 4 real calls to Claude Haiku 4.5 on Bedrock through the shared cache. (4) Everything the "
    "script writes (cache files, ledger) goes to a temporary folder that is deleted at the end, so no real harness "
    "cache or cost ledger was changed. (5) Every real Bedrock call passes through a counter that sits outside the "
    "cache, so \"no call was made\" is measured independently rather than taken from the cache's own report. (6) "
    "Each check prints PASS or FAIL with its output; the results below are copied from that output.")

doc.add_heading("Offline checks (no AWS, no cost)", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["T1 Developer's cache checks (check_bedrock_cache.py): the cache logic with a fake Bedrock. Each check "
     "is listed below", "exit 0", "14 passed, 0 failed", "PASS"],
    ["T1 Developer's cost checks (check_cost_meter.py): estimates, prices and the daily ledger", "exit 0",
     "11 passed, 0 failed", "PASS"],
    ["T1 Developer's batch checks (check_bedrock_batch.py): batch set-up and results going into the cache",
     "exit 0", "5 passed, 0 failed", "PASS"],
    ["T4a Cache key: the same request with its fields in another order must be treated as the same; a changed "
     "prompt, temperature or model must be treated as new", "exit 0", "key checks ok", "PASS"],
    ["T5 A mistyped mode (BEDROCK_CACHE_MODE=foo) must stop the run before any call, not be silently ignored",
     "exit 0", "ValueError: bad BEDROCK_CACHE_MODE 'foo', want one of {…}", "PASS"],
    ["T7 Cache files must never be committed to git (they can hold real page text)", "exit 0",
     ".gitignore written with \"*\" and \"!.gitignore\"", "PASS"],
    ["T8 The cost estimate printed before a run must use the right prices: 40 Sonnet calls, 1000 in / 200 out",
     "exit 0", "$0.176 on demand, $0.088 as batch", "PASS"],
    ["T9 A per-day total must be kept across runs (AC3)", "exit 0",
     "2026-10-01: $0.3000 across 2 recorded run(s); an empty day is $0.0000", "PASS"],
    ["T10 A batch job with no S3 bucket or role must refuse clearly, not guess a bucket", "exit 0",
     "BatchInfraMissing: BEDROCK_BATCH_S3_BUCKET and BEDROCK_BATCH_ROLE_ARN must both be set…", "PASS"],
    ["T12 Every script that calls Bedrock must go through the shared cache (AC2)", "exit 1",
     "33 scripts call Bedrock without experiments._shared", "FAIL"],
    ["T15 Teachers see no change: the deployed Lambda must not use any of this code", "exit 0",
     "no imports", "PASS"],
])

doc.add_heading("Developer's check scripts (T1): what each check tests", level=2)
doc.add_paragraph("These three scripts were committed with the ticket by the developer; T1 runs them. They don't "
                  "call Bedrock: a fake client stands in for it, records every call it receives and returns a canned "
                  "reply. Each check then counts how many requests reached the fake client. They prove the logic, "
                  "not real Bedrock behaviour; the live checks below repeat the important ones for real.")
table([0.35, 5.35, 0.8], ["#", "check_bedrock_cache.py: what it checks", "Result"], [
    ["1", "Sending the same request twice reaches Bedrock only once", "PASS"],
    ["2", "The cache's counters show the first request as a miss and the second as a hit", "PASS"],
    ["3", "The answer from the cache is identical to the original answer", "PASS"],
    ["4", "A request with a changed message reaches Bedrock again (a new call)", "PASS"],
    ["5", "A request with only the model changed also reaches Bedrock again", "PASS"],
    ["6", "The original request, sent again after those, is still answered from the cache", "PASS"],
    ["7", "16 threads sending the same request at the same moment leave exactly one cache file", "PASS"],
    ["8", "That file is valid and its token usage is intact (no corruption from the race)", "PASS"],
    ["9", "replay mode with a request it has never seen stops with CacheMissError", "PASS"],
    ["10", "That replay miss does not reach Bedrock", "PASS"],
    ["11", "record mode reaches Bedrock every time, even for a repeat", "PASS"],
    ["12", "off mode reaches Bedrock every time", "PASS"],
    ["13", "off mode counts nothing as a hit or miss. Weaker than its name (\"wrote nothing new\"): it checks the "
           "counters, not the files. Live T5 confirmed the cache file is untouched", "PASS"],
    ["14", "invoke_model (the other way of calling Bedrock) with the same body twice is answered from the cache. "
           "Weaker than its name (\"body in different key order\"): both bodies have the same order, so it proves a "
           "plain repeat only. T4a covers field order for converse requests, not for invoke_model bodies", "PASS"],
])
table([0.35, 5.35, 0.8], ["#", "check_cost_meter.py: what it checks", "Result"], [
    ["1", "Estimate for 40 Sonnet calls (1000 in / 200 out tokens) equals the hand-worked $0.176", "PASS"],
    ["2", "Estimate for 100 Haiku calls (500 in / 100 out tokens) equals the hand-worked $0.11", "PASS"],
    ["3", "A batch estimate is exactly half the normal estimate", "PASS"],
    ["4", "Actual cost of 1M input + 1M output tokens equals Sonnet's input + output price", "PASS"],
    ["5", "Token counts are read the same in both formats Bedrock returns (converse and native)", "PASS"],
    ["6", "Prompt-cache read/write tokens are priced at their own lower rates", "PASS"],
    ["7", "Batch pricing ignores prompt-cache tokens", "PASS"],
    ["8", "The ledger totals two runs recorded today ($1.2345 + $0.0100 = $1.2445)", "PASS"],
    ["9", "The day's summary names both runs", "PASS"],
    ["10", "A day with no runs totals $0", "PASS"],
    ["11", "The total cost read back from the cache files matches the tokens in them, with no extra bookkeeping",
     "PASS"],
])
table([0.35, 5.35, 0.8], ["#", "check_bedrock_batch.py: what it checks", "Result"], [
    ["1", "With no S3 bucket and no role set, a batch job refuses with BatchInfraMissing", "PASS"],
    ["2", "With only the bucket set (no role), it still refuses", "PASS"],
    ["3", "With both set, it builds the batch settings", "PASS"],
    ["4", "Writing a batch result into the cache reports one entry written", "PASS"],
    ["5", "A normal cache client in replay mode then finds that batch result as an ordinary hit. Note: the fake "
          "batch result is already in the converse format, so this doesn't prove a real batch result (native "
          "format) can be read back (see finding 2)", "PASS"],
])

doc.add_heading("Live checks (Haiku 4.5, 4 real calls)", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Calls", "Response", "Result"], [
    ["The cost estimate must be printed before any call is made (AC3)", "0",
     "estimated $0.000242 for 4 live calls", "PASS"],
    ["T2 A first, new request must call Bedrock once and be saved with its token usage", "1",
     "Answer 'OK', 14 in / 4 out tokens; cache: 0 hits, 1 misses; 1 file with op, model_id, recorded_at, usage",
     "PASS"],
    ["T3 Running the same request again (auto) must not call Bedrock (AC1)", "0",
     "cache: 1 hits, 0 misses; same answer", "PASS"],
    ["T3 Running it again in replay mode, set by environment variable, must not call Bedrock (AC1)", "0",
     "cache: 1 hits, 0 misses", "PASS"],
    ["T4b In replay, a changed prompt, temperature or model must stop with an error, not call Bedrock", "0",
     "CacheMissError ×3: \"…in replay mode -- the request changed…\"", "PASS"],
    ["T5 record mode must call again and replace the saved answer (for a deliberate refresh)", "1",
     "Calls again; the one file is rewritten with a new recorded_at", "PASS"],
    ["T5 off mode must call without reading or writing the cache (for one-off live calls)", "1",
     "Calls through; cache file not read or changed; report shows 0 hits, 0 misses", "PASS"],
    ["T6 A damaged cache file must not crash the run: replay stops, auto fetches it again", "1",
     "replay raises CacheMissError (no call); auto re-fetches and rewrites it", "PASS"],
    ["T8 The actual cost printed after a run must match the tokens used (AC3)", "0",
     "$0.000037 per call = tokens × Haiku price; same as actual_cost_from_cache; ~$0.00015 in all", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["T11 A real evaluation script run twice unchanged (auto, then replay): estimate first, 0 misses on the "
     "second run, a ledger line", "0 new calls", "Not covered"],
    ["T13 Bulk labelling uses Sonnet, with an Opus spot-check against a bar set before the run",
     "See test plan", "Not covered"],
    ["T14 Batch job end to end: submit, wait, write into the cache, then hits in replay; cost at 50%. "
     "Blocked: no IAM role for Bedrock batch and no batch prefix in the dev account (finding 2)",
     "Completed", "Not covered"],
    ["T16 The measured turn in a harness still uses the product's production model", "No change",
     "Not covered"],
])

doc.add_heading("Findings", level=1)
doc.add_heading("1. 33 evaluation scripts still call Bedrock without the shared cache", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: acceptance criterion 2 (\"All existing evaluation scripts use the cache\") isn't met; "
                 "re-running any of these pays again"],
    ["Steps", "In rag/experiments, list the .py files that create a bedrock-runtime client (or ChatBedrock) and "
              "don't import experiments._shared (smoke test T12)."],
    ["Expected", "None."],
    ["Actual", "33 files, including labellers and calibrators the ticket names: teacher_eval/judge.py; "
               "teacher_eval/online7507/label_c2.py, label_c3.py, label_c4.py, label_c5.py, label_pools.py, "
               "relabel_check.py, validate_label_fix.py; grading_baseline/grader.py; "
               "guardrail_curriculum/calib_grounding.py. teacher_eval/online7507/bedrock_cache.py is a second, "
               "separate cache, which bedrock_cache.py's own docstring says must be migrated."],
    ["Scope note", "Some of the 33 may reasonably stay outside the cache (latency measurements, guardrail probes, "
                   "embedding runs). The migration list the docstring points to (results/7525-build.md) isn't in "
                   "the repo, so which ones are in scope needs confirming."],
])
doc.add_heading("2. Batch jobs can't run: no S3 bucket or role exists", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: acceptance criterion 4 (\"Bulk labelling can run as batch jobs at the lower price\") "
                 "can't be shown to work"],
    ["Steps", "Call BatchConfig.from_env() without BEDROCK_BATCH_S3_BUCKET and BEDROCK_BATCH_ROLE_ARN (T10)."],
    ["Expected", "A bucket and role to run a batch job with."],
    ["Actual", "BatchInfraMissing, as designed. No Terraform bucket fits (bedrock_batch.py docstring), and no "
               "script calls submit_batch_job. The 5 batch checks use a fake client only."],
    ["AWS check (1 Oct)", "Read-only look at the dev account (us-west-2), nothing created. Bucket: only "
                          "swo-genai-pov-…-dev-ai-export, whose content-sync permissions cover ai-export/ only, so batch "
                          "use needs a new prefix and grant. Role: the only roles Bedrock can assume are the "
                          "bedrock-cw-logging ones, which can write CloudWatch logs but have no S3 access. Models: "
                          "Haiku 4.5 has batch quotas (minimum 100 records per job); Sonnet 5 shows no batch quotas, "
                          "although the ticket wants Sonnet for bulk labelling. No batch job has ever run in the region."],
    ["Scope note", "Infra decision, not a code defect: a role (trusting bedrock.amazonaws.com, S3 access to one "
                   "prefix) and a bucket prefix are needed from the infra owner. Then confirm Sonnet 5 batch support. "
                   "Until a job runs, it's also unproven that batch output (Bedrock's native InvokeModel body) can be "
                   "read back by a harness that calls converse: write_into_cache stores it under a converse key."],
])
doc.add_heading("3. Batch spend would be counted at full price", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low: no batch job has run yet, so no total is wrong today"],
    ["Steps", "Write a batch result into a cache with write_into_cache, then total it with actual_cost_from_cache()."],
    ["Expected", "Priced at the batch rate (50% of input + output)."],
    ["Actual", "actual_cost_from_cache() calls actual_cost(alias, usage) without batch=True (cost_meter.py:123), "
               "so a batch entry is priced at on-demand rates, double the real cost."],
    ["Cause", "Batch entries carry batch_record_id, so they could be told apart and passed batch=True."],
])
doc.add_heading("4. Unpriced models are counted as $0", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low: understates spend for any model not in the price table"],
    ["Steps", "Cache a response from a model with no PRICES row (e.g. teacher_eval/judge.py's "
              "us.openai.gpt-5.6-sol), then call actual_cost_from_cache()."],
    ["Expected", "Never under-counted: the product's config.py uses FALLBACK_PRICE (the dearest row) for exactly "
                 "this case."],
    ["Actual", "The entry is skipped (cost_meter.py:111) and adds $0 to the total."],
])

doc.add_heading("Notes", level=1)
for text in (
    "No screenshots: this ticket has no UI. The evidence is the smoke script's terminal output (results above).",
    "Real Bedrock calls in the live run: 4, exactly the ones that should call (first call, record, off, the corrupt "
    "file in auto). The two unchanged re-runs and the three changed requests in replay made none.",
    "The estimate ($0.000242) was higher than the actual spend (~$0.00015), so it erred on the safe side.",
    "Observation: calls made in off mode don't appear in the cache report (\"0 hits, 0 misses\"), so that spend "
    "isn't visible there.",
    "Observation: actual_cost_from_cache() totals the whole cache folder, not one run. Each harness works out its "
    "own run's cost (online7511/run_gate_v3.py diffs the cache; standards_suggest_7532/cost_since.py filters by "
    "file time).",
    "Observation: the per-day ledger only contains runs whose script calls Ledger().record() (32 do). Nothing "
    "enforces the $10 / $30 daily gate the docstring mentions.",
    "Observation: each harness folder has its own gitignored .cache, so another worktree or a colleague's checkout "
    "pays again for the same requests.",
    "Observation: Opus prices are estimated (list price × 1.1, \"estimated\": True), but totals don't say so.",
    "Observation: anything that changes per run inside a prompt (a per-run thread suffix, a timestamp, today's "
    "date) makes every request a miss. T11's replay run would catch this.",
):
    doc.add_paragraph(text, style="List Bullet")
