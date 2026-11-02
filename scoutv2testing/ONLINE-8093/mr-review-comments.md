# ONLINE-8093 MR review comments

swo **!6354** at `41ace7e971`, rag **!101** at `de38e41b` (both `ONLINE-5385_scout_release_2`). Line numbers are at
those heads. Rows marked **(general)** don't sit on a changed line; post them as an overview comment.

Checks run at these heads: swo `test:ai-pins` 86/86, `__coreStream` 196/196, `__aiFetch` 18/18, `__coreAbandon`
19/19, `__actionRecordRetry` pass; rag `run_checks.sh` 110/110, top-level `check_*.py` all pass except
`check_route_errors.py`.

## Fixed since the last review (no comment needed)

| Was | Fixed by |
|---|---|
| Headline numbers had no committed gate or RESULT | rag `8d13dda6` (declared before rows) + `ce3e2f16` `experiments/integration_8093/RESULT.md`: 147 vs 132, G1 0/16, TTFT 1.197× |
| Prod ran the strict guardrail only (curriculum fix not in prod) | rag `de38e41b` `infra/swo/envs/prod.tfvars:53` |
| "Thinking off" covered only the planner and retitle | rag `ec5e9db5` `llm.py:157` (every `MODEL_FAST` call via `_request`) |
| Docs missed the migration, `guardrail_curriculum_enabled`, `core_legacy_threads` | swo `d5e30b9752` |

## rag !101

### Must answer before merge

| File:line | Comment |
|---|---|
| `lambdas/ai_assistant/src/core/guardrail_route.py:229` | Only the typed message is wrapped in `guardContent`. A saved shortcut's teacher-written instructions (`core/context/shortcut.py:135`, up to 1000 chars) sit in their own block, so they are never input-checked, and `route_ask` (`runtime.py:2284`) never shows them to the classifier. With the curriculum profile now on in prod (`prod.tfvars:53`), a benign typed ask plus a harmful shortcut can run under the relaxed profile. Include the shortcut text in the guarded and classified text, and add a must-block case. |
| `infra/swo/envs/prod.tfvars:53` | Turning this on publishes a **new** prod curriculum guardrail version that was never screened (the integration run used dev `u5k53i63fu9b` v4). Please screen the prod version against the must-block set after apply, or say why dev v4 stands in for it. |
| `infra/swo/modules/api-gateway/routes.tf:1-5` | Every unprefixed route is removed. Please confirm the deployed `NUXT_ENV_AI_URL` (Secrets Manager `swo/<env>/frontend-vue3`) ends in `/v3` in **prod** and dev, and that gateway access logs show no non-`/v3` traffic in the last 30 days. |
| `commands/migrate_legacy_threads_command.py:134` | No per-thread try/except around `saver.list` / `replay_rows` (134-162): one malformed checkpoint aborts the whole `--apply`, and every rerun stops at the same thread (reproduced: `AttributeError 'int' object has no attribute 'get'`). `--verify` crashes the same way. Catch per thread, count `failed`, list the ids, exit 1. |

### Should fix

