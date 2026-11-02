*QA: ONLINE-7526 (Scout cost and speed), dev2, teacher account with the AI flag on, AWS read access to dev (us-west-2)*

*API (chat and thread listing):* PASS 8/8
* Chat <kbd>POST /assistant/v2/turn</kbd>: 401 <kbd>not_signed_in</kbd>for a guest; a blank message from the teacher gets 400 _"Message cannot be empty."_, so the request passed the daily-cap and rate-limit checks without a model call.
* Thread listing <kbd>POST /v3/assistant/thread/listing</kbd>: 401 for a guest; 200 for the teacher, with no internal <kbd>_usage</kbd>or <kbd>cost_microusd</kbd>in the response. First call 5.17 s (likely a cold start: a guest 401 takes 0.87 s on the same path), then 1.00 s.

*AWS, read-only:* PASS 9/9
* The content-cache table <kbd>swo-genai-pov-content-cache-dev</kbd>and its alarms are gone. <kbd>swo-ai-daily-usage</kbd>is kept (created 2026-01-09, so moved, not recreated).
* Both Lambdas point at <kbd>swo-ai-daily-usage</kbd>and have no cap or cache-table env var: the $5 cap is set only in code ( <kbd> DAILY_COST_LIMIT_USD = 5.0 </kbd>).
* Today's daily row holds dollars and all four token counts: $0.298217; input 342, output 2,761, cache read 342,021, cache write 69,982. Priced at Sonnet rates those tokens come to $0.2988, which fits a few cheaper Haiku calls.
* CloudWatch: 187 of 191 completed turns in the last 24 h log the stage split (<kbd>model_ms</kbd>, <kbd>tools_ms</kbd>, …). Snapshot: mean $0.0233 per turn, first content p50 4.97 s / p95 13.76 s, total p50 5.63 s / p95 24.41 s; cache reads are 82% of input-side tokens, uncached input 2%.

*Chat turn:* PASS 4/4
* One class-overview turn: <kbd>cost_usd</kbd>$0.013357 matches the price table exactly (2 input, 416 output, 26,669 cache read, 1,058 cache write); only 2 tokens billed at the full input rate; stage timings in <kbd>turn.end</kbd>; students shown as pseudonyms only. The turn ran about 2 minutes before the 07:40 UTC deploy, on the previous image (history caching was already in it).

*Developer checks:* PASS 240/240 (<kbd>check_daily_usage</kbd>17, <kbd>check_history_cache</kbd>10, <kbd>check_cache_layers</kbd>12, <kbd>check_lazy_imports</kbd>5, <kbd>check_telemetry</kbd>41, <kbd>check_routes</kbd>155, on origin <kbd>cf63ca2c</kbd>). In the code: <kbd>infra/caylent</kbd>, the alb/cloudfront/ecs modules and the local server's fixed user <kbd>112233</kbd>are gone.

*Findings:*

**The guardrail scoping isn't implemented (medium, scope item 4 / AC3).**
 No ONLINE-7526 commit touches the guardrail and there's no cost read or parity gate. <kbd>loop.py:220</kbd>still puts every message under <kbd>guardrailConfig</kbd>on every model call. AC3 holds only because nothing changed.

**No measurement of deployed turns, before and after (medium, scope item 1 / AC1).**
 Gate G-7526 ran on local snapshots: PASS, cost per turn 0.857 of control ($0.02458 → $0.02106, 40 turns; first-content p50 ×1.07, p95 ×0.885). There are no CloudWatch before/after figures in the repo, and the <kbd>first-load-latency.md</kbd>that <kbd>f8ea9c5c</kbd>cites isn't in it.

*Not covered yet:* the 429 at $5 on chat and gateway (needs a write to the tester's own daily row); one request just under the cap; the 10-a-minute chat rate limit; flag-off teacher; a single turn's exact increment on the daily row; turns 2–4 reading the history from cache and a 6-minute gap; cold-start rate and the 7-days-before window; guardrail parity; the verify suite.

*Observations (not failures):*
* Deployed turns average about 30.6k input-side tokens and $0.0233, above the ticket's 12.3k and the pre-ticket $0.017 (≈ $0.0187 at billed rates). The turns differ, so this isn't a regression, but the before/after needs comparable windows.
* <kbd>infra/swo/output.txt</kbd>and <kbd>changes.json</kbd>are committed Terraform state dumps that still list the deleted table: the same kind of dead weight.
* The class-overview reply names classes by id prefix (<kbd>024253e6…</kbd>), not by name. That comes from the page's data, not this ticket.
* The gate's T1 ask (_"What is the main idea of this article?"_ on the US Government article) was blocked by the guardrail on every pass (v12). Dev runs v14 now.

Details and screenshot (1) in the attached *ONLINE-7526-test-results.docx*.
