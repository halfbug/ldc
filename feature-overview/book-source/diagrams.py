"""Draws every figure for the Scout developer book into ./fig as PNG."""
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


def box(ax, x, y, w, h, text, color=NAVY, size=9.5, bold_first=True, align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                linewidth=1.4, edgecolor=color, facecolor=FILL[color], zorder=3))
    lines = text.split("\n")
    if bold_first and len(lines) > 1:
        ax.text(x + w / 2, y + h - 2.2, lines[0], ha="center", va="top", fontsize=size, weight="bold", color=color, zorder=4)
        ax.text(x + w / 2 if align == "center" else x + 1.5, y + h - 5.6, "\n".join(lines[1:]),
                ha=align, va="top", fontsize=size - 1.2, color="#222", linespacing=1.35, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
                weight="bold" if bold_first else "normal", color=color, zorder=4)


def uml(ax, x, y, w, title, fields, color=NAVY, row=3.0, size=8.6):
    h = 4.2 + row * len(fields) + 1.2
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="square,pad=0", linewidth=1.4,
                                edgecolor=color, facecolor="white"))
    ax.add_patch(FancyBboxPatch((x, y - 4.2), w, 4.2, boxstyle="square,pad=0", linewidth=1.4,
                                edgecolor=color, facecolor=FILL[color]))
    ax.text(x + w / 2, y - 2.1, title, ha="center", va="center", weight="bold", color=color, fontsize=size + 0.6)
    for i, f in enumerate(fields):
        ax.text(x + 1.2, y - 4.2 - 0.8 - row * (i + 0.5), f, va="center", fontsize=size, family="DejaVu Sans Mono",
                color="#222")
    return h


def arrow(ax, x1, y1, x2, y2, text="", color=GREY, style="-|>", dashed=False, size=8.2, offset=1.4, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13, color=color, linewidth=1.3,
                                 linestyle="--" if dashed else "-", connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + offset, text, ha="center", va="bottom", fontsize=size, color=color,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)


# 1. System architecture -------------------------------------------------------
fig, ax = canvas(10, 6.8)
box(ax, 2, 46, 24, 18, "Teacher's browser\nfrontend-v3 (Nuxt 3 / Vue 3)\nai/ module: surfaces,\ncapabilities, executor,\nchat UI", NAVY)
box(ax, 37, 54, 20, 10, "Lambda Function URL\nRESPONSE_STREAM", ORANGE, size=8.8)
box(ax, 63, 52, 35, 14, "Scout Core v2 lambda\nai-assistant-v2 · streams chat turns\nauth inside (CoreAuthMiddleware)", TEAL, size=9)
box(ax, 37, 36, 20, 12, "API Gateway\n+ authorizer lambda\n(29 s, no streaming)", PURPLE, size=8.8)
box(ax, 63, 35, 29, 13, "ai_assistant lambda (v1 door)\nthreads, search, leveling,\nquestion generation", TEAL, size=8.8)
box(ax, 2, 13, 26, 21, "swo-3.0 backend\nLaravel 9 / PHP 8.3\nauth, classes, content,\nScout actions, insights,\ncredits, audit", ORANGE)
box(ax, 2, 2, 26, 7, "PostgreSQL (SWO data)", GREY)
ax.add_patch(FancyBboxPatch((63, 1), 36, 28, boxstyle="round,pad=0.3,rounding_size=1.2", linewidth=1,
                            edgecolor=GREEN, facecolor="white", linestyle="--"))
ax.text(81, 26.3, "AWS services (both lambdas)", ha="center", fontsize=8.2, color=GREEN, weight="bold")
box(ax, 64.5, 13, 15.5, 9, "Bedrock\n(the model)", GREEN, size=8.5)
box(ax, 82, 13, 15.5, 9, "MongoDB\n(threads)", GREEN, size=8.5)
box(ax, 64.5, 2.5, 15.5, 9, "Pinecone\n(search index)", GREEN, size=8.5)
box(ax, 82, 2.5, 15.5, 9, "DynamoDB\n(usage, $ caps)", GREEN, size=8.5)
arrow(ax, 26, 59, 37, 59, "chat turn", ORANGE, offset=0.5)
arrow(ax, 57, 59, 63, 59, "", ORANGE)
arrow(ax, 26, 49, 37, 42, "other\nAI calls", PURPLE, offset=-1)
arrow(ax, 57, 42, 63, 42, "", PURPLE)
arrow(ax, 95, 52, 95, 29.5, "", TEAL)
arrow(ax, 77, 35, 77, 29.5, "", TEAL)
arrow(ax, 15, 46, 15, 34.5, "normal app API + Scout actions", NAVY, style="<|-|>", offset=0)
arrow(ax, 15, 13, 15, 9, "", GREY, style="<|-|>")
arrow(ax, 46, 36, 28.5, 28, "token + credits check", PURPLE, dashed=True, offset=0.4)
arrow(ax, 63, 37, 28.5, 22, "token check, facts", TEAL, dashed=True, offset=-4.5)
save(fig, "01_architecture.png")

