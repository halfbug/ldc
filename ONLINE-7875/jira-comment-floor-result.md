## ONLINE-7875 floor test: result (4 sessions, 720 runs)

**MR:** https://gitlab.com/sw6/ops/rag/-/merge_requests/100 (branch `ONLINE-7875_ttft_floor_test`, latest commit `5a041c33`)
**Full results:** `experiments/ttft_floor_7875/RESULT.md`, raw rows in `rows.jsonl`. Every table rebuilds with `measure.py --report --pool-shas`.
**Attached:** session logs `v2_session1.log` to `v2_session4.log` (the console output of each counted session, one line per run).

### Setup

- **Sessions:** 21 Oct 07:15 and 15:12, 22 Oct 07:31, 27 Oct 06:48 UTC. 720 runs, 20 per cell, clean tree.
- **Settings (same as dev):**
  - models: Sonnet 5 main, Haiku 4.5 fast;
  - effort `low`, thinking unset (the model's default);
  - strict guardrail `z6mtpcbzm5x1:16`, curriculum guardrail `u5k53i63fu9b:4`.
- **Calls measured:** on 3 pages (article, Classrooms, TOC):
  - the first model call of a plain answer;
  - the second model call of a search turn. Its first call ran live; the search result was a fixed render.
- **Six arms.** Each differs from `routed` (the request as Scout sends it) in one thing only:
  - `other_profile`: the other guardrail profile;
  - `guardrail_off`: no guardrail;
  - `small_prompt`: one-line prompt;
  - `small_prompt_no_gr`: one-line prompt, no guardrail;
  - `fast_model`: Haiku instead of Sonnet.
- **Headline figure is the in-AWS time:** Bedrock's `latencyMs` minus the client's time from first text to the last byte, computed per run. This removes upload time from the test machine.

### Results (in-AWS time to first text, p50 / p90)

| Arm | Plain answer | Search, 2nd call |
|---|---|---|
| `routed` (as Scout sends it) | 5.70 s / 7.31 s | 3.66 s / 4.49 s |
| `other_profile` | 5.73 s / 7.26 s | 3.59 s / 4.35 s |
| **`guardrail_off`** | **1.28 s / 1.42 s** | **1.34 s / 1.56 s** |
| `small_prompt` (guardrail on) | 3.84 s / 6.66 s | 2.84 s / 3.26 s |
| `small_prompt_no_gr` (model floor) | 1.05 s / 1.18 s | 1.06 s / 1.26 s |
| `fast_model` (Haiku 4.5, guardrail on) | 4.33 s / 4.84 s | 2.80 s / 3.80 s |

### Findings

- **The stream guardrail is the floor.**
  - Turning it off cuts the plain answer by **4.41 s** (5.70 → 1.28 s) and the search second call by **2.32 s** (3.66 → 1.34 s).
  - The effect holds in all 4 sessions: 4.4–4.7 s plain, 2.1–2.4 s search.
- **The guardrail holds the whole stream.** With it on, the response opens and then nothing arrives, not even `messageStart`, for 3.9 s (plain) and 1.7 s (search). With it off, the first event arrives with the response.
- **The hold grows with reply length.** The guardrail releases text only after checking it. With the guardrail on, `small_prompt` (157 output tokens) is 1.9 s faster than `routed` (468 output tokens).
- **Nothing else comes close.** Change from `routed`, in-AWS p50:
  - Prompt cut to one line (guardrail off): −0.23 s plain, −0.28 s search.
  - `other_profile`: +0.04 s plain, −0.07 s search.
  - `fast_model` (Haiku 4.5, guardrail on): −1.37 s plain, −0.86 s search. That still leaves 4.3 s and 2.8 s, above the 2 s gate.
- **C3: dev's `first_model_text_ms` is measured after the guardrail hold.**
  - The clock starts when the call is sent (`loop.py:462`). It stops at the first text shown (`loop.py:507`). That moment comes after Bedrock's guardrail and after the loop's `bedrock_held` hold (`loop.py:501-504`).
  - So dev's 4.7 s (ONLINE-7764, D1) includes the guardrail.
  - The guardrail label wait (~0.5 s, `guardrail_wait_ms`) comes before the call and adds on top.
- **C2: first event and reasoning.** The first event is the first text in every arm (p50 gap 0.1 ms). No run (0 of 720) had reasoning before the text, so there is no first-reasoning figure.
- **Population:**
  - 0 errors and 0 retries.
  - 1 blocked run: the article ask in `other_profile` (strict). Under curriculum, the profile dev routes it to, 0 of 60 runs were blocked.

### Limits

- The in-AWS figure is an estimate from `latencyMs`. It agrees with the client clock wherever upload is small.
- Test prompts are ~21–22k tokens, against ~33k on dev. Compare the arms with each other, not with dev's 4.7 s.
- Coverage: 3 pages, 6 asks, fixed search hits, and no thinking measured.
- Session 4's client clock was slowed by upload from the test machine, which was slow that day. Its in-AWS numbers match the other sessions, so it is used for in-AWS figures only.

### Recommendations for step 2 (for review; no product change until agreed)

1. **Measure asynchronous guardrail mode first** (`streamProcessingMode: asynchronous`). Add it as one more arm in the same script and post the number here before any product change. Expected: first text moves toward the 1.3 s `guardrail_off` floor.
2. **Run a safety review before shipping async mode.** In async mode, text the guardrail later blocks may already be on screen. That risk needs a decision from Salman / safety. Also check:
   - how the loop's `bedrock_held` hold (ONLINE-6554) and the curriculum override behave when a block arrives after text was shown;
   - whether either guardrail profile masks output, and whether async mode still applies that masking.
3. **If async mode is rejected, shorten guarded replies.** Under the synchronous guardrail, time to first text tracks reply length.
4. **Don't pursue prompt trimming, a profile change or Haiku alone for this.** Prompt trimming and a profile change each move first text by 0.3 s or less. Haiku saves 1.4 s but is still above the 2 s gate.
5. **Track the label wait (~0.5 s, `guardrail_wait_ms`) separately.** It stays on every guarded turn, whichever option is chosen.
