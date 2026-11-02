*QA: ONLINE-7525 (Shared response cache for Scout evaluation runs), local rag checkout on ONLINE-5385_scout_ai_integration (35b99fba), live Bedrock in us-west-2 (tester's AWS SSO session)*

No swo-3.0 change and no UI, so this was tested from a terminal, not on dev2. Teachers see no change: the Lambda imports nothing from {{experiments/}}.

*How it was tested:* rag on {{ONLINE-5385_scout_ai_integration}} at {{35b99fba}} (contains ONLINE-7525 commits {{9d11e0d2}}, {{d3c400f8}}), dependencies installed with {{make install-dev}}. AWS access confirmed with {{aws sts get-caller-identity}} (SSO, us-west-2). Then {{SMOKE_LIVE=1 AWS_DEFAULT_REGION=us-west-2 bash ONLINE-7525-smoke-tests.sh}}: it runs the developer's three check scripts, then its own offline checks, prints a cost estimate, and makes 4 real Haiku 4.5 calls through the shared cache. Everything it writes goes to a temp folder that is deleted afterwards, so no real cache or ledger changed. Real Bedrock calls are counted by a wrapper outside the cache, so "no call" is measured independently of the cache's own report.

*Developer's check scripts (fake Bedrock client, no AWS):* PASS 30/30
* {{check_bedrock_cache.py}} 14/14: a repeat request reaches Bedrock once; a changed message or model calls again; the original is still a hit afterwards; 16 simultaneous writers leave one valid file; {{replay}} raises on an unseen request without calling; {{record}} always calls; {{off}} always calls and counts nothing; {{invoke_model}} repeats are cached.
* {{check_cost_meter.py}} 11/11: estimates match hand-worked figures ($0.176 Sonnet, $0.11 Haiku), batch is half; actual cost from tokens in both Bedrock formats; prompt-cache tokens at their own rate; ledger totals and an empty day at $0; cost read back from cache files.
* {{check_bedrock_batch.py}} 5/5: refuses with no bucket or only a bucket; builds settings with both; a batch result written into the cache is found by a normal {{replay}} client.
* Weaker than their names: _"off mode wrote nothing new"_ checks counters, not files (live T5 covers it); _"invoke_model … different key order"_ sends the same order twice, so it only proves a plain repeat; the batch read-back uses a fake result already in {{converse}} format (finding 2).

*Smoke script, offline checks:* PASS 7/8 (plus T1 above)
* Cache key ignores key order and changes with the prompt, temperature or model. An unknown {{BEDROCK_CACHE_MODE}} is refused. Each cache folder gets its own {{.gitignore}}.
* Estimate: 40 Sonnet calls at 1000 in / 200 out → *$0.176*, *$0.088* as a batch job.
* Per-day ledger: _"2026-10-01: $0.3000 across 2 recorded run(s)"_; an empty day is $0.0000.
* Batch with no bucket or role → {{BatchInfraMissing}} _"BEDROCK_BATCH_S3_BUCKET and BEDROCK_BATCH_ROLE_ARN must both be set…"_
* *FAIL:* 33 scripts still call Bedrock without the shared cache (finding 1).

*Live checks (Haiku 4.5):* PASS 9/9
* Estimate printed before any call: _"estimated $0.000242 for 4 live calls"_.
* First call recorded: 1 miss, 1 cache file with the token usage.
* *Unchanged re-run makes no Bedrock call*, in both {{auto}} and {{replay}}: _"cache: 1 hits, 0 misses"_, same answer.
* A changed prompt, temperature or model in {{replay}} → {{CacheMissError}} _"…in replay mode -- the request changed…"_, no call.
* {{record}} always calls and rewrites the entry; {{off}} calls without reading or writing the cache; a corrupt cache file is a miss, re-fetched in {{auto}}, no crash.
* Actual cost: *$0.000037* per call (14 in / 4 out tokens), the same from {{actual_cost_from_cache}}; about *$0.00015* for the whole run.
* A wrapper counted every real Bedrock call: 4 in total, exactly the ones that should call.

*Findings:*
# *33 evaluation scripts still call Bedrock without the shared cache (medium, AC2).* 
Includes the labellers and calibrators: {{teacher_eval/judge.py}}, {{teacher_eval/online7507/label_c2..c5.py}}, {{label_pools.py}}, {{relabel_check.py}}, {{validate_label_fix.py}}, {{grading_baseline/grader.py}}, {{guardrail_curriculum/calib_grounding.py}}. {{teacher_eval/online7507/bedrock_cache.py}} is still a separate cache. Some (latency, guardrail probes, embeddings) may be fine to leave out; the migration list the docstring cites ({{results/7525-build.md}}) isn't in the repo.
# *Batch jobs can't run: no S3 bucket or role exists (medium, AC4).* 
{{bedrock_batch.py}} refuses clearly, as designed, and no script submits a job, so AC4 is unproven. A read-only check of the dev account (us-west-2, 1 Oct, nothing created) found: the only bucket is {{…-dev-ai-export}}, whose permissions cover {{ai-export/}} only; the only roles Bedrock can assume are the {{bedrock-cw-logging}} ones, with no S3 access; Haiku 4.5 supports batch (minimum 100 records per job) but *Sonnet 5 shows no batch quotas*, although the ticket wants Sonnet for bulk labelling. Needs a role and bucket prefix from infra. Also unproven until a real job: whether batch output (Bedrock's native body) can be read back by a harness that calls {{converse}}.
# *Batch spend would be priced at full rate (low).* 
{{actual_cost_from_cache()}} doesn't pass {{batch=True}} ({{cost_meter.py:123}}), so batch entries count double. They carry {{batch_record_id}}, so they can be told apart.
# *Unpriced models count as $0 (low).* 
{{actual_cost_from_cache()}} skips models with no price row ({{cost_meter.py:111}}), e.g. the GPT judge in {{teacher_eval/judge.py}}. The product's {{config.py}} uses the dearest price ({{FALLBACK_PRICE}}) for this.

*Not covered yet:* a real evaluation script run twice unchanged (T11, costs real money, needs an agreed estimate); Sonnet labelling with an Opus spot-check (T13); a batch job end to end (T14, blocked on the role and bucket prefix); the measured turn still using the production model (T16).

*Observations (not failures):*
* Calls made in {{off}} mode don't appear in the cache report (_"0 hits, 0 misses"_).
* {{actual_cost_from_cache()}} totals the whole cache folder, not one run, so each harness works out its own run's cost.
* The ledger only holds runs whose script calls {{Ledger().record()}} (32 do); nothing enforces the $10 / $30 daily gate.
* Each harness folder has its own {{.cache}}, so another worktree or checkout pays again for the same requests.
* Opus prices are estimated (list × 1.1), but totals don't say so.

Details in the attached *ONLINE-7525-test-results.docx* (no screenshots: the evidence is the script's terminal output).