# 2. Frontend folder map --------------------------------------------------------
fig, ax = canvas(10, 4.2)
box(ax, 2, 32, 96, 8, "frontend-v3/ai/  — the whole AI feature lives here", NAVY, size=11, bold_first=False)
items = [
    ("index.ts", "the only\npublic door", NAVY),
    ("context/", "surfaces\ncapabilities\nexecutor\npage card\nroster", TEAL),
    ("components/", "AiAssistant-\nDialog\nresult cards\nAiAction-\nPreview", ORANGE),
    ("composables/", "useAiChat\nuseAiActions\nuseAiEnabled\nuseAiWindow", PURPLE),
    ("services/", "aiHttp\ncoreStream\nactionsClient\n*Client.ts", GREEN),
    ("intents/", "fixed flows:\nlevel article\ngenerate\nquestions", GREY),
]
for i, (t, d, c) in enumerate(items):
    x = 2 + i * 16.3
    box(ax, x, 2, 14.5, 23, t + "\n" + d, c, size=9.2)
    arrow(ax, x + 7.25, 32, x + 7.25, 25.6, "", c)
save(fig, "02_frontend_map.png")

# 3. UML: surface and capability -----------------------------------------------
fig, ax = canvas(10, 6.2)
uml(ax, 2, 60, 34, "«interface» AiSurfaceDefinition", [
    "name: string", "chrome?: boolean", "subject?(): AiSubject", "view?(): AiViewState",
    "content?(): string", "capabilities?: AiCapability[]", "suggestedAsks?(): AiSuggestedAsk[]"], NAVY)
uml(ax, 52, 60, 46, "«interface» AiCapability<A>", [
    "id: string            title: string", "args?: AiSchema<A>", "risk?: 'low' | 'confirm' | 'forbidden'",
    "available?(): boolean", "preview?(args): AiPreview", "run(args, ctx): unknown", "verify?(args): boolean",
    "describeResult?(args): string"], TEAL)
uml(ax, 2, 22, 34, "«interface» AiSubject", ["type: string", "id?: string | number", "title?: string",
                                              "grade?: string"], ORANGE)
uml(ax, 52, 22, 46, "registry.ts", ["registerSurface(def): id", "unregisterSurface(id)", "defineCapability(cap)",
                                     "visibleCapabilities()"], PURPLE)
arrow(ax, 36, 48, 52, 48, "has 0..*", GREY, style="-|>")
arrow(ax, 19, 33.4, 19, 22.2, "subject()", GREY, offset=0)
arrow(ax, 75, 22.2, 75, 31, "", GREY, dashed=True)
ax.text(76.5, 26.5, "useAiSurface() puts\nthe surface here", fontsize=8.2, color=GREY)
save(fig, "03_uml_surface.png")

# 4. Surface stacking ------------------------------------------------------------
fig, ax = canvas(10, 4.6)
box(ax, 4, 4, 52, 38, "Article page surface (depth 1)\narticle.setTab   article.setRating\nlevel text   generate questions", NAVY)
box(ax, 18, 8, 34, 18, "Open dialog surface (depth 2)\nsetRating  ← wins on same id", ORANGE)
box(ax, 64, 26, 33, 16, "Navbar surface\nchrome: true\n(sorted last when space\nruns short)", GREY)
box(ax, 64, 4, 33, 18, "What Scout sees\ndialog actions first, then\npage actions, navbar last.\nDialog closes → its actions\nvanish by themselves.", TEAL)
arrow(ax, 52, 17, 64, 13, "", TEAL)
save(fig, "04_surface_stack.png")

# 5. Sequence: one chat turn ----------------------------------------------------
fig, ax = canvas(10, 8.6)
cols = [("Teacher", 6, GREY), ("useAiChat\n(browser)", 24, NAVY), ("coreStream /\naiFetch", 42, PURPLE),
        ("rag /turn\nrouter", 60, TEAL), ("runtime +\nloop", 76, TEAL), ("Bedrock\nmodel", 93, GREEN)]
top = 77
for name, x, c in cols:
    box(ax, x - 7, top, 14, 7, name, c, size=8.4)
    ax.plot([x, x], [top, 3], color=c, linewidth=1, linestyle=(0, (4, 3)))
msgs = [
    (6, 24, "types a question", GREY), (24, 42, "build page card + names → codes", NAVY),
    (42, 60, "POST /assistant/v2/turn  (JWT, ?host=)", PURPLE), (60, 76, "scrub names, preflight, stream_turn", TEAL),
    (76, 93, "ConverseStream (prompt + tools)", TEAL), (93, 76, "text + toolUse", GREEN),
    (76, 76, "run tools (search, level, …)", TEAL), (76, 42, "SSE: text.delta, status, cards", TEAL),
    (93, 76, "", GREEN), (76, 42, "SSE: action needed → pause", ORANGE),
    (42, 24, "executor runs capability + verify()", NAVY), (24, 60, "resume turn with action_result", NAVY),
    (60, 42, "SSE: final answer, turn.end", TEAL), (24, 6, "codes → real names, show reply", NAVY)]
y = 71
for a, b, t, c in msgs:
    if not t:
        continue
    if a == b:
        ax.add_patch(FancyArrowPatch((a, y), (a, y - 3), arrowstyle="-|>", mutation_scale=11, color=c,
                                     connectionstyle="arc3,rad=-1.6"))
        ax.text(a + 4.5, y - 1.5, t, fontsize=8, color=c, va="center")
    else:
        arrow(ax, a, y, b, y, t, c, offset=0.4, size=8)
    y -= 4.8
