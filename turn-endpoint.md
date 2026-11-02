I now have the full picture end-to-end. Here's the complete report.

Overview

The /assistant/turn endpoint lives in the rag repo (/home/lenovo/rag/lambdas/ai_assistant/src), while the polling client lives in the swo-3.0 repo (/home/lenovo/swo-3.0/frontend-v3/ai). It is a side-channel polling endpoint, not the answer itself — the real chat answer still comes back on the original POST /assistant/ call. This endpoint just reads a small MongoDB "progress row" that the same chat call writes to while it runs, via LangChain callback hooks on the LangGraph agent.

---

1. Route registration

File: /home/lenovo/rag/lambdas/ai_assistant/src/routers/assistant_router.py

# line 51 (schemas import) → TurnProgressRequest
# line 64: router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/turn")                                              # line 106
async def turn_progress_route(request: TurnProgressRequest, http_request: Request):   # line 107
    ...
    return await dispatch(                                          # line 135
        http_request,
        {"turn_id": request.turn_id},
        request.user_id,
    )

- Method/path: POST /assistant/turn — POST only, despite being read-only. There's an explicit note (docstring, and TurnProgressRequest docstring in schemas/models.py:111-121) that a GET can't work because main.py's Lambda handler builds request_data only from the JSON body, never queryStringParameters.
- Request body schema (schemas/models.py:111-123):
class TurnProgressRequest(BaseModel):
    turn_id: str
    user_id: str
- No query params are used (host=... in your example is presumably just the API base URL, not consumed by this handler).

2. Service function that handles it

Dispatch chain: assistant_router.dispatch() → AssistantService.handle_request() → _handle_turn_progress().

Route table entry — /home/lenovo/rag/lambdas/ai_assistant/src/services/assistant_service.py:2433-2442:
elif clean_path == "/turn" and method == "POST":
    return await self._handle_turn_progress(request_data, user_id)

