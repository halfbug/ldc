"""
Scout turn as a LangGraph graph  (pause / resume / stop).

Guide concept                         -> LangGraph
---------------------------------------------------------------------------
loop.py _run_loop()                   -> agent <-> tools cycle
PendingAction / PendingPrompt         -> interrupt() inside the `pause` node
thread.pending saved in MongoDB       -> the checkpoint (MongoDBSaver in prod)
sibling tool results kept for resume  -> ToolMessages already in checkpointed state
_action_result_block()                -> action_result_to_tool_message()
STOPPED_NOTE / keep what was shown    -> stop finalizer in streaming.py (uses keep_len)
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

NOT_PERFORMED = (
    "Not performed: the teacher sent a new message instead of answering or approving this, "
    "so nothing happened."
)
STOPPED_NOTE = "[The teacher stopped this answer here.]"
ONLY_ONE_PAUSE = (
    "Only one action or question can wait on the teacher at a time. "
    "This one was not shown; ask again after they respond."
)
SYSTEM_PROMPT = "You are Scout, an assistant for teachers on Studies Weekly Online."

# Tools that never finish the job themselves: the browser / teacher must act (Chapter 6.1).
PAUSING_TOOLS = {"page_action", "ask_user"}


class TurnState(TypedDict, total=False):
    messages: Annotated[List[AnyMessage], add_messages]
    turn_id: str
    # Mirrors thread.pending from the guide: {tool_call_id, tool, kind, event, wire}
    pending: Optional[Dict[str, Any]]
    # Length of `messages` that is "safe history": after the user message, or after the
    # paused call's result. Stop trims back to this, so no tool call is left dangling.
    keep_len: int
    status: Literal["complete", "stopped"]


# --------------------------------------------------------------------------- helpers
def action_result_to_tool_message(pending: Dict[str, Any], ar: Dict[str, Any]) -> ToolMessage:
    """Port of _action_result_block(): the answer becomes the tool's result."""
    tool_call_id = pending.get("tool_call_id") or ar.get("id") or ""
    capability = str(ar.get("capability") or "").strip()
    message = str(ar.get("message") or "").strip()
    status = str(ar.get("status") or "ok")

    if not capability or pending.get("kind") == "prompt":
        return ToolMessage(
            content=f"The teacher answered: {message or '(no answer)'}.",
            tool_call_id=tool_call_id,
        )
    parts = [f"The browser's result for {capability}: {status}."]
    if message:
        parts.append(message)
    return ToolMessage(
        content=" ".join(parts),
        tool_call_id=tool_call_id,
        status="error" if status == "error" else "success",
    )


def pending_from_call(call: Dict[str, Any]) -> Dict[str, Any]:
    """Port of PendingAction / PendingPrompt.to_wire(). id = the model's own toolUse id."""
    args = call.get("args") or {}
    if call["name"] == "page_action":
        wire = {"id": call["id"], "capability": args.get("capability", ""), "args": args.get("args", {})}
        return {"tool_call_id": call["id"], "tool": call["name"], "kind": "action",
                "event": "pending_action", "wire": wire}
    wire = {"id": call["id"], "question": args.get("question", ""),
            "options": args.get("options", []), "allow_free_text": args.get("allow_free_text", True)}
    return {"tool_call_id": call["id"], "tool": call["name"], "kind": "prompt",
            "event": "pending_prompt", "wire": wire}


# --------------------------------------------------------------------------- builder
def build_graph(llm_with_tools, tools: Dict[str, Any], checkpointer):
    """
    llm_with_tools: chat model ALREADY bound to all tool schemas, e.g.
                    ChatBedrockConverse(model="amazon.nova-micro-v1:0").bind_tools([...])
    tools: {name: async callable(**args) -> str} for NON-pausing tools
    checkpointer: InMemorySaver for tests, MongoDBSaver in production
    """
    # ---- ingest: runs once per NEW user message (not on resume) -----------------------
    async def ingest(state: TurnState) -> Dict[str, Any]:
        return {"keep_len": len(state["messages"]), "pending": None, "status": None}

    # ---- agent: the model call. Tokens stream out via stream_mode="messages" ----------
    async def agent(state: TurnState, config) -> Dict[str, Any]:
        get_stream_writer()({"event": "status", "label": "Thinking"})
        reply = await llm_with_tools.ainvoke(
            [SystemMessage(SYSTEM_PROMPT), *state["messages"]], config
        )
        return {"messages": [reply]}

    def after_agent(state: TurnState) -> Literal["tools", "finalize"]:
        last = state["messages"][-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else "finalize"

    # ---- tools: run normal tools; turn the FIRST pausing tool into state.pending ------
    async def run_tools(state: TurnState) -> Dict[str, Any]:
        write = get_stream_writer()
        last: AIMessage = state["messages"][-1]
        results: List[ToolMessage] = []
        pending: Optional[Dict[str, Any]] = None
        for call in last.tool_calls:
            if call["name"] in PAUSING_TOOLS:
                if pending is None:
                    pending = pending_from_call(call)           # Chapter 6.3: only one pause
                else:
                    results.append(ToolMessage(ONLY_ONE_PAUSE, tool_call_id=call["id"], status="error"))
                continue
            write({"event": "status", "label": f"Running {call['name']}"})
            try:
                out = await tools[call["name"]](**(call.get("args") or {}))
                results.append(ToolMessage(str(out), tool_call_id=call["id"]))
            except Exception as exc:  # a tool crash is a tool result, not a dead turn
                results.append(ToolMessage(f"Tool failed: {exc}", tool_call_id=call["id"], status="error"))
        # sibling results are checkpointed with the state: "sent back together with the answer"
        return {"messages": results, "pending": pending}

    def after_tools(state: TurnState) -> Literal["pause", "agent"]:
        return "pause" if state.get("pending") else "agent"

    # ---- pause: THE interrupt. Nothing is waiting in memory (Chapter 6.3) -------------
    async def pause(state: TurnState) -> Dict[str, Any]:
        pending = state["pending"]
        # Re-executed from the top on resume, so everything above interrupt() must be
        # side-effect free. The value goes out as an `__interrupt__` update -> SSE event.
        ar = interrupt({"event": pending["event"], "wire": pending["wire"], "kind": pending["kind"]})
        msg = action_result_to_tool_message(pending, ar)
        return {
            "messages": [msg],
            "pending": None,
            "keep_len": len(state["messages"]) + 1,   # the answer is now safe history
        }

    # ---- finalize ---------------------------------------------------------------------
    async def finalize(state: TurnState) -> Dict[str, Any]:
        return {"status": "complete", "pending": None}

    g = StateGraph(TurnState)
    g.add_node("ingest", ingest)
    g.add_node("agent", agent)
    g.add_node("tools", run_tools)
    g.add_node("pause", pause)
    g.add_node("finalize", finalize)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "agent")
    g.add_conditional_edges("agent", after_agent, {"tools": "tools", "finalize": "finalize"})
    g.add_conditional_edges("tools", after_tools, {"pause": "pause", "agent": "agent"})
    g.add_edge("pause", "agent")          # resume: the SAME tool call returns, loop continues
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
