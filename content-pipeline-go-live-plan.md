# Go-live plan: curriculum content pipeline (SWO → S3 → Pinecone)

Written 2026-09-24. Scope is deliberately narrow: **the two-repo pipeline that gets
curriculum into the vector index** — `swo-3.0`'s `ai:export-content` and `rag`'s
`sync-content` on Fargate. This is the piece this session built, fixed, and backfilled
to dev, so it's the piece I can assess with verified evidence rather than assumption.

**Out of scope, and not assessed here:** retrieval relevance/metadata correctness
(`ONLINE-6857-12-retrieval-relevance`, `ONLINE-6857-13-metadata-backfill-tooling`,
`ONLINE-6857-DOM-Awareness` — that last branch's own title, "articles have no
source_type", says there's unresolved work on exactly the metadata shape the content
flip depends on), guardrails (`ldc/guardrials-docs/` is already tracking that
separately), the chat/turn experience, credits, and everything else under the
`ONLINE-6857-*` umbrella. **Confirm those separately before calling the assistant
itself production-ready** — this document only answers "is the data pipeline ready."

Every fact below was verified this session against `/home/lenovo/rag` (branch
`ONLINE-6857-v2-14-testing-feedback`, the fargate/prune-guard work already merged in
at commit `2584240`) and `/home/lenovo/swo-3.0` (branch
`ONLINE-6857-ai-export-dev-schedule`, based on `origin/ONLINE-6857-v2-14-testing-feedback`,
commit `f0a6a34873`, **not yet pushed**). Do not re-derive what's cited; do verify
anything you depend on that isn't.

## Bottom line

**Not ready.** Not far off, either — the pipeline works, correctly, at the scale
production needs (788,798 of 788,799 documents landed clean in dev). What's missing is
specifically the *production* half of "production-ready": a production bucket, a
production Mongo, confirmation of the production Pinecone index's shape, and one
real-data test of the code paths that have never fired outside a synthetic check.

None of the blockers below are large. All of them are the kind of gap that's invisible
until the day something depends on it.

---

## What's already proven — don't re-test these

| Claim | Evidence |
|---|---|
| Export command is correct at scale | 788,799 documents, 9 types, dev bucket, run `20260903T180020Z` |
| Sync command is correct at scale | 788,798 of 788,799 landed in `content-v2`; the 1 is a known, understood manifest gap |
| Silent write failures can't happen | `NdjsonShardWriter` and both `latest.json`/`run.json` writes raise instead of swallowing `false` (commit `a43a1c0e7a`) |
| Non-ASCII vector IDs don't crash a 7-hour run | Percent-encoding fix (`5fca7ab`), verified against the Alaska GUID that actually failed |
| A partial-types export can't prune the rest of the namespace | Scoped-deletion guard (`2584240`), verified against exactly that scenario |
| Sparse/BM25 fits the corpus safely | 200,122 terms, ~3MB BSON against Mongo's 16MB cap — measured, not estimated |
| The backfill can't be interrupted destructively | State written per-batch, after the vectors land — proven by the actual mid-run failure and clean resume on 2026-09-14 |
| Credentials aren't logged in plaintext anymore | Mongo URI redaction (`2a4793e`) |
| The trigger can't fire on a stale image | Verified live: `grep -c scope_deletions` inside a real task returned `3` before the trigger was trusted |

This is a real amount of hardening. The list below is what's left, not a re-litigation
of the above.

---

## Hard blockers — must resolve before a production run

### 1. The scheduled export has no bucket override, and production's disk isn't a dedicated one

This is the one I'd stop the launch for. Every dev export in this whole engagement was
run with `--bucket=swo-genai-pov-976193258093-dev-ai-export` passed explicitly — by
hand, or via `config('ai_export.disk')`. **The two `Kernel.php` schedule entries pass
`--disk` and `--path` only, never `--bucket`.** Without a `--bucket` override, the
export writes through whatever `filesystems.php`'s `s3` disk resolves to —
`env('AWS_BUCKET')` — which in this codebase is the **CDN/static bucket**
(`static.studiesweekly.com` in dev; presumably its production equivalent). A scheduled
production run would write curriculum NDJSON shards straight into the bucket serving
real site traffic, unless a dedicated disk is configured first.

**Action:**
- Create the production equivalent of `modules/s3-ai-export` — a dedicated bucket,
  private, versioned, `DenyInsecureTransport`, lifecycle on `runs/*`. No prod tfvars
  exists yet (`terraform.tfvars.example` only demonstrates `environment = "dev"` /
  `pinecone_index_name = "stage-rag-index"` — a prod deployment is genuinely
  unbuilt, not just unconfigured).