save(fig, "05_sequence_turn.png")

# 6. Executor gates ---------------------------------------------------------------
fig, ax = canvas(10, 3.6)
gates = [("1 Allowlist", "is this id\nreally offered?"), ("2 Mode", "plan mode runs\nnothing"),
         ("3 Schema", "are the args\nvalid?"), ("4 Risk", "confirm card\nfirst?"),
         ("5 Staleness", "same page as\nwhen planned?"), ("6 run()", "call the app's\nown store"),
         ("7 verify()", "re-read state:\ndid it happen?")]
for i, (t, d) in enumerate(gates):
    x = 1 + i * 14
    c = ORANGE if i == 6 else (NAVY if i < 5 else TEAL)
    box(ax, x, 8, 12, 20, t + "\n" + d, c, size=9)
    if i:
        arrow(ax, x - 2, 18, x, 18, "", GREY)
ax.text(50, 3, "Any gate fails → Scout reports an error code (for example E_UNVERIFIED), never a fake success.",
        ha="center", fontsize=9, color=RED)
save(fig, "06_executor_gates.png")

# 7. Pseudonym flow ---------------------------------------------------------------
fig, ax = canvas(10, 3.8)
box(ax, 1, 10, 18, 20, "Page data\nAyesha Khan\nstudent_password: ***", ORANGE)
box(ax, 25, 10, 20, 20, "roster.ts\npseudonym() → code\npublicFacts() allowlist", NAVY)
box(ax, 51, 10, 20, 20, "Sent to rag / model\n\"Student K7QF2M scored\n54% on week 3\"", TEAL)
box(ax, 77, 10, 21, 20, "Shown to teacher\nrehydrate() puts the\nreal name back:\n\"Ayesha scored 54%…\"", GREEN)
arrow(ax, 19, 20, 25, 20, "", GREY); arrow(ax, 45, 20, 51, 20, "", GREY); arrow(ax, 71, 20, 77, 20, "", GREY)
ax.text(48, 3, "Names never leave the browser. The model only ever sees codes.", ha="center", fontsize=9.5, color=RED)
save(fig, "07_pseudonyms.png")

# 8. rag internals ----------------------------------------------------------------
fig, ax = canvas(10, 6.4)
box(ax, 2, 50, 26, 12, "routers/core_router.py\nPOST /turn, /grade,\n/group, /admin/turn …", TEAL)
box(ax, 36, 50, 26, 12, "core/runtime.py\npreflight() → stream_turn()\n_run_turn()", TEAL)
box(ax, 70, 50, 28, 12, "core/context/build.py\nbuild_context(): teacher,\npage card, history", PURPLE)
box(ax, 36, 28, 26, 14, "core/loop.py\n_run_loop(): model → tools\n→ model … until done\nor paused", NAVY)
box(ax, 2, 28, 26, 14, "core/prompts/\nconstitution.py (shared core)\n+ prompt_registry.json", ORANGE)
box(ax, 70, 28, 28, 14, "core/tools/*.py\nsearch_curriculum, level_article,\nwrite_artifact, page_action,\nlesson_pack, …", GREEN)
box(ax, 70, 4, 28, 16, "core/engines/*.py\nquestions, compose, level,\ngrade, slides, rubric\n(focused model calls)", GREEN)
box(ax, 2, 4, 60, 16, "Screens on every reply (loop.py imports them)\nname_claim · student_wording · standards_claim · ability_claim\nbare_codes · leak · citations · guardrail", RED)
arrow(ax, 28, 56, 36, 56, "", GREY); arrow(ax, 62, 56, 70, 56, "", GREY)
arrow(ax, 49, 50, 49, 42, "", GREY); arrow(ax, 28, 35, 36, 35, "system blocks", GREY, offset=0.6)
arrow(ax, 62, 35, 70, 35, "toolUse", GREY, style="<|-|>", offset=0.6); arrow(ax, 84, 28, 84, 20, "", GREY)
arrow(ax, 49, 28, 49, 20, "", GREY)
save(fig, "08_rag_internals.png")

# 9. UML tool types ---------------------------------------------------------------
fig, ax = canvas(10, 5.6)
uml(ax, 2, 54, 36, "«protocol» CoreTool", ["name: str", "spec: dict  (Bedrock toolSpec)",
                                          "async run(args, ctx, emit)", "    -> ToolOutcome"], TEAL)
uml(ax, 2, 28, 36, "TurnContext", ["request, thread_id, turn_id", "user_id, mode, grade", "context, refs: RefStore",
                                  "capability_ids, resolved"], NAVY)
uml(ax, 54, 54, 44, "ToolOutcome", ["content: str   (what the model reads)", "pause: Pause | None",
                                   "data: dict | None", "is_error: bool", "reply: str | None"], ORANGE)
uml(ax, 54, 22, 20, "PendingAction", ["capability", "args"], PURPLE, size=8.2)
uml(ax, 77, 22, 21, "PendingPrompt", ["question", "options"], PURPLE, size=8.2)
arrow(ax, 38, 47, 54, 47, "returns", GREY); arrow(ax, 20, 36.5, 20, 28.4, "reads", GREY, offset=0)
arrow(ax, 70, 31, 64, 22.4, "", GREY); arrow(ax, 82, 31, 87, 22.4, "", GREY)
ax.text(60, 29, "pause =", fontsize=8.4, color=GREY)
save(fig, "09_uml_tools.png")

