# ONLINE-7526 test-results report content. Built by ../make_test_results_docx.py ONLINE-7526

title = doc.add_paragraph()
run = title.add_run("ONLINE-7526: Scout Cost and Speed — QA Test Results")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("Daily cap in dollars, cached conversation history, stage timings, faster cold starts, dead weight removed")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Ticket", "ONLINE-7526"],
    ["Environment", "dev2 (rag branch ONLINE-5385_scout_ai_integration; no swo-3.0 change). Chat Lambda "
                    "swo-genai-pov-ai-assistant-v2-dev last deployed 2026-10-01 07:40:45 UTC, gateway Lambda "
                    "swo-genai-pov-ai-assistant-dev 07:39:27 UTC"],
    ["Account", "Teacher account with the AI feature flag on; AWS read access to the dev account (us-west-2)"],
    ["Page", "Scout chat on dev2 (/beta/), plus direct API calls and read-only AWS checks"],
    ["Date", "1 Oct 2026"],
    ["Overall result", "PASS on everything run so far: API and AWS checks 17/17, the 240 checks that ship with the ticket 240/240, and "
                       "the turn and the daily usage row both match the price table. 2 findings: the guardrail scoping is not built, and "
                       "there is no deployed before/after measurement. The $5 cap refusal, the rate limit and multi-turn "
                       "caching are not covered yet."],
])

doc.add_heading("API results", level=1)
doc.add_paragraph("Run with ONLINE-7526-api-tests.sh against dev2 with the teacher's own token. The chat checks "
                  "send a blank message, which rag refuses after the sign-in, daily-cap and rate-limit checks and "
                  "before any model call, so nothing here spends AI credits. The AWS checks only read.")
doc.add_heading("rag chat: POST /assistant/v2/turn (Function URL)", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["Guest (no token)", "401", "not_signed_in: \"Your session has ended. Please sign in again.\"", "PASS"],
    ["Blank message, teacher under the cap", "400",
     "empty_message: \"Message cannot be empty.\" (passed the daily-cap check; no model call)", "PASS"],
    ["Not refused by the daily cap", "—", "no DAILY_LIMIT_EXCEEDED in the response", "PASS"],
])
doc.add_heading("rag gateway: POST /v3/assistant/thread/listing (API Gateway)", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["Guest (no token)", "401", "\"Unauthorized\" (API Gateway authorizer)", "PASS"],
    ["Listing, first call", "200", "1 thread of 189, pinned first; 5.17 s (a guest 401 takes 0.87 s, so about 4.3 s "
     "was spent in the Lambda, likely a cold start)", "PASS"],
    ["No internal usage record (_usage) in the response", "—", "absent", "PASS"],
    ["No daily-row fields (cost_microusd) in the response", "—", "absent", "PASS"],
    ["Listing, warm", "200", "1.00 s, about the same as the guest round trip", "PASS"],
])
doc.add_heading("AWS (read-only): DynamoDB, Lambda, CloudWatch", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["Content-cache table swo-genai-pov-content-cache-dev removed", "—", "ResourceNotFoundException", "PASS"],
    ["Its CloudWatch alarms removed", "—", "0 left", "PASS"],
    ["Daily-usage table kept, not recreated", "—", "swo-ai-daily-usage, created 2026-01-09", "PASS"],
    ["Chat Lambda: DAILY_USAGE_TABLE_NAME, no cap or cache-table env var", "—",
     "swo-ai-daily-usage; none of CONTENT_CACHE_*, DAILY_COST_*, DAILY_TOKEN_*", "PASS"],
    ["Gateway Lambda: the same", "—", "swo-ai-daily-usage; none", "PASS"],
    ["Today's daily row has dollars and cached tokens", "—",
     "cost $0.298217; input 342, output 2,761, cache read 342,021, cache write 69,982; total 415,106 (= the sum)",
     "PASS"],
    ["core_turn log lines carry the stage split", "—", "187 of 191 completed turns in 24 h have model_ms", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["Teacher over the $5 cap, chat and gateway (needs a write to the tester's own daily row)", "429", "Not covered"],
    ["Just under the cap: one more request allowed, the next refused", "200 then 429", "Not covered"],
    ["11th chat message in a minute (rate limit)", "429", "Not covered"],
    ["Teacher without the AI flag", "403", "Not covered"],
    ["One turn adds exactly its tokens and dollars to the daily row (read before and after)", "See test plan",
     "Not covered"],
    ["Generate / level request adds once to the row; reads add nothing", "See test plan", "Not covered"],
    ["Turns 2 to 4 of one thread read the history from cache; a 6-minute gap writes it again", "See test plan",
     "Not covered"],
    ["Cold-start rate before and after (REPORT lines)", "See test plan", "Not covered"],
    ["Cost and latency for the 7 days before the deploy, to compare with after", "See test plan", "Not covered"],
    ["Guardrail block/allow parity; no chat-quality regression (verify suite)", "See test plan", "Not covered"],
])

doc.add_heading("Chat: one turn's cost and cache", level=1)
doc.add_paragraph("A class-overview question in Scout chat (thread ccb28eb0-…), one model call, no tools. The "
                  "turn.end event is stamped 12:38 PKT (07:38 UTC), about 2 minutes before the chat Lambda's "
                  "07:40:45 UTC deploy, so it ran on the previous image. That image already had the history cache "
                  "(c0ec9795, 27 Sep); it may not have had the 1 Oct constitution checkpoint (83ec2cc0).")