- Add an `AI_EXPORT_DISK`-pointed disk (or set `AWS_BUCKET` won't work — that's the
  CDN bucket) in `config/filesystems.php`, or extend `ExportAiContent`'s `--bucket`
  resolution to read from `ai_export.bucket` config so the schedule can pass it the
  same way manual runs did. **Decide which, then make `Kernel.php`'s two calls use it.**
  Today they cannot — verify this yourself: `grep -n "'--bucket'" backend/app/Console/Kernel.php`
  currently returns nothing.

### 2. `env-template` has zero `AI_EXPORT_*` variables

Production's `.env` is built by `envsubst < env-template > .env` — a completely
different mechanism from dev/stage's `swo/{env}/backend` Secrets Manager JSON. Setting
`AI_EXPORT_SCHEDULE_ENABLED` in Secrets Manager, the way dev's runbook describes,
**does nothing for production** — that path isn't read there at all.

**Action:** add `AI_EXPORT_SCHEDULE_ENABLED`, and any of the other `ai_export.*`
config keys you want non-default, as `${VAR}` lines in `backend/env-template`, and set
the corresponding GitLab CI/CD variable for the production environment.

### 3. Production's `app()->environment()` value for the schedule gate — confirm, don't assume

`->environments(['production', 'local'])` already includes `production` — unlike dev,
which needed the fix in `f0a6a34873`. But that fix hasn't been proven against a real
`APP_ENV` value the way dev's was (`tinker --execute="echo app()->environment();"`
returned `dev`, confirming the exact string). **Run the same one-line check on a real
production host before relying on the schedule** — `APP_ENV: "production"` in
`.gitlab-ci.yml:821` matches the array by inspection, but this pipeline has already
shown once that "matches by inspection" and "confirmed on the host" are different
levels of certainty worth keeping separate.

### 4. No production Pinecone target exists yet — literally, in this repo

