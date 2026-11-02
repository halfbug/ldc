# AI Code Audit Plan — Studies Weekly Online (Scout AI)

**Scope:** every piece of AI code in both repos:

- `rag`: AI lambdas, Terraform, experiments
- `swo-3.0`: `frontend-v3/ai/` plus the Laravel `api/ai/*` surface

**Focus areas:** ① Cost and token usage · ② Infrastructure · ③ Performance · ④ Security

**Baseline revisions:**

| Repo | Branch | Commit |
|---|---|---|
| `rag` | `prod-infrastructure` | `5dbb9b18` |
| `swo-3.0` | `master` | `5dda392150` |

The prompt-caching material (§2.2, §3.1, §3.1a, A2.1, A3) was updated on 2026-10-05 against `rag`
`ONLINE-5385_scout_ai_integration` @ `86d92ea0`, where the cache layout changed. Everything else still
reflects the baseline above.

**Prepared:** 2026-10-02 · **Updated:** 2026-10-05

> **How to read this.** §1–§3 give the picture: what exists, how a request flows, and where the money goes.
> §4 is the method. §5–§8 hold one checklist per focus area. Every item has an ID, the evidence that
> prompted it, how to test it, and what counts as a pass. §9 lists docs that no longer match the code. §10 is a
> copy-paste runbook. **The "Lead" findings came from a read-only reconnaissance pass. They are hypotheses
> with code pointers. Each one must be reproduced before it goes into the final report.**

---

## Table of contents

