## ONLINE-7875 step 2: async guardrail test, progress (session 1 of 4)

### Background

- The floor test (4 sessions, 720 runs) found that the **stream guardrail is the floor**: with it off, first text drops from 5.7 s to 1.3 s (plain answer) and from 3.7 s to 1.3 s (search second call).
- Salman reviewed it on Slack (28 Oct) and agreed the next step:
  - **Add an async guardrail arm** (`streamProcessingMode: async`) to the same test.
  - **In the same run, replay `cost_speed_7526`'s blocked turn under strict** and record what the stream sends when the block comes after text is already shown (stop reason, any replacement text).
  - **Record how the loop handles it** (`bedrock_held`, the curriculum override).
  - **Check whether either guardrail profile masks anything.**
  - **No product change:** async can't ship until that has been reviewed.
  - Two small fixes: say thinking is "unset" (the model's default), not "off", and make `SMALL_SYSTEM` say K-8 instead of K-12. **Both done.**

### What was found in the code before running

- **The curriculum override retry no longer exists.** ONLINE-7578 removed it (`387c8688`) on every branch. Today a block is handled by:
  - the up-front curriculum route (the classifier picks the profile before the call);
  - the `bedrock_held` hold (`loop.py:501-504`);
  - one regeneration of an output-only block, and only when nothing was shown yet (`loop.py:394`).
- **Dev now checks only the typed ask on input.** Dev's `live` alias (version 87, image `105207ce`) runs release_2, where the input check reads only the teacher's typed words (`guardContent`, ONLINE-8093 `96166558`). The floor test's request checked every message, as dev did in the ONLINE-7764 week. So I added two arms to measure today's request too:
  - `typed_only`: what dev sends today;
  - `typed_only_async`: today's request with async.
- **Both profiles mask.** Deployed strict `:16` and curriculum `:4` both set `EMAIL` and `PHONE` to `ANONYMIZE`, and SSN, card numbers, AWS keys and base64 images to `BLOCK`.

### What was built (MR !100)

- **Plan written before any counted run:** `experiments/ttft_floor_7875/GATE-step2.md`.
- **`measure.py`:** 9 arms (the 6 from step 1, plus `async_guardrail`, `typed_only` and `typed_only_async`) on the same 6 calls.
- **`block_replay.py`:** runs every case through the real loop (`ModelCaller.call`) and records Bedrock's events, what the teacher saw, regeneration, and what was raised.
  - **Block cases:** `cost_speed_7526` T1 (US Government article, "What is the main idea of this article?") under strict, sync/async × all input/typed-only input.
  - **Mask cases:** an ask whose reply should contain an email address and a phone number, under both profiles × sync/async.
- **Smoke run first (not counted):** clean. It found that the first masking ask made Sonnet call a tool, so the probe now sends the ask without tools (`3ecfbf65`).

### Progress so far

- **Session 1 done** (29 Oct, `3ecfbf65`, clean tree): 270 timing runs and 80 replay runs, 0 errors, 0 retries. Log attached: `step2_session1.log`.
- **Sessions 2–4 to run on later days** (20 runs per timing cell in total), then `RESULT-step2.md` and the rows get committed.

### Session 1 results (provisional, one session)

**Timing** (in-AWS time to first text, p50, 15 runs per cell):

| Arm | Plain answer | Search, 2nd call |
|---|---|---|
| `routed` (floor test request) | 5.90 s | 4.14 s |
| `typed_only` (dev today) | 5.68 s | 4.21 s |
| `async_guardrail` | 2.33 s | 3.01 s |
| `typed_only_async` | 2.21 s | 2.52 s |
| `guardrail_off` (floor) | 1.22 s | 1.29 s |

- **Async removes about 3.5 s on plain answers.** It's still about 1 s above the floor.
- **On search it removes less** (about 1.1 s; 1.7 s with typed-only). The input check still runs before any text streams, so the response opens about 1.4 s later than with the guardrail off.
- **Typed-only alone (sync) changes nothing.** The hold comes from the output check, not from the input size.

**A block after text is shown** (the test turn blocked in 1 of 10 runs in three of the four cases; verdict `topic:Political and Extremist Content:BLOCKED`, output side):
- **Sync (dev today):** about 1,000 characters of the answer are shown. Then the text is cut mid-sentence and Bedrock's "Sorry — … my answer didn't make it past a content check" message is appended. The teacher sees both.
- **Async:** the **whole answer** (1,052 characters) streams and finishes. About 0.6 s later the stream stops with `guardrail_intervened`, and **Bedrock sends no replacement text**. The teacher has already read the full blocked answer.
- **Loop handling in both modes:**
  - `bedrock_held` catches Bedrock's message in sync and releases it;
  - **no regeneration**, because text was already shown;
  - the loop raises `guardrail_intervened`, so the teacher gets the "I am programmed to be a helpful and harmless AI assistant…" error, and the turn is left out of stored history.
- The blocked text here was a harmless answer about US government. The verdict looks like a false positive, but the mechanism is what matters.

**Masking:**
- **Sync:** both profiles masked in 20 of 20 runs. The teacher saw `{EMAIL}` / `{PHONE}`.
- **Async:** **neither profile masked, in 20 of 20 runs.** The raw email address and phone number reached the teacher, even though the trace said `ANONYMIZED`.

### Provisional reading (for the safety review, not a decision)

- Async buys about 3.5 s on plain answers, but:
  - a teacher can read a whole answer the guardrail then blocks;
  - email and phone masking stops working.
- If async is considered, measure it on the typed-only request (what dev already sends); it's the faster one on search.

### Next

- Run sessions 2–4 on later days, then write `RESULT-step2.md` with the final numbers.
- No product change until Salman's review.
