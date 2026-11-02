# ONLINE-7764: D1–D4 Logs Insights queries

Log group: `/aws/lambda/swo-genai-pov-ai-assistant-v2-dev`. Time range: the collection week.

Every query keeps only lines that carry the new fields (`ispresent(...)`), so lines written before the deploy drop out.

Rules for reading the results (from the ticket):
- Turn kind = `model_steps` + `tools.0`.
- A row with `turns` < 30 is "insufficient data", with no decision.
- A stage is the main cause when its `*_share_p50` ≥ 0.40 and its own p50 ≥ 1000 ms.
- Each share is worked out per turn first (stage ms / that turn's `first_content_ms`). The query then takes the median, not p50 stage / p50 total.

Base filter, the same one Q2–Q4 used in the investigation:
`message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500`

---

## D1: plain answers (one model call, no tool)

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500
  and model_steps = 1 and not ispresent(tools.0) and ispresent(first_model_text_ms)
| fields ttft_ms - guardrail_wait_ms - first_model_text_ms as before_call_ms,
         first_content_ms - ttft_ms as hold_ms,
         first_call_input_tokens + first_call_cache_read_tokens + cache_write_tokens as first_call_prompt_tokens
| fields first_call_cache_read_tokens / first_call_prompt_tokens as cache_read_share,
         cache_write_tokens / first_call_prompt_tokens as cache_write_share
| fields least(floor(cache_write_share * 5), 1) as cache_missed
| fields guardrail_wait_ms / first_content_ms as guard_share,
         first_model_text_ms / first_content_ms as model_share,
         before_call_ms / first_content_ms as before_share,
         hold_ms / first_content_ms as hold_share
| stats count() as turns,
        pct(first_content_ms, 50) as first_p50,
        pct(guardrail_wait_ms, 50) as guard_p50, pct(guard_share, 50) as guard_share_p50,
        pct(first_model_text_ms, 50) as model_p50, pct(model_share, 50) as model_share_p50,
        pct(before_call_ms, 50) as before_p50, pct(before_share, 50) as before_share_p50,
        pct(hold_share, 50) as hold_share_p50,
        pct(first_call_prompt_tokens, 50) as prompt_p50,
        pct(cache_read_share, 50) as cache_read_share_p50,
        pct(cache_write_share, 50) as cache_write_share_p50,
        avg(cache_missed) as cache_missed_turns_share
```

The cache columns use the turn's `cache_write_tokens`, not a first-call field:
- Bedrock's `inputTokens` leaves out both cache reads and cache writes. `first_call_input_tokens` is 2 on every turn, so on its own it isn't the prompt size.
- In D1 the first call is the turn's only cached call: on all 40 D1 turns from 13–14 Oct, the turn's cache reads equal the first call's exactly. The turn's other ~300 input tokens are the uncached guardrail call. So `cache_write_tokens` is the first call's write.
- `cache_missed_turns_share` is the share of turns that wrote at least 20% of their prompt (cold or partly cached). The medians alone hide these turns: on 13–14 Oct, 15 of 40 turns wrote 20% or more, while the median write share was 0.02.

Reading it:
- If `guard_share_p50` qualifies, raise it.
- If `model_share_p50` qualifies, check the cache:
  - A large `cache_missed_turns_share`, and those turns slower to first text: caching ticket. Compare `first_model_text_ms` for missed and warm turns with `by cache_missed`.
  - Mostly warm (`cache_read_share_p50` high): prompt-size or model ticket. `prompt_p50` gives the prompt size.
- If `before_share_p50` qualifies, look at the time before the first call is sent.
- If nothing qualifies, no ticket.

The four time shares add up to about 1, which is a check that nothing is missing.

## D2: search turns

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500
  and tools.0 = 'search_curriculum' and ispresent(search_calls)
| fields search_retrieve_ms - search_embed_ms as pinecone_ms,
         coalesce(search_standards_wait_ms, 0) as standards_ms
| fields search_target_ms / first_content_ms as target_share,
         search_embed_ms / first_content_ms as embed_share,
         pinecone_ms / first_content_ms as pinecone_share,
         search_resolve_ms / first_content_ms as resolve_share,
         standards_ms / first_content_ms as standards_share
| stats count() as turns,
        pct(first_content_ms, 50) as first_p50, avg(search_calls) as searches_avg,
        pct(search_target_ms, 50) as target_p50, pct(target_share, 50) as target_share_p50,
        pct(search_embed_ms, 50) as embed_p50, pct(embed_share, 50) as embed_share_p50,
        pct(pinecone_ms, 50) as pinecone_p50, pct(pinecone_share, 50) as pinecone_share_p50,
        pct(search_resolve_ms, 50) as resolve_p50, pct(resolve_share, 50) as resolve_share_p50,
        pct(standards_ms, 50) as standards_p50, pct(standards_share, 50) as standards_share_p50
  by model_steps, tools.0
| sort turns desc
```

Reading it: if a stage qualifies, optimize that stage only. If none does, leave search alone. `search_standards_wait_ms` is missing on turns with no standards lookup, so it counts as 0 there.

## D3: do retries explain the tail?

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade'
  and first_content_ms > 10000 and ispresent(provider_retries)
| fields least(provider_retries, 1) as retried
| stats count() as tail_turns, sum(retried) as retried_turns, avg(retried) as retried_share
```

Reading it:
- If `retried_share` ≥ 0.25, open a retry/watchdog ticket. Otherwise drop it.
- SDK-internal throttling retries aren't counted. They show up as a slower `first_model_text_ms`.

To see which turn kinds the tail comes from, add `by model_steps, tools.0`.

## D4: does the lead-in sentence shorten the wait?

The log line has no lead-in flag. The query infers it from fields that are already logged, using `runtime.py` `lead_in_for` and `loop.py` around line 1101:
- Only `write_artifact` and `generate_questions` ever stream a lead-in.
- A dispatched turn (`model_steps` = 0) for either tool always streams one, so it has no no-lead-in group to compare with.
- A planner-routed turn streams one only when its first model call wrote no text. On the line, that is `first_model_text_ms` being absent.

So a comparison within the same turn kind is only possible for planner-routed `write_artifact` and `generate_questions` turns:

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500
  and model_steps >= 1 and tools.0 in ['write_artifact', 'generate_questions'] and ispresent(guardrail_wait_ms)
| fields ispresent(first_model_text_ms) as model_wrote_first
| stats count() as turns, pct(first_content_ms, 50) as first_p50, pct(first_content_ms, 90) as first_p90
  by model_steps, tools.0, model_wrote_first
| sort model_steps, tools.0, model_wrote_first
```

How to read the result:
- `model_wrote_first = 0` means the lead-in was streamed.
- `model_wrote_first = 1` means the model's own text came first, with no lead-in.
- Compare the two rows of the same kind. The 30-turn rule applies to each row.

Limit: if a lead-in fails, the line does not record it, so that turn lands in the lead-in group anyway. A lead-in failure never fails the turn, and the failure is logged on its own line.

---

## Daily routine

Every day, set the Logs Insights time range to **absolute, from 2026-10-12 13:15 UTC (the release of version 66) to now**. The decisions need the turns added up over the whole collection week, not one day at a time.

1. Run the **progress** query. It shows how close each turn kind is to the 30-turn floor.
2. Run the **daily trend** query. It shows each day on its own row, so a bad day stands out.
3. Run D1–D4 and paste the results into the daily log (see the last section).

### Progress: turns per kind since the release

`provider_retries` is on every line from the new build, including turns with no model call, so it marks the new build.

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500
  and ispresent(provider_retries)
| stats count() as turns, pct(first_content_ms, 50) as first_p50, pct(first_content_ms, 90) as first_p90
  by model_steps, tools.0
| sort turns desc
```

### Daily trend

```
filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500
  and ispresent(provider_retries)
| fields least(provider_retries, 1) as retried
| stats count() as turns, pct(first_content_ms, 50) as first_p50, pct(first_content_ms, 90) as first_p90,
        pct(guardrail_wait_ms, 50) as guard_p50, pct(first_model_text_ms, 50) as model_text_p50,
        sum(retried) as retried_turns, sum(search_calls) as searches
  by bin(1d)
| sort @timestamp asc
```