Handler — assistant_service.py:3571-3619:
async def _handle_turn_progress(
    self, request_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    turn_id = (request_data or {}).get("turn_id")
    unknown = {"turn_id": turn_id, "state": "unknown",
               "phase": None, "phases": []}

    if not turn_id:
        return unknown

    try:
        from src.services.database.models.turn_progress import TurnProgress

        row = (TurnProgress.objects(turn_id=turn_id, user_id=str(user_id))
               .only("phase", "phases", "state", "llm_calls").first())
        if row is None:
            return unknown

        return {
            "turn_id": turn_id,
            "state": row.state,
            "phase": row.phase,
            "phases": list(row.phases or []),
            "llm_calls": row.llm_calls,
        }
    except Exception as e:
        logger.warning("Turn progress unavailable", extra={...})
        return unknown

3. Where turn state is stored

MongoDB (via mongoengine), collection turn_progress.

Model: /home/lenovo/rag/lambdas/ai_assistant/src/services/database/models/turn_progress.py
class TurnProgress(Document):
    turn_id = StringField(required=True, unique=True)
    thread_id = StringField(required=False)
    user_id = StringField(required=True)
    phase = StringField(required=False)
    phases = ListField(StringField(), default=list)   # capped at MAX_PHASES = 32
    llm_calls = IntField(default=0)
    started_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    expires_at = DateTimeField(required=True)          # TTL index, 0-second expireAfterSeconds
    state = StringField(default="running")             # running | done

    meta = {
        "collection": "turn_progress",
        "indexes": [
            {"fields": ["turn_id"], "unique": True},
            {"fields": ["expires_at"], "expireAfterSeconds": 0},
        ],
    }
- PROGRESS_TTL_SECONDS = 120 — rows self-expire via Mongo TTL index (~2 minutes after last write).
- turn_id origin: minted client-side, not server-side. Frontend does crypto.randomUUID() before sending the chat request (useAiChat.ts:957), so it can start polling immediately, and passes it in the chat body's turn_id. The chat handler (assistant_service.py:1763-1764) reads request.turn_id and upserts the row (TurnProgress.objects(turn_id=turn_id).update_one(..., upsert=True) in turn_progress.begin).
- Lookup on poll: TurnProgress.objects(turn_id=turn_id, user_id=str(user_id)) — scoped to the caller's user_id as well as turn_id.

4/5. How state, phase, phases, llm_calls are computed — polling vs. sync

This is a polling endpoint that reads state written by a synchronous LangGraph run happening in the same Lambda invocation as the original POST /assistant/, not a separate async background job (Lambda can't keep working after it returns, per the docstring in turn_progress.py model). The trick: the chat-processing code writes progress rows while the graph executes, and a second, short, separate HTTP request (this /turn endpoint) reads them mid-flight.

Phase-tracking logic: /home/lenovo/rag/lambdas/ai_assistant/src/utils/turn_progress.py

THINKING = "Thinking"                              # line 31
COMPOSING = "Putting that together"                # line 35

TOOL_LABELS = {                                    # lines 61-69
    "content_search": "Searching Studies Weekly",
    "support_search": "Searching help articles",
    "cp_content": "Reading the page",
    "read_page": "Reading the page",
    "generate_question": "Writing questions",
    "adapt_content": "Levelling the article",
    "run_action": "Working on the page",
}

def label_for_tool(name): return TOOL_LABELS.get((name or "").strip(), THINKING)

def begin(turn_id, thread_id, user_id):            # line 80 — upserts row, phase=THINKING, state="running"
def record(turn_id, phase, *, llm_call=False):      # line 114 — moves phase, appends to phases[], increments llm_calls
def finish(turn_id):                                # line 153 — sets state="done"

def progress_callbacks(turn_id):                    # line 178
    class _ProgressHandler(BaseCallbackHandler):
        def _model_started(self):
            record(turn_id, COMPOSING if self._tool_ran else THINKING, llm_call=True)
        def on_chat_model_start(...): self._model_started()
        def on_llm_start(...): self._model_started()
        def on_tool_start(self, serialized, input_str, **kwargs):
            self._tool_ran = True
            record(turn_id, label_for_tool((serialized or {}).get("name")))
    return _ProgressHandler()

Phase transition trigger: it's a LangChain BaseCallbackHandler bound into the LangGraph run's config["callbacks"], so transitions are driven by LangGraph/LangChain node & tool execution events, not polled or computed by this endpoint itself:
- on_llm_start / on_chat_model_start fires each time the "agent" node calls the model → phase becomes "Thinking" (if no tool has run yet) or "Putting that together" (if a tool already ran).
- on_tool_start fires when a "tools" node executes a tool call → phase becomes the tool's human label, e.g. "Searching help articles" for support_search.
- The graph has exactly two nodes (agent, tools) per the module docstring, which is why the label logic can't distinguish "writing the final answer" from "about to call another tool" — hence "Putting that together" covers both after the first tool call.
- record() drops consecutive duplicate phases (no-op if row.phase == phase and not an llm_call), and appends distinct phases to the phases history list (capped at 32).

Wiring into the graph invocation: assistant_service.py:1763-1767
_turn_id = getattr(request, "turn_id", None)
turn_progress.begin(_turn_id, request.thread_id, request.user_id or "")
_progress_handler = turn_progress.progress_callbacks(_turn_id)
if _progress_handler is not None:
    config.setdefault("callbacks", []).append(_progress_handler)
...
result = agent.graph.invoke(state, config)   # line 1804

So your sample response (phases: ["Thinking", "Searching help articles", "Putting that together"], llm_calls: 2) corresponds to: agent node called model (Thinking, llm_call 1) → decided to call support_search tool (phase → "Searching help articles") → agent node called model again (Putting that together, llm_call 2, since a tool already ran).

6. llm_calls

Incremented in record(), utils/turn_progress.py:145-146: update["inc__llm_calls"] = 1 whenever llm_call=True is passed — which only happens from _model_started() (i.e., once per on_llm_start/on_chat_model_start event). So it counts the number of model invocations made by the LangGraph agent during this turn (not tool calls).

7. Possible state values and final client response

- In the DB row / from _handle_turn_progress: only "running" (set in begin()) and "done" (set in finish()). There is no "error" state ever written — finish() is called unconditionally on every exit path of the chat handler: normal success (assistant_service.py:2258), TurnDeadlineExceeded (line 1818), GraphRecursionError (line 1896), ValueError (line 2281), and generic Exception (line 2296). So even a failed/timed-out/looping turn is reported as state: "done" here — the real success/error status lives only in the original chat response's status field (AssistantChatResponse.status = "success"|"error"), not in this endpoint.
- From the router itself, when no row is found (never began, or already TTL-expired): state: "unknown" with HTTP 200, phase: null, phases: [] — deliberately not a 404 (per docstrings at assistant_router.py:128-131 and _handle_turn_progress docstring).
- The actual final answer (content, status success/error, checkpoint IDs, pending actions, etc.) is returned only by the original POST /assistant/ (or /assistant/thread resume) call that this turn_id was attached to — this /assistant/turn polling channel never carries the answer, by design ("A side channel, never the answer").

8. Frontend usage (polling loop)

Repo: /home/lenovo/swo-3.0/frontend-v3 (a sibling repo to rag, found via cwd /home/lenovo/swo-3.0).

- HTTP client: /home/lenovo/swo-3.0/frontend-v3/ai/services/turnProgress.ts
  - TurnProgress interface (line 12-18): { turn_id, state: 'running'|'done'|'unknown', phase, phases, llm_calls? }
  - PROGRESS_POLL_MS = 700 (line 48), PROGRESS_QUIET_MS = 2_500 (line 49) — tuned from measured turn-latency percentiles (p50 2.2s, p95 6.0s, p99 14.6s) documented in the comment above them.
  - fetchTurnProgress(turnId, auth, signal) (line 64-92) POSTs to aiUrl('assistant','turn') with body { turn_id, user_id }, isSuccess: () => true (since this route has no success field), and swallows all errors → returns null.
- Polling loop: /home/lenovo/swo-3.0/frontend-v3/ai/composables/useAiChat.ts
  - turnId = crypto.randomUUID() minted client-side before sending the chat request (line 957), attached as turn_id in the chat body (line 967), and stamped onto every leg of a multi-step turn via withTurn() (lines 208-210).
  - startProgress(turnId, threadId) (lines 232-273): waits PROGRESS_QUIET_MS (2.5s) before the first poll, then chains setTimeout calls (not setInterval, to avoid stacking unanswered requests) every PROGRESS_POLL_MS (700ms):
const tick = async () => {
    if (activeTurnId !== turnId) return
    progressAbort = new AbortController()
    const progress = await fetchTurnProgress(turnId, await getAuth(), progressAbort.signal)
    if (activeTurnId !== turnId) return
    if (progress?.state === 'done') {
        store.loadingPhase = null
    } else if (progress?.phase && store.loadingThreadId === threadId) {
        store.loadingPhase = progress.phase
    }
    progressTimer = setTimeout(tick, PROGRESS_POLL_MS)
}
progressTimer = setTimeout(tick, PROGRESS_QUIET_MS)
  - Note: state === 'done' clears loadingPhase but does not stop the poll loop — comment explains multi-leg turns (continueActions/approval resumes) reuse the same visible turn id, so done just means one leg finished. The loop is only stopped by stopProgress() (line 212-217), called from clearPending, which runs in a finally on all chat send paths.
  - store.loadingPhase is only consumer-facing field actually rendered; phases (full history) isn't used by the UI. Rendered in /home/lenovo/swo-3.0/frontend-v3/ai/components/AiAssistantDialog.vue:1520-1523: store.loadingPhase ? \${store.loadingPhase}...` : 'Just a moment...'`.

❯ where it send the status to the database

The actual writes to MongoDB happen in /home/lenovo/rag/lambdas/ai_assistant/src/utils/turn_progress.py, in three functions, all using mongoengine's TurnProgress.objects(...).update_one(...) (an upsert-style query, not .save()):

1. begin() — opens the row (write #1), lines 88-109
TurnProgress.objects(turn_id=turn_id).update_one(
    set__thread_id=thread_id,
    set__user_id=str(user_id),
    set__phase=THINKING,
    set__phases=[THINKING],
    set__llm_calls=0,
    set__state="running",
    set__started_at=now,
    set__updated_at=now,
    set__expires_at=expiry_from(now),
    upsert=True,
)
Called from assistant_service.py:1764: turn_progress.begin(_turn_id, request.thread_id, request.user_id or "") — right before agent.graph.invoke(state, config) runs.

2. record() — updates phase/llm_calls mid-run (write #2, N times), lines 124-148
row = TurnProgress.objects(turn_id=turn_id).only("phase", "phases").first()
if row is None: return
if row.phase == phase and not llm_call: return

update = {
    "set__phase": phase,
    "set__updated_at": now,
    "set__expires_at": expiry_from(now),
}
if row.phase != phase and len(row.phases or []) < MAX_PHASES:
    update["push__phases"] = phase
if llm_call:
    update["inc__llm_calls"] = 1

TurnProgress.objects(turn_id=turn_id).update_one(**update)
This is not called directly from assistant_service.py — it's called by the _ProgressHandler LangChain callback object (progress_callbacks(), lines 197-219), whose on_llm_start/on_chat_model_start/on_tool_start methods fire automatically as LangGraph executes the agent's nodes. The handler is registered into the graph's callback list at assistant_service.py:1765-1767 (config.setdefault("callbacks", []).append(_progress_handler)), so each write to Mongo is triggered from inside LangGraph's own callback dispatch machinery while agent.graph.invoke() (line 1804) is running — same Lambda invocation, same synchronous call stack, just fired reactively per node/tool event.

3. finish() — closes the row (final write), lines 162-173
TurnProgress.objects(turn_id=turn_id).update_one(
    set__state="done",
    set__updated_at=now,
    set__expires_at=expiry_from(now),
)
Called from every exit path of process_chat in assistant_service.py (success at line 2258, TurnDeadlineExceeded at 1818, GraphRecursionError at 1896, ValueError at 2281, generic Exception at 2296).

All three functions wrap their Mongo call in try/except Exception and only logger.warning on failure — never raise — per the module's stated rule that "nothing here may fail a turn." The /assistant/turn GET-like poll endpoint (_handle_turn_progress in assistant_service.py:3571) only reads this collection via TurnProgress.objects(turn_id=..., user_id=...).only(...).first(); it never writes to it.

❯ how does langgraph call this

  Read 3 files, ran 9 shell commands

This confirms the mechanism exactly. Here's how LangGraph actually drives the _ProgressHandler callback:

The chain of calls

1. The graph node functions never see config explicitly.
/home/lenovo/rag/lambdas/ai_assistant/src/agents/assistant_agent.py:132-140:
workflow = StateGraph(AssistantAgentState)
workflow.add_node("agent", self._agent_node)   # def _agent_node(self, state)  -- no config param
workflow.add_node("tools", self._tool_node)
Note neither _agent_node nor _tool_node accepts a config argument, so nothing in this codebase is manually threading config["callbacks"] down into the LLM call or the tool call.

2. LangGraph wraps each node in a RunnableCallable and passes config through a contextvar, not a parameter.
/home/lenovo/rag/.venv/lib/python3.13/site-packages/langgraph/_internal/_runnable.py:329-393 (RunnableCallable.invoke):
callback_manager = get_callback_manager_for_config(config, self.tags)
run_manager = callback_manager.on_chain_start(None, input, name=..., run_id=...)
child_config = patch_config(config, callbacks=run_manager.get_child())
with set_config_context(child_config, run) as context:
    ret = context.run(self.func, *args, **kwargs)   # self.func is _agent_node
set_config_context (lines 65-77 same file) does:
config_token = var_child_runnable_config.set(config)
var_child_runnable_config is a contextvars.ContextVar imported from langchain_core.runnables.config. So when agent.graph.invoke(state, config) runs (with config["callbacks"] = [..., _progress_handler] set at assistant_service.py:1804,1737-1767), LangGraph doesn't pass that config as an argument to _agent_node — it stashes it in this ambient contextvar for the duration of the node's execution, then calls the plain function.

3. Any LangChain Runnable.invoke() called synchronously inside the node picks the config back up automatically.
/home/lenovo/rag/.venv/lib/python3.13/site-packages/langchain_core/runnables/config.py:192-208, ensure_config():
def ensure_config(config: RunnableConfig | None = None) -> RunnableConfig:
    ...
    if var_config := var_child_runnable_config.get():
        ...  # inherit callbacks, tags, etc. from the ambient config
Inside _agent_node, self.llm_service.invoke(...) (assistant_agent.py:212) eventually calls llm_with_tools.invoke(messages, **model_kwargs) at /home/lenovo/rag/lambdas/ai_assistant/src/services/assistant_llm_service.py:466 — no config= kwarg is passed. llm_with_tools is a ChatBedrock (langchain_aws), a LangChain Runnable, so its .invoke() calls ensure_config() internally, reads the contextvar, and builds a CallbackManager from the inherited callbacks list — firing on_chat_model_start/on_llm_start on every handler in it, including _ProgressHandler.

Same for tools: _tool_node → _invoke_one → tool.invoke(args) at assistant_agent.py:302 — tool is a LangChain BaseTool, also a Runnable, so it inherits the same ambient config and fires on_tool_start on _ProgressHandler.

4. _ProgressHandler (turn_progress.py:197-219) reacts to those events and writes to Mongo:
def on_chat_model_start(self, serialized, messages, **kwargs): self._model_started()
def on_llm_start(self, serialized, prompts, **kwargs): self._model_started()
def on_tool_start(self, serialized, input_str, **kwargs):
    self._tool_ran = True
    record(turn_id, label_for_tool((serialized or {}).get("name")))

Summary for citation

LangGraph doesn't call _ProgressHandler directly or pass it as an explicit argument anywhere in assistant_agent.py/assistant_llm_service.py. It's pure LangChain "ambient config" propagation: config["callbacks"] set once on agent.graph.invoke(state, config) (assistant_service.py:1737-1767, 1804) is pushed into a ContextVar (var_child_runnable_config) around each node call by LangGraph's RunnableCallable.invoke (langgraph/_internal/_runnable.py:392), and every nested LangChain Runnable.invoke() call made inside that node (the ChatBedrock.invoke() for the LLM, the BaseTool.invoke() for each tool) transparently re-reads that same ContextVar via ensure_config() (langchain_core/runnables/config.py:208) and fires its callback events on the handlers found there — which is how the Thinking/tool-label/Putting that together phase writes in turn_progress.py get triggered without any explicit wiring between the graph nodes and the progress tracker.
