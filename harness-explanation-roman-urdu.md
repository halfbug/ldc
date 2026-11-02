# Harness Explanation (Roman Urdu) — Conversation Log

**Date:** 2026-08-27

---

## Q1: What type of agent are we currently using — harness or loop engineering?

I'm Claude Code, running as a harness-based coding agent — not a bespoke "loop engineering" setup you'd build yourself. Concretely:

- **Model**: Sonnet 5 (claude-sonnet-5)
- **Harness**: Claude Code CLI — I run inside an agentic loop the harness manages: it sends my messages to the model, executes any tool calls I request, feeds results back, and repeats until I stop calling tools. That loop, permissions, and tool plumbing are all handled by the harness, not something I've hand-rolled per task.
- **Tools available to me here**: Bash, Read, Edit, Write, Agent (subagents/forks), Workflow (scripted multi-agent orchestration), Artifact, Skill, ScheduleWakeup, ToolSearch (for deferred tools like WebFetch/WebSearch/Monitor/etc.), plus a persistent file-based memory system.
- **Extras layered on**: subagents (fresh-context or "fork" of this conversation) for delegation, and Workflow for deterministic multi-agent orchestration when explicitly requested — but I don't invoke those unless the task calls for it.

So the short answer: it's the standard Claude Code agent harness (model + tool-calling loop + permissions), not a custom-engineered loop for this session.

---

## Q2: What is "harness" — explain in Roman Urdu, basic to advance

Theek hai, main "harness" ko Roman Urdu mein basic se advance tak explain karta hoon — jaisa ke AI agents (mujh jaisay tools, e.g. Claude Code) ke context mein use hota hai.

### Basic level

**Harness** matlab woh "structure" ya "system" jo AI model (jaise Claude) ke around bana hota hai taake woh sirf baatein na kare, balke **kaam bhi kar sake**.

Socho: AI model sirf ek "dimagh" hai — ye text samajh sakta hai aur text generate kar sakta hai. Lekin ye khud se:
- file nahi khol sakta
- code run nahi kar sakta
- internet search nahi kar sakta

**Harness** woh "jism" (body) hai jo is dimagh ko haath-pair deta hai — tools, permissions, aur ek loop jisme ye kaam karta hai.

### Thoda advance

Harness ke 3 basic cheezein hoti hain:

1. **Tool-calling loop** — Model ek message deta hai, agar usay kisi tool (jaise Bash, file Read/Write) ki zaroorat ho to woh "request" karta hai. Harness woh tool chalata hai (jaise terminal command run karna), result wapas model ko deta hai, aur ye cycle chalta rehta hai jab tak kaam khatam na ho.

2. **Permissions/safety layer** — Harness decide karta hai ke kaunsa tool bina poochay chal sakta hai aur kaunsay ke liye user se ijazat lena zaroori hai (jaise `rm -rf` ya `git push`).

3. **Context management** — Lambi conversation ko manage karna, purani baatein summarize karna, taake model "yaad" rakh sake bina overload huay.

### Advance level

Ek "agent" = **Model + Harness**. Model akela sirf ek raw intelligence hai; harness usay:

- **Tools** deta hai (file edit, terminal, search, web fetch, sub-agents spawn karna)
- **Environment** deta hai (kaunsi directory mein kaam ho raha hai, git repo hai ya nahi)
- **Orchestration** deta hai — jaise ye ability ke model apne aap ko "fork" kar sakay ya parallel subagents chala sakay complex tasks ke liye
- **Guardrails** deta hai — destructive commands se pehle confirm karna, secrets leak na hone dena

Is session mein mera harness hai **Claude Code CLI**, jo mujhe Bash, Edit, Write, Agent (subagents), Workflow (multi-agent orchestration), Artifact, aur memory system deta hai — aur ye sab chalta hai ek tool-calling loop ke through jo harness khud manage karta hai, model nahi.

**Simple analogy**: Model = driver ka dimagh/skill. Harness = gaari + steering + brakes + rules of the road — jo us skill ko actually kahin le jaane ke qabil banata hai.

---

## Q3: So the assistant currently coming in "rag" is also a harness agent?

Haan bilkul — conceptually woh bhi ek **harness-based agent** hai, lekin ye Claude Code jaisa harness nahi hai, balke apna alag, custom-built system hai.

### Kya hai `rag` ka assistant

`rag/lambdas/ai_assistant/` mein jo assistant chal raha hai, uska architecture hai:

- **Model**: AWS Bedrock (jo underlying LLM chalata hai)
- **Orchestration framework**: **LangGraph** — ye woh "harness" ka role play karta hai. Ye decide karta hai ke model kab tool call karega, result kaise wapas jayega, conversation state kaise maintain hogi
- **Tools**: `tools/` folder mein defined hain (jaise `run_action.py`, `ask_user.py` — jo actually **browser mein** execute hoti hain, lambda mein nahi)
- **Routing**: `capability_router.py` deterministically decide karta hai ke har turn par konse tools model ko diye jayein (sab tools hamesha available nahi hotay)
- **State/memory**: MongoDB (`mongoengine` + `MongoDBSaver` checkpointer) conversation history save karta hai
- **Retrieval**: Pinecone + OpenAI embeddings (ye "RAG" part hai — Retrieval Augmented Generation)

### Farq Claude Code harness se

| | Claude Code (mujh jaisa) | rag ka `ai_assistant` |
|---|---|---|
| Harness | Claude Code CLI | LangGraph |
| Model | Sonnet/Opus (Anthropic API direct) | Bedrock |
| Deployment | Terminal/local session | AWS Lambda (containerized) |
| Tools kahan run hotay | Local machine (Bash, files) | Kuch tools **browser mein** run hotay (`run_action.py`, `ask_user.py` turn ko pause karte hain jab tak browser response na de) |
| Purpose | General coding agent | SWO app ke andar ek specific chat assistant jo app ke stores/actions ko control karta hai |

### Ek dilchasp cheez

`run_action.py` aur `ask_user.py` jaise tools **lambda ke andar execute nahi hotay** — ye turn ko "pause" kar dete hain aur actual execution browser (frontend-v3) mein hoti hai, phir result wapas lambda ko bheja jata hai. Ye is architecture ka unique hissa hai — kyunki assistant ko **app ke real stores/state** access karna hota hai (jo sirf browser mein exist karta hai), lambda mein nahi.

To summary: dono "harness" pattern follow karte hain (model + tools + loop), lekin ye do bilkul alag implementations hain — ek Claude Code hai, doosra ek custom LangGraph-based agent jo SWO ke apne product ke liye bana hai.