# 10. Confirmed action state machine ---------------------------------------------
fig, ax = canvas(10, 4.4)
st = {"proposed": (4, 22, GREY), "confirmed": (30, 34, NAVY), "declined": (30, 8, RED), "done": (56, 34, GREEN),
      "drifted": (56, 8, ORANGE), "undone": (82, 34, PURPLE)}
for k, (x, y, c) in st.items():
    box(ax, x, y, 15, 8, k, c, size=9.5)
arrow(ax, 19, 28, 30, 37, "teacher approves", GREY, offset=0.4)
arrow(ax, 19, 24, 30, 12, "teacher declines", GREY, offset=-3)
arrow(ax, 45, 38, 56, 38, "execute()", GREY, offset=0.4)
arrow(ax, 45, 35, 56, 13, "preview changed", GREY, offset=-3)
arrow(ax, 71, 38, 82, 38, "undo()", GREY, offset=0.4)
ax.text(63.5, 5, "new card shown; teacher\nconfirms again", ha="center", va="top", fontsize=8.2, color=ORANGE)
ax.text(2, 2, "AiAction rows in Laravel (ScoutActionService). The preview hash must match at confirm time.", fontsize=8.6,
        color=GREY)
save(fig, "10_action_states.png")

# 11. Model cost vs accuracy chart --------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6), dpi=200)
models = ["Nova Micro", "Claude Haiku 4.5", "Claude Sonnet 4.5"]
cost = [0.00037, 0.0036, 0.047]
acc = [90.5, 93.4, 90.3]
bars = a1.bar(models, cost, color=[TEAL, NAVY, ORANGE])
a1.set_yscale("log"); a1.set_title("Cost per turn (USD, log scale)", fontsize=10)
for b, v in zip(bars, cost):
    a1.text(b.get_x() + b.get_width() / 2, v * 1.15, f"${v:.4f}", ha="center", fontsize=8.5)
bars = a2.bar(models, acc, color=[TEAL, NAVY, ORANGE]); a2.set_ylim(80, 100)
a2.set_title("Routing accuracy (22-ask benchmark, %)", fontsize=10)
for b, v in zip(bars, acc):
    a2.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v}%", ha="center", fontsize=8.5)
for a in (a1, a2):
    a.tick_params(axis="x", labelsize=8); a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); save(fig, "11_model_chart.png")

# 12. Cost per tool -----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.8), dpi=200)
tools = ["Class feedback", "Weekly plan", "Lesson pack", "Lesson plan", "Slides", "Question set", "Report cards",
         "District question", "Leveling", "Quick question"]
vals = [0.22, 0.09, 0.08, 0.08, 0.05, 0.04, 0.03, 0.02, 0.015, 0.013]
ax.barh(tools[::-1], vals[::-1], color=TEAL)
for i, v in enumerate(vals[::-1]):
    ax.text(v + 0.003, i, f"${v:.3f}", va="center", fontsize=8.5)
ax.set_title("Average AI cost per use (ONLINE-7857, test runs)", fontsize=10)
ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=8.5)
fig.tight_layout(); save(fig, "12_cost_per_tool.png")

# 13. Prompt size before/after -------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 2.6), dpi=200)
ax.barh(["Before (ONLINE-7588)"], [8.8], color=ORANGE, label="rules")
ax.barh(["Before (ONLINE-7588)"], [8.6], left=[8.8], color=NAVY, label="tool descriptions")
ax.barh(["After: shared core"], [5.2], color=TEAL, label="shared core (+ feature rules only when used)")
ax.set_xlabel("thousand tokens sent on every chat call"); ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.38), ncol=3, frameon=False)
ax.text(17.6, 1, " 17.7k", va="center", fontsize=9); ax.text(5.4, 0, " ~5.2k", va="center", fontsize=9)
ax.set_xlim(0, 21); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); save(fig, "13_prompt_size.png")

# 14. Ticket status donut -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 3.6), dpi=200)
labels = ["Done 65", "Testing 4", "Selected 3", "Backlog 3"]
ax.pie([65, 4, 3, 3], colors=[TEAL, NAVY, ORANGE, GREY], startangle=90,
       wedgeprops=dict(width=0.38, edgecolor="white"))
ax.legend(labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=10)
ax.text(0, 0, "75\ntickets", ha="center", va="center", fontsize=12, weight="bold", color=NAVY)
save(fig, "14_status_donut.png")

# 15. Which check to run --------------------------------------------------------------
fig, ax = canvas(10, 4.6)
box(ax, 2, 30, 30, 14, "Changed ai/context/ logic?\nnpx vite-node\nai/context/__verify.ts", NAVY)
box(ax, 35, 30, 30, 14, "Changed a page surface?\n__audit.ts, then the resting\ncard (__aiContextDebug)", PURPLE)
box(ax, 68, 30, 30, 14, "Changed a component?\ncurl it from the dev server\n(Vite must compile it)", ORANGE)
box(ax, 2, 6, 30, 16, "Changed rag?\nfor t in tests/check_*.py;\ndo uv run python $t; done", TEAL)
box(ax, 35, 6, 30, 16, "Changed Laravel?\nphpunit --filter <Test>\nphpcs -n <files>\n(artisan test wipes the DB!)", RED)
box(ax, 68, 6, 30, 16, "Changed the whole turn?\n__probe.ts / __chain.ts\n(rag running on :8002)", GREEN)
save(fig, "15_which_check.png")

