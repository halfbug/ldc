"""SSE layer (Chapters 3, 7, 8): producer task -> asyncio.Queue -> stream_turn() generator."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, RemoveMessage, ToolMessage
from langgraph.types import Command

from .cancel import CancelSignal, CancelStore
from .graph import NOT_PERFORMED, STOPPED_NOTE

_DONE = object()
_TERMINAL = ("turn.end", "error")


@dataclass
class CoreConfig:
    heartbeat_s: float = 10.0
    turn_ceiling_s: float = 180.0
    cancel_poll_s: float = 0.5
    ceiling_record_grace_s: float = 5.0


class PreflightError(Exception):
    def __init__(self, status: int, code: str, message: str = "") -> None:
        self.status, self.code, self.message = status, code, message

    def body(self) -> Dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message or self.code}}


def sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


def _text_of(chunk: Any) -> str:
    c = getattr(chunk, "content", "")
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")


def _pending_interrupt(state) -> Optional[Dict[str, Any]]:
    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


# ------------------------------------------------------------------ preflight (Ch. 7.2)
async def preflight(graph, request: Dict[str, Any]) -> Dict[str, Any]:
    thread_id = request.get("thread_id")
    if not thread_id:
        raise PreflightError(400, "thread_id_required")
    message = (request.get("message") or "").strip()
    action_result = request.get("action_result")
    if not message and not action_result:
        raise PreflightError(400, "empty_request")
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    pending = _pending_interrupt(state)
    if action_result and not pending:
        raise PreflightError(409, "nothing_to_resume")
    if action_result:
        mode = "resume"
    elif pending:
        mode = "not_performed"          # typed a new message instead of answering (Ch. 7.4)
    else:
        mode = "new"
    return {"mode": mode, "pending": pending}


# ------------------------------------------------------------------ the producer
async def _stop_finalize(graph, config, shown: str) -> None:
    """Chapter 8.5: keep only what the teacher was shown, plus the stopped note."""
    state = await graph.aget_state(config)
    msgs = state.values.get("messages", [])
    keep = state.values.get("keep_len", len(msgs))
    note = f"{shown}\n\n{STOPPED_NOTE}" if shown else STOPPED_NOTE
    await graph.aupdate_state(
        config,
        {
            "messages": [RemoveMessage(id=m.id) for m in msgs[keep:]] + [AIMessage(content=note)],
            "pending": None,
            "status": "stopped",
        },
        as_node="finalize",             # next node after finalize is END -> the thread is idle
    )


async def _run_graph(graph, config, graph_input, emit, shown_parts: list) -> str:
    """Drive the graph and translate LangGraph stream parts into Scout SSE events."""
    async for mode, chunk in graph.astream(
        graph_input, config, stream_mode=["messages", "updates", "custom"]
    ):
        if mode == "messages":
            msg, meta = chunk
            if isinstance(msg, AIMessageChunk) and meta.get("langgraph_node") == "agent":
                text = _text_of(msg)
                if text:
                    shown_parts.append(text)
                    await emit("text.delta", {"text": text})
        elif mode == "custom":
            if chunk.get("event") == "status":
                await emit("status", {"label": chunk["label"]})
        elif mode == "updates" and "__interrupt__" in chunk:
            value = chunk["__interrupt__"][0].value          # interrupt() payload
            await emit(value["event"], value["wire"])        # pending_action | pending_prompt
    final = await graph.aget_state(config)
    return "paused" if _pending_interrupt(final) else "complete"


async def _run_turn(graph, request, emit, cancel: CancelSignal, store: CancelStore,
                    cfg: CoreConfig, turn_id: str, mode: str) -> None:
    thread_id, user_id = request["thread_id"], request.get("user_id", "")
    config = {"configurable": {"thread_id": thread_id}}
    await emit("turn.start", {"thread_id": thread_id, "turn_id": turn_id, "core": "langgraph"})
    await store.mark_running(thread_id, turn_id, user_id)
    shown: list[str] = []
    t0 = time.monotonic()
    try:
        # Stop that beat the turn (Ch. 8.3 "early stop"): do not start the model at all.
        if await store.cancel_seen(thread_id, turn_id):
            cancel.set("cancel_endpoint")
            if mode == "new":
                await graph.aupdate_state(
                    config,
                    {"messages": [HumanMessage(request["message"]), AIMessage(STOPPED_NOTE)],
                     "status": "stopped", "pending": None},
                    as_node="finalize",
                )
            await emit("turn.end", {"status": "stopped", "outcome": "stopped", "stopped_by": cancel.reason})
            return

        # ---- build the graph input for the three kinds of request --------------------
        if mode == "new":
            graph_input: Any = {"messages": [HumanMessage(request["message"])], "turn_id": turn_id}
        elif mode == "resume":
            graph_input = Command(resume=request["action_result"])   # Ch. 7: same tool call returns
        else:  # "not_performed": close the paused call, add the new message, run the loop (Ch. 7.4)
            state = await graph.aget_state(config)
            pend = state.values["pending"]
            n = len(state.values["messages"])
            await graph.aupdate_state(
                config,
                {"messages": [ToolMessage(NOT_PERFORMED, tool_call_id=pend["tool_call_id"], status="error"),
                              HumanMessage(request["message"])],
                 "pending": None, "turn_id": turn_id, "keep_len": n + 2},
                as_node="pause",
            )
            graph_input = None          # continue from `pause` -> `agent`

        # ---- run until finished, paused, or stopped (Ch. 8.4) ------------------------
        stopped = await _run_unless_stopped(
            _run_graph(graph, config, graph_input, emit, shown), cancel, store,
            thread_id, turn_id, cfg.cancel_poll_s,
        )
        if stopped is None:                                   # Stop won the race
            await _stop_finalize(graph, config, "".join(shown).strip())
            await emit("turn.end", {"status": "stopped", "outcome": "stopped", "stopped_by": cancel.reason})
            return
        await emit("turn.end", {"status": stopped, "outcome": stopped,
                                "timings": {"total_ms": int((time.monotonic() - t0) * 1000)}})
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await emit("error", {"code": "internal", "message": "Something went wrong. Try again.",
                             "retryable": True, "detail": str(exc)[:200]})
    finally:
        await store.clear_running(thread_id, turn_id)


async def _run_unless_stopped(coro, cancel: CancelSignal, store: CancelStore,
                              thread_id: str, turn_id: str, poll_s: float) -> Optional[str]:
    """Port of _run_unless_stopped + _watch_for_cancel. Returns the status, or None if stopped."""
    async def watch() -> None:
        while not cancel.event.is_set():
            if await store.cancel_seen(thread_id, turn_id):
                cancel.set("cancel_endpoint")
                return
            await asyncio.sleep(poll_s)

    run = asyncio.create_task(coro)
    stop_wait = asyncio.create_task(cancel.event.wait())
    poller = asyncio.create_task(watch())
    try:
        await asyncio.wait({run, stop_wait}, return_when=asyncio.FIRST_COMPLETED)
        if run.done():
            return run.result()
        run.cancel()                      # also cancels the model call it is awaiting
        try:
            await run
        except asyncio.CancelledError:
            pass
        return None
    finally:
        for t in (run, stop_wait, poller):
            if not t.done():
                t.cancel()


# ------------------------------------------------------------------ the consumer (Ch. 3.2)
async def stream_turn(graph, request: Dict[str, Any], prepared: Dict[str, Any],
                      store: CancelStore, cfg: Optional[CoreConfig] = None) -> AsyncIterator[str]:
    cfg = cfg or CoreConfig()
    started = time.monotonic()
    turn_id = request.get("turn_id") or f"t-{uuid.uuid4().hex[:8]}"
    queue: asyncio.Queue = asyncio.Queue()
    cancel = CancelSignal()

    async def emit(event: str, data: Dict[str, Any]) -> None:
        await queue.put((event, data))

    task = asyncio.create_task(asyncio.wait_for(
        _run_turn(graph, request, emit, cancel, store, cfg, turn_id, prepared["mode"]),
        timeout=cfg.turn_ceiling_s))
    task.add_done_callback(lambda _t: queue.put_nowait(_DONE))

    terminal_sent = False
    try:
        while True:
            remaining = cfg.turn_ceiling_s - (time.monotonic() - started)
            if remaining <= 0:
                task.cancel()
                if not terminal_sent:
                    yield sse("error", {"code": "turn_ceiling", "message": "This took too long. Try again.",
                                        "retryable": True})
                    terminal_sent = True
                await asyncio.wait({task}, timeout=cfg.ceiling_record_grace_s)
                return
            try:
                item = await asyncio.wait_for(queue.get(), timeout=min(cfg.heartbeat_s, remaining))
            except asyncio.TimeoutError:
                if not terminal_sent:
                    yield ": keep-alive\n\n"                      # heartbeat comment
                continue
            if item is _DONE:
                if not terminal_sent:                             # task died with no ending
                    yield sse("error", {"code": "internal", "message": "Something went wrong.",
                                        "retryable": True})
                    terminal_sent = True
                return
            if terminal_sent:
                continue
            event, data = item
            yield sse(event, data)
            if event in _TERMINAL:                                # exactly one ending
                terminal_sent = True
    finally:
        if not terminal_sent and not task.done():
            cancel.set("disconnect")                              # local-only; Lambda needs /cancel
