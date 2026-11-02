"""Draws the figures for the Scout streaming guide (SSE, pause, resume, stop) into ./fig as PNG."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "fig")
os.makedirs(OUT, exist_ok=True)

NAVY, TEAL, ORANGE, PURPLE, GREY, GREEN, RED = "#1F3A5F", "#2A9D8F", "#E76F51", "#6D5BD0", "#5F6B7A", "#3A8E4C", "#C0392B"
FILL = {NAVY: "#E3EAF3", TEAL: "#DDF2EF", ORANGE: "#FBE7E1", PURPLE: "#ECE9FB", GREY: "#EEF0F3", GREEN: "#E2F2E5", RED: "#F8E1DE"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color=NAVY, size=9.0, bold_first=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                linewidth=1.4, edgecolor=color, facecolor=FILL[color], zorder=3))
    lines = text.split("\n")
    if bold_first and len(lines) > 1:
        ax.text(x + w / 2, y + h - 2.0, lines[0], ha="center", va="top", fontsize=size, weight="bold", color=color,
                zorder=4)
        ax.text(x + w / 2, y + h - 5.2, "\n".join(lines[1:]), ha="center", va="top", fontsize=size - 1.3,
                color="#222", linespacing=1.35, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
                weight="bold" if bold_first else "normal", color=color, zorder=4)


def arrow(ax, x1, y1, x2, y2, text="", color=GREY, style="-|>", dashed=False, size=7.8, offset=1.0, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12, color=color, linewidth=1.3,
                                 linestyle="--" if dashed else "-", connectionstyle=f"arc3,rad={rad}", zorder=2))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + offset, text, ha="center", va="bottom", fontsize=size, color=color,
                zorder=4, bbox=dict(facecolor="white", edgecolor="none", pad=0.6))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)


def seq(name, cols, msgs, height=9.0, notes=()):
    """A UML sequence diagram. cols: (key, label, x, colour). msgs: (num, from, to, text, colour, dashed?)."""
    fig, ax = canvas(10, height)
    top = height * 10 - 9
    xs = {key: x for key, _, x, _ in cols}
    y = top - 4
    for msg in msgs:
        num, a, b, text, col = msg[:5]
        dashed = msg[5] if len(msg) > 5 else (xs[b] < xs[a])
        xa, xb = xs[a], xs[b]
        lines = text.count("\n") + 1
        tag = f"{num}. " if num else ""
        if a == b:
            y -= 3.6 + 2.8 * lines
            right = xa < 80
            ax.add_patch(FancyArrowPatch((xa, y + 1.2), (xa, y - 1.2), arrowstyle="-|>", mutation_scale=10,
                                         color=col, connectionstyle=f"arc3,rad={-1.4 if right else 1.4}", zorder=3))
            ax.text(xa + 3.0 if right else xa - 3.0, y, tag + text, fontsize=8.6, color=col, va="center",
                    ha="left" if right else "right", linespacing=1.3, zorder=4,
                    bbox=dict(facecolor="white", edgecolor=col, linewidth=0.6, boxstyle="round,pad=0.35"))
            y -= 1.2 + 0.8 * lines
        else:
            y -= 2.8 + 2.7 * lines
            ax.add_patch(FancyArrowPatch((xa, y), (xb, y), arrowstyle="-|>", mutation_scale=11, color=col,
                                         linewidth=1.3, zorder=3, linestyle="--" if dashed else "-"))
            ax.text((xa + xb) / 2, y + 0.7, tag + text, fontsize=8.6, color=col, ha="center", va="bottom",
                    linespacing=1.3, zorder=4, bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
    bottom = y - 4
    for key, label, x, col in cols:
        box(ax, x - 7.8, top, 15.6, 8, label, col, size=8.4)
        ax.plot([x, x], [top, bottom], color=col, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ax.set_ylim(bottom - 1, height * 10)
    save(fig, name)


# S1. What SSE looks like on the wire ------------------------------------------------------
fig, ax = canvas(10, 4.6)
ax.add_patch(FancyBboxPatch((2, 4), 60, 40, boxstyle="round,pad=0.3,rounding_size=1", facecolor="#F4F6F8",
                            edgecolor=GREY, linewidth=1))
wire = [("event: turn.start", NAVY), ('data: {"thread_id":"t-1","turn_id":"u-9","core":"v2"}', NAVY), ("", None),
        ("event: status", NAVY), ('data: {"label":"Searching the curriculum"}', NAVY), ("", None),
        (": keep-alive", GREY), ("", None),
        ("event: text.delta", NAVY), ('data: {"text":"Here are three articles"}', NAVY), ("", None),
        ("event: turn.end", NAVY), ('data: {"status":"complete","cost_usd":0.021}', NAVY), ("", None)]
for i, (line, col) in enumerate(wire):
    yy = 41 - i * 2.6
    ax.text(4, yy, line if line else "⏎ (blank line)", family="DejaVu Sans Mono", fontsize=7.6,
            color=col or "#9AA3AD", va="center")
notes = [(39.7, "one event = an event: line + a data: line"), (35.8, "a blank line ends the event"),
         (25.4, "a line starting with ':' is a comment:\nthe heartbeat. The browser ignores it."),
         (11.1, "exactly one turn.end (or error)\nends every stream")]
for yy, text in notes:
    if text:
        ax.text(66, yy, text, fontsize=8, color=TEAL, va="center")
        ax.plot([62.5, 65.3], [yy, yy], color=TEAL, linewidth=1)
save(fig, "s01_sse_wire.png")

# S2. The streaming path, end to end ---------------------------------------------------------
fig, ax = canvas(10, 5.2)
ax.text(2, 50, "rag (server)", fontsize=9.5, weight="bold", color=TEAL)
ax.text(2, 22, "frontend-v3 (browser)", fontsize=9.5, weight="bold", color=NAVY)
server = [("_run_turn()\ntask: loop, tools", TEAL), ("emit()\n→ asyncio.Queue", TEAL), ("stream_turn()\nyields sse()", TEAL),
          ("StreamingResponse\ntext/event-stream", TEAL), ("Function URL\nRESPONSE_STREAM", ORANGE)]
for i, (t, col) in enumerate(server):
    box(ax, 2 + i * 19.5, 32, 17, 13, t, col, size=7.8)
    if i:
        arrow(ax, 2 + i * 19.5 - 2.5, 38.5, 2 + i * 19.5, 38.5, "", GREY)
client = [("UI\ncoreLive → dialog", NAVY), ("applyCoreEvent()\nupdates state", NAVY), ("toCoreEvent()\nJSON → event", NAVY),
          ("SseParser.push()\nbytes → messages", NAVY), ("read loop\nconsumeCoreStream()\nreader.read()", NAVY)]
for i, (t, col) in enumerate(client):
    box(ax, 2 + i * 19.5, 4, 17, 13, t, col, size=7.8)
    if i:
        arrow(ax, 2 + i * 19.5, 10.5, 2 + i * 19.5 - 2.5, 10.5, "", GREY)
arrow(ax, 88.5, 32, 88.5, 17.3, "bytes, as they\nare written", ORANGE, offset=-3)
save(fig, "s02_stream_path.png")

# S3. Producer and consumer inside stream_turn -------------------------------------------------
fig, ax = canvas(10, 4.6)
box(ax, 2, 22, 26, 18, "_run_turn() task\nproducer: runs the loop,\ncalls emit(event, data)\nfor every event", TEAL, size=8.6)
box(ax, 36, 25, 22, 12, "asyncio.Queue\n(event, data) items\n+ _DONE at the end", PURPLE, size=8.6)
box(ax, 66, 22, 32, 18, "stream_turn() loop\nconsumer: queue.get() with\ntimeout = heartbeat (10 s)\nyields sse(event, data)", NAVY, size=8.6)
arrow(ax, 28, 31, 36, 31, "", GREY)
arrow(ax, 58, 31, 66, 31, "", GREY)
box(ax, 2, 2, 30, 14, "Nothing for 10 s?\nyield \": keep-alive\"\nso proxies keep the line open", GREY, size=8.2)
box(ax, 35, 2, 30, 14, "Past the 180 s ceiling?\ncancel the task,\nsend error turn_ceiling", RED, size=8.2)
box(ax, 68, 2, 30, 14, "Sent turn.end / error?\nkeep the stream open only\nfor bookkeeping, send nothing", GREEN, size=8.2)
for x in (17, 50, 83):
    arrow(ax, 82, 22, x, 16.3, "", GREY, dashed=True)
save(fig, "s03_queue.png")

# S4. Turn states (UML state diagram) ----------------------------------------------------------
fig, ax = canvas(10, 4.8)
box(ax, 2, 22, 15, 9, "request sent", GREY, size=8.6)
box(ax, 24, 22, 17, 9, "streaming", NAVY, size=8.8)
box(ax, 58, 36, 16, 9, "turn.end\ncomplete", GREEN, size=8.6, bold_first=False)
box(ax, 58, 22, 16, 9, "turn.end\npaused", ORANGE, size=8.6, bold_first=False)
box(ax, 58, 3, 16, 9, "turn.end\nstopped", PURPLE, size=8.6, bold_first=False)
box(ax, 2, 3, 15, 9, "error", RED, size=8.6)
arrow(ax, 17, 26.5, 24, 26.5, "", GREY)
ax.text(20.5, 32.5, "200 +\nturn.start", fontsize=7.2, color=GREY, ha="center")
arrow(ax, 41, 30, 58, 40.5, "model finished", GREY, offset=0.4)
arrow(ax, 41, 28, 58, 28, "a tool paused", GREY, offset=0.5)
arrow(ax, 33, 22, 58, 7.5, "Stop pressed", GREY, offset=-4.2)
arrow(ax, 27, 22, 14, 12.3, "", RED, dashed=True)
ax.text(23, 14, "ceiling, idle\nor crash", fontsize=7.2, color=RED, ha="left")
arrow(ax, 62, 22, 39, 22, "", ORANGE, dashed=True, rad=-0.6)
ax.text(76, 17, "action_result → resume\n(a new request)", fontsize=7.4, color=ORANGE, ha="center")
save(fig, "s04_states.png")

# S5. Pause: three kinds -----------------------------------------------------------------------
fig, ax = canvas(10, 4.8)
box(ax, 34, 38, 32, 9, "turn.end {status: \"paused\"}", ORANGE, size=9, bold_first=False)
box(ax, 2, 14, 30, 17, "pending_action, risk low\nrunAction() runs it at once\n(open a tab, read pacing)", NAVY, size=8.4)
box(ax, 35, 14, 30, 17, "pending_action, needs approval\nholdForApproval(): card\nwaits for Approve / Not now", PURPLE, size=8.4)
box(ax, 68, 14, 30, 17, "pending_prompt (ask_user)\nholdForPrompt(): question\nwith buttons, waits", TEAL, size=8.4)
for x in (17, 50, 83):
    arrow(ax, 50, 38, x, 31.3, "", GREY)
box(ax, 20, 1, 60, 8, "all three end the same way: POST /v2/turn with an action_result", GREEN, size=8.6, bold_first=False)
for x in (17, 50, 83):
    arrow(ax, x, 14, 50 + (x - 50) * 0.5, 9.3, "", GREY, dashed=True)
save(fig, "s05_pause_kinds.png")

COLS = [("ui", "Teacher /\nScout UI", 8.5, GREY), ("chat", "useAiChat\ncoreClient", 25, NAVY),
        ("exec", "executor", 41, PURPLE), ("rag", "rag: router\nruntime", 58, TEAL), ("loop", "loop.py\n+ tools", 74.5, TEAL),
        ("db", "MongoDB\nthreads", 91, GREEN)]

# S6. Pause sequence ---------------------------------------------------------------------------
seq("s06_pause_seq.png", COLS, [
    (1, "loop", "loop", "model returns toolUse page_action\nor ask_user", TEAL),
    (2, "loop", "loop", "tool.run() → ToolOutcome(pause=\nPendingAction | PendingPrompt)", TEAL),
    (3, "loop", "rag", "LoopResult(status=\"paused\", pending={tool_use_id,\nkind, wire, results})", TEAL, True),
    (4, "loop", "chat", "emit(\"pending_action\", wire)  → SSE", ORANGE),
    (5, "rag", "db", "thread.pending = result.pending\nthreads.save_thread()", TEAL),
    (6, "rag", "chat", "SSE turn.end {status: \"paused\"}", TEAL),
    (7, "chat", "chat", "applyCoreEvent(): state.pendingAction\nsendCoreTurn() resolves", NAVY),
    (8, "chat", "exec", "risk low: runRequested() → runAction()", NAVY),
    (9, "chat", "ui", "or: approval card / question card", NAVY),
], height=8.2)

# S7. Resume sequence --------------------------------------------------------------------------
seq("s07_resume_seq.png", COLS, [
    (1, "ui", "chat", "Approve / answer chosen\n(or the action already ran)", GREY),
    (2, "chat", "chat", "resumeHeld() / actions.resultFor()\n→ action_result {id, capability,\nstatus, message}", NAVY),
    (3, "chat", "rag", "POST /v2/turn {thread_id, message: \"\",\naction_result}", NAVY),
    (4, "rag", "db", "preflight(): load_thread()", TEAL),
    (5, "db", "rag", "thread + pending (if none: 409 nothing_to_resume)", GREEN),
    (6, "rag", "rag", "_action_result_block() → toolResult\nfor the paused toolUseId (+ sibling results)", TEAL),
    (7, "rag", "loop", "run_loop() continues the SAME tool call", TEAL),
    (8, "loop", "chat", "SSE text.delta … turn.end {complete}", TEAL),
], height=8.0)

# S8. Stop across two Lambda environments ---------------------------------------------------
STOP_COLS = [("ui", "Teacher", 8.5, GREY), ("chat", "coreClient", 25, NAVY), ("envB", "Lambda env B\n/v2/turn/cancel", 41.5, ORANGE),
             ("db", "MongoDB", 58, GREEN), ("envA", "Lambda env A\nstreaming turn", 74.5, TEAL), ("model", "Bedrock", 91, PURPLE)]
seq("s08_stop_seq.png", STOP_COLS, [
    (0, "envA", "model", "loop is waiting on the model", TEAL),
    (1, "ui", "chat", "presses Stop", GREY),
    (2, "chat", "chat", "stopCoreTurn(): remember this turn\nas stopped, controller.abort()", NAVY),
    (3, "chat", "envB", "POST /v2/turn/cancel {thread_id, turn_id}", NAVY),
    (4, "envB", "db", "request_cancel(): set cancel_turn_id\n(or record an early Stop by turn id)", ORANGE),
    (5, "envA", "db", "_watch_for_cancel(): poll every 0.5 s", TEAL),
    (6, "db", "envA", "cancel_requested() → true", GREEN),
    (7, "envA", "envA", "CancelSignal.set(\"cancel_endpoint\")\n_run_unless_stopped(): loop_task.cancel()", TEAL),
    (8, "envA", "db", "save only what was shown + STOPPED_NOTE\nthread.pending = None", TEAL),
    (9, "chat", "ui", "keep the partial answer, marked stopped", NAVY),
], height=8.6)

# S9. Timers on a timeline ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.0), dpi=200)
rows = [("Cancel poll (server)", 0.5, PURPLE), ("Heartbeat ': keep-alive' (server)", 10, TEAL),
        ("Idle limit between bytes (browser)", 60, NAVY), ("Turn ceiling (server)", 180, ORANGE),
        ("Lambda timeout (AWS)", 210, RED)]
for i, (label, s, col) in enumerate(rows[::-1]):
    ax.barh(i, s, color=col, height=0.55)
    ax.text(s + 2, i, f"{s:g} s", va="center", fontsize=8.5)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows[::-1]], fontsize=8.5)
ax.set_xlim(0, 235)
ax.set_xlabel("seconds")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "s09_timers.png")


# ---------------------------------------------------------------- helpers for flowcharts
from matplotlib.patches import Polygon  # noqa: E402


def diamond(ax, cx, cy, text, color=NAVY, w=26, h=9, size=8.0):
    ax.add_patch(Polygon([(cx - w / 2, cy), (cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2)], closed=True,
                         facecolor=FILL[color], edgecolor=color, linewidth=1.4, zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=size, color=color, weight="bold", zorder=4,
            linespacing=1.25)


def label(ax, x, y, text, color=GREY, size=7.8, ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=color, weight="bold", zorder=5,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.4))


def mono_box(ax, x, y, w, h, lines, color=GREY, size=7.4, title=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8", facecolor="#F4F6F8",
                                edgecolor=color, linewidth=1.1, zorder=3))
    top = y + h - 2.2
    if title:
        ax.text(x + 1.2, top, title, fontsize=size + 0.6, color=color, weight="bold", va="center", zorder=4)
        top -= 3.0
    for i, (text, col) in enumerate(lines):
        ax.text(x + 1.2, top - i * 2.6, text, family="DejaVu Sans Mono", fontsize=size, color=col or "#222",
                va="center", zorder=4)


# S10. stream_turn(): one pass of the loop, as a flowchart --------------------------------------
fig, ax = canvas(10, 8.8)
box(ax, 38, 79, 24, 6, "while True:", NAVY, size=8.6, bold_first=False)
diamond(ax, 50, 69, "past the 180 s\nceiling?", RED)
box(ax, 70, 63.5, 28, 11, "task.cancel()\nyield error turn_ceiling\nwait ≤5 s for bookkeeping\nreturn", RED, size=7.8)
box(ax, 35, 53, 30, 7, "item = await queue.get()\n(wait at most 10 s)", NAVY, size=8.0, bold_first=False)
diamond(ax, 50, 43.5, "nothing came\nin 10 s?", GREY)
box(ax, 6, 39.5, 22, 8, "yield \": keep-alive\"\n(heartbeat)", GREY, size=7.8)
diamond(ax, 50, 32, "item is _DONE?\n(task finished)", PURPLE)
box(ax, 70, 26.5, 28, 11, "no ending sent yet?\nyield error internal\nreturn", PURPLE, size=7.8)
diamond(ax, 50, 20.5, "ending already\nsent?", GREEN)
box(ax, 6, 16.5, 22, 8, "skip silently\n(bookkeeping\nstill running)", GREEN, size=7.8)
box(ax, 31, 2, 38, 10, "yield sse(event, data)\nturn.end or error → ending sent", TEAL, size=8.2)
arrow(ax, 50, 79, 50, 73.6, "", GREY)
arrow(ax, 63, 69, 70, 69, "", RED); label(ax, 66.5, 71, "yes", RED)
arrow(ax, 50, 64.5, 50, 60.2, "", GREY); label(ax, 52.5, 62.3, "no")
arrow(ax, 50, 53, 50, 48, "", GREY)
arrow(ax, 37, 43.5, 28.2, 43.5, "", GREY); label(ax, 32.5, 45.5, "yes")
arrow(ax, 50, 39, 50, 36.6, "", GREY); label(ax, 53, 37.8, "no")
arrow(ax, 63, 32, 70, 32, "", PURPLE); label(ax, 66.5, 34, "yes", PURPLE)
arrow(ax, 50, 27.5, 50, 25.1, "", GREY); label(ax, 53, 26.3, "no")
arrow(ax, 37, 20.5, 28.2, 20.5, "", GREEN); label(ax, 32.5, 22.5, "yes", GREEN)
arrow(ax, 50, 16, 50, 12.2, "", GREY); label(ax, 53, 14.1, "no")
for y0, x0 in ((43.5, 5.6), (20.5, 5.6), (7, 30.6)):
    ax.plot([x0, 2.5], [y0, y0], color=GREY, linewidth=1.2, linestyle="--", zorder=1)
ax.plot([2.5, 2.5], [7, 82], color=GREY, linewidth=1.2, linestyle="--", zorder=1)
arrow(ax, 2.5, 82, 37.8, 82, "", GREY, dashed=True)
label(ax, 2.5, 62, "back to\nthe top", GREY, size=7.4, ha="left")
save(fig, "s10_stream_loop.png")

# S11. One turn's events over time --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.4), dpi=200)
lanes = ["turn.start", "status", ": keep-alive", "text.delta", "artifact.*", "turn.end"]
colours = [NAVY, PURPLE, GREY, TEAL, ORANGE, GREEN]
marks = {"turn.start": [0.3], "status": [0.4, 1.6, 2.4], ": keep-alive": [12.4],
         "text.delta": [x / 10 for x in range(140, 175, 3)], "artifact.*": [x / 10 for x in range(176, 224, 4)],
         "turn.end": [22.8]}
for i, lane in enumerate(lanes):
    y = len(lanes) - 1 - i
    xs = marks[lane]
    ax.scatter(xs, [y] * len(xs), color=colours[i], s=34, zorder=3, marker="|" if lane in ("text.delta", "artifact.*")
               else "o", linewidths=2)
ax.axvspan(2.4, 14.0, color="#EEF0F3", zorder=0)
ax.text(8.2, 5.35, "a tool runs (no text yet): only status labels and, after 10 s of silence, a heartbeat",
        ha="center", fontsize=7.8, color=GREY)
ax.annotate("\"Thinking\" → \"Searching the curriculum\"\n→ \"Writing the lesson plan\"", xy=(1.6, 4), xytext=(3.2, 3.2),
            fontsize=7.4, color=PURPLE, arrowprops=dict(arrowstyle="-", color=PURPLE, lw=0.8))
ax.set_yticks(range(len(lanes)))
ax.set_yticklabels(lanes[::-1], fontsize=8.5, family="DejaVu Sans Mono")
ax.set_xlabel("seconds since the request (illustration)", fontsize=8.5)
ax.set_xlim(0, 24)
ax.set_ylim(-0.6, 5.8)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
fig.tight_layout()
save(fig, "s11_event_timeline.png")

# S12. Chunks are not events: what SseParser does -----------------------------------------------
fig, ax = canvas(10, 6.4)
ax.text(2, 61, "1. bytes arrive in chunks of any size", fontsize=9, weight="bold", color=NAVY)
chunks = [['event: status', 'data: {"label":"Sear'], ['ching"}', '', 'event: text.de'], ['lta', 'data: {"text":"Hi"}', '']]
for i, lines in enumerate(chunks):
    mono_box(ax, 2 + i * 33, 44, 30, 14, [(ln if ln else "⏎ (blank line)", None if ln else "#9AA3AD") for ln in lines],
             NAVY, title=f"chunk {i + 1}")
ax.text(2, 39, "2. the parser keeps any line that has no line end yet (`pending`)", fontsize=9, weight="bold",
        color=PURPLE, zorder=6, bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
pend = ['data: {"label":"Sear', 'event: text.de', '(nothing)']
for i, p in enumerate(pend):
    mono_box(ax, 2 + i * 33, 27, 30, 8.5, [(p, PURPLE)], PURPLE, title="pending after this chunk")
    arrow(ax, 17 + i * 33, 44, 17 + i * 33, 35.8, "", GREY)
ax.text(2, 22, "3. a blank line completes an event, which is handed on", fontsize=9, weight="bold", color=TEAL,
        zorder=6, bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
outs = [["(no event yet)"], ['{event: "status",', ' data: {"label":"Searching"}}'], ['{event: "text.delta",', ' data: {"text":"Hi"}}']]
for i, o in enumerate(outs):
    mono_box(ax, 2 + i * 33, 4, 30, 14, [(t, TEAL if i else "#9AA3AD") for t in o], TEAL, title="events out")
    arrow(ax, 17 + i * 33, 27, 17 + i * 33, 18.3, "", GREY)
save(fig, "s12_chunks.png")

# S13. consumeCoreStream(): what each read can return -------------------------------------------
fig, ax = canvas(10, 6.0)
box(ax, 2, 46, 22, 9, "reader.read()\nthe next chunk", NAVY, size=8.2)
box(ax, 39, 46, 22, 9, "idle timer\n60 s, reset every read", GREY, size=8.2)
box(ax, 76, 46, 22, 9, "abort signal\nfires on Stop / leave", ORANGE, size=8.2)
diamond(ax, 50, 35, "Promise.race(…)\nwho finished first?", PURPLE, w=30, h=10)
for x in (13, 50, 87):
    arrow(ax, x, 46, 50 + (x - 50) * 0.35, 40.2, "", GREY)
outs = [(2, "bytes\nparser.push() → deliver()\n→ read again", TEAL), (21.5, "done\nflush(); no ending?\n→ stream_closed", GREY),
        (41, "'idle'\n→ idle_timeout", GREY), (60.5, "'aborted'\nthrow AbortError(state)\n(partial state kept)", ORANGE),
        (80, "read() threw\naborted? AbortError\nelse → network", RED)]
for x, t, col in outs:
    box(ax, x, 6, 18, 17, t, col, size=7.6)
    arrow(ax, 50, 30, x + 9, 23.3, "", GREY)
arrow(ax, 6, 23, 6, 46, "", TEAL, dashed=True, rad=0.0)
label(ax, 9.5, 34, "loop", TEAL)
save(fig, "s13_read_race.png")

# S14. Which event writes which field of CoreTurnState -----------------------------------------
fig, ax = canvas(10, 6.2)
events = [("turn.start", NAVY), ("status", PURPLE), ("text.delta", TEAL), ("artifact.start/delta/end", ORANGE),
          ("content_results", GREEN), ("pending_action", ORANGE), ("pending_prompt", ORANGE), ("turn.end", GREEN),
          ("error", RED)]
fields = ["threadId, turnId, model", "status", "text  (+= each piece)", "artifacts[]", "contentResults",
          "pendingAction", "pendingPrompt", "end    → isTurnOver", "error  → isTurnOver"]
for i, ((ev, col), fld) in enumerate(zip(events, fields)):
    y = 54 - i * 6.0
    box(ax, 2, y, 27, 4.6, ev, col, size=8.0, bold_first=False)
    ax.add_patch(FancyBboxPatch((58, y), 40, 4.6, boxstyle="square,pad=0", facecolor="white", edgecolor=NAVY,
                                linewidth=1.0, zorder=3))
    ax.text(59.5, y + 2.3, "state." + fld, family="DejaVu Sans Mono", fontsize=7.8, va="center", zorder=4)
    arrow(ax, 29.5, y + 2.3, 57.6, y + 2.3, "", col)
ax.text(78, 61.2, "CoreTurnState  (one per turn)", ha="center", fontsize=9, weight="bold", color=NAVY)
ax.text(43, 61.2, "applyCoreEvent()", ha="center", fontsize=9, weight="bold", color=PURPLE)
save(fig, "s14_state_fields.png")


def history(ax, x, y, w, rows, title, color):
    """A Bedrock message list: rows of (role, [(block text, colour)])."""
    ax.text(x, y + 2, title, fontsize=9, weight="bold", color=color)
    cy = y - 2
    for role, blocks in rows:
        h = 3.2 * len(blocks) + 2.4
        cy -= h
        ax.add_patch(FancyBboxPatch((x, cy), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", facecolor="white",
                                    edgecolor=GREY, linewidth=0.9, zorder=2))
        ax.text(x + 1.2, cy + h - 1.6, role, fontsize=7.4, color=GREY, weight="bold", va="center", zorder=4)
        for i, (text, col) in enumerate(blocks):
            by = cy + h - 4.6 - i * 3.2
            ax.add_patch(FancyBboxPatch((x + 9, by - 1.2), w - 10.5, 2.6, boxstyle="square,pad=0",
                                        facecolor=FILL.get(col, "#F4F6F8"), edgecolor=col, linewidth=0.8, zorder=3))
            ax.text(x + 10, by + 0.1, text, fontsize=7.2, family="DejaVu Sans Mono", va="center", zorder=4)
        cy -= 1.5
    return cy


# S15. What is saved when a turn pauses --------------------------------------------------------
fig, ax = canvas(10, 5.2)
history(ax, 2, 46, 52, [
    ("user", [("Where is my class compared with…?", NAVY)]),
    ("assistant", [("text: \"Let me check.\"", GREY), ("toolUse X  page_action(pacing.where)", ORANGE),
                   ("toolUse Y  search_curriculum(…)", TEAL)]),
], "thread.messages  (the model's history)", NAVY)
mono_box(ax, 60, 14, 38, 33, [
    ("tool_use_id: \"X\"", ORANGE), ("tool:  \"page_action\"", None), ("kind:  \"action\"", None),
    ("wire:  {id: X, capability,", None), ("        args, stateVersion}", None), ("resume_instruction: …", None),
    ("results: [toolResult Y]", TEAL)], ORANGE, size=7.4, title="thread.pending")
arrow(ax, 54.5, 26, 59.6, 26, "", GREY)
box(ax, 2, 2, 96, 9, "Y already ran, so its result is kept in pending.results. X has no result yet — that missing "
    "toolResult IS the pause.\nBoth are saved to MongoDB, so the resume can reach any Lambda environment.", ORANGE,
    size=8.0, bold_first=False)
save(fig, "s15_pause_record.png")

# S16. The browser's action loop (useAiChat) ----------------------------------------------------
fig, ax = canvas(10, 7.4)
box(ax, 34, 64, 32, 7, "a turn's response arrives\n(sendTurn resolves)", NAVY, size=8.0, bold_first=False)
diamond(ax, 50, 54, "pending_prompt?", TEAL, w=26, h=8)
box(ax, 72, 50, 26, 8, "holdForPrompt()\nquestion card — wait", TEAL, size=7.8)
diamond(ax, 50, 42, "pending_action?", ORANGE, w=26, h=8)
box(ax, 7, 38, 21, 8, "done:\nshow the answer", GREEN, size=7.8)
box(ax, 34, 27, 32, 7, "actions.runRequested(pending)\n→ executor: gates, run(), verify()", PURPLE, size=7.6,
    bold_first=False)
diamond(ax, 50, 17, "needs_confirmation?", PURPLE, w=30, h=8)
box(ax, 72, 13, 26, 8, "holdForApproval()\napproval card — wait", PURPLE, size=7.8)
box(ax, 32, 1, 36, 8, "sendTurn({ message: '',\naction_result: resultFor(…) })", NAVY, size=7.6, bold_first=False)
arrow(ax, 50, 64, 50, 58.2, "", GREY)
arrow(ax, 63, 54, 72, 54, "", TEAL); label(ax, 67.5, 56, "yes", TEAL)
arrow(ax, 50, 50, 50, 46.2, "", GREY); label(ax, 53, 48.1, "no")
arrow(ax, 37, 42, 28.2, 42, "", GREEN); label(ax, 32.5, 44, "no", GREEN)
arrow(ax, 50, 38, 50, 34.2, "", GREY); label(ax, 53.5, 36.1, "yes")
arrow(ax, 50, 27, 50, 21.2, "", GREY)
arrow(ax, 65, 17, 72, 17, "", PURPLE); label(ax, 68.5, 19, "yes", PURPLE)
arrow(ax, 50, 13, 50, 9.2, "", GREY); label(ax, 52.5, 11.1, "no")
ax.plot([31.6, 2.5], [5, 5], color=NAVY, linewidth=1.2, linestyle="--", zorder=1)
ax.plot([2.5, 2.5], [5, 67.5], color=NAVY, linewidth=1.2, linestyle="--", zorder=1)
arrow(ax, 2.5, 67.5, 33.6, 67.5, "", NAVY, dashed=True)
label(ax, 4, 22, "loop: the resumed\nturn may pause again\n(at most 4 steps)", NAVY, size=7.4, ha="left")
ax.text(85, 43.5, "the teacher's click later calls\nresumeHeld() → the same sendTurn", ha="center", fontsize=7.2,
        color=GREY)
save(fig, "s16_action_loop.png")

# S17. The history after a resume, and after a new message instead --------------------------------
fig, ax = canvas(10, 5.0)
history(ax, 2, 44, 47, [
    ("assistant", [("toolUse X  page_action(pacing.where)", ORANGE), ("toolUse Y  search_curriculum", TEAL)]),
    ("user", [("toolResult Y  (from pending.results)", TEAL),
              ("toolResult X  \"The browser's result", ORANGE), ("  for pacing.where: ok. …\"", ORANGE)]),
    ("assistant", [("text: \"Your class is on week 9 …\"", GREEN)]),
], "A. resumed with an action_result", GREEN)
history(ax, 51, 44, 47, [
    ("assistant", [("toolUse X  page_action(pacing.where)", ORANGE), ("toolUse Y  search_curriculum", TEAL)]),
    ("user", [("toolResult Y  (from pending.results)", TEAL), ("toolResult X  NOT_PERFORMED (error)", RED),
              ("text: the teacher's new question", NAVY)]),
    ("assistant", [("answers the new question", GREEN)]),
], "B. the teacher typed something else", RED)
box(ax, 2, 1, 96, 8, "Every toolUse gets exactly one toolResult with the same id. Resume fills X with the browser's "
    "result;\na new message fills it with NOT_PERFORMED, so the history is never left half-finished.", NAVY, size=8.0,
    bold_first=False)
save(fig, "s17_history_resume.png")

# S18. How the server routes an action_result ----------------------------------------------------
fig, ax = canvas(10, 5.8)
box(ax, 34, 49, 32, 7, "POST /v2/turn with action_result", NAVY, size=8.2, bold_first=False)
diamond(ax, 50, 39, "thread.pending\nsaved?", GREY, w=26, h=9)
box(ax, 72, 35, 26, 8, "409 nothing_to_resume\n(plain JSON, no stream)", RED, size=7.8)
diamond(ax, 50, 25, "answer = an offered button\nwith a resume recipe?", TEAL, w=36, h=10)
box(ax, 66, 9, 32, 12, "deterministic_continuation()\nrun the tool directly with\nvalues[answer], no model guess",
    TEAL, size=7.6)
box(ax, 2, 9, 30, 12, "_action_result_block()\n→ toolResult for the paused\ntoolUseId → _run_loop()\ncontinues with the model",
    NAVY, size=7.6)
arrow(ax, 50, 49, 50, 43.6, "", GREY)
arrow(ax, 63, 39, 72, 39, "", RED); label(ax, 67.5, 41, "no", RED)
arrow(ax, 50, 34.5, 50, 30.1, "", GREY); label(ax, 53, 32.3, "yes")
arrow(ax, 68, 25, 82, 21.3, "", TEAL); label(ax, 75, 25, "yes", TEAL)
arrow(ax, 32, 25, 17, 21.3, "", NAVY); label(ax, 25, 25, "no", NAVY)
ax.text(50, 3, "Example: after \"Which grade?\" the teacher clicks \"Grade 2\" → level_article runs at once, "
        "so a rewrite cannot be claimed without being done.", ha="center", fontsize=7.6, color=GREY)
save(fig, "s18_resume_routing.png")

# S19. request_cancel(): the four answers -------------------------------------------------------
fig, ax = canvas(10, 6.4)
box(ax, 32, 56, 36, 7, "POST /v2/turn/cancel {thread_id, turn_id}", NAVY, size=8.0, bold_first=False)
diamond(ax, 50, 46, "thread belongs to\nsomeone else?", RED, w=30, h=9)
box(ax, 74, 42, 24, 8, "\"not_found\" → 404", RED, size=8.0, bold_first=False)
diamond(ax, 50, 33, "running_turn_id\n== turn_id?", TEAL, w=30, h=9)
box(ax, 74, 29, 24, 8, "set cancel_turn_id\n→ \"cancelled\"", TEAL, size=7.8)
diamond(ax, 50, 20, "turn_id already in\nthe transcript?", GREY, w=30, h=9)
box(ax, 74, 16, 24, 8, "\"not_running\"\n(already ended: no-op)", GREY, size=7.8)
box(ax, 14, 1, 72, 10, "early Stop: upsert into the cancels collection by turn_id (kept 1 hour) → \"cancelled\"\n"
    "the turn checks it before its first model call", ORANGE, size=7.6, bold_first=False)
arrow(ax, 50, 56, 50, 50.6, "", GREY)
arrow(ax, 65, 46, 74, 46, "", RED); label(ax, 69.5, 48, "yes", RED)
arrow(ax, 50, 41.5, 50, 37.6, "", GREY); label(ax, 53, 39.5, "no")
arrow(ax, 65, 33, 74, 33, "", TEAL); label(ax, 69.5, 35, "yes", TEAL)
arrow(ax, 50, 28.5, 50, 24.6, "", GREY); label(ax, 53, 26.5, "no")
arrow(ax, 65, 20, 74, 20, "", GREY); label(ax, 69.5, 22, "yes")
arrow(ax, 50, 15.5, 50, 11.2, "", GREY); label(ax, 53, 13.3, "no")
save(fig, "s19_request_cancel.png")

# S20. _run_unless_stopped(): three tasks race -------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.6), dpi=200)
ax.barh(2, 3.2, left=0.2, height=0.5, color=TEAL)
ax.text(1.0, 2, "model call", va="center", fontsize=7.8, color="white")
ax.barh(2, 2.1, left=3.4, height=0.5, color="#1E7F74")
ax.text(3.6, 2, "tool", va="center", fontsize=7.8, color="white")
ax.text(5.65, 2, "✕ loop_task.cancel()", va="center", fontsize=8.2, color=RED, weight="bold")
ticks = [x / 2 for x in range(0, 12)]
ax.scatter(ticks, [1] * len(ticks), marker="|", s=160, color=PURPLE, linewidths=2)
ax.text(0.2, 1.35, "poller: cancel_requested()? every 0.5 s", fontsize=7.6, color=PURPLE)
ax.barh(0, 5.3, left=0.2, height=0.35, color="#EEF0F3", edgecolor=GREY)
ax.text(0.4, 0, "stop_wait: waiting for CancelSignal", va="center", fontsize=7.6, color=GREY)
ax.axvline(5.2, color=ORANGE, linestyle="--", linewidth=1.2)
ax.text(5.15, 2.55, "Stop recorded\nin MongoDB", ha="right", fontsize=7.6, color=ORANGE)
ax.axvline(5.5, color=RED, linestyle="--", linewidth=1.2)
ax.text(5.65, 0.75, "next poll sees it → CancelSignal.set()\n→ stop_wait wins the race → save what\nwas shown → turn.end stopped", fontsize=7.6, color=RED)
ax.set_yticks([0, 1, 2])
ax.set_yticklabels(["stop_wait", "poller", "loop_task"], fontsize=8.5, family="DejaVu Sans Mono")
ax.set_xlim(0, 9.5)
ax.set_ylim(-0.6, 3.1)
ax.set_xlabel("seconds (illustration): asyncio.wait({loop_task, stop_wait}, FIRST_COMPLETED)", fontsize=8.2)
ax.spines[["top", "right", "left"]].set_visible(False)
fig.tight_layout()
save(fig, "s20_stop_race.png")
print("sse figures done")