# 16. Feature map -----------------------------------------------------------------------
fig, ax = canvas(10, 6.0)
box(ax, 36, 26, 28, 10, "Scout", NAVY, size=14)
areas = [("Page awareness\n& window", 2, 50), ("Trust &\nprivacy", 26, 50), ("Memory &\nshortcuts", 50, 50),
         ("Confirmed\nactions", 74, 50), ("Search &\ndiscovery", 2, 2), ("Leveling &\nquestions", 26, 2),
         ("Lesson plans\n& calendar", 50, 2), ("Insights &\nreports", 74, 2), ("Grading\n(hidden)", 2, 26),
         ("Admin Scout", 74, 26)]
palette = [TEAL, RED, PURPLE, ORANGE, GREEN, NAVY, TEAL, PURPLE, GREY, ORANGE]
for (t, x, y), c in zip(areas, palette):
    box(ax, x, y, 22, 9, t, c, size=9.2, bold_first=False)
    arrow(ax, 50, 31, x + 11, y + (0 if y > 30 else 9) if y != 26 else y + 4.5, "", GREY, style="-")
save(fig, "16_feature_map.png")
# 17. Two doors into rag ----------------------------------------------------------------
fig, ax = canvas(10, 4.8)
box(ax, 2, 14, 22, 20, "frontend-v3\ncoreClient.ts →\nNUXT_ENV_AI_CORE_URL\n\naiHttp.ts / aiUrl() →\nNUXT_ENV_AI_URL", NAVY, size=9)
box(ax, 31, 30, 20, 14, "Function URL\nauth NONE\nRESPONSE_STREAM\nCORS", ORANGE, size=8.6)
box(ax, 57, 30, 12, 14, "alias\nlive", ORANGE, size=8.6)
box(ax, 75, 28, 23, 18, "Scout Core v2\n/v2/turn\n/v2/turn/cancel\n/v2/admin/turn\n/v2/thread/messages", TEAL, size=8.6)
box(ax, 31, 3, 20, 14, "API Gateway\nHTTP API\n29 s limit", PURPLE, size=8.6)
box(ax, 57, 3, 12, 14, "authorizer\nlambda", PURPLE, size=8.6)
box(ax, 75, 2, 23, 18, "ai_assistant (v1)\nthread listing, pin,\nsearch, rename,\nlevel-content,\nquestion generation", TEAL, size=8.6)
arrow(ax, 24, 29, 31, 37, "", ORANGE); arrow(ax, 51, 37, 57, 37, "", ORANGE); arrow(ax, 69, 37, 75, 37, "", ORANGE)
arrow(ax, 24, 19, 31, 10, "", PURPLE); arrow(ax, 51, 10, 57, 10, "", PURPLE); arrow(ax, 69, 10, 75, 10, "", PURPLE)
ax.text(50, 46.5, "Streaming door", ha="center", fontsize=9.5, weight="bold", color=ORANGE)
ax.text(50, 19, "Normal door", ha="center", fontsize=9.5, weight="bold", color=PURPLE)
save(fig, "17_core_v2_paths.png")

# 18. UML deployment view of the streaming lambda ------------------------------------------
fig, ax = canvas(10, 5.6)
box(ax, 1, 40, 14, 12, "Browser\nPOST /v2/turn\n?host=…", NAVY, size=8.6)
box(ax, 19, 40, 15, 12, "Function URL\nRESPONSE_STREAM", ORANGE, size=8.6)
box(ax, 38, 40, 10, 12, "alias\nlive", ORANGE, size=8.6)
ax.add_patch(FancyBboxPatch((52, 2), 47, 52, boxstyle="square,pad=0", linewidth=1.5, edgecolor=TEAL,
                            facecolor="#F6FBFA", zorder=1))
ax.text(53.5, 51.5, "«node» AWS Lambda  ai-assistant-v2-<env>\n2048 MB · 210 s · 25 reserved", fontsize=8.4,
        weight="bold", color=TEAL, va="top")
ax.add_patch(FancyBboxPatch((54.5, 4), 42.5, 40, boxstyle="square,pad=0", linewidth=1.2, edgecolor=GREY,
                            facecolor="white", linestyle="--", zorder=1))
ax.text(56, 42.5, "«artifact» image: Dockerfile.stream", fontsize=8.2, color=GREY, va="top")
layers = [("Lambda Web Adapter (extension)", PURPLE), ("uvicorn  :8080   (/_ready probe)", NAVY),
          ("lambda_stream.app  (FastAPI)", TEAL), ("CoreAuthMiddleware: host · token · user · limits", RED),
          ("core_router → runtime → loop (Chapter 9)", GREEN)]
for i, (t, col) in enumerate(layers):
    y = 33 - i * 7.0
    box(ax, 57, y, 37.5, 5.6, t, col, size=8.4, bold_first=False)
    if i:
        arrow(ax, 75.75, y + 7.0, 75.75, y + 5.7, "", GREY)
