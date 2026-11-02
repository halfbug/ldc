# Task: extract `infra/` into `rag-infra`, delete the authorizer Lambda, move API Gateway to a Cognito JWT authorizer

Three changes in one pass, by explicit user decision. Every fact below was verified
against `/home/lenovo/rag` on branch `ONLINE-6857-v2-14-testing-feedback` (clean
tree, 423 commits). Do not re-derive it; do verify anything you depend on.

⚠️ **Scope warning, stated once and then accepted.** This PR both moves a repo and
changes production authentication. Those are independently risky and normally ship
separately. The user chose to combine them. Proceed — but keep the two concerns in
**separate commits** so a reviewer can read them apart, and never let a "make the
split work" edit quietly change auth behaviour.

## Hard constraints — read before touching anything

1. **Never run `git filter-repo` inside `/home/lenovo/rag`.** Work only on a fresh
   clone. It rewrites history in place and there is no undo.
2. **Never force-push. Never push to `origin` or `ver2` at all.** `rag` has two
   remotes (`origin` = gitlab `sw6/ops/rag`, `ver2` = github
   `halfbug/assistant-aws`). This task ends with a *local* `rag-infra` and a *local*
   branch on `rag`. A human pushes.
3. **Never rewrite `rag`'s shared history** — the secret commit is on 11 local and 24
   remote branches across both remotes. See Phase 0.
4. **No AWS mutations.** No `make apply` / `plan` / `bootstrap`, no `terraform
   apply`, nothing under `scripts/deploy-image.sh`, `apply-lambda.sh`,
   `promote-to-stable.sh`. `terraform init -backend=false` and `terraform validate`
   are allowed. Do not create the Cognito pool, touch SSM, ECR, or Lambda.
5. **Do not rotate or print secret values.** Count occurrences if you must confirm
   one exists.
6. Branch off the current branch, never `master`/`main`. Commits:
   `ONLINE-####: <lowercase summary>`, body explains *why* and what was rejected.
   **No AI attribution in commits on this workstream.**
7. Do not refactor surrounding code to current style. Note that
   `infra/swo/main.tf:389` carries a comment explicitly citing this rule about the
   dashboard's name-derived variables — respect it.

## Context

- `infra/` is 161 tracked files: `infra/swo` (live) and `infra/caylent` (stale —
  `main.tf:72` points at `../lambdas/authorizer`, which resolves to the nonexistent
  `infra/lambdas`).
- **State is remote** (S3 backend, `infra/swo/versions.tf`; bucket injected at init
  by `scripts/init.sh:33` as `swo-genai-pov-$ACCOUNT_ID-$ENV-infra`). Moving the
  directory does not move or endanger state. This is why the split is safe.
- **CI is a stub** — `.gitlab-ci.yml` is entirely commented out. Nothing to rewire.
- Each environment has its **own** copy of `modules/lambda-zip`
  (`infra/swo/modules/lambda-zip` and `infra/caylent/modules/lambda-zip`), so
  deleting swo's copy cannot affect caylent. Verified.

## Phase 0 — HUMAN preconditions

Report these; do not attempt them. **Two are genuine blockers for the auth half**
(the split half can proceed regardless).

### 0a. Rotate the leaked secrets — blocking, security

`infra/swo/errored.tfstate` is **tracked in HEAD** (commit `21b73c9`, blob
`82917c9f7344375bfaa6ba9c84b64fadd7db947d`), despite `.gitignore` listing it —
gitignore never untracks what is already indexed. 344 KB, 88 resources, 1
`aws_ssm_parameter`, **3 `SecureString` values in plaintext**.

Reachable from 11 local and 24 remote branches on two remotes. Therefore:
**rotating the 3 values is the only action that reduces exposure**, and it needs no
history rewrite. A full `rag` history rewrite is a separate team-coordinated event
(every clone invalidated) — do not attempt it, do not block on it. Phase 1 drops the
blob from `rag-infra` anyway, so the new repo is clean from birth.

### 0b. There is no Cognito token source yet — blocking, functional

`swo-3.0/frontend-v3/ai/services/aiHttp.ts:76` sends
`authStore.state.access_token` — the **Laravel-issued** JWT. A Cognito User Pool JWT
authorizer validates only tokens minted by that pool (`iss` = the pool, `aud` = the
client id). **A Laravel JWT will be rejected with a 401 at the gateway.**