| File:line | Comment |
|---|---|
| `experiments/integration_8093/RESULT.md:3` | The rows it cites (`../teacher_eval/runs/int-*.jsonl`) are gitignored (`experiments/teacher_eval/.gitignore:1`), and `../stack_review` (whose PLAN, manifest and scoring this run reuses) isn't committed. Nobody can re-score 147 vs 132 from the repo. Commit the rows (or say where they live) and the stack review harness. |
| `lambdas/ai_assistant/src/core/threads.py:666` | Thread titles call `client.converse` on `cfg.model_fast` directly, so `ec5e9db5`'s thinking-off in `llm._request` doesn't reach them; with a 40-token cap, Haiku 5.5 would think and return no title. Same for `core/context/relevance.py:199`. `decisions.md` #20 says fast-model calls never think. Add `thinking_off_fields` here or reword. |
| `lambdas/ai_assistant/src/core/threads.py:145` | `set_title` creates the listing row with `core='v2'` before the record writes `core_threads`. In that window a typed turn gets 409 `thread_is_v1`; if the record never lands the thread can't be typed into again and reopening is 404. Raise `thread_is_v1` only when `row.core != "v2"`. |
| **(general)** `threads.py:451-456` | A v1 listing row with no `core_legacy_threads` copy returns `success: true, messages: []` with no log, so any thread the migration skipped or failed on opens blank. Log a warning/metric, and consider `legacy_missing: true` for the UI. |
| `commands/migrate_legacy_threads_command.py:37-38` | `$match` then `$group` per chunk re-reads every checkpoint doc past `after` (blobs included): O(N × chunks), when only 67 of 15,001 checkpoint threads have a listing row. Drive it from `history_listing` (`core != "v2"`), or `$sort` before `$group`. |
| `commands/requirements.txt:21-28` | `langgraph*` is pinned but `langchain-core` isn't (a fresh install got 1.7.0; the gate's writer was 1.2.14), nor `langchain-pinecone` / `langchain-openai`, and the image uses plain `pip install`. `--verify` equality was only shown on the gate's versions. |
| `lambdas/ai_assistant/tests/check_route_errors.py:24` | Imports `src.services.database.models.search_index`, deleted by 967ba8a2 → `ModuleNotFoundError`. It and `check_throttle.py` are outside the `run_checks.sh` glob, so CI never runs them. Move to `tests/core/`. |
| `lambdas/ai_assistant/src/core/engines/plan_build.py:307` | If any paragraph matches `RUN_IN_STEP` ("Warm-up: Ask students…"), `_plain_steps` (256) never runs and the other plain paragraphs are lost. `"Lesson Plan:\n\nWarm-up: Ask students …\n\nDiscuss the article."` → 1 step. |
| `infra/swo/modules/lambda-container/outputs.tf:6` | Nothing routes to `stable-v3` any more; every route is on `development` (`$LATEST`). `promote_assistant_to_stable`, `update_stable_alias` and `deploy.sh --promote` no longer change what's served, so prod gateway traffic has no rollback lever. Point the `/v3` routes at `stable-v3`, or retire the alias. |
| `README.md:56` | "deploy:prod … also promotes the v1 routes" is no longer true (see `outputs.tf:6`). |
| `infra/swo/README.md:125,128,147` | stable-v3 promote/rollback sections are stale for the same reason. |
| `experiments/teacher_eval/MEASURED-AND-FAILED.md:2991` | Cites `swo 9e3f40c989`, which exists in neither repo (also `9e3f40c9` at 2932). |
| `experiments/teacher_eval/MEASURED-AND-FAILED.md:2895` | `bold_terms` copies `required_terms`' result and `vocab_terms_5385`'s commits; its own are `e32a57a3`, `cbb8f9b5`. |
| `experiments/teacher_eval/MEASURED-AND-FAILED.md:2980` | `rubric_7754` repeats `rubric_add_7754`; its only commit is `0ed2f44e`. |
| `lambdas/ai_assistant/README.md:56` | Images install from `uv.lock` (`uv export --frozen`), not `pyproject.toml`; mention `checks:uv_lock`. |
| `lambdas/ai_assistant/tests/README.md:24` | "the checkpointer is Mongo": there is no checkpointer now. |

### Nits

| File:line | Comment |
|---|---|
| `lambdas/authorizer/src/services/policy_generator.py:57-59` | Dead patterns for `/v3/adapt`, `/adapt`, `/v3/generate`. |
| `lambdas/ai_assistant/src/core/threads.py:410` | `running_turn_id` has no timestamp; a turn killed by the Lambda timeout leaves every record 409ing until the next typed turn ends. Store `running_at`. |
| `commands/legacy_replay.py:401-402` | Repeats 397-398. |
| `experiments/teacher_eval/MEASURED-AND-FAILED.md:2913-2914` | `envsweep` and `envv1purge` are identical; own commits `621b2cf9` / `6a51ec13`. |
| `experiments/lesson_pack_7761b/pack.py:141` | Imports `run_gate` from the deleted `lesson_pack_7761/`. |
| `lambdas/ai_assistant/src/core/guardrail_route.py:126` | Comment says "five-token cap"; it is 16. |
| `commands/ai_sync_command.py:731` | `--dry-run` prints "Prune refused", which would trip the `content-prune-refused` alarm if run as the ECS task. |
| `lambdas/ai_assistant/src/routers/assistant_router.py:104` | Request id only in `x-request-id`, not in CORS `expose_headers`; the browser can't read it. Put it in the body. |
| `infra/swo/variables.tf` | CRLF→LF shows ±565 lines; the real change is 5 comment lines. |
| **(general)** | Against `prod-infrastructure` this MR also carries ONLINE-7857, 5385, 7494, 7854, 7761 commits. Intended? |