table([2.3, 3.4, 0.8], ["Check", "Observed", "Result"], [
    ["Cost matches the one price table",
     "2 × $2.20 + 416 × $11.00 + 26,669 × $0.22 + 1,058 × $2.75 per M tokens = $0.013357, exactly turn.end "
     "cost_usd", "PASS"],
    ["Prompt read from cache, little fresh input",
     "input 2, cache read 26,669, cache write 1,058 (the new message, written for the next turn)", "PASS"],
    ["Stage timings reported", "context 3.5 ms, model 7,334 ms, first text 7,177 ms", "PASS"],
    ["Student names kept out of the reply", "Pseudonyms only (Student KJPRFQ, Student KMTSQC, Student S73H4S)",
     "PASS"],
])

doc.add_heading("Deployed turns, last 24 hours (CloudWatch)", level=1)
doc.add_paragraph("Logs Insights over core_turn lines with outcome complete on swo-genai-pov-ai-assistant-v2-dev, "
                  "for the 24 hours before the run. The window spans the 07:40 UTC deploy, so it mixes the two "
                  "images. It's a snapshot, not the ticket's before/after figure.")
table([2.9, 2.8, 0.8], ["Measure", "Value", "Result"], [
    ["Completed turns", "191 (187 with the stage split)", "Pending"],
    ["Mean cost per turn", "$0.0233", "Pending"],
    ["First content p50 / p95", "4.97 s / 13.76 s", "Pending"],
    ["Total p50 / p95", "5.63 s / 24.41 s", "Pending"],
    ["Input-side tokens: cache read / uncached / cache write",
     "4,801,250 (82.2%) / 114,101 (2.0%) / 925,234 (15.8%); about 30.6k per turn", "Pending"],
])

doc.add_heading("Findings", level=1)
doc.add_heading("1. The guardrail scoping isn't implemented", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: one of the ticket's five scope items (and AC3) has no change behind it"],
    ["Steps", "Read the ONLINE-7526 commits in rag (9), and rag/lambdas/ai_assistant/src/core/loop.py build_request."],
    ["Expected", "A read of the guardrail's billed cost; if material, only the new teacher message and the model's "
                 "output checked, behind a declared gate with block/allow parity on the guardrail test cases."],
    ["Actual", "No commit touches the guardrail; there's no cost read or parity gate in experiments/cost_speed_7526. "
               "build_request (loop.py:220) still puts every message under guardrailConfig on every model call. "
               "guardContent is used only for threads holding ONLINE-6554 curriculum grants (loop.py:199)."],
    ["Scope note", "AC3 (\"parity holds\") is true only because nothing changed. Ask whether the cost was read and "
                   "judged not material, and where that is written."],
])
doc.add_heading("2. No measurement of deployed turns, before and after", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: scope item 1 and AC1 ask for figures from deployed turns"],
    ["Steps", "Read experiments/cost_speed_7526/GATE.md and RESULT.md."],
    ["Expected", "Per-stage timings, cold-start rate, cache hit rate and cost per turn from CloudWatch, then before "
                 "and after figures for cost per turn and p50/p95 latency."],
    ["Actual", "Gate G-7526 ran on local snapshots (ports 8061 / 8062) on a frozen 24-turn set: PASS, arm/control "
               "0.857 ($0.02458 → $0.02106 per turn, 40 matched turns; first-content p50 ×1.07, p95 ×0.885). No "
               "CloudWatch figures are in the repo; the first-load-latency.md handoff that f8ea9c5c cites isn't in it."],
    ["Scope note", "The local result is real. The 24-hour snapshot above shows the deployed fields now exist (187/191 "
                   "turns), so the before/after can be run with the queries in ONLINE-7526.md (tests 2 and 4)."],
])

doc.add_heading("Screenshots", level=1)
doc.add_heading("1. API and AWS checks", level=2)
image("01-api-and-aws-run.png", "ONLINE-7526-api-tests.sh with AWS_CHECKS=1: 17 pass, 0 fail, 2 skipped (no "
      "flag-off token; rate limit not run). Cropped above the first check to leave out the tester's AWS sign-in identity.")

doc.add_heading("Notes", level=1)
for text in (
    "The 240 checks that ship with the ticket pass on origin at cf63ca2c: check_daily_usage 17, check_history_cache 10, "
    "check_cache_layers 12, check_lazy_imports 5, check_telemetry 41, check_routes 155.",
    "Checked in the code on origin: no infra/caylent; no alb, cloudfront or ecs modules and no commented-out module "
    "blocks in infra/swo/main.tf; the local server's fixed user id 112233 is gone. terraform plan was not run.",
    "Today's row is consistent with the price table: its tokens priced at Sonnet rates come to $0.2988 against "
    "$0.2982 recorded, a gap that fits a few cheaper Haiku calls (thread titles).",
    "Observation: in the last 24 hours, the deployed mean cost per turn ($0.0233) is above the pre-ticket DEV mean "
    "the code cites ($0.017 at list price, about $0.0187 at the billed rates), and turns average about 30.6k "
    "input-side tokens, not the ticket's 12.3k. The turns differ, so this isn't a regression; it's why the "
    "before/after needs the same turn set or the same window type.",
    "Observation: infra/swo/output.txt (terraform show output, 4,187 lines) and infra/swo/changes.json are committed "
    "Terraform state dumps that still list the content-cache table and its alarms. Not in the ticket's list, but the "
    "same kind of dead weight.",
    "Observation: the class-overview reply names classes by id prefix (024253e6…, fd1a4c04…), not by name. That "
    "comes from the page's published data, not this ticket.",
    "Observation: the first version of the test script checked the table name content-cache, which never existed, "
    "so that check would have passed either way. It was fixed to the deployed name before the AWS run.",
    "Observation: the gate's thread T1 was blocked by the guardrail on every pass (\"What is the main idea of this "
    "article?\" on the US Government article, topic Political and Extremist Content, guardrail v12). Dev now runs v14; "
    "worth checking during the guardrail parity test.",
):
    doc.add_paragraph(text, style="List Bullet")