So the moment the JWT authorizer goes live, every AI request fails unless Cognito
tokens are already flowing. Someone must first decide: Laravel logins federate into
Cognito, the frontend acquires a Cognito token alongside the Laravel one, or the pool
issues tokens some third way. **Do not invent this.** Write the Terraform so the
issuer/audience are variables (Phase 2), and state in your report that the cutover
is gated on 0b.

### 0c. Credit metering loses its home — blocking, functional

The authorizer does *two* jobs and Cognito replaces only one:

| Job | Where | Cognito? |
|---|---|---|
| Validate the JWT | `lambdas/authorizer/src/services/auth_service.py`, `utils/jwt_utils.py` | ✅ replaced |
| Fetch the user's credit balance from Laravel and inject it into the request context | `services/credits_service.py:42-56`, `services/response_builder.py:44,76` | ❌ **no replacement** |

A JWT authorizer cannot call Laravel and cannot inject `credits`. Note that
`lambdas/ai_assistant/src/services/credits_service.py` does **not** help — it prices
token usage from `bedrock_pricing.json`; it never calls Laravel. Verified.

The balance check must move into the assistant Lambda (a new Laravel call on the
request path, with its own latency and failure mode) or be dropped. That is a
product decision. Phase 3 step 3 implements the *mechanical* part only and leaves a
loud `TODO(ONLINE-####)` where the balance check belonged.

## Phase 1 — create `rag-infra` with history, minus the secret

Target layout: **hoist** `infra/swo` → `rag-infra/swo` (not
`rag-infra/infra/swo`). Safe because every path inside infra is file-relative; the
only escaping paths are being rewritten anyway. It also preserves depth:
`../../lambdas` from `rag/infra/swo/` ≡ `../../rag/lambdas` from `rag-infra/swo/`,
given sibling checkouts under `/home/lenovo`.

1. Install filter-repo (absent; `bfg` also absent): `uv tool install git-filter-repo`,
   else `pip install --user git-filter-repo`. Verify `git filter-repo --version`.
   *(Unverified — if both fail, stop and report. Do not fall back to `git subtree
   split`, which cannot drop the blob in the same pass.)*
2. `git clone --no-local /home/lenovo/rag /home/lenovo/rag-infra`
   (`--no-local` gives a real object copy, not hardlinks into `rag/.git`.)
3. In the clone only: `git remote remove origin && git remote remove ver2` — belt
   and braces against constraint 2.
4. Rewrite in **two passes** (one pass cannot do this: `--invert-paths` applies to
   the whole invocation, so mixing keep- and drop-paths inverts your intent):
   - Pass A, keep and hoist: `git filter-repo --path infra --path-rename infra/:`
   - Pass B, drop the state file (**post-hoist** path):
     `git filter-repo --path swo/errored.tfstate --invert-paths --force`
   Before Pass B, confirm `git cat-file -e HEAD:swo/errored.tfstate` succeeds —
   filter-repo silently no-ops on a non-matching path and you would not notice
   until verify.
5. Verify: `git ls-files | wc -l` → **160**;
   `git rev-list --all --objects | grep -ci tfstate` → **0**;
   `git log --oneline | wc -l` → ≈128. (56 of those commits also touched
   `lambdas/`, so their messages describe changes only partly present. Expected —
   do not reword history.)
6. **Write `rag-infra/.gitignore`** — the new repo inherits nothing. Port the
   Terraform and lambda-package sections from `rag/.gitignore`, adjusting hoisted
   paths (`!infra/terraform.tfvars.example` → `!terraform.tfvars.example`). The
   `**/*.tfstate` and `**/*.tfstate.*` globs are **mandatory** — their absence is
   exactly how `errored.tfstate` got committed. Keep the explanatory comment; it
   records the incident. Carry `**/CLAUDE.md` too.

`caylent/` comes along as-is. Do not fix or delete it — flag it and let the user
decide.

Commit this as the split, alone.

## Phase 2 — `rag-infra`: remove the authorizer, wire Cognito

Separate commit from Phase 1. Terraform ends up with **zero** dependency on `rag`
lambda *source* — the authorizer was the only one. Only the three container build
contexts remain, and those are shell-only.

### 2a. Delete the Lambda authorizer

- `swo/main.tf:133-152` — delete `module "authorizer_lambda"` entirely (the block
  starting at `:133`; `source_path = "../../lambdas/authorizer"` was at `:137`).