1. [Executive summary: what to look at first](#1-executive-summary--what-to-look-at-first)
2. [System map](#2-system-map)
3. [Where the tokens and dollars go](#3-where-the-tokens-and-dollars-go)
4. [Audit method, phases and timeline](#4-audit-method-phases-and-timeline)
5. [Workstream A: Cost and token usage](#5-workstream-a--cost--token-usage)
6. [Workstream B: Infrastructure](#6-workstream-b--infrastructure)
7. [Workstream C: Performance](#7-workstream-c--performance)
8. [Workstream D: Security and privacy](#8-workstream-d--security--privacy)
9. [Documentation drift register](#9-documentation-drift-register)
10. [Runbook: commands and queries](#10-runbook--commands-and-queries)
11. [Severity rubric and finding template](#11-severity-rubric-and-finding-template)
12. [Deliverables](#12-deliverables)

---

## 1. Executive summary: what to look at first

The reconnaissance pass turned up these leads. They are ranked by how bad things would be if each one is confirmed.

| # | Lead | Area | Prelim. severity | Where |
|---|---|---|---|---|
| 1 | **Live dev credentials (Mongo URI, OpenAI, Pinecone keys) in git history.** They are in `errored.tfstate`, which the commit added. The Pinecone key can also reach `prod-rag-index`. | Security | **Critical** | `rag` commit `21b73c96`, `infra/swo/main.tf:127-129` |
| 2 | **The gateway authorizer has no host allowlist.** Any `*-online.studiesweekly.com` host is accepted. A missing or `localhost` host falls back to *prod* Laravel. A dev token can pass the prod gateway. | Security | **High** | `lambdas/authorizer/src/lambda_handler.py:39-79` |
| 3 | **IDOR:** `GET /assistant/search/message` reads a `SearchIndex` by id **with no user filter**. | Security | **High** | `services/assistant_service.py:1682-1694` |
| 4 | **Unowned write:** `POST /assistant/thread/record` writes a client-supplied Human or AI message pair into **any** `thread_id`. That allows stored prompt injection. | Security | **High** | `services/assistant_service.py:1341-1357` |
| 5 | **AI credits are not enforced.** A zero balance is reported as 100, nothing calls `redeem`, and `credits/purchase` accepts any `user_id` with no admin check (it is broken today only because the service is null). The only spend control left is the \$5/day DynamoDB cap, and that cap **fails open**. | Cost / Security | **High** | `AiController.php:69-73, 134-157`; `daily_usage_service.py:26`; `main.py:213` |
| 6 | **Real student PII reaches the lambda in `scrub_names`.** It carries first name, last name, email and username, and the service scrubs them before Bedrock. That contradicts the "no name leaves the browser" invariant. Telemetry redaction does not visibly cover `scrub_names`. | Privacy | **High** | `frontend-v3/ai/context/scrubNames.ts:27-52`; `rag core/telemetry.py:86` |
| 7 | **Prod `/v3/*` routes serve `$LATEST`,** which is unpromoted code. Two ECR repos have mutable tags. | Infra | **Med-High** | `modules/api-gateway/routes.tf:13-78`; `main.tf:19,26` |
| 8 | **Per-turn cost is about 35–50× what the docs say.** Measured cost is about $0.021 per turn on Sonnet 5; the swo docs still quote Nova at $0.0005–0.0007. The worst case is about \$1.54 per turn (budget 400k in and 60k out, 12 calls). | Cost | **Med-High** | `rag core/config.py:19-36,165-182`; `experiments/cost_speed_7526/RESULT.md` |
| 9 | **Page context is sent twice** (`cp_content` plus prose `page_context`), and `page_content` goes up to 14.5k characters. Both are re-sent on each of up to 5 legs of a turn. The server accepts up to 100k characters of page text. | Cost | **Med** | `useAiChat.ts:240-366`; `pageText.ts:170`; `core/config.py:177` |
| 10 | **Conversations are kept for 5 years** (`mongodb_ttl_days = 1826`) in a K-12 product. The authorizer log group never expires. Full request and response bodies are logged. | Privacy / Infra | **Med** | `envs/prod.tfvars:40`; `main.py:241`; `assistant_service.py:500` |

```mermaid
quadrantChart
    title Leads: likelihood of being real vs impact
    x-axis Low likelihood --> High likelihood
    y-axis Low impact --> High impact
    quadrant-1 Fix now
    quadrant-2 Verify quickly
    quadrant-3 Backlog
    quadrant-4 Cheap wins
    Leaked creds in git: [0.9, 0.95]
    Authorizer host trust: [0.8, 0.85]
    Search IDOR: [0.75, 0.75]
    thread/record write: [0.75, 0.8]
    Credits not enforced: [0.9, 0.65]
    scrub_names PII: [0.85, 0.7]
    $LATEST in prod: [0.8, 0.55]
    Double page context: [0.7, 0.4]
    5-yr retention: [0.9, 0.5]
    AI code in student bundle: [0.6, 0.25]
```

---

## 2. System map

### 2.1 Components and trust boundaries

```mermaid
flowchart LR
    subgraph Browser["Teacher's browser (frontend-v3, Nuxt 3, ssr:false)"]
        UI["AiAssistantDialog / useAiChat"]
        SURF["useAiSurface: page card<br />cp_content ≤36, page_content ≤14.5k"]
        EXEC["executor.ts<br />run() → verify()"]
        RED["redact.ts / roster.ts<br />pseudonyms + scrub_names"]
        UI --> SURF --> RED
        EXEC --> UI
    end

    subgraph AWS["AWS us-west-2 (rag/infra/swo)"]
        APIGW["HTTP API Gateway<br />throttle 5k/10k prod<br />no WAF"]
        AUTHZ["authorizer λ<br />128MB · 15s · no VPC<br />cache 60s (token+route)"]
        V1["ai-assistant λ (v1 doors)<br />2048MB · 29s · RC 50<br />aliases stable-v3 / development=$LATEST"]
        FURL["Function URL<br />auth NONE · RESPONSE_STREAM"]
        V2["scout-core-v2 λ<br />LWA + uvicorn · RC 25 · ≤210s<br />alias live"]
        DDB[("DynamoDB daily_usage<br />$5/user/day · fail-open")]
        SSM[("SSM /swo-genai-pov/env/*")]
        BR["Bedrock<br />Sonnet 5 + Haiku 4.5 (v2)<br />Nova Lite (v1) · Guardrails MEDIUM"]
        NAT["VPC private subnets → NAT EIP"]
        ECS["ECS Fargate content-sync<br />hourly / weekly"]
        S3[("S3 ai-export")]
    end

    subgraph SaaS["External SaaS"]
        MONGO[("MongoDB Atlas<br />threads · checkpoints<br />TTL 1826 days")]
        PC[("Pinecone<br />prod/stage-rag-index")]
        OAI["OpenAI embeddings"]
    end

    subgraph Laravel["swo-3.0 backend (Laravel 9)"]
        LAPI["api/ai/*<br />user/credits · stats · actions<br />memories · briefing · search-index"]
        PG[("Postgres<br />ai_stats · ai_actions<br />ai_user_packages")]
        LAPI --> PG
    end

    UI -- "Bearer JWT + ?host=" --> APIGW --> AUTHZ
    AUTHZ -- "GET user/credits (token, host-derived URL)" --> LAPI
    APIGW --> V1
    UI -- "POST /v2/turn SSE + JWT" --> FURL --> V2
    V2 -- "credits check (30s cache, host allowlist)" --> LAPI
    V2 -- "remember/forget with teacher JWT" --> LAPI
    V1 & V2 --> NAT --> MONGO & PC & OAI
    V1 & V2 --> BR
    V1 & V2 --> DDB
    V1 & V2 --> SSM
    LAPI -- "ai:export-content" --> S3 --> ECS --> PC
    LAPI -- "search-index (sync, 60s)" --> APIGW

    classDef risk fill:#fde2e2,stroke:#c0392b,color:#000
    class AUTHZ,FURL,DDB,MONGO risk
```

Nodes shaded red are where the high-severity security and cost leads sit.

### 2.2 One chat turn, end to end (the cost path)

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser (useAiChat)
    participant F as Function URL → scout-core-v2
    participant L as Laravel api/ai
    participant D as DynamoDB
    participant M as Mongo (thread)
    participant BR as Bedrock (Sonnet/Haiku)
    participant P as Pinecone + OpenAI

    B->>B: buildPageCard() → cp_content + page_context + page_content
    B->>B: pseudonymise, identity audit (warn only), attach scrub_names
    B->>F: POST /v2/turn (JWT, ?host, thread_id, card, scrub_names)
    F->>L: GET user/credits (cached 30s, host allowlisted)
    F->>D: daily spend check (pre-call; fail-open)
    F->>M: load whole thread doc (≤12MB)
    loop ≤12 model calls, ≤3 tools/step, budget 400k in / 60k out
        F->>BR: tools(7k) + constitution(7k) [1h] + teacher [5m] + page ctx [5m] + last 40 msgs [5m]
        BR-->>F: stream tokens (SSE to browser, 10s heartbeat)
        opt search_curriculum
            F->>P: embed (LRU 512) + query (pool 60/150)
            F->>BR: Haiku relevance judge: ≤13 batches, re-send after 3s
        end
        F-->>M: cancel poll every 0.5s
    end
    F->>M: replace_one(thread) + Haiku summary of >40 msgs
    F->>D: record spend (post-call)
    F-->>B: final + pending_action?
    opt page action (≤4 legs)
        B->>B: executor: forbidden / plan / confirm / run / verify
        B->>F: action_result + FULL page card again (new turn leg)
    end
    B->>F: title call after first reply (extra model call)
```

### 2.3 Two generations of code live side by side

| | v1 "gateway doors" | v2 "Scout Core" |
|---|---|---|
| Entry | API Gateway + authorizer λ | Lambda Function URL (auth in code) |
| Code | `services/assistant_service.py`, `agents/` (LangGraph) | `lambdas/ai_assistant/src/core/` |
| Model | Nova Lite (prod tfvars) | Sonnet 5 + Haiku 4.5 |
| Identity | authorizer context | in-code JWT check, host allowlist, rejects a mismatched body `user_id` |
| Threads | LangGraph `MongoDBSaver` | `core/threads.py` whole-document |
| Routes | `/assistant/*`, `/generate`, `/level-content`, `/v3/*` | `/v2/turn`, `/v2/turn/cancel`, grading |

> The audit must cover **both**. Most of the security leads (#2–#4) are in v1 code that is still deployed and
> still reachable, even though the product flow now goes through v2.
> `question_process` and `content_adaptation_process` have **no tracked source** any more; only `__pycache__`and `.env` remain. Confirm whether they are still deployed.

---

## 3. Where the tokens and dollars go

### 3.1 Anatomy of a typical turn (measured, `experiments/cost_speed_7526`)

The measured per-turn mix is about 20k cache-read tokens, about 4.8k cache-write tokens and about 290 output tokens.

The prices below come from `core/config.py:32-36`. The cache multipliers (0.1× for reads, 1.25× for writes) are Bedrock's.

| Component | Tokens | Rate (\$/M) | \$/turn | Share |
|---|---|---|---|---|
| Cache **write** | 4,800 | 2.75 | 0.0132 | **\~63%** |
| Cache read | 20,000 | 0.22 | 0.0044 | \~21% |
| Output | 290 | 11.00 | 0.0032 | \~15% |
| **Total** | | | **≈ \$0.021** | matches the measured \$0.0211 |

```mermaid
pie showData
    title Typical v2 turn cost split (USD × 10⁻⁴)
    "Cache write (~4.8k tok)" : 132
    "Cache read (~20k tok)" : 44
    "Output (~290 tok)" : 32
```

> **Insight to verify:** cache writes, not output, dominate turn cost. Anything that busts a cache layer pays 1.25× (or 2× for the 1-hour core layer) instead of 0.1× on the next call:
>
> - page context changing between legs
> - Plan↔Agent mode changing the tool list and the mode wording
> - teacher memory changing (`remember` / `forget`)
> - a teacher idle for more than 5 minutes
>
> Cutting cache writes is the biggest single lever.

> **The layout changed after this measurement.** On `rag` `ONLINE-5385_scout_ai_integration` @ `86d92ea0`,
> tools + constitution share a **1-hour** checkpoint billed at 2× input (\$4.40/M on Sonnet 5), and the
> teacher block has its own layer. The \$0.021 figure predates this; A1.1 must re-measure it. The full
> boundary map, with code snippets, is in [cache.md](cache.md).

### 3.1a Cache boundaries in one picture (current code)

```mermaid
flowchart LR
    T["tools<br/>(page_action only in Agent)"] --> C["constitution"] --> CP1(["① 1h"])
    CP1 --> TE["teacher"] --> CP2(["② 5m"])
    CP2 --> PG["page · article · capabilities<br/>+ acting_block(mode)"] --> CP3(["③ 5m"])
    CP3 --> LV["scope · summary · mode_block<br/>(not cached)"] --> H["history"] --> CP4(["④ 5m"])
```

| Layer | Defined in | Busted by |
|---|---|---|
| ① tools + constitution, 1h | `core/runtime.py:1415` `_system_blocks()`; `CORE_CACHE_POINT` at `core/loop.py:38` | deploy; first Plan↔Agent switch in an hour (each mode has its own entry) |
| ② teacher, 5m | `_system_blocks()`; block from `core/context/teacher.py` | memory or teacher-context change; 5 min idle |
| ③ page, 5m | `_system_blocks()`; `cache` flag on `ContextBlock` (`core/context/types.py:20`) | page change, navigation, mode switch; 5 min idle |
| ④ history, 5m | `core/loop.py` `with_history_cache_point()` / `build_request()` | expected growth each turn |

### 3.2 Multipliers that inflate one user-visible turn

```mermaid
flowchart TD
    T["1 teacher message"] --> L1["Leg 1: up to 12 model calls"]
    L1 -->|pending_action| L2["Leg 2..5: full page card re-sent<br />(MAX_ACTION_STEPS = 4)"]
    L1 --> S["search_curriculum:<br />≤13 Haiku judge calls<br />+ duplicate on 3s re-send"]
    L1 --> E["Engines: level / questions / compose<br />Sonnet per section (×4 concurrent)<br />+ Haiku verify per chunk + repair round"]
    E --> R["Retries: botocore 3 adaptive × app 2<br />+ idle retry on loop<br />(abandoned attempts report no usage)"]
    L1 --> X["Post-turn: Haiku summary (>40 msgs)<br />+ title call (first reply)"]
    style R fill:#fde2e2,stroke:#c0392b
    style S fill:#fff3cd,stroke:#b8860b
    style L2 fill:#fff3cd,stroke:#b8860b
```

### 3.3 Bounds and projections

- **Worst case per turn:** 400k × $2.20/M + 60k × $11/M ≈ **$1.54**. The $5/day cap is checked *before* each turn and recorded *after* it. That means 3 parallel worst-case turns, or turns already in flight, can go well past the cap.
- **Projection formula** for the report. Fill it in with real telemetry:
  `monthly $ = active_teachers × turns/teacher/day × school_days × $/turn × (1 + engine_share + retry_share)`.
  - Illustrative only: 1,000 teachers × 15 turns × 20 days × $0.021 ≈ **$6.3k/month** before engines and retries.
  * The same load on the worst-case tail is unbounded except by the $5 cap: 1,000 teachers × $5 × 20 days = \$100k/month.
- **Fixed costs to include** (they are missing from every existing cost figure, per ProductionReadiness §3.5):
  - NAT gateway hours plus data processing (all Bedrock, OpenAI, Pinecone and Mongo traffic)
  - Fargate content-sync
  - Atlas tier
  - Pinecone pods or serverless
  - CloudWatch ingestion: full bodies are logged
  - Guardrails per-text-unit charges

---

## 4. Audit method, phases and timeline

### 4.1 Approach

1. **Static review.** Read code against each checklist item, record `file:line`, and treat no finding as real until it is reproduced.
2. **Dynamic testing on local and dev.** Use the existing harnesses (`__route.ts`, `__chain.ts`, `run_gate.py`, `check_*.py`) plus targeted curl tests in §10.
3. **Telemetry mining.** Read the per-turn telemetry rows (`core/telemetry.py`, `observe.py`), CloudWatch Logs Insights, Cost Explorer (tag or service filter), and DynamoDB `daily_usage`.
4. **Infra review.** Run `terraform plan` (read-only) plus `tfsec`/`checkov`, compare the deployed state with the repo (aliases, image digests, tfvars), and look at IAM Access Analyzer.
5. **Dependency and secret scanning.** `gitleaks` or `trufflehog` over **full history** in both repos; `pip-audit` per lambda; `bun audit` / `npm audit`; `composer audit`; ECR scan results.

> **Rules of engagement:**
>
>

### 4.2 Phases

```mermaid
gantt
    title AI code audit: 3 weeks (adjust to team size)
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d
    section 0. Triage
    Verify & contain Critical leads (#1-#4)   :crit, t0, 2026-10-05, 2d
    section 1. Baseline
    Env setup, access, telemetry export        :b1, 2026-10-05, 2d
    Cost baseline (run_gate, __route, CE)      :b2, after b1, 2d
    section 2. Workstreams
    A Cost & tokens                            :a, after b2, 4d
    B Infrastructure                           :b, 2026-10-07, 5d
    C Performance                              :c, after b2, 4d
    D Security & privacy                       :crit, d, 2026-10-07, 7d
    section 3. Report
    Consolidate, severity, remediation plan    :r1, after d, 2d
    Readout + re-test window                   :r2, after r1, 2d
```

### 4.3 Coverage map

| Area | rag `core/` (v2) | rag v1 services | authorizer | infra/swo | frontend-v3 `ai/` | Laravel `api/ai` |
|---|---|---|---|---|---|---|
| A Cost | ●●● | ●● | ○ | ●● | ●●● | ●● (credits) |
| B Infra | ● | ● | ●● | ●●● | ○ | ● |
| C Perf | ●●● | ●● | ● | ●● | ●●● | ●● |
| D Security | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● |

---

## 5. Workstream A: Cost and token usage

**Goal:** a defensible $/turn and $/feature number, a list of the multipliers, a hard upper bound per user and per org, and a ranked list of savings.

### A1. Baseline measurement (do first)

| ID | Task | How | Output |
|---|---|---|---|
| A1.1 | Re-run the history-caching cost gate on HEAD | `experiments/cost_speed_7526/run_gate.py` | \$/turn by turn index; TTFT/total p50 and p95 |
| A1.2 | Per-capability token baseline from the browser side | `npx vite-node ai/context/__route.ts --runs=3 --json=…` | tokens per capability, routing accuracy |
| A1.3 | Production distribution from telemetry rows | §10 queries on `llm_calls`, `cache_read/write`, `retries`, `cost_usd`, `estimated` | histograms (p50/p95/p99/max) |
| A1.4 | Spend by service in Cost Explorer | Bedrock (per model and inference profile), NAT, Lambda, Fargate, CloudWatch, Guardrails | monthly table, dev vs prod |
| A1.5 | Reconcile telemetry `cost_usd` with the Bedrock bill | sum telemetry for a day against CE for the same day | drift %. If above 10%, find the gap (abandoned retries report no usage) |

### A2. Prompt and context size

| ID | Check | Evidence / lead | Pass criterion |
|---|---|---|---|
| A2.1 | Size of the constitution and tool specs on every call, and whether both are cached | \~7k + \~7k tokens; both behind the 1-hour checkpoint ① (`core/runtime.py:1415-1440`) | Hit rate on ① ≥ 95% across teachers; ① written about once an hour per mode |
| A2.2 | **Duplicate page facts:** `cp_content` and `page_context` both sent | `useAiChat.ts:240-249, 328-330`; `rag schemas/models.py:115` | Only one representation reaches the model. Measure the delta with `window.__aiContextDebug = true` |
| A2.3 | `page_content` cap: 14.5k in code, 6k in the docs. Find the source of the 4.8× token amplification | `pageText.ts:170`; BudgetAudit lines 172-203 | Cap documented and chosen from data; no double-counting in the context |
| A2.4 | **Server-side input caps:** page text 100k, message 8k | `core/config.py:177-178` | Server cap at most about 1.5× the client cap (proposed 10k) |
| A2.5 | History replay: 40 verbatim messages × 20k-char tool results worst case | `core/context/history.py:37`; `config.py:187` | Measure input tokens at 10, 20 and 40 turns; summariser cost per thread |
| A2.6 | Tool-result truncation stays visible (StartHere invariant) | `_MAX_CHARS`, 20k cap with notice | No result is cut in the middle of JSON. Fuzz with large results |
| A2.7 | `cp_content` caps: the paired rag limit (`tools/cp_content.py`) is gone | `cpContent.ts:90-122` (36 entries / 1,400 chars) | Find the v2 equivalent; both sides agree |

### A3. Cache efficiency (the biggest lever, see §3.1 and [cache.md](cache.md))

The layers are ① tools + constitution (1 h), ② teacher, ③ page and ④ history (5 min each). See §3.1a.

| ID | Check | How |
|---|---|---|
| A3.1 | Cache-write tokens per turn, by layer | Join `cache_tools_h` / `cache_instructions_h` / `cache_teacher_h` / `cache_page_h` from `core/cache_layers.py` with `cache_write_tokens` per call |
| A3.2 | Cost of Plan↔Agent switches | `page_action` is Agent-only (`core/tools/__init__.py` `AGENT_ONLY`) and the tools sit under ①, so each mode has its own 1-hour entry; `acting_block(mode)` sits inside ③. Count 1h writes (`cacheDetails` ttl=1h) around switches. If they are frequent, consider sending `page_action` in both modes and refusing it in code |
| A3.3 | Page card changes between action legs bust ③ | `__chain.ts` with an action that changes the page; compare `cache_page_h` across legs |
| A3.4 | Does the 1-hour core pay off | Writes of ① per hour per mode in prod. A 1h write costs 2× vs 1.25×, so it only pays off if ① would otherwise be written again more than about 1.6 times an hour. Also: share of turns more than 5 min after the previous one (② ③ ④ re-written) |
| A3.5 | Engine caching (`core/engines/llm.py:142`) | Hit rate per engine. Non-streaming calls default to `cache_system=False` (`llm.py:374`); check whether any of them repeat the same article |
| A3.6 | v1 caches the system prompt only | `services/assistant_llm_service.py:488-498`: Nova rejects a `cachePoint` in the tool list. Measure the v1 cache-read share |
| A3.7 | Cache cost matches the bill | Telemetry `cost_usd` (which prices 1h writes separately, `core/config.py:265-272`) vs the Cost Explorer Bedrock usage types for the same day |
| A3.8 | Nothing per-turn before a checkpoint | `check_request_text_pin.py` covers the constitution. Add a check that no dates or ids enter the teacher or page blocks |

### A4. Call multipliers and loops

| ID | Check | Evidence | Pass criterion |
|---|---|---|---|
| A4.1 | Steps per turn vs the cap of 12 | `core/loop.py:1040-1050` | p99 ≤ 6. Alert when a turn reaches the cap |
| A4.2 | Relevance judge fan-out and the **3 s duplicate re-send** | `core/context/relevance.py:34-47, 209-233` | Measure the duplicate-billing rate. Consider cancelling the original or skipping the judge for small pools |
| A4.3 | Stacked retries: botocore 3 × app 2 × repair | `engines/llm.py:126-130, 333-395`; `level.py:386-400` | Worst-case calls per engine invocation documented; usage of abandoned attempts estimated |
| A4.4 | Levelling cost by article length | `engines/level.py:620-635, 839` | \$/article curve; sections × (Sonnet + Haiku check) |
| A4.5 | Question generation cost per set | `engines/questions.py:279-447` | \$/set, repair-round rate |
| A4.6 | Browser legs re-send the full card (up to 5×) | `useAiChat.ts:616, 655, 691, 763, …` | Tokens per leg from `__chain.ts`. Consider a delta or cached card |
| A4.7 | Calls with no user click: title, `scoutMemory.fetchContext`, warm-up stream on cold start | `useAiActionRecord.ts:128`; `AiAssistantRoot.vue:88-101`; `core/runtime.py:2323` | Each one justified, or made cheaper (Haiku / template) |

### A5. Spend controls and billing integrity

```mermaid
flowchart LR
    REQ[Turn request] --> C1{"Laravel credits ≥ min?"}
    C1 -- "balance 0 → reported as 100 (!)" --> C2{"DynamoDB spend < $5 today?"}
    C2 -- "DDB error → ALLOW (fail-open)" --> RUN[Run turn ≤ $1.54]
    C2 -- "yes" --> RUN
    RUN --> REC["Record spend AFTER<br />(concurrent turns overshoot)"]
    REC -.->|"never"| REDEEM["Laravel credits/redeem<br />(no caller)"]
    style C1 fill:#fde2e2
    style REDEEM fill:#fde2e2
    style C2 fill:#fff3cd
```

| ID | Check | Evidence | Pass criterion |
|---|---|---|---|
| A5.1 | A zero or null balance is shown as 100 | `AiController.php:69-73` | Product decision recorded. If credits are meant to gate, enforce them |
| A5.2 | Nothing calls `redeem`; credits are cosmetic | grep both repos | Either wire it up atomically or delete the dead surface |
| A5.3 | `redeem` race (no `lockForUpdate`), `(int)` cast on fractional amounts | `AiController.php:182-218` | Atomic decrement; concurrency test |
| A5.4 | `getUserBalance` ignores `expires_at` and `status` | `UserPackage.php` | Expired or refunded packages excluded |
| A5.5 | Daily cap overshoot from parallel turns | 3–5 parallel `/v2/turn` with a large page | Overshoot bounded (for example, an in-flight reservation/lease of estimated cost) |
| A5.6 | Daily cap fails open on a DynamoDB error | `main.py:213`; `lambda_stream.py:303`; `throttle.py:169-191` | Alarm on fail-open events at least; ideally fail closed above a cost threshold |
| A5.7 | No per-org or per-district cap; no global circuit breaker | `daily_usage_service.py` | Org cap and account-level Bedrock spend alarm (Budgets) |
| A5.8 | `ai_stats` cost and token fields are self-reported by the client | `AiController.php:351-361` | Billing and reports use server telemetry only |
| A5.9 | `x-swo-synthetic` header hides real traffic from dashboards | `main.py:128-135`; `observability.tf:178` | Header honoured only for allowlisted test identities |

### A6. Model selection

| ID | Check |
|---|---|
| A6.1 | Sonnet vs Haiku share of spend per feature; candidates to move to Haiku (classification, titles, checks) |
| A6.2 | Engine model ids are read at import (`engines/llm.py:47-48`), but `get_core_config` reads per call. Confirm deployed env vars match |
| A6.3 | `max_tokens` 32k on the loop vs the real output distribution (p99). Lower it to limit runaway generation |
| A6.4 | Pricing table freshness: `scripts/pricing_update.py`, `check_pricing_table.py`; unknown models priced at the dearest rate |
| A6.5 | Re-record the model-choice cost basis. ModelEvaluation says "stay on Nova" and was overtaken without a recorded decision |

---

## 6. Workstream B: Infrastructure

### 6.1 Deployed topology to verify against the repo

```mermaid
flowchart TB
    subgraph Edge
        GW["HTTP API GW<br />throttle prod 5k rps / 10k burst<br />no usage plan · no WAF"]
        FU["Function URL (auth NONE)"]
    end
    subgraph Aliases["Lambda aliases"]
        ST["stable-v3 → pinned version"]
        DEV["development → $LATEST ⚠"]
        LIVE["live (core v2)"]
    end
    GW -- "/assistant, /generate, /level-content" --> ST
    GW -- "/v3/* (prod too!)" --> DEV
    FU --> LIVE
    subgraph Images["ECR"]
        I1["assistant: MUTABLE ⚠"]
        I2["content-sync: MUTABLE ⚠"]
        I3["core-v2: IMMUTABLE ✓"]
    end
    ST & DEV --> I1
    LIVE --> I3
    subgraph Net["VPC"]
        PRIV["private subnets"] --> NATG["NAT GW (EIP on Atlas allowlist)"] --> INET(("Internet:<br />Bedrock, OpenAI,<br />Pinecone, Atlas"))
    end
    ST & DEV & LIVE --> PRIV
```

### B-checklist

| ID | Check | Evidence | Pass criterion |
|---|---|---|---|
| B1 | **Prod `/v3/*` → `development` = `$LATEST`** | `modules/api-gateway/routes.tf:13-78`; `lambda-container/main.tf:71-75` | Prod routes only to promoted, versioned aliases |
| B2 | Mutable ECR tags for assistant and content-sync | `main.tf:19,26` | IMMUTABLE; deploy by digest |
| B3 | Deployed model and alias match the repo ("cannot tell": `terraform.tfvars` is untracked) | DeployedRealityAudit | Drift report: `aws lambda get-alias`, image digest, env vars vs repo |
| B4 | Reserved / provisioned concurrency: v1 50, v2 25, authorizer none | `main.tf:285-318`; `monitoring.tf:62` | Sized to load test; authorizer gets reserved concurrency |
| B5 | Timeouts chain (v1: API GW 29s / λ 29s / service 25s; v2: 210s / turn 180s / idle 45s) | `core/config.py:160-165` | Each layer shorter than the one outside it; no orphan billing after a client disconnects |
| B6 | No VPC endpoints: Bedrock, DynamoDB, SSM, ECR and CloudWatch all go through NAT | none in `*.tf` | Gateway endpoints (DynamoDB, S3) and interface endpoints (Bedrock, SSM, Logs) if NAT cost justifies them |
| B7 | Security group egress `0.0.0.0/0` all ports | `lambda-container/security_groups.tf:17-49` | 443 only (plus the Atlas port) |
| B8 | IAM wildcards: `foundation-model/*`, `inference-profile/*` all regions, `guardrail/*`, `execute-api:*:*:*/*/*` | `lambda-container/iam.tf:94-137` | Scoped to the model ARNs and guardrail actually used; use the core-v2 role as the model |
| B9 | No WAF; gateway throttle 5k rps is far above reserved concurrency | `modules/api-gateway/main.tf:26-27` | WAF with rate-based rule per IP and per token; throttle sized to RC |
| B10 | Function URL `auth NONE`: only in-code auth plus RC 25 | `modules/scout-core-v2/main.tf:153` | Accept with justification, or put it behind CloudFront with WAF |
| B11 | X-Ray off despite Powertools `Tracer` | no `tracing_config` | Active tracing on both λ (sampled) |
| B12 | Log retention: authorizer group missing (never expires); λ 30/7 days | `modules/lambda-zip/main.tf` | Managed group with retention; data-classification review |
| B13 | Alarms "fire to nothing"; dashboard doesn't cover the assistant | ProductionReadiness §3.1-3.2 | SNS subscribed; alarms for 5xx, throttles, fail-open, cost/hour, Bedrock throttling |
| B14 | Single region, no Bedrock throttling or retry policy | ProductionReadiness §3.7 | Cross-region inference profile documented; quota headroom checked (`service-quotas`) |
| B15 | Mongo TTL 1826 days; validation block commented out | `envs/prod.tfvars:40`; `variables.tf:119` | Retention set by policy; validation restored |
| B16 | DynamoDB PITR prod only; Atlas backup tier | `versions.tf`, Atlas console | Documented RPO/RTO |
| B17 | Terraform state: S3 encrypted plus locking ✓; tracked `output.txt` and `changes.json` dumps | `infra/swo/` | Dumps removed from git (account IDs, role ARNs, email) |
| B18 | Build tooling: root Makefile now delegates to `infra/swo` (the CLAUDE.md note is stale) | `Makefile:107-132` | Every documented target works; CI does the deploy, not laptops |
| B19 | Are `question_process` / `content_adaptation_process` still deployed with no source in git? | `git ls-files` = 0 | Retire or restore the source; no unreviewable code running |
| B20 | Laravel `AISearchController::getSearchIndex`: sync `Http::timeout(60)` holds an FPM worker | `AISearchController.php:60` | Lower timeout plus cache, or drop it if unused |

---

## 7. Workstream C: Performance

### 7.1 Latency budget of a v2 turn (measured p50; p95 in brackets)

```mermaid
gantt
    title v2 turn latency budget (p50 ≈ 8.5s, p95 15–18s)
    dateFormat  X
    axisFormat  %s
    section Before model
    Auth: Laravel credits (cached 30s)    :0, 300
    Daily-cap check (new boto3 client)    :300, 450
    Load thread doc (whole, ≤12MB)        :450, 800
    section Model
    TTFT (p50 ~6s, p95 12–14s)            :crit, 800, 6100
    Stream remainder + tools              :6100, 8000
    section After
    replace_one thread + summary          :8000, 8500
```

*Segment widths before TTFT are placeholders. Workstream C's first job is to replace them with measured values
taken from telemetry (`ttft_ms`) and X-Ray spans.*

### C-checklist

| ID | Check | Evidence | Method / target |
|---|---|---|---|
| C1 | Cold start: fat image (langchain, langgraph, and others that v2 doesn't use), VPC ENI, warm-up Haiku call | `pyproject.toml:37-57`; `runtime.py:2323` | CloudWatch `InitDuration` p50/p95; image size; split v2 deps out of the image |
| C2 | Whole-thread load and `replace_one` each turn; 12 MB cap | `core/threads.py:230-294` | Save latency vs thread size; consider append-only messages |
| C3 | Cancel poll does a `find_one` every 0.5 s per running turn | `core/config.py:175` | Mongo ops/turn; consider a longer interval or change streams |
| C4 | v1 `asyncio.run()` per invocation; sync pymongo/boto3 in `to_thread` | `main.py:58-77` | Concurrency profile; thread-pool saturation under load |
| C5 | New boto3 client per daily-cap check | `daily_usage_service.py:44-80` | Module-level client reuse |
| C6 | Relevance judge: 16 parallel Haiku calls | `relevance.py` | Search tool p95; Bedrock throttling events |
| C7 | Embedding LRU is per process and lost on cold start | `core/context/index.py:104-170` | Hit rate; consider caching common queries |
| C8 | Laravel `user/credits` runs the readable-publications query every turn (v2 bypasses the 30 s authorizer cache) | `AiController.php:96-108`; `lambda_stream.py:62` | Query time; add a cache |
| C9 | `ai_stats` missing indexes on `user_id`, `created_at`; varchar `user_id` with regex CAST join | `pgsql-schema.sql:41465-41479`; `AiReportController.php:1293` | `EXPLAIN ANALYZE` on reports at real row counts |
| C10 | `AiReportController` N+1 per model or feature, loading every row for medians in PHP | `AiReportController.php:240-245, 508-560` | Push percentiles into SQL (`percentile_cont`) |
| C11 | `ai_user_packages.user_id`, `ai_credit_transactions.user_id` unindexed FKs | schema.sql:22967, 47884 | Add indexes |
| C12 | **Frontend bundle:** `ai/context/index.ts` barrel (about 80 modules, executor 2,366 lines) imported statically by 137 files; Root imported eagerly | `layouts/default.vue:13` | `npx nuxi analyze`; AI code out of student and flag-off chunks |
| C13 | Streaming paint re-renders the full markdown and `buildPageCard()` every 80 ms (roughly quadratic) | `AiCoreLiveReply.vue:29-41`; `AiAssistantDialog.vue:2824` | Performance profile on a 2k-token reply; target < 8 ms per frame |
| C14 | Deep watchers on `store.messages` (persistence and scroll) | `useAiPersistence.ts:405-421`; `AiAssistantDialog.vue:2215` | Profile long threads; shallow watch with a version counter |
| C15 | Surface watcher cleanup on unmount | `useAiSurface.ts:50-115` | Heap snapshot after 20 navigations; no growth |
| C16 | Load test | k6/Artillery on dev: 25 → 50 → 100 concurrent turns | Throttles, 5xx and p95 at RC saturation; Bedrock quota headroom |

---

## 8. Workstream D: Security and privacy

### 8.1 Trust boundaries and attack surface

```mermaid
flowchart LR
    ATT(["Attacker:<br />any teacher account,<br />or a token from another env"])
    subgraph TB1["Boundary 1: browser → AWS"]
        Q["?host= param"]
        BODY["body: user_id, thread_id,<br />message_id, scrub_names"]
        HDR["x-swo-synthetic"]
    end
    subgraph TB2["Boundary 2: AWS → Laravel"]
        AZ["authorizer → host-derived<br />Laravel URL"]
        MEM["remember/forget tools<br />with teacher JWT"]
    end
    subgraph TB3["Boundary 3: content → model"]
        PCC["Pinecone docs"]
        ART["article HTML"]
        HIST["recorded thread turns"]
    end
    ATT --> Q -->|"no allowlist (F1)"| AZ
    ATT --> BODY -->|"search/message no owner (F2)<br />thread/record no owner (F3)"| HIST
    ATT --> HDR -->|"hide from dashboards"| X1["telemetry"]
    HIST & PCC & ART -->|"prompt injection"| MODEL["Model"] --> MEM -->|"delete_all_memories,<br />no confirmation"| L[("Teacher memory")]
    MODEL --> PA["page_action → browser<br />executor (confirm + verify) ✓"]
    style AZ fill:#fde2e2
    style HIST fill:#fde2e2
    style MEM fill:#fff3cd
    style PA fill:#e2f5e2
```

### 8.2 STRIDE summary

| Threat | Where | Lead | Test (§10) |
|---|---|---|---|
| **S**poofing | authorizer host trust; cross-env tokens | F1 | D-T1 |
| **T**ampering | `thread/record` into foreign thread; ECR mutable tags; `$LATEST` in prod | F3, B1-B2 | D-T3 |
| **R**epudiation | `x-swo-synthetic` hides traffic; client-reported `ai_stats` | A5.8-9 | D-T7 |
| **I**nfo disclosure | search IDOR; creds in git; `str(e)` in errors; bodies in logs; `scrub_names` | F2, F6, F9, F16 | D-T2, D-T5 |
| **D**enial of service / wallet | fail-open caps; 100k page text; no WAF; credits not enforced | A5, B9 | D-T6 |
| **E**levation | `credits/purchase` any `user_id` (latent); `credits/expire` no admin; model-triggered memory wipe | Laravel, F12 | D-T4, D-T8 |

### D-checklist

**D1 — Authentication and authorization (rag)**

| ID | Check | Evidence |
|---|---|---|
| D1.1 | Authorizer host allowlist; fallback to prod on a missing or `localhost` host | `authorizer/src/lambda_handler.py:39-79` |
| D1.2 | Authorizer cache key leaves out host (`Authorization`, `routeKey`; 60 s) | `modules/api-gateway/main.tf:61-63` |
| D1.3 | Wildcard Allow policy per route prefix | `policy_generator.py:115-124` |
| D1.4 | Every v1 route that takes `thread_id` / `message_id` / `user_id` enforces ownership: enumerate all of them, not only the two found | `assistant_service.py` (load/delete ✓, record ✗, search/message ✗) |
| D1.5 | v1 thread routes: does the frontend send body `user_id`, and is it ever trusted? | `assistantClient.ts:450-470, 690-703` |
| D1.6 | v2 JWT validation: signature, `exp`, audience; mismatched body `user_id` rejected ✓ | `core/lambda_stream.py:188-225`; `core_router.py:41-84` |
| D1.7 | Checkpoint / message id guessability (uuid6 is time-based) and where ids leak | LangGraph; logs; responses |

**D2 — Laravel `api/ai/*`**

| ID | Check | Evidence |
|---|---|---|
| D2.1 | `credits/purchase` without admin check, arbitrary `user_id` | `AiController.php:134-157` |
| D2.2 | `credits/expire` without admin check | `:255` |
| D2.3 | `user/credits` (used by the authorizer): what it returns to students; no route-level feature middleware | `:64-84` |
| D2.4 | `POST /feedback` always 500 (`AiFeedback` model missing) | `:20, :462` |
| D2.5 | Unbounded jsonb (`stats.response`, `feedback.response_details`); no throttle on stats/feedback/redeem/decline/result | routes 1395-1429 |
| D2.6 | "Teacher-only" student-insights / misconceptions / pacing routes: verify role checks exist | routes 1482-1530 |
| D2.7 | `search-index` builds `host` from the `Origin` header and echoes upstream body and host in errors | `AISearchController.php:54-71` |

**D3 — Privacy (K-12: FERPA / COPPA / state student-privacy laws)**

| ID | Check | Evidence |
|---|---|---|
| D3.1 | **`scrub_names` carries real names, emails and usernames to the lambda.** Prove they never reach Mongo checkpoints, telemetry, CloudWatch, error bodies or Bedrock. Measure scrub recall | `scrubNames.ts:27-52`; `core/name_scrub.py`; `core/telemetry.py:86` |
| D3.2 | Identity audit is `'warn'` and dev-only, so a surface publishing a real name ships silently in prod | `redact.ts:151-233` |
| D3.3 | Every student-publishing surface goes through `publicFacts()` (allowlist ✓); grep for bypasses | `roster.ts:815-828` |
| D3.4 | Full request and response bodies logged | `main.py:145, 176, 241`; `assistant_service.py:500` |
| D3.5 | Laravel logs `$request->all()` (assistant I/O) on failure | `AiController.php:436, 491` |
| D3.6 | Retention: Mongo 5 years, authorizer logs forever, `ai_stats` / `ai_actions` no pruning, sessionStorage transcript with real names survives logout | `prod.tfvars:40`; `useAiPersistence.ts` |
| D3.7 | Data processing terms: OpenAI embeddings and Pinecone receive curriculum and query text. Confirm no student data and confirm DPAs | `core/context/index.py` |

**D4 — Prompt injection and model-driven actions**

| ID | Check | Evidence |
|---|---|---|
| D4.1 | Server-side tools that write with the teacher's JWT without confirmation (`forget.delete_all_memories`, `remember`) | `core/tools/forget.py:63`; `remember.py` |
| D4.2 | Browser executor: write capabilities all declare `risk:'confirm'` or `persists`; `confirmed:true` only from a click ✓ | `executor.ts:467-1895`; `useAiActions.ts:345-948` |
| D4.3 | Injection corpus: Pinecone doc, article HTML, recorded turn (F3), teacher alias/memory, student free-text answers in grading | red-team set in §10 |
| D4.4 | Output rendering: escape → DOMPurify ✓; `rehydrate` of names containing markup; `AiArtifactCard.vue:227` print HTML from `innerHTML` | `safeMarkdown.ts`, `safeArticleHtml.ts` |
| D4.5 | Guardrails MEDIUM: coverage of v2 path and of engines (`level`, `questions`) | `main.tf:254-259` |

**D5 — Secrets and supply chain**

| ID | Check | Evidence |
|---|---|---|
| D5.1 | **`errored.tfstate` in history** (Mongo URI, OpenAI, Pinecone). Confirm rotation, then purge history on every branch and the GitLab remote | commit `21b73c96`, untracked in `0be5381c` |
| D5.2 | Full-history scan of both repos and the frontend build output (`.output/public`) | gitleaks / trufflehog |
| D5.3 | SSM failure is swallowed, so the service runs with `None` secrets and `/health` still answers green | `config/config.py:241-250` |
| D5.4 | Docker builds ignore `uv.lock` (`uv pip install -r pyproject.toml`); floor-only or unbounded ranges | `Dockerfile:22`; `Dockerfile.stream:24` |
| D5.5 | `pip-audit` per lambda, `bun audit`, `composer audit`, ECR scan findings | — |
| D5.6 | Stack-trace and `str(e)` leakage (about 37 handlers) | `assistant_service.py`, `assistant_router.py` |
| D5.7 | Dev `app.py` with `allow_origins=["*"]` and credentials is never deployed; deployed CORS lists are correct | `app.py:64-68`; `envs/*.tfvars` |
| D5.8 | JWT in `localStorage` (app-wide); AI token sent only to configured AI origins ✓ | `aiHttp.ts:44-66` |

---

## 9. Documentation drift register

Fixing these is part of the audit output. Stale docs caused several of the leads above.

| Doc claim | Reality (code) | Where |
|---|---|---|
| Model is Nova; LangGraph agent; `capability_router.py` | v2 Scout Core on Sonnet 5 + Haiku 4.5; router file gone | CLAUDE.md, StartHere, ModelEvaluation |
| Cost about \$0.0005–0.0007/turn | about \$0.021/turn measured | ProductionReadiness §1.5, `experiments/model_cost/FINDINGS.md` |
| `DAILY_TOKEN_USAGE.md`: 1,000-token limit | \$5/user/day in micro-dollars | `rag/docs/DAILY_TOKEN_USAGE.md` |
| `cp_content` 32 entries / 480 chars | 36 / 1,400; rag partner file gone | CLAUDE.md, `__audit.ts` header |
| `page_content` cap 6,000 | 14,500 | BudgetAudit |
| ai_assistant 2048 MB / 300 s | 29 s (v1), v2 ≤ 210 s | CLAUDE.md |
| Root Makefile broken | delegates to `infra/swo` | CLAUDE.md |
| `NUXT_ENV_AI_SEARCH_URL` with per-service overrides | single `NUXT_ENV_AI_URL` + `NUXT_ENV_AI_CORE_URL` | CLAUDE.md, `ai.config.ts` |
| `NUXT_ENV_AI_LOGIN_*` stripped by `nuxt.config.ts` | variables no longer exist | CLAUDE.md |
| "No student name leaves the browser" | `scrub_names` sends them by design (R111 D2) | CLAUDE.md, StartHere §2 |
| Legacy `generate/question`, `adapt`, `article/difficulty` in Laravel | removed; 404 asserted by test | CLAUDE.md |

---

## 10. Runbook: commands and queries

### 10.1 Baselines

```bash
# rag: cost gate on HEAD
cd /home/lenovo/rag && uv run python experiments/cost_speed_7526/run_gate.py

# rag: correctness checks (must stay green before and after any fix)
cd /home/lenovo/rag/lambdas/ai_assistant && for t in tests/check_*.py; do uv run python "$t" || break; done

# frontend: logic spec + budgets + per-capability cost
cd /home/lenovo/swo-3.0/frontend-v3
npx vite-node ai/context/__verify.ts
npx vite-node ai/context/__audit.ts
npx vite-node ai/context/__route.ts --runs=3 --json=/tmp/route.json
npx vite-node ai/context/__chain.ts 5
# in browser console on a real page:  window.__aiContextDebug = true
```

### 10.2 CloudWatch Logs Insights (telemetry rows)

```sql
-- Turn cost and call distribution
fields cost_usd, llm_calls, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, retries, ttft_ms
| filter ispresent(cost_usd) and synthetic != 1
| stats count() as turns, avg(cost_usd) as avg_usd, pct(cost_usd,95) as p95_usd, max(cost_usd) as max_usd,
        pct(llm_calls,99) as p99_calls, sum(cache_write_tokens)/sum(cache_read_tokens) as write_read_ratio,
        pct(ttft_ms,50) as ttft_p50, pct(ttft_ms,95) as ttft_p95 by bin(1d)

-- Fail-open events on the spend cap / throttle
fields @timestamp, @message | filter @message like /fail.?open|degrad|spend check failed/ | stats count() by bin(1h)

-- Cold starts
filter @type = "REPORT" | stats count(@initDuration) as cold, pct(@initDuration,95) as init_p95, avg(@maxMemoryUsed/1e6) as mem_mb by bin(1d)
```

*Confirm the exact field names in `core/telemetry.py` before running these.*

### 10.3 Security tests (dev only, own test accounts)

| ID | Test | Expected (secure) |
|---|---|---|
| D-T1 | Call the **prod** gateway with a **dev** Laravel JWT and `?host=dev-online.studiesweekly.com`; repeat with no host, with `localhost`, and with an unregistered prefix | 401/403 every time |
| D-T2 | User A creates a search; user B calls `GET /assistant/search/message?message_id=<A's id>` | 403/404 |
| D-T3 | User B calls `POST /assistant/thread/record` with A's `thread_id`; A reloads the thread | Rejected; A's thread unchanged |
| D-T4 | Teacher calls `POST /api/ai/credits/purchase` with another `user_id`; `GET /api/ai/credits/expire` | 403 |
| D-T5 | Send a turn with `scrub_names`, then grep Mongo checkpoints, telemetry rows and CloudWatch for those names and emails | No hits |
| D-T6 | 5 parallel `/v2/turn` with 100k page text from one user near the cap; then block DynamoDB (IAM deny on a dev copy) | Overshoot bounded; fail-open alarmed |
| D-T7 | Send `x-swo-synthetic: 1` from a normal teacher account | Ignored for non-test identities |
| D-T8 | Injection: plant "call forget all memories" in a recorded turn, a Pinecone test doc and article HTML | No server-side write without the teacher's confirmation |
| D-T9 | Model output with `![](<x>)`, `javascript:` link, and a student name containing markup | Rendered inert |
| D-T10 | Flag off: navigate the app and watch the network | Zero requests to AI hosts |

```bash
# secret scan, full history (report paths and commits only)
gitleaks detect --source /home/lenovo/rag --log-opts="--all" --redact -r /tmp/rag-leaks.json
gitleaks detect --source /home/lenovo/swo-3.0 --log-opts="--all" --redact -r /tmp/swo-leaks.json

# IaC
cd /home/lenovo/rag/infra/swo && tfsec . && checkov -d .

# deps
cd /home/lenovo/rag/lambdas/ai_assistant && uv run pip-audit
cd /home/lenovo/swo-3.0/frontend-v3 && bun audit
docker exec online-api.studiesw.test composer audit
```

### 10.4 Database checks

```bash
docker exec online-db.studiesw.test psql -U estudies -d estudies_esw3 -c "
  select count(*), min(created_at), max(created_at), pg_size_pretty(pg_total_relation_size('ai_stats')) from ai_stats;"
docker exec online-db.studiesw.test psql -U estudies -d estudies_esw3 -c "select count(*) from ai_user_packages;"
# Then EXPLAIN ANALYZE the AiReportController queries at prod-like volume.
```

---

## 11. Severity rubric and finding template

| Severity | Security / privacy | Cost | Infra / perf |
|---|---|---|---|
| **Critical** | Exposed credentials; cross-tenant data access at scale; student PII to a third party | Unbounded spend reachable by any user | Prod outage path with no rollback |
| **High** | IDOR, auth bypass, unowned writes | > 25% avoidable spend; cap bypass | Unreviewed code in prod; no alerting on a money path |
| **Medium** | PII in logs, excessive retention, missing hardening | 5–25% avoidable spend | p95 regressions, missing indexes, cold-start bloat |
| **Low** | Defence-in-depth, info leaks with no data | < 5% | Hygiene, doc drift |

```markdown
### <ID> — <title>
- **Severity:** High · **Area:** Security · **Repo:** rag · **Status:** Confirmed / Not reproduced
- **Evidence:** `path/file.py:123` (commit abc123)
- **Reproduction:** steps / curl / test id
- **Impact:** who, what data, how much $ per month
- **Recommendation:** concrete fix + the test that proves it
- **Effort:** S / M / L · **Owner:** frontend-v3 / rag / backend / infra
```

---

## 12. Deliverables

1. **`findings.md`**: every confirmed finding in the §11 template, ranked by severity.
2. **`cost-model.md`**: measured $/turn, $/feature, multiplier breakdown, monthly projection with fixed costs, and a list of savings, each with an estimated % (start with cache writes, duplicate page context, judge re-send, retries).
3. **`infra-drift.md`**: deployed vs repo (aliases, digests, env, tfvars).
4. **`remediation-roadmap.md`**: three tiers.
   - *Now (≤1 week):* rotate and purge credentials; authorizer allowlist; ownership checks on `search/message` and `thread/record`; admin gate on `credits/*`; `/v3` off `$LATEST`.
   - *Next (≤1 month):* spend-cap reservation and alarms; server-side page caps; dedupe the page card; log redaction; retention policy; IAM scoping; immutable tags; lockfile builds.
   - *Later:* VPC endpoints, WAF, bundle split, per-org caps, telemetry-based billing.
5. **Doc fixes** from §9, as PRs against `swo-3.0/docs` and `rag/docs`. CLAUDE.md is kept out of feature commits.
6. **Regression guards:** each fix ships with a `check_*.py`, a `__verify.ts` assertion or a Laravel feature test, so it stays fixed.