arrow(ax, 15, 46, 19, 46, "", GREY); arrow(ax, 34, 46, 38, 46, "", GREY); arrow(ax, 48, 46, 57, 37.5, "", GREY)
box(ax, 1, 14, 30, 14, "ECR repository\nai-assistant-v2-lambda-<env>\nIMMUTABLE tags (git shas)", GREY, size=8.6)
arrow(ax, 31, 21, 54.5, 21, "image", GREY, dashed=True, offset=0.4)
save(fig, "18_core_v2_inside.png")

# 19. Release and rollback -----------------------------------------------------------------
fig, ax = canvas(10, 4.6)
ax.text(2, 44, "First time (two Terraform applies)", fontsize=9.5, weight="bold", color=NAVY)
steps = [("1 terraform apply", "enabled = true\nimage_tag = \"\"\n→ ECR repo only"),
         ("2 push the image", "deploy-core-v2-\nimage.sh builds\nand pushes <sha>"),
         ("3 terraform apply", "image_tag = <sha>\n→ function, alias,\nURL, alarms")]
for i, (t, d) in enumerate(steps):
    box(ax, 2 + i * 21, 24, 19, 16, t + "\n" + d, NAVY, size=8.4)
    if i:
        arrow(ax, 2 + i * 21 - 2, 32, 2 + i * 21, 32, "", GREY)
ax.text(68, 44, "Every release / rollback", fontsize=9.5, weight="bold", color=ORANGE)
for i, v in enumerate(["v5", "v6", "v7"]):
    box(ax, 66 + i * 11, 8, 9, 8, v, GREY if v != "v7" else TEAL, size=9.5, bold_first=False)
box(ax, 77, 25, 20, 8, "alias live", ORANGE, size=9.5, bold_first=False)
arrow(ax, 89, 25, 92.5, 16.3, "release-core-v2.sh\nIMAGE_TAG", TEAL, offset=0.5, size=7.6)
arrow(ax, 84, 25, 81.5, 16.3, "", ORANGE, dashed=True)
ax.text(64, 21.5, "--rollback 6\nmoves it back", fontsize=7.6, color=ORANGE)
box(ax, 66, 37, 31, 4.5, "Function URL → always serves live", ORANGE, size=8.2, bold_first=False)
arrow(ax, 87, 36.6, 87, 33.4, "", ORANGE)
save(fig, "19_core_v2_release.png")

# 20/21. Sequence: "Where is my class compared with where it should be?" -------------------
PACE_COLS = [("Teacher", 9, GREY), ("frontend-v3 chat\nuseAiChat · coreClient", 25.5, NAVY),
             ("executor +\npacing.ts", 42, PURPLE), ("rag: Scout Core v2\nrouter · runtime · loop", 58.5, TEAL),
             ("Bedrock\nmodel", 75, GREEN), ("Laravel\nbackend", 91.5, ORANGE)]


