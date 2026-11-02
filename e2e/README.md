# ldc/e2e

Playwright checks for QA tickets, run against a deployed environment (dev2 by default). Kept outside `swo-3.0` and
`rag` on purpose. Same tool and version as `swo-3.0/e2e` (`@playwright/test` 1.63.0); rag has no browser tests.
Selectors come from frontend-v3 (`aria-label`s and `data-cy`), the same ones `swo-3.0/e2e/pages` uses.

## Run

```bash
cp .env.example .env        # fill in accounts and, for the rag checks, the two URLs from the Network tab
./run.sh --project=api      # HTTP checks only: no browser, no Scout credits
./run.sh --project=ui       # browser checks; real Scout turns only with E2E_AI_TURNS=1
./run.sh --grep '#12'       # one test case
```

`run.sh` runs inside `mcr.microsoft.com/playwright:v1.63.0-noble`, so the host needs only Docker. Results:
`results/html/index.html` (traces of failures), `results/junit.xml`.

- **Use dedicated QA accounts.** Signing in through `auth/login` signs the same account out of any browser that is
  using it (one active session per user).
- Never commit `.env`. Tests skip, with the reason, when an account or input they need isn't set.
- The rag checks pause 13 s between calls: the throttle counts refused requests too.

## ONLINE-8093 coverage (`tests/online-8093`, cases from `~/ldc/scoutv2testing/ONLINE-8093/ONLINE-8093.md`)

| Case | Spec | Needs | Credits |
|---|---|---|---|
| 1, 3, 9 plain turn, one title, no student name, no "K-12" | `ui-teacher-scout` | teacher | yes |
| 2 sidebar through `/v3`, no gateway errors | `ui-teacher-scout`, `api-rag` | teacher, `E2E_GW_URL` | no |
| 4 history article not stopped by the content check | `ui-teacher-scout` | `E2E_HISTORY_ARTICLE_PATH` | yes |
| 10 chip-started chat continued by typing | `ui-teacher-scout` | `E2E_CHIP_LABEL`, `E2E_CHIP_PAGE_PATH` | yes |
| 12 old chat opens with messages (migration ran) | `ui-teacher-scout` | `E2E_LEGACY_THREAD_TITLE` | no |
| 14 chat from search revealed in the sidebar | `ui-teacher-scout` | `E2E_SEARCH_TERM` | no |
| 15 Stop before the first token | `ui-teacher-scout` | teacher | yes |
| 16, 17 district / school Insights + admin door | `ui-admin-insights` | admin accounts | the ask only |
| 18 reopened chat admin can't continue starts a new chat | `ui-admin-insights` | admin with an earlier chat | yes |
| 20 teacher on the admin door → 403 `scout_off` | `api-rag` | teacher, `E2E_CORE_URL` | no |
| 21 credits per role; admin/context per role | `api-laravel` | each role | no |
| 22 flag off → 404 | `api-laravel` | no-flag teacher | no |
| 23 ten removed Laravel routes, removed gateway routes → 404 | `api-laravel`, `api-rag` | teacher, `E2E_GW_URL` | no |
| 24 Function URL: no token 401, outside `/assistant/v2/` 404 | `api-rag` | `E2E_CORE_URL` | no |
| 26 stats over 512 KB → 422 | `api-laravel` | teacher | no |

Left to manual testing (ONLINE-8093.md): 5-8 guardrail and plan-parsing content checks, 11 chip during a typed turn,
13 old chip thread, 19 exports, 25 throttles, 27 single session, 28 fixed apology, 29 docs walk-through.
