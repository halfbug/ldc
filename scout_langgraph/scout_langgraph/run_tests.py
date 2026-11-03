"""End-to-end checks: complete, pause->resume, ask_user, NOT_PERFORMED, 409, Stop (mid + early)."""
import asyncio, json
from langgraph.checkpoint.memory import InMemorySaver
from .cancel import InMemoryCancelStore
from .fake_llm import ScriptedChatModel
from .graph import STOPPED_NOTE, build_graph
from .streaming import CoreConfig, PreflightError, preflight, stream_turn


async def search_curriculum(query: str = "") -> str:
    return "3 articles found: Volcanoes, Plate Tectonics, Earthquakes"


def parse(frames):
    out = []
    for f in frames:
        if f.startswith(":"):
            out.append(("heartbeat", None)); continue
        ev, data = f.strip().split("\n", 1)
        out.append((ev[7:], json.loads(data[6:])))
    return out


async def turn(graph, store, req, cfg=None, mid=None):
    prepared = await preflight(graph, req)
    frames = []
    async for f in stream_turn(graph, req, prepared, store, cfg or CoreConfig(heartbeat_s=0.2)):
        frames.append(f)
        if mid:
            await mid(f)
    return parse(frames)


def summary(events):
    text = "".join(d["text"] for e, d in events if e == "text.delta")
    kinds = [e for e, _ in events if e not in ("text.delta", "status", "heartbeat")]
    return text.strip(), kinds