def pace_seq(name, msgs, height=9.6):
    fig, ax = canvas(10, height)
    top = height * 10 - 9
    xs = dict((label.split("\n")[0], x) for label, x, _ in PACE_COLS)
    y = top - 4
    for num, a, b, text, col in msgs:
        xa, xb = xs[a], xs[b]
        lines = text.count("\n") + 1
        tag = f"{num}. "
        if a == b:
            y -= 3.2 + 2.4 * lines
            right = xa < 80
            ax.add_patch(FancyArrowPatch((xa, y + 1.2), (xa, y - 1.2), arrowstyle="-|>", mutation_scale=10,
                                         color=col, connectionstyle=f"arc3,rad={-1.4 if right else 1.4}", zorder=3))
            ax.text(xa + 3.2 if right else xa - 3.2, y, tag + text, fontsize=7.3, color=col, va="center",
                    ha="left" if right else "right", linespacing=1.3, zorder=4,
                    bbox=dict(facecolor="white", edgecolor=col, linewidth=0.6, boxstyle="round,pad=0.35"))
            y -= 1.0 + 0.6 * lines
        else:
            y -= 2.4 + 2.3 * lines
            ax.add_patch(FancyArrowPatch((xa, y), (xb, y), arrowstyle="-|>", mutation_scale=11, color=col,
                                         linewidth=1.3, zorder=3, linestyle="--" if xb < xa else "-"))
            ax.text((xa + xb) / 2, y + 0.7, tag + text, fontsize=7.3, color=col, ha="center", va="bottom",
                    linespacing=1.3, zorder=4, bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
    bottom = y - 4
    for label, x, col in PACE_COLS:
        box(ax, x - 7.5, top, 15, 7.5, label, col, size=7.6)
        ax.plot([x, x], [top, bottom], color=col, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ax.set_ylim(bottom - 1, height * 10)
    save(fig, name)


pace_seq("20_pacing_seq_a.png", [
    (1, "Teacher", "frontend-v3 chat", "\"Where is my class compared\nwith where it should be?\"", GREY),
    (2, "frontend-v3 chat", "frontend-v3 chat", "sendMessage() → buildPageCard()\nnames → pseudonym codes", NAVY),
    (3, "frontend-v3 chat", "rag: Scout Core v2", "sendCoreTurn() → streamTurn()\nPOST <AI_CORE_URL>/v2/turn?host=…", NAVY),
    (4, "rag: Scout Core v2", "Laravel", "CoreAuthMiddleware → CreditsVerifier\nGET api/ai/user/credits (JWT)", TEAL),
    (5, "Laravel", "rag: Scout Core v2", "200 → user_id", ORANGE),
    (6, "rag: Scout Core v2", "rag: Scout Core v2", "core_router.turn() → preflight()\n→ stream_turn() → _run_turn()\nthreads.load_thread(), build_context()", TEAL),
    (7, "rag: Scout Core v2", "Bedrock", "loop._run_loop(): ConverseStream\n(constitution + page card + tools)", TEAL),
    (8, "Bedrock", "rag: Scout Core v2", "toolUse page_action\n{capability: \"pacing.where\"}", GREEN),
    (9, "rag: Scout Core v2", "rag: Scout Core v2", "PageActionTool.run() → PendingAction\nthreads.save_thread() (MongoDB)", TEAL),
    (10, "rag: Scout Core v2", "frontend-v3 chat", "SSE: pending_action\nturn.end {status: \"paused\"}", TEAL),
], height=9.2)

pace_seq("21_pacing_seq_b.png", [
    (11, "frontend-v3 chat", "executor +", "useAiActions.runRequested()\n→ dispatch() → runAction()", NAVY),
    (12, "executor +", "executor +", "gates: allowlist, schema,\nrisk 'low', effect 'read'\n(no confirm card)", PURPLE),
    (13, "executor +", "Laravel", "pacing.where run() → classesFor()\n→ fetchPacing(): GET api/ai/pacing\n?classroom_id=…&tz=…", PURPLE),
    (14, "Laravel", "Laravel", "PacingController@index → scope():\nauthorize('viewPacing')\n→ ClassPacing::for() → analyse()\n→ PacingStatement::for()", ORANGE),
    (15, "Laravel", "executor +", "JSON: expected, actual,\nbehind_by, next, statement, asks", ORANGE),
    (16, "executor +", "frontend-v3 chat", "formatPacing() → ActionOutcome", PURPLE),
    (17, "frontend-v3 chat", "rag: Scout Core v2", "actions.resultFor() → sendTurn()\nPOST /v2/turn {action_result} (auth again)", NAVY),
    (18, "rag: Scout Core v2", "Bedrock", "_run_turn(): _action_result_block()\n→ _run_loop(): ConverseStream", TEAL),
    (19, "Bedrock", "rag: Scout Core v2", "reply that quotes the statement", GREEN),
    (20, "rag: Scout Core v2", "rag: Scout Core v2", "reply screens, save_thread(),\nrecord usage", TEAL),
    (21, "rag: Scout Core v2", "frontend-v3 chat", "SSE: text.delta … turn.end {complete}", TEAL),
    (22, "frontend-v3 chat", "Teacher", "applyCoreEvent() → rehydrate()\n→ answer on screen", NAVY),
], height=11.2)

# 22-25. Section 12.4: cheaper and faster turns ------------------------------------------------
CACHED, FRESH, CHANGED = "#BFE3DC", "#F6C9BC", "#F3B0A3"


def strip(ax, x, y, parts, h=6, cap=None):
    """A request drawn as blocks left to right: (label, width, fill, text colour)."""
    for label, w, fill, tc in parts:
        ax.add_patch(FancyBboxPatch((x, y), w - 0.4, h, boxstyle="square,pad=0", linewidth=0.8,
                                    edgecolor="#5F6B7A", facecolor=fill, zorder=3))
        ax.text(x + (w - 0.4) / 2, y + h / 2, label, ha="center", va="center", fontsize=7.6, color=tc, zorder=4)
        x += w
    return x


def cache_mark(ax, x, y, h=6, text="cachePoint"):
    ax.plot([x - 0.2, x - 0.2], [y - 1.2, y + h + 1.2], color=NAVY, linewidth=2.2, zorder=5)
    ax.text(x - 0.2, y + h + 1.6, text, ha="center", fontsize=6.8, color=NAVY, weight="bold", zorder=5)


def legend(ax, x, y, items):
    for i, (label, fill) in enumerate(items):
        ax.add_patch(FancyBboxPatch((x + i * 25, y), 3, 2.4, boxstyle="square,pad=0", facecolor=fill,
                                    edgecolor="#5F6B7A", linewidth=0.8))
        ax.text(x + i * 25 + 4, y + 1.2, label, va="center", fontsize=7.8, color="#222")


# 22. How prompt caching works
fig, ax = canvas(10, 3.8)
ax.text(1, 35, "Call 1", fontsize=9, weight="bold", color=NAVY, va="center")
end = strip(ax, 9, 32, [("tools", 14, FRESH, INK if False else "#222"), ("rules (system)", 22, FRESH, "#222"),
                        ("conversation", 26, FRESH, "#222"), ("new msg", 10, FRESH, "#222")])
cache_mark(ax, 45, 32)
ax.text(1, 19, "Call 2", fontsize=9, weight="bold", color=NAVY, va="center")
strip(ax, 9, 16, [("tools", 14, CACHED, "#222"), ("rules (system)", 22, CACHED, "#222"),
                  ("conversation", 26, FRESH, "#222"), ("tool result", 12, FRESH, "#222"), ("…", 6, FRESH, "#222")])
cache_mark(ax, 45, 16)
ax.text(27, 10.5, "same bytes as call 1 → read from cache (cheap, fast)", ha="center", fontsize=7.8, color=TEAL)
legend(ax, 9, 3, [("billed as fresh input", FRESH), ("read from the cache", CACHED)])
save(fig, "22_cache_concept.png")

# 23. ONLINE-7526: cache the conversation too
fig, ax = canvas(10, 6.4)
ax.text(1, 61, "BEFORE — cache stopped after tools + rules", fontsize=9, weight="bold", color=ORANGE)
y = 51
for i, extra in enumerate([0, 12, 24]):
    ax.text(1, y - i * 8 + 3, f"step {i + 1}", fontsize=8, color=GREY, va="center")
    parts = [("tools + rules", 20, CACHED, "#222"), ("history", 18 + extra, FRESH, "#222")]
    strip(ax, 10, y - i * 8, parts)
    cache_mark(ax, 30, y - i * 8, text="")
ax.text(1, 27, "AFTER — a second cachePoint at the end of the history (with_history_cache_point)", fontsize=9,
        weight="bold", color=TEAL)
y = 15
for i, extra in enumerate([0, 12, 24]):
    ax.text(1, y - i * 6.4 + 2.5, f"step {i + 1}", fontsize=8, color=GREY, va="center")
    cached = 18 + extra - (12 if i else 0)
    parts = [("tools + rules", 20, CACHED, "#222"), ("history", 18 + extra - (12 if i else 0), CACHED if i else FRESH, "#222")]
    if i:
        parts.append(("new", 12, FRESH, "#222"))
    strip(ax, 10, y - i * 6.4, parts, h=5)
    cache_mark(ax, 30, y - i * 6.4, h=5, text="")
    cache_mark(ax, 10 + 20 + parts[1][1] + (12 if i else 0), y - i * 6.4, h=5, text="")
legend(ax, 70, 60, [("fresh", FRESH)])
legend(ax, 84, 60, [("cached", CACHED)])
ax.text(99, 30, "illustration,\nnot to scale", ha="right", fontsize=7.4, color=GREY, style="italic")
save(fig, "23_history_cache.png")

# 24. ONLINE-7528: stable tools across page switches
fig, ax = canvas(10, 4.6)
ax.text(1, 44, "BEFORE — the page's action list lived inside the page_action tool", fontsize=9, weight="bold",
        color=ORANGE)
ax.text(1, 37.5, "Article page", fontsize=8, color=GREY, va="center")
strip(ax, 18, 35, [("tools + page_action enum: A", 30, CACHED, "#222"), ("rules", 20, CACHED, "#222"),
                   ("page card A", 14, FRESH, "#222")])
ax.text(1, 29.5, "Gradebook", fontsize=8, color=GREY, va="center")
strip(ax, 18, 27, [("tools + page_action enum: B", 30, CHANGED, "#222"), ("rules", 20, CHANGED, "#222"),
                   ("page card B", 14, FRESH, "#222")])
ax.text(84, 31.5, "first block changed →\nthe whole cached prefix\n(~9,000 tokens) is\nwritten again", fontsize=7.6,
        color=RED, va="center")
ax.text(1, 20, "AFTER — page_action's schema never changes; the action list moved into the page context",
        fontsize=9, weight="bold", color=TEAL)
ax.text(1, 13.5, "Article page", fontsize=8, color=GREY, va="center")
strip(ax, 18, 11, [("tools (same on every page)", 30, CACHED, "#222"), ("rules", 20, CACHED, "#222"),
                   ("page card A + actions", 18, FRESH, "#222")])
ax.text(1, 5.5, "Gradebook", fontsize=8, color=GREY, va="center")
strip(ax, 18, 3, [("tools (same on every page)", 30, CACHED, "#222"), ("rules", 20, CACHED, "#222"),
                  ("page card B + actions", 18, FRESH, "#222")])
ax.text(88, 9, "only the small\npage part is new", fontsize=7.6, color=TEAL, va="center")
save(fig, "24_stable_tools.png")

# 25. ONLINE-7588: shared core, rules travel with the feature
fig, ax = canvas(10, 4.4)
ax.text(1, 42, "BEFORE — every call carried every rule and every tool's long description", fontsize=9,
        weight="bold", color=ORANGE)
strip(ax, 1, 33, [("8.6k: descriptions of 18 tools", 43, FRESH, "#222"), ("8.8k: every rule, for every feature", 44, FRESH, "#222"),
                  ("page…", 10, GREY_FILL if False else "#EEF0F3", "#222")], h=6)
ax.text(1, 26, "AFTER — a small shared core; each feature's rules arrive only when that feature is used",
        fontsize=9, weight="bold", color=TEAL)
end = strip(ax, 1, 17, [("short tools:\n\"when to use\"", 18, CACHED, "#222"), ("shared core\n~5.2k, cached 1 h", 22, CACHED, "#222"),
                        ("About you\n(per teacher)", 15, CACHED, "#222"), ("page module\n+ page card", 16, "#EEF0F3", "#222"),
                        ("history +\nmessage", 15, "#EEF0F3", "#222")], h=7)
box(ax, 66, 1, 32, 8, "tool result = facts only\n(rules never ride in results)", PURPLE, size=7.6)
box(ax, 1, 1, 60, 8, "Rule registry (prompt_registry.json): every rule sentence has exactly one home;\n"
    "a test caps the size of core + tools, so the prompt cannot quietly grow again", NAVY, size=7.6, bold_first=False)
save(fig, "25_prompt_layers.png")
print("figures:", len(os.listdir(OUT)))
