# scoutv2testing

QA testing of Scout v2 (SWO AI assistant) tickets on dev2. One folder per ticket. **`ONLINE-7532/` is the
reference: every new ticket copies its file set, section order and document format exactly.** Don't change the
format of an existing ticket's files, and don't restyle `ONLINE-7532/`.

To make test cases for a new ticket, use the `ticket-testing` skill (`~/.claude/skills/ticket-testing/SKILL.md`).

## Folder layout (per ticket)

```
make_test_results_docx.py      shared .docx builder: styles, colours, helpers (run with the ticket name)
<TICKET>/
  <TICKET>.md                  explanation + Mermaid diagrams + test plan; later dev2 results, findings, file index
  <TICKET>-api-tests.sh        API checks the tester runs with their own token (status AND message checked)
  <TICKET>-test-results.docx   report attached to Jira, built by ../make_test_results_docx.py <TICKET>
  report_content.py            this ticket's report content (a copy of ONLINE-7532's, content replaced)
  jira-comment.md              comment to paste, in Jira wiki markup
  screenshots/                 NN-short-slug.png, numbered in the order the report shows them
```

The `.md` and `-api-tests.sh` come first (planning). The `.docx`, `jira-comment.md`, `screenshots/` and the
results sections of the `.md` are added once the tester sends results.

## Environment

| What | Where |
|---|---|
| Frontend (Vue 3) | `https://dev2-online.studiesweekly.com/beta/` |
| Laravel API | `https://dev2-online-api.studiesweekly.com/api/...` |
| rag (ai_assistant) | A Lambda URL, `https://<id>.lambda-url.us-west-2.on.aws/assistant/...?host=dev2-online.studiesweekly.com`. Copy it from the Network tab; it changes per deploy |
| Code | `/home/lenovo/swo-3.0` (frontend-v3, backend) and `/home/lenovo/rag`, branch `ONLINE-5385_scout_ai_integration` |

## Rules learned on ONLINE-7532

- **Never run requests with the tester's token.** Claude Code's auto mode refuses it, and it's their live session.
  Write the script; the tester runs it in their own terminal with `export SWO_TOKEN=…`.
- **Check the response message, not only the status.** A wrong URL returned 422 for a different reason and
  "passed" 7 checks. Guard each URL (e.g. require `/v2/<route>` in `RAG_URL`).
- **rag's rate limit counts invalid requests too.** Pause between rag calls (13 s for a 5-per-minute limit).
- **The deployed rag parses every body first:** a non-JSON body is `400 invalid_body` on dev2, not the router's 422.
- **Confirm a defect in the code before logging it** (file:line or commit), and name the layer: is it this ticket
  or a neighbouring feature?
- **Report only what the evidence shows.** Use Pass / Partial / Not run per test case. A screenshot showing a
  button isn't proof its behaviour works. If two screenshots are identical (same md5), include it once and say so.
- **Findings** get severity (low / medium / high), steps, expected, actual, and the cause if known.
  Observations (not failures) go in their own list.
- Node isn't installed. Build the `.docx` with
  `uv run --no-project --with python-docx python make_test_results_docx.py <TICKET>` from this folder. LibreOffice isn't installed either, so
  ask the tester to look through the `.docx` in Word once.
- In `jira-comment.md`, use Jira markup: `*bold*`, `_italic_`, `{{code}}`, `*` bullets, `#` numbered lists.
  Never use Markdown `**bold**`.
- A `~$…docx` file next to a report is Word's lock file (the tester has it open). Leave it alone.
- **Crop identity out of terminal screenshots** before they go in a report: `aws sts get-caller-identity` prints the
  tester's SSO email and the account id. Crop from the original with Pillow (`uv run --no-project --with pillow`), so
  no result lines are lost; a tester's own crop can cut off the bottom (ONLINE-7526).

## Tickets