async def main():
    store = InMemoryCancelStore()
    ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (c or exit(1))

    # ---------- 1. pause (page_action) -> resume -> complete
    llm = ScriptedChatModel([
        {"text": "Let me search.", "tool_calls": [{"name": "search_curriculum", "args": {"query": "volcano"}, "id": "tu-1"}]},
        {"text": "Found three articles. Opening Lessons.", "tool_calls": [{"name": "page_action", "args": {"capability": "open_tab", "args": {"tab": "Lessons"}}, "id": "tu-2"}]},
        {"text": "The Lessons tab is open."},
    ])
    g = build_graph(llm, {"search_curriculum": search_curriculum}, InMemorySaver())
    ev = await turn(g, store, {"thread_id": "A", "user_id": "u", "message": "volcano lesson, open Lessons"})
    text, kinds = summary(ev)
    ok(kinds == ["turn.start", "pending_action", "turn.end"], f"1a pause events: {kinds}")
    ok([d for e, d in ev if e == "turn.end"][0]["status"] == "paused", "1b turn.end status=paused")
    pa = [d for e, d in ev if e == "pending_action"][0]
    ok(pa["id"] == "tu-2" and pa["capability"] == "open_tab", "1c pending_action carries the toolUse id")

    ev = await turn(g, store, {"thread_id": "A", "user_id": "u",
                               "action_result": {"id": "tu-2", "capability": "open_tab", "status": "ok", "message": "Lessons tab open"}})
    text, kinds = summary(ev)
    ok(kinds == ["turn.start", "turn.end"] and text == "The Lessons tab is open.", f"1d resume continues same call: {text!r}")
    ok([d for e, d in ev if e == "turn.end"][0]["status"] == "complete", "1e resumed turn complete")
    msgs = g.get_state({"configurable": {"thread_id": "A"}}).values["messages"]
    tm = [m for m in msgs if m.type == "tool" and m.tool_call_id == "tu-2"][0]
    ok("open_tab: ok" in tm.content, f"1f toolResult for paused id: {tm.content!r}")
    ok(any(m.type == "tool" and m.tool_call_id == "tu-1" for m in msgs), "1g sibling/earlier tool result kept")

    # ---------- 2. 409 nothing_to_resume
    try:
        await preflight(g, {"thread_id": "A", "action_result": {"id": "x"}})
        ok(False, "2 should 409")
    except PreflightError as e:
        ok(e.status == 409 and e.code == "nothing_to_resume", "2 409 nothing_to_resume")

    # ---------- 3. ask_user prompt + new message instead (NOT_PERFORMED)
    llm = ScriptedChatModel([
        {"text": "Which grade?", "tool_calls": [{"name": "ask_user", "args": {"question": "Which grade?", "options": ["Grade 2", "Grade 3"]}, "id": "tu-9"}]},
        {"text": "Sure, here is something else."},
    ])
    g2 = build_graph(llm, {}, InMemorySaver())
    ev = await turn(g2, store, {"thread_id": "B", "user_id": "u", "message": "level this article"})
    ok(summary(ev)[1] == ["turn.start", "pending_prompt", "turn.end"], "3a pending_prompt emitted")
    ev = await turn(g2, store, {"thread_id": "B", "user_id": "u", "message": "never mind, different question"})
    ok(summary(ev)[0] == "Sure, here is something else.", "3b new message runs a fresh turn")
    msgs = g2.get_state({"configurable": {"thread_id": "B"}}).values["messages"]
    tm = [m for m in msgs if m.type == "tool"][0]
    ok(tm.content.startswith("Not performed") and tm.status == "error", "3c paused call closed as NOT_PERFORMED")
    ok(not g2.get_state({"configurable": {"thread_id": "B"}}).tasks[0:1] or not any(t.interrupts for t in g2.get_state({"configurable": {"thread_id": "B"}}).tasks), "3d nothing pending afterwards")

    # ---------- 4. Stop mid-stream
    long = " ".join(f"word{i}" for i in range(40))
    llm = ScriptedChatModel([{"text": long, "delay": 0.05}])
    g3 = build_graph(llm, {}, InMemorySaver())
    cfg = CoreConfig(heartbeat_s=0.2, cancel_poll_s=0.1)
    state = {"seen": 0}
    async def press_stop(frame):
        if "text.delta" in frame:
            state["seen"] += 1
            if state["seen"] == 5:
                print("   ... teacher presses Stop after 5 words")
                print("   cancel ->", await store.request_cancel("C", "u", "turn-c"))
    ev = await turn(g3, store, {"thread_id": "C", "user_id": "u", "turn_id": "turn-c", "message": "write a lot"}, cfg, press_stop)
    text, kinds = summary(ev)
    end = [d for e, d in ev if e == "turn.end"][0]
    ok(end["status"] == "stopped" and end["stopped_by"] == "cancel_endpoint", f"4a stopped by cancel endpoint: {end}")
    ok(len(text.split()) < 40, f"4b stream really stopped early ({len(text.split())} of 40 words shown)")
    msgs = g3.get_state({"configurable": {"thread_id": "C"}}).values["messages"]
    ok(msgs[-1].content.endswith(STOPPED_NOTE), "4c saved thread ends with stopped note")
    saved_words = len(msgs[-1].content.replace(STOPPED_NOTE, "").split())
    ok(saved_words == len(text.split()), f"4d saved ONLY what was shown ({saved_words} words), not the full answer")
    ok(await store.request_cancel("C", "u", "turn-c") == "not_running", "4e cancel after the turn ended is a no-op")

    # ---------- 5. early Stop (cancel recorded before the turn starts)
    llm = ScriptedChatModel([{"text": "should never run"}])
    g4 = build_graph(llm, {}, InMemorySaver())
    await store.request_cancel("D", "u", "turn-d")
    ev = await turn(g4, store, {"thread_id": "D", "user_id": "u", "turn_id": "turn-d", "message": "hello"})
    ok([d for e, d in ev if e == "turn.end"][0]["status"] == "stopped" and llm._i == 0, "5 early stop: model never called")

    # ---------- 6. heartbeat + ceiling
    llm = ScriptedChatModel([{"text": "slow slow slow", "delay": 0.6}])
    g5 = build_graph(llm, {}, InMemorySaver())
    ev = await turn(g5, store, {"thread_id": "E", "user_id": "u", "message": "go"}, CoreConfig(heartbeat_s=0.2, turn_ceiling_s=1.0))
    ok(any(e == "heartbeat" for e, _ in ev), "6a ': keep-alive' heartbeat written during silence")
    last = ev[-1]
    ok(last[0] == "error" and last[1]["code"] == "turn_ceiling", f"6b turn_ceiling error: {last}")
    ok(sum(1 for e, _ in ev if e in ("turn.end", "error")) == 1, "6c exactly one terminal event")
    print("\nALL CHECKS PASSED")

asyncio.run(main())