## swo !6354

### Should fix

| File:line | Comment |
|---|---|
| `backend/app/Http/Middleware/EnforceSingleActiveSession.php:40` | Every `api/ai/*` path skips the single-session check for Scout-flagged users, so a superseded device can still call `alias-roster` / `alias-key` (real student names), `actions/*/confirm`/`undo`, `admin/exports/*`. rag calls about 12 paths; allowlist those and add a `ScoutServiceSessionTest` case that `alias-roster` is still superseded. |
| `backend/app/Http/Requests/Ai/UpdateAiActionRequest.php:19` | `params` has no size cap, so ONLINE-8054 doesn't cover `PATCH actions/{id}`. Add `JsonMaxSize` and an `AiPayloadSizeLimitTest` case. |
| `backend/app/Models/User.php:3372` | `hasStaffEmail()` grants the $10 cap on the email domain alone; also require `email_verified_at`. |
| `frontend-v3/ai/services/retryOnConflict.ts:1` | `[300, 900, 2000]` gives up after ~3.2 s, but a typed turn holds the thread 10-60 s. A chip pressed during a typed turn loses its record (`useAiActionRecord.ts:160` swallows it), and after reload the action is missing. Wait for the in-flight turn's `turn.end`, or retry to the turn ceiling. |
| `frontend-v3/ai/composables/useAiActionRecord.ts:120` | Titling before recording opens rag's `thread_is_v1` window. The record path now creates the listing row (`ensure_listing`), so record first; the "title first" comment at 39-44 is obsolete. |
| `frontend-v3/ai/composables/useAiThreads.ts:384` | `adminCanContinue = false` is set before the replay arrives and stays false if it fails, so an admin who types while a thread loads (the composer isn't disabled) or after a failed load gets a new chat via `useAiChat.ts:2362` without being told. Set it only from the replay, or disable send while `isLoadingThread`. |
| `frontend-v3/scripts/check-core-events.mjs:21` | Reads `docs/ScoutCoreV2.md`, deleted by this MR → ENOENT. Point at the new docs or retire it. |
| `frontend-v3/scripts/run-ai-pins.mjs:14` | `ai/services/__aiConfigUrl.verify.ts` (27/27 pass) was dropped and isn't in the stale list; the new `__aiFetch`, `__coreAbandon`, `__actionRecordRetry`, plus `__coreStream`'s new cases, aren't in SUITES. |
| `frontend-v3/scripts/run-ai-pins.mjs:34` | One hard-coded vite-node config; `__aiFetch` and `__coreAbandon` need `ai/services/__verify/vite-node.config.ts`. |
| `docs/scout/deploy-and-environments.md:78` | "Fill it once … **after** the rag release": every old chat opens blank between the deploy and the migration. The order should be: rebuild the commands image; dry run; `--apply` **before** the rag image ships; deploy rag before or with swo; `--apply` again for threads written in between; `--verify`; don't drop `checkpoints` until `--verify` is clean in prod. Also explain the `ownerless` / `conflict` counters, and that chip threads created before the deploy stay v1. |
| `docs/scout/deploy-and-environments.md:72` | "default off … Production needs it on": both tfvars now set it (rag `de38e41b`). Say it is on in dev and prod, and that the classifier is pinned to Haiku 4.5. |
| `docs/scout/deploy-and-environments.md:69` | Variables are in `infra/swo/variables.tf` / `variables_scout_core_v2.tf` and `envs/<env>.tfvars`, not `modules/scout-core-v2/main.tf`; spend caps are code constants, not Terraform. |
| `docs/scout/deploy-and-environments.md:39` | `--promote` no longer affects any route (see rag `outputs.tf:6`). |
| `docs/scout/deploy-and-environments.md:36` | Add `checks:uv_lock`; Python is 3.13. |
| `docs/scout/decisions.md:84` | Add what is no longer input-checked: only typed text is; shortcut instructions, article, history and tool results aren't; output always is; form/chip/approval turns check everything. |
| `docs/scout/decisions.md:88` | "Fast-model calls never think" isn't true for titles and relevance (rag `threads.py:666`, `relevance.py:199`). |
| `docs/scout/research/security-and-privacy/prod-readiness-privacy-2026-10-02.md:15-17` | Points at the exact commit/path of an unrotated live OpenAI key and old Mongo/Pinecone values. Confirm rotation before merge, or drop the pointer. |
| `docs/scout/research/index.md:6` | "names of real people are redacted" is false ("Salman" ~1,130 times, `/Users/salman` paths, other staff names). Redact or correct. |
| `docs/scout/README.md:37-38` | Admins aren't checked via `user/credits` (teacher-only, 404 for admins): admin Scout is `/assistant/v2/admin/turn` against `api/ai/admin/context`. Document the admin door, its throttle (10/100/600), ONLINE-7806's "Insights starts a new chat", and list the Function URL routes. |
| `docs/scout/README.md:48` | `/generate-from-topic` is no longer on the gateway; it's `/v2/generate-from-topic` on the Function URL. |
| `docs/scout/troubleshooting.md:10` | Add the admin `scout_off` case (`admin/context` 403/404) and the new "I couldn't find that conversation." (`not_found`). |
| `docs/scout/troubleshooting.md:13` | Caps are constants in `daily_usage_service.py` ($10/wk staff via `raised_spend_cap`); throttles `utils/throttle.py`; in-flight `too_many_turns`. Add 409 (record conflict), 422 (payload size) and the swo per-route 429. |
| `docs/scout/add-a-capability.md:15` | `capability()` is a type helper and registers nothing; registration is `useAiSurface({capabilities})` or `defineCapability()`. |
| `docs/scout/content-and-index.md:10` | rag `docs/ContentPipelineFlow.md` still exists on the branch; point at it, not the archive tag. |
| `docs/scout/content-and-index.md:34` | Only an import queues an export; an edit waits for the Sunday 03:00 full export. |
| `docs/scout/content-and-index.md:39` | The `content-prune-refused` alarm exists; document `--force-large-prune`. |
| `docs/scout/local-setup.md:8` | `https://localhost:3002/beta/`. |
| `docs/scout/local-setup.md:15` | `E2ePlannerSeeder` doesn't set `FEATURE_FRONTEND_AI_ASSISTED_GRADING`; give the seed command. |
| `docs/scout/decisions.md:50` | `outline.ts` says 82 of 183 exceed / 101 fit, not "102 of 183". |
| **(general)** | Not documented: student aliases and name scrub; the chat-search reveal (ONLINE-8027) and Insights continue rule (ONLINE-7806). |

### Nits

| File:line | Comment |
|---|---|
| `docs/scout/decisions.md:8,20,28` | Real first name. |
| `docs/CustomLessonPlan.md:14,16,114` | `/Users/salman/...` paths. |
| `docs/scout/local-setup.md:41` | `yarn dev` → `bun run dev`. |
| `docs/scout/onboarding/README.md:9` | Doesn't say how the snapshots were made; the deck has 14 slides, `prompts/onboarding-deck.md:7` asks 10-12. The deck and explorer predate `d5e30b9752` (no migration or guardrail setting). |
| `docs/scout/research/index.md:10` | Names the old `ONLINE-8093_scout_cleanup` branch. |
| `frontend-v3/ai/services/aiHttp.ts:116` | 90 s default now caps generate-from-topic (Lambda 210 s); confirm p99 < 90 s. |
| **(general)** | Commit subjects are capitalised and very long with no body (convention: `ONLINE-####: lowercase`, body for why). `AGENTS.md`, `.cursor`, `.windsurf` edited in a feature commit. |