- `swo/main.tf:370-373` — delete the `authorizer_lambda = { invoke_arn,
  function_name, function_arn }` block passed to `module.api_gateway`.
- `swo/main.tf:380` — remove `module.authorizer_lambda` from `depends_on`.
- `swo/main.tf:389` — remove `authorizer_lambda_name` from
  `module.cloudwatch_dashboard`, **and remove the widget that consumes it** in
  `swo/modules/cloudwatch-dashboard/`. ⚠️ Read the comment at `main.tf:389` first:
  it says a dashboard silently watching a function name nothing creates "is the
  failure this whole change is fixing." Deleting the Lambda but leaving the widget
  recreates precisely that bug.
- `swo/modules/api-gateway/variables.tf` — remove the `authorizer_lambda` variable.
- `swo/modules/api-gateway/lambda_permissions.tf` — remove the authorizer's
  `aws_lambda_permission`.
- **Delete `swo/modules/lambda-zip/`** — the authorizer was its only consumer
  (`swo/main.tf:134`). caylent has its own copy and is unaffected.

### 2b. Replace the authorizer resource

`swo/modules/api-gateway/main.tf:51-65` is currently
`aws_apigatewayv2_authorizer.lambda_authorizer` with `authorizer_type = "REQUEST"`,
`authorizer_uri`, `authorizer_payload_format_version = "2.0"`,
`enable_simple_responses = false`, `identity_sources = ["$request.header.Authorization",
"$context.routeKey"]`, `authorizer_result_ttl_in_seconds = 300`.

Replace with a JWT authorizer:

```hcl
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.main.id
  name             = "${var.api_name}-authorizer"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = var.cognito_audience
    issuer   = var.cognito_issuer
  }

  depends_on = [aws_apigatewayv2_api.main]
}
```

Notes to get right, each of which is a real behaviour change worth a comment in the
file:
- `identity_sources` **loses** `$context.routeKey`. A JWT authorizer permits only
  header/query identity sources, and there is no per-route policy to cache. The
  existing comment about route-scoped cache keys and wildcard ARNs becomes obsolete
  — delete it rather than leaving it to mislead.
- `authorizer_result_ttl_in_seconds` does not apply to JWT authorizers. Dropping it
  is correct, not an omission.
- A JWT authorizer is **all-or-nothing per route**: it cannot return a policy, so
  the fine-grained wildcard ARNs the old one built are gone. If any route relied on
  path-scoped authorization, say so in your report.

### 2c. Variables, not resources, for the pool

Do **not** create the user pool (constraint 4, and 0b is unresolved). Add to
`swo/variables.tf`, matching that file's habit of carrying reasoning inline (see the
nova-lite note at `:173`):

```hcl
variable "cognito_issuer" {
  description = "Cognito User Pool issuer URL, e.g. https://cognito-idp.<region>.amazonaws.com/<pool-id>."
  type        = string
}

variable "cognito_audience" {
  description = "Accepted audiences — the Cognito app client ids."
  type        = list(string)
}
```

No defaults: an unset pool must fail at plan time, loudly, rather than deploy an
authorizer that trusts nothing. Add both to `swo/terraform.tfvars.example` with
placeholder values and a comment pointing at precondition 0b. Thread them through
`swo/modules/api-gateway/variables.tf`.

### 2d. Routes

`swo/modules/api-gateway/routes.tf` has **10** references to
`aws_apigatewayv2_authorizer.lambda_authorizer` — `authorizer_id` at `:54, 68, 82,
96, 110, 124, 162, 176, 190, 204` plus the matching `depends_on` entries. Repoint
all to `aws_apigatewayv2_authorizer.jwt`. Grep for `lambda_authorizer` afterwards
and expect zero hits.
⚠️ Also confirm `authorization_type` on each route is `"JWT"`, not `"CUSTOM"` — grep
for `authorization_type` in that file and fix every one. A route left on `CUSTOM`
pointing at a JWT authorizer is a plan-time error at best and a 500 at worst.

### 2e. Docker build contexts — the one remaining coupling

`swo/scripts/deploy-image.sh:14-20` sets `LAMBDA_DIR="../../lambdas/{question_process,
ai_assistant,content_adaptation_process}"` and `cd`s there for `buildx build`. These
three are container lambdas and stay in `rag`.