`terraform.tfvars.example`'s only illustrated value is `pinecone_index_name =
"stage-rag-index"`. A real `prod-rag-index` already exists in the account (per
`commands/sparse_encoder.py`'s own docstring, which lists it alongside `stage-rag-index`
as one of four indexes reachable by the same API key) — but:
- **Its `metric` has never been checked this session.** The dev backfill was blocked
  once already by discovering `stage-rag-index` needed to be (and was) `dotproduct`.
  Run the identical check before any production write:
  ```bash
  curl -s -H "Api-Key: $KEY" https://api.pinecone.io/indexes/prod-rag-index | python3 -m json.tool
  ```
- **The same API key can see and write both indexes.** `_preflight()`'s own docstring
  in `ai_sync_command.py` describes this exact near-miss already happening once with a
  *different* project's index. A misconfigured `PINECONE_INDEX_NAME` pointed at
  `prod-rag-index` from a dev or test invocation is not a hypothetical — it's the
  documented failure mode of this exact system, and now there's a real production
  index for it to hit.
- **No production Mongo exists in this repo's config either.** Dev/stage point at
  `stage-rag` on the shared `sw-ai.4hbzz.mongodb.net` cluster. Production needs its own
  database — sharing `content_index` state between stage and production is exactly the
  "dev may not write to stage" concern already on record for dev, at higher stakes.

**Action:** stand up the production S3, Mongo, Fargate task, and IAM as their own
Terraform environment (`environment = "prod"`), pointed at a verified `prod-rag-index`
and a dedicated production Mongo database. Treat this as new infrastructure to build,
not existing infrastructure to point at.

### 5. Update and delete have never run against real content

Every number in the "already proven" table above is from **add-only** activity —
`updated 0` and `deleted 0` on every run so far, dev included. The code paths that
matter most for a live system — a document shrinking (orphan-chunk trimming) and a
document being unpublished (prune) — have executed exactly zero times against real
data. This was flagged as the priority follow-up test after the backfill and hasn't
been run yet.

**Action, in dev, before trusting this in production:**
1. Edit a real article so it produces fewer chunks. Confirm `chunks deleted > 0` and no
   orphaned high-numbered chunks survive.
2. Unpublish a real article. Confirm `deleted 1` and its vectors are gone.

Both are cheap — minutes each — and both are the one gap between "the happy path
works" and "the whole state machine works."

### 6. The question-count / privacy-filter question is now a production question, not a dev curiosity

Given your own statement that prod and dev share the same article/question data: the
408,686-vs-~54,700 gap flagged during the dev backfill is not dev-specific noise —
whatever ships from dev's corpus characteristics will ship identically from
production's, because it's the same underlying rows. This was an open item before;
given prod/dev data parity, it's now squarely a go-live blocker, since it's a live
question about whether teacher-authored `customized_content` is actually excluded by
the filter, and a shared vector index has no tenancy to undo that after the fact.

**Action:** run the verification query from the backfill runbook's Gate 1, step 7,
against production data (or dev, given parity) — confirm `teacher_authored = 0` for
the three exported assignment types — before the first production export ships
anything.

---

## Should-fix-before-launch — real risk, not launch-blocking on its own

- **No alarm on a failed task.** No SNS topic exists in this Terraform config to point
  one at. A production sync that silently stops (bad credential, expired token, Mongo
  unreachable) looks identical to a healthy no-op unless someone is watching logs.
  Fine for a manually-run dev pipeline; not fine for something meant to run unattended
  in production.
- **Single AZ.** The Fargate network config names one subnet
  (`subnet-0791c61aedc8776b2` in dev). A capacity event in that AZ fails `RunTask`
  outright. Worth a second AZ for production, where an export missing its window has
  real consequences.
- **Credential rotation is still open.** Four exposures on record across this
  engagement (an `AKIA` key, `ASIA` session credentials, a Pinecone key printed via
  tinker, the Mongo password since redacted in code but not yet rotated in Atlas). None
  are catastrophic on their own in dev; carrying any of them into a production
  credential set would be a mistake. Rotate before reusing any secret value dev used
  for anything production touches.
- **The EventBridge trigger flag lives in a gitignored `terraform.tfvars`.** Fine for
  dev, where I fixed the "silently reverts to false and destroys the rule" trap
  directly. For production, put this decision somewhere reviewable — a committed
  default, or a documented runbook step — so "is automation live in prod" is answerable
  by reading the repo, not by finding the right laptop.
- **The three retrieval/metadata branches.** Not reviewed this session, but their names
  alone (fixing article filtering *after* the Pinecone backfill) suggest the metadata
  shape `content_search` depends on for the rebuilt namespace may still be settling.
  Read those branches, or talk to whoever owns them, before treating the `content-v2`
  → assistant cutover (see below) as a formality.

---

## Explicitly deferred — accepted for launch, revisit after

- **The one-document `unresolved` gap** (empty-text documents, plus the known
  manifest/body mismatch). Retried harmlessly every run; not worth blocking on.
- **`prune`-side automation** (the S3-trigger wiring) doesn't need to be live on day
  one. Manual/scheduled export + manual sync trigger is an acceptable launch posture;
  full automation can follow once the update/delete tests above give confidence.
- **The assistant's cutover to `content-v2`.** Nothing forces this to happen at the
  same moment as the pipeline going live. The pipeline can run in production, feeding a
  namespace nothing reads yet, exactly as it does in dev today — which is in fact the
  safest way to prove production end-to-end before a single real user query depends on
  it. See the phased plan below.

---

## Phased plan

**Phase 0 — decisions needed from you before any of this starts**
- Is production a separate AWS account, or `environment = "prod"` in the same account
  (976193258093) as dev? Nothing in either repo answers this; it changes how much of
  `infra/swo` can be reused verbatim versus needs new bootstrapping.
- Fix for blocker #1: dedicated disk config, or extend `--bucket` resolution into
  `ai_export.*` config? Either is small; pick one so `Kernel.php` can be finished.
- **Terraform's own scripts are not environment-isolated for secrets.**
  `bootstrap.sh`/`init.sh`/`plan.sh`/`apply.sh` pass only `-var="environment=$ENV"` and
  `-var="region=$REGION"` — everything else (`mongodb_uri`, `pinecone_index_name`,
  `pinecone_api_key`, ...) comes from the single, gitignored `terraform.tfvars`, which
  today holds dev's values. Running `make apply ENV=prod` as-is would create
  prod-named resources wired to dev's Mongo and dev's Pinecone index, silently. Fix
  before Phase 1 step 1: a separate `terraform.prod.tfvars` with production-only
  values, invoked via `TF_ARGS="-var-file=terraform.prod.tfvars"`. Also note: the
  `environment` variable's validation accepts `"prod"`, not `"production"`.
- **Backfill production by cloning stage's vectors, or by re-running the export and
  embedding cold?** Cloning is legitimate, not a shortcut that trades correctness for
  speed — vector ids are deterministic and OpenAI embeddings are deterministic for a
  fixed model, so if production's rows are truly byte-identical to what dev exported,
  a clone produces the same vectors a cold run would, in minutes of Pinecone-to-Pinecone
  I/O instead of ~7-8 hours of embedding calls. See the dedicated step below if you
  choose it. Either way, **resolve blocker #6 (the privacy-filter question) first** —
  cloning would ship any leak into production faster than a cold run would, not slower.

**Phase 1 — production infrastructure, no schedule live yet**
1. Terraform: production S3 bucket, IAM read/write policies, Fargate task, in their own
   `environment = "prod"` state, using `terraform.prod.tfvars` per the Phase 0 fix above.
2. Confirm `prod-rag-index`'s metric and dimension (blocker #4).
3. Provision a dedicated production Mongo database.
4. Wire `env-template` (blocker #2) and the bucket fix (blocker #1) in `swo-3.0`.
5. **Populate the index — pick one:**

   **5a. Cold run** (default; use if the clone's preconditions below aren't met).
   Manual export, manual sync — the exact shape of every dev run so far — against
   production infrastructure, into a namespace nothing reads. Same corpus (per your
   parity statement), same verification steps, ~7-8 hours, under $1.

   **5b. Clone from stage** (faster; use only after blocker #6 is resolved and the
   parity claim below is actually checked, not just believed).

   - **Verify parity precisely first**, not just informally: compare row counts and,
     for a real sample, `content_sha` values between what a *test* production export
     would produce and what's already in `stage-rag-index`'s `content-v2` manifest.
     "Same articles" as a business statement and "same `content_sha` for every row"
     as the technical requirement for a clone are different bars — one stale
     `updated_at` or one production-only draft breaks it for that document, silently,
     with no manifest-diff step around to catch it (the clone bypasses that safety
     net entirely for whatever doesn't match).
   - **Pinecone and Mongo move together, or not at all.** Mongo's `content_index` is
     a *claim* — "this doc_id is already in Pinecone with this sha" — not content.
     Clone one without the other and every future dry run reports `already indexed`
     for documents that were never actually written to the new index: the same
     silent-success-without-substance failure this whole pipeline was built to stop
     happening on the export side.
   - **Scope both clones narrowly — never a wholesale copy:**
     - *Mongo:* copy only the `content_index` and `sparse_stats` collections, by
       name. `stage-rag` is not a content-sync-only database — the same
       `mongodb/database` SSM parameter is read by the assistant lambda's
       conversation/checkpointer state too. A `mongodump` of the whole database
       would carry real teacher conversation threads into a production seed.
     - *Pinecone:* copy only the `content-v2` namespace. `stage-rag-index` also
       holds `__default__` (881k legacy ada-002 vectors), `support`, `default`, and
       an empty leftover `content-v2-smoke` — a whole-index copy drags all of it
       into production. Do this as a scripted fetch-then-upsert scoped to the one
       namespace, not a whole-index operation — verify against Pinecone's current
       API docs before assuming any specific backup/restore call supports
       namespace scoping; don't take that on faith.
   - **After cloning, run a real production export and a dry run against it.**
     `to index`/`to delete` coming back non-zero is the list of documents where the
     parity assumption didn't hold — treat that as expected reconciliation, not a
     failure, and let a normal incremental sync repair exactly those.
   - This does not remove the need for steps 1-4 above. Cloning seeds the index
     faster; production still needs its own working export writing a real
     `run.json`/`latest.json`, because that's what every future incremental sync
     diffs against.

**Phase 2 — correctness gaps closed**
6. Run the update/delete tests (blocker #5) in dev first, then again in production
   against the now-populated production namespace.
7. Resolve the privacy-filter question (blocker #6) — before Phase 1 ideally, since it
   affects what Phase 1 ships, but no later than here.
8. Confirm the production `app()->environment()` value (blocker #3).

**Phase 3 — turn the crank on, still not live to users**
9. Enable `AI_EXPORT_SCHEDULE_ENABLED` in production, confirm a real scheduled run
   (not a manual one) completes cleanly.
10. Decide on the EventBridge auto-sync trigger for production, or keep it manual —
    either is defensible at this stage.

**Phase 4 — the actual cutover**
11. Only now: flip the assistant's `CONTENT_NAMESPACE` / `EMBEDDING_MODEL` /
    `ENABLE_HYBRID_SEARCH` together, in production, after resolving the retrieval/
    metadata branches noted above and running the retrieval check scripts
    (`check_content_schema.py`, `check_content_types.py`, `check_retrieval_cascade.py`,
    `check_forced_retrieval.py`) against the production namespace.
12. Rollback plan: unsetting `CONTENT_NAMESPACE` reverts instantly, because the legacy
    namespace is never written to by this pipeline — confirmed true in dev, re-confirm
    in production before relying on it under pressure.

---

## What I'd tell a tech lead in one paragraph

The pipeline's *logic* is production-grade — every failure mode this engagement found
got fixed and verified at real scale. What's missing is entirely *environment*: there
is no production bucket, no production Mongo, unverified assumptions about the
production Pinecone index, an unwired schedule (no `--bucket`, no env-template
entries), and two code paths (update, delete) that have literally never executed
against real data. None of that is hard. All of it is real, and none of it should be
discovered by production traffic instead of by this list.