| Ticket | Feature | Status |
|---|---|---|
| ONLINE-7532 | Suggest standards for a teacher's own questions (page + chat) | Tested 2026-09-30: UI 6/6, API 15/15, chat 8 checks; 3 findings; 403s, flag-off and the 35-question run not yet covered |
| ONLINE-7525 | Shared Bedrock response cache, cost meter and batch helper for eval harnesses (rag `experiments/_shared`, no UI) | Planned 2026-09-30: 16 test cases; offline checks 30/30 pass. 2026-10-01: `ONLINE-7525-smoke-tests.sh` (no API, so it replaces -api-tests.sh) offline 10 pass / 1 fail (T12, AC2: 33 scripts not on the cache); live run 18 pass / 1 fail (T12), ~$0.00015; report (.docx, 11 tables incl. a per-check list of the developer scripts, no screenshots) and jira-comment.md written; 4 findings; T11/T13/T16 not run; T14 blocked: no Bedrock batch role or prefix in dev (checked read-only with swo-admin), Sonnet 5 shows no batch quotas |
| ONLINE-7526 | Scout cost and speed: daily cap in dollars ($5), conversation-history prompt caching, stage timings, lazy imports, dead-weight removal (rag only, no UI change) | Planned 2026-10-01: 23 test cases; developer checks 240/240 on origin `cf63ca2c`. Tested 2026-10-01 on dev2: API + AWS script 17/0/2 (content-cache table and alarms gone, daily table kept, $ + cached tokens in the row, stage split on 187/191 turns); one turn.end matches the price table exactly (pre-deploy image); report (.docx, 9 tables, 1 screenshot) and jira-comment.md written; 2 findings (guardrail scoping not built; no deployed before/after). Not covered: $5 refusal (needs a row write), throttle, turns 2-4, before window, cold-start rate, guardrail parity, verify suite |
| ONLINE-7528 | Page switches stop re-paying Scout's cached prompt: `page_action`'s per-page enum removed so the tools cache holds across pages (rag only, `00e330ce`; no UI change) | Planned 2026-10-01: 15 test cases; `check_tool_registry` 99/99 and `check_context` 244/244 pass locally on `cf63ca2c`; gate G-7528-v2 PASS (cost 0.746, accuracy 12/16 vs 12/16, 0 not-offered). Tested 2026-10-01 on dev2 (CloudWatch + 4 screenshots): 6/6 page switches read 17,685 cached tokens (old code 0); mean $0.0320 vs est. old $0.0767 (0.42×); actions: image dialog, week 5, briefing ran, locked question correctly refused, reader mode pending (which tab); nothing not-offered ran (deleteAll blocked by guardrail, not rag's check); report (.docx, 5 tables, 4 screenshots) and jira-comment.md written; 0 findings. `cache_*_h` hashes are in Mongo `tokenz` only. Not covered: previous page's action on People, harmless wrong id, Plan mode, confirm preview, nav question, measured old-code baseline, AC4 checks on deployed commit |
| ONLINE-8093 | Scout release 2 on `ONLINE-5385_scout_release_2` (swo !6354 `41ace7e971`, rag !101 `de38e41b`): cleanup, guardrail teacher-text only + curriculum profile (dev and prod), write_artifact plain plans + K–8, LangChain removal + legacy-thread migration, fast model thinking off, round 2 tech debt | Planned 2026-10-26: 29 test cases (teacher, district admin, school admin); `ONLINE-8093-api-tests.sh` (26 Laravel/gateway/Function URL checks, read-only, not yet run); `mr-review-comments.md` (file:line comments for both MRs); Playwright suite in `~/ldc/e2e` (32 tests: 19 API, 13 UI; typechecks; credential-free run 1 pass, 18 skip). Developer checks at the heads: swo pins 86/86, rag core 110/110, top-level all but `check_route_errors.py`.. Tested 2026-10-26 on the LOCAL stack (utteacher/utdistrictadmin/utschooladmin, Playwright): UI 11/11, API 14/15 (utdistrictadmin is also a teacher); 0 findings, 3 observations; report (.docx, 4 tables, 10 screenshots) and jira-comment.md written. Needed FEATURE_FRONTEND_AI_ADMIN_ASSISTANT in backend/.env and one manual queue:work for Insights figures. Not covered: gateway/Function URL checks (dev only), flag-off, old v1 chats, chip, manual cases |
| SCOUT-RELEASE-2 | All tickets on `ONLINE-5385_scout_release_2` (swo !6354 `f556f63883`, rag !101 `24e95372`): ONLINE-5385, 7494, 7761, 7767, 7806, 7854, 7857, 7970, 8027, 8050–8064, 8093, 8095 | Tested 2026-10-28 on the LOCAL stack with the dev guardrails (strict v16 + curriculum v4 on a second rag at :8003), Playwright `~/ldc/e2e/tests/release2` (30 tests) + rag run_checks 113/113 + lock checks; report `SCOUT-RELEASE-2-test-results.docx` (13 tables, 39 screenshots by ticket). 8 findings: slides on a war article blocked (classifier OTHER → strict, topic:Violence), lesson pack drops plan / worksheet fails, rename race 500 (pre-existing), T2 typed answer not replayed, Hot Text parked vs ticket, 8062 check deleted, 8058 check dead, lesson-plan ask → weekly plan. Not covered: 8095 (no data), 7857 (no usage table), 7494, 8050 drift, T4/T8/T9/T11/T13, flag-off |