Change each to `"${LAMBDA_SOURCE_ROOT:-../../rag/lambdas}/..."`. Add a guard before
the build that fails loudly if the directory is missing, naming the variable — a
missing sibling checkout currently produces a bare `cd` failure. Match the script's
existing `❌ … 💡 …` message style.

No Terraform variable is needed for this; nothing in `.tf` reads lambda source any
more. Say so in a comment so nobody re-adds one.

### 2f. Repo furniture

- `rag-infra/Makefile` — port the 16 delegating targets from `rag/Makefile:135-191`,
  changing `-C infra/swo` → `-C swo`. Drop the `rag`-only targets (`install`,
  `install-dev`, `run`, `mongo`, pricing, `build-authorizer`). Keep the `help`
  shape.
  ℹ️ `rag/README.md:259-262` and the root `CLAUDE.md` both claim this delegation is
  `-C infra` and broken for all but `plan`/`apply`. **That is stale** — the Makefile
  already says `-C infra/swo` and all 16 targets resolve. Do not reproduce the
  claim; fix it in Phase 3.
- `rag-infra/README.md` — sibling-checkout requirement, `LAMBDA_SOURCE_ROOT`, the
  Cognito variables and their dependency on 0b, the remote-S3 init line, and the
  `make -C swo …` deploy sequence. Carry over what `infra/swo/README.md` documents
  rather than rewriting it.

### 2g. Verify

`cd swo && terraform init -backend=false && terraform validate`
⚠️ `validate` proves syntax and references only. It will **not** prove the Cognito
authorizer works, and it no longer needs the `rag` checkout at all (that is the
point). Leave `terraform plan` to a human with credentials, and say so.

## Phase 3 — `rag`: delete the authorizer, adapt the assistant, drop `infra/`

Branch `ONLINE-####_extract_infra` — ask the user for the ticket; if unavailable use
the current branch's `ONLINE-6857` prefix and say you did. Keep the auth change and
the infra removal in separate commits.

1. **Untrack the state file:** `git rm --cached infra/swo/errored.tfstate`. It leaves
   HEAD; history is Phase 0a's problem. Do not delete the working file without
   asking — it may be diagnostic.
2. **Move `infra/` aside, do not delete it.** `git rm -r infra` leaves untracked
   files behind, and `infra/swo/terraform.tfvars`, `.terraform/`,
   `.terraform.lock.hcl` and `errored.tfstate` are untracked-but-present.
   ⚠️ **`infra/swo/terraform.tfvars` is in no repo's history and is unrecoverable.**
   Move the whole directory to `/home/lenovo/infra-preserved/`, tell the user, and
   copy `terraform.tfvars` into `rag-infra/swo/` (gitignored there, so it will not
   be committed).
3. **`lambdas/ai_assistant/src/main.py:162-173`** — the downstream break. It reads
   `event["requestContext"]["authorizer"]["lambda"]`; the `.lambda` key exists
   **only** for REQUEST-type authorizers. Cognito puts claims at
   `.authorizer.jwt.claims`. Left alone, `:162` yields `{}`, `:167` logs "Missing
   user_id in authorizer context", `:173` sets `credits = 0`, and every assistant
   route fails.
   - Read `user_id` from the JWT claims (`sub`, or whichever claim carries the
     platform user id — this depends on 0b's federation choice, so **if it is
     unresolved, read from `sub` and mark it `TODO(ONLINE-####)` rather than
     guessing a custom claim name**).
   - `credits` has no source. Leave a loud `TODO(ONLINE-####)` citing precondition
     0c; do not silently default to 0, and do not invent a Laravel call.
   - Match the file's existing logging idiom.
4. **Keyed-on-user_id consumers** — `src/utils/adapt_rate_limiter.py:16` and
   `src/utils/model_capacity_limiter.py:20` document keying on "the authorizer
   `user_id`". Update the comments to name the new source. Behaviour is unchanged so
   long as step 3 preserves the same id.
5. **Delete `lambdas/authorizer/`** and its references:
   - `Makefile:53` (`install`), `:62` (`install-dev`), `:124-126`
     (`build-authorizer`), and the name in the `.PHONY` list at `:7`.
   - ⚠️ `lambdas/authorizer/tests/test_authorizer.py` is one of only **two** real
     pytest suites in the repo (the other is `content_adaptation_process`). Deleting
     it is intended here, but call it out in your report — the root `CLAUDE.md`
     documents that pytest story and will need updating.
6. **Remove the infra Makefile targets:** `rag/Makefile:135-191`. Prefer replacing
   them with one target that prints where infra moved, rather than deleting them —
   a silent "No rule to make target" after a repo split is a bad experience. Ask if
   unsure; default to the message.
7. **Fix the hard reverse dependency:**
   `lambdas/ai_assistant/tests/check_artifact_language.py:336` does
   `(REPO / "infra/swo/modules/api-gateway/routes.tf").read_text()` and asserts
   `POST /adapt` targets `processing_lambda_stable_v3` and not the assistant lambda.
   After the split this is a `FileNotFoundError`.
   Resolve the infra checkout through an env var with a sibling default
   (`RAG_INFRA_ROOT`, default `<repo>/../rag-infra`, and note the path is now
   `swo/modules/...` with no `infra/` prefix), and **print a loud SKIP if absent**
   rather than failing — the check must not go red for someone who cloned only
   `rag`. Keep the assertion itself byte-identical. Match the file's `check(...)`
   idiom.
8. **Update the stale path comments** (documentation only, but they rot):
   `src/config/config.py:152,182`, `src/services/assistant_service.py:189,4493`,
   `src/services/daily_usage_service.py:9`, `src/utils/cache_metrics.py:18`,
   `tests/check_routes.py:7,112`,
   `lambdas/content_adaptation_process/src/schemas/content_schemas.py:45`.
   `infra/swo/...` → `rag-infra swo/...`. Do not restructure them; they carry
   incident reasoning.
9. **`rag/README.md`** — rewrite the deployment section (~`:259-267`) to point at
   `rag-infra`, drop the stale "no `infra/Makefile`" claim, and fix `:40` ("deploy
   scripts under `infra/*/scripts/`"). Add a line on the new auth model.
10. **`rag/.gitignore`** — remove the now-dead `!infra/terraform.tfvars.example`
    negation. **Keep** the `**/*.tfstate` globs and their comment: cheap insurance
    and an incident record.
11. Do **not** touch `swo-3.0` or `rag/docs/AiAssistantConsolidation.md`. Grep
    `/home/lenovo/swo-3.0/docs/` and `frontend-v3/` for `rag/infra` and for the
    Laravel-token assumption in `ai/services/aiHttp.ts`, and **report** what you
    find. The frontend token change belongs to precondition 0b, not to this task.

## Phase 4 — verify, then report

Run these and paste real output:

```bash
# rag-infra
cd /home/lenovo/rag-infra/swo && terraform init -backend=false && terraform validate
grep -rn "lambda_authorizer\|authorizer_lambda\|lambda-zip" . --include=*.tf   # expect 0 in swo/
grep -rn "authorization_type" modules/api-gateway/routes.tf                    # expect all JWT
cd /home/lenovo/rag-infra && git ls-files | wc -l                              # expect 160
git rev-list --all --objects | grep -ci tfstate                                # expect 0

# rag — assistant checks (no AWS, no DB)
cd /home/lenovo/rag/lambdas/ai_assistant
uv run python tests/check_routes.py
uv run python tests/check_artifact_language.py
for t in tests/check_*.py; do uv run python "$t" || break; done

# rag — nothing still points at what was removed
cd /home/lenovo/rag && grep -rn "infra/swo\|infra/caylent\|lambdas/authorizer" \
  --include=*.py --include=*.md --include=Makefile --include=*.sh . \
  | grep -v '\.venv\|node_modules\|/experiments/'
```

Report, explicitly:
- what changed in each repo, the two commit ranges, and the verification output;
- **that preconditions 0a (rotate 3 secrets), 0b (no Cognito token source — the
  frontend still sends a Laravel JWT and will 401), and 0c (credit metering has no
  home) are all still outstanding, and that 0b and 0c mean this branch must not be
  deployed as-is**;
- that no `terraform plan` ran, so Cognito wiring is unproven;
- that nothing was pushed and `rag-infra`'s remote does not exist yet — the user
  creates it (`sw6/ops/rag-infra`?) and pushes both branches;
- whether `caylent/` should be kept, fixed, or dropped;
- that deleting `lambdas/authorizer` removes one of the repo's two pytest suites,
  and the root `CLAUDE.md` says so and needs updating.
