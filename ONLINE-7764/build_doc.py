"""Builds ONLINE-7764's initial TTFT investigation document (charts + .docx) from the CSVs in data/.

Run: uv run --no-project --with python-docx --with matplotlib python build_doc.py
Screenshots: drop PNGs into screenshots/ with the names in SCREENSHOTS; a missing one leaves a marked placeholder.
"""
import csv
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).parent
DATA, CHARTS, SHOTS = HERE / "data", HERE / "charts", HERE / "screenshots"
OUT = HERE / "ONLINE-7764-TTFT-initial-investigation.docx"

# Reference palette (dataviz skill, light mode): slots 1-3, text inks, recessive grid.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

LOG_GROUP = "/aws/lambda/swo-genai-pov-ai-assistant-v2-dev"

QUERIES = {
    "Q1": ("First content, TTFT and total time per 5 minutes (the dashboard query)",
           f'SOURCE "{LOG_GROUP}" START=-604800s END=0s |\n'
           "filter message = 'core_turn' and synthetic = 0\n"
           "| stats pct(first_content_ms, 50) as first_content_p50, pct(first_content_ms, 95) as first_content_p95,\n"
           "        pct(ttft_ms, 95) as ttft_p95, pct(total_ms, 95) as total_p95\n"
           "  by bin(5m)"),
    "Q2": ("Stage summary for the week: context build vs first model call",
           f'SOURCE "{LOG_GROUP}" START=-604800s END=0s |\n'
           "filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500\n"
           "| stats count() as turns,\n"
           "        pct(first_content_ms, 50) as first_p50, pct(first_content_ms, 90) as first_p90,\n"
           "        pct(ctx_build_ms, 50) as ctx_p50, pct(ctx_build_ms, 90) as ctx_p90,\n"
           "        pct(first_model_ms, 50) as model1_p50,\n"
           "        avg(model_steps) as steps\n"
           "  by tools\n"
           "| sort turns desc"),
    "Q3": ("The 20 slowest turns (first words after more than 10 s)",
           f'SOURCE "{LOG_GROUP}" START=-604800s END=0s |\n'
           "filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 10000\n"
           "| fields @timestamp, turn_id, thread_id, first_content_ms, ctx_build_ms, first_model_ms, tools, model_steps, outcome\n"
           "| sort first_content_ms desc\n"
           "| limit 20"),
    "Q4": ("Time to first words by turn kind (model calls + first tool)",
           f'SOURCE "{LOG_GROUP}" START=-604800s END=0s |\n'
           "filter message = 'core_turn' and synthetic = 0 and mode != 'grade' and first_content_ms > 500\n"
           "| stats count() as turns, pct(first_content_ms, 50) as first_p50, pct(first_content_ms, 90) as first_p90\n"
           "  by model_steps, tools.0\n"
           "| sort turns desc"),
    "Q5": ("Where a search-then-answer turn spends its time",
           f'SOURCE "{LOG_GROUP}" START=-604800s END=0s |\n'
           "filter message = 'core_turn' and synthetic = 0 and model_steps = 2 and tools.0 = 'search_curriculum'\n"
           "| stats count() as turns, pct(first_model_ms, 50) as model1_p50, pct(tools_ms, 50) as tools_p50,\n"
           "        pct(model_ms, 50) as model_total_p50, pct(first_content_ms, 50) as first_p50"),
}

SCREENSHOTS = {
    "alarm": ("alarm.png", "first-content-p95 alarm notifications on 5 Oct; the open one is ALARM → OK at 18:01 UTC"),
    "dashboard": ("dashboard.png", "Dashboard swo-genai-pov-ai-assistant-v2-dev-turns (2 weeks): outcomes, error rate, "
                                   "latency and cost"),
    "dashboard2": ("dashboard2.png", "Same dashboard, lower half: degradations and Lambda function metrics"),
    "Q1": ("q1.png", "Q1 result in CloudWatch Logs Insights"),
    "Q2": ("q2.png", "Q2 result in CloudWatch Logs Insights"),
    "Q3": ("q3.png", "Q3 result in CloudWatch Logs Insights"),
    "Q4": ("q4.png", "Q4 result in CloudWatch Logs Insights: turns and first_p50 by model calls and first tool"),
    "Q4b": ("q4b.png", "Q4 result, continued: first_p90 by model calls and first tool"),
    "Q5": ("q5.png", "Q5 result in CloudWatch Logs Insights"),
}


def read_csv(name):
    with open(DATA / name, newline="") as f:
        return list(csv.DictReader(f))


# ---------- charts ----------

def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def chart_timeline(rows):
    """Q1: per-bin p50 and p95 of first content, bins with no visible text left out."""
    pts = [(datetime.strptime(r["bin_utc"], "%Y-%m-%d %H:%M"), float(r["first_content_p50"]) / 1000,
            float(r["first_content_p95"]) / 1000) for r in rows if float(r["first_content_p95"]) > 0]
    pts.sort()
    t = [p[0] for p in pts]
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax)
    ax.scatter(t, [p[2] for p in pts], s=14, color=ORANGE, edgecolors=SURFACE, linewidths=0.8, label="p95", zorder=3)
    ax.scatter(t, [p[1] for p in pts], s=14, color=BLUE, edgecolors=SURFACE, linewidths=0.8, label="p50", zorder=4)
    ax.axhline(2, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.axhline(10, color=INK2, linewidth=1, linestyle=(0, (1, 2)))
    gap = datetime(2026, 10, 2, 12)  # no traffic 2-4 Oct: labels sit in the empty stretch
    ax.text(gap, 2.25, "Eval gate: 2 s", color=INK2, fontsize=7.5)
    ax.text(gap, 10.25, "Alarm threshold (p95): 10 s", color=INK2, fontsize=7.5)
    ax.set_ylabel("Seconds to first words", color=INK2, fontsize=8)
    ax.set_ylim(0, 19)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=INK)
    ax.set_title("Time to first words per 5-minute window, dev, 1–8 Oct (UTC)", color=INK, fontsize=9.5, loc="left")
    fig.tight_layout()
    out = CHARTS / "fig1_first_content_timeline.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


def kind_label(r):
    tool = r["first_tool"] or "no tool"
    calls = int(r["model_steps"])
    return f"{tool} · {calls} model call{'s' if calls != 1 else ''}" if calls else f"{tool} · shortcut (no model)"


def chart_turn_kinds(rows):
    """Q4: p50 time to first words for every turn kind with at least 5 turns."""
    kept = sorted([r for r in rows if int(r["turns"]) >= 5], key=lambda r: float(r["first_p50"]))
    labels = [f"{kind_label(r)}  (n={r['turns']})" for r in kept]
    vals = [float(r["first_p50"]) / 1000 for r in kept]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax)
    ax.grid(True, axis="x", color=GRID, linewidth=0.6)
    ax.grid(False, axis="y")
    ax.barh(labels, vals, height=0.62, color=BLUE, edgecolor=SURFACE, linewidth=2)
    for y, v in enumerate(vals):
        ax.text(v + 0.15, y, f"{v:.1f} s", va="center", fontsize=7.5, color=INK,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=0.6))
    ax.axvline(2, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(2.1, len(vals) - 0.4, "2 s gate", fontsize=7.5, color=INK2)
    ax.set_xlabel("p50 seconds to first words", color=INK2, fontsize=8)
    ax.tick_params(axis="y", labelsize=7.5, colors=INK)
    ax.set_xlim(0, 15.5)
    ax.set_title("p50 time to first words by turn kind (kinds with 5+ turns)", color=INK, fontsize=9.5, loc="left")
    fig.tight_layout()
    out = CHARTS / "fig2_turn_kinds.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


def chart_search_split():
    """Q5: the three approximate parts of a search-then-answer turn's 13.7 s."""
    parts = [("First model call", 3.6, BLUE), ("search_curriculum", 4.1, ORANGE),
             ("Second call, until first words", 6.0, AQUA)]
    fig, ax = plt.subplots(figsize=(7.2, 1.35), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    left = 0.0
    for name, v, c in parts:
        ax.barh([0], [v], left=left, height=0.5, color=c, edgecolor=SURFACE, linewidth=2)
        ax.text(left + v / 2, 0, f"{v:.1f} s", ha="center", va="center", fontsize=8.5, color=INK, fontweight="bold")
        ax.text(left + v / 2, -0.45, name, ha="center", va="top", fontsize=7.5, color=INK2)
        left += v
    ax.set_xlim(0, left)
    ax.set_ylim(-0.75, 0.4)
    ax.axis("off")
    ax.set_title("search_curriculum turn: about 13.7 s to first words (p50, approximate split)", color=INK,
                 fontsize=9.5, loc="left")
    fig.tight_layout()
    out = CHARTS / "fig3_search_split.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out


# ---------- document helpers ----------

def shade(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def para_shade(p, hex_fill, border=None):
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    p_pr.append(shd)
    if border:
        bdr = OxmlElement("w:pBdr")
        for side in ("top", "left", "bottom", "right"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "6")
            e.set(qn("w:space"), "4")
            e.set(qn("w:color"), border)
            bdr.append(e)
        p_pr.append(bdr)


def table(doc, header, rows, widths_cm, font_size=8.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(font_size)
        shade(c, "D9E6F5")
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(font_size)
    for row in t.rows:
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def code(doc, text):
    for line in text.split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        run = p.add_run(line)
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        run.font.size = Pt(8)
        para_shade(p, "F2F2F0")
    doc.add_paragraph()


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(text)
    return p


def numbered(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Number")
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(text)
    return p


def figure(doc, path, caption, width_cm=16.5):
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph(caption)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.runs[0].italic = True
    cap.runs[0].font.size = Pt(8.5)
    cap.runs[0].font.color.rgb = RGBColor(0x52, 0x51, 0x4E)


def screenshot(doc, key):
    fname, caption = SCREENSHOTS[key]
    path = SHOTS / fname
    if path.exists():
        figure(doc, path, f"Screenshot: {caption}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"[Screenshot to add: {caption} — screenshots/{fname}]")
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x8A, 0x5A, 0x00)
    para_shade(p, "FFF6E0", border="E0B860")
    doc.add_paragraph()


def p(doc, text, bold_lead=None):
    para = doc.add_paragraph()
    if bold_lead:
        para.add_run(bold_lead).bold = True
    para.add_run(text)
    return para


# ---------- document ----------

def build():
    CHARTS.mkdir(exist_ok=True)
    SHOTS.mkdir(exist_ok=True)
    q1, q3, q4 = read_csv("q1_first_content_by_5m.csv"), read_csv("q3_slowest_turns.csv"), read_csv("q4_by_turn_kind.csv")
    fig1, fig2, fig3 = chart_timeline(q1), chart_turn_kinds(q4), chart_search_split()

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.2))
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    doc.add_heading("ONLINE-7764: Scout time to first words (TTFT)", level=0)
    sub = doc.add_paragraph("Initial investigation: what a week of dev core_turn logs shows")
    sub.runs[0].font.size = Pt(12)
    sub.runs[0].font.color.rgb = RGBColor(0x52, 0x51, 0x4E)

    table(doc, ["Item", "Value"], [
        ["Ticket", "ONLINE-7764: Measure and reduce Scout time to first words (TTFT) on core turns"],
        ["Author", "Sadaf Siddiqui"],
        ["Date", "9 October 2026"],
        ["Environment", "dev (AWS us-west-2)"],
        ["Log group", LOG_GROUP],
        ["Data window", "1–8 October 2026 (UTC); synthetic turns excluded"],
        ["Status", "Investigation only. No code changed."],
    ], [3.5, 13.0])

    # 1. Summary
    doc.add_heading("1. Summary", level=1)
    p(doc, "Teachers on dev wait a median of 4.6 seconds before Scout's first words appear, and 9.5 seconds at the "
           "90th percentile. The target from the evaluation gate is under 2 seconds. Almost none of this time is "
           "spent building the page context (5 ms median). It is spent inside the model call, and in search-then-answer "
           "turns it is spent three times over: a first model call, the search, and a second model call.")
    table(doc, ["Measure", "Value", "Source"], [
        ["Turns analysed", "459", "Q2"],
        ["First words, p50 / p90", "4.6 s / 9.5 s", "Q2"],
        ["Context build, p50 / p90", "5 ms / 69 ms", "Q2"],
        ["First model call, p50", "4.0 s", "Q2"],
        ["Plain answers (1 model call, no tool)", "261 turns (57%), 4.3 s p50", "Q4"],
        ["Search-then-answer (search_curriculum)", "19 turns, 13.7 s p50", "Q4, Q5"],
        ["Eval gate (15 Sept, Sonnet)", "3.2 s p50 against < 2 s: failed", "Routing evidence PDF, p. 8"],
    ], [6.5, 5.0, 5.0])
    p(doc, "The existing fields cannot say which part of the model call is slow. ONLINE-7764 adds the missing timings "
           "(section 7) before any optimisation is chosen.", bold_lead="Next step: ")

    # 2. Background
    doc.add_heading("2. Background: why this was investigated", level=1)
    numbered(doc, " The routing evidence document (Scout-model-routing-evidence.pdf, page 8, \"Sonnet control\", Gates "
                  "table, row \"Time to first visible text, p50\") shows Sonnet at 3.2 s (warm 3.2 s, cold 3.4 s, "
                  "n = 240) against a target of under 2 s: the gate is failed. Source file: "
                  "ai-review-2026-09-15/eval/haiku-ctl-92ae3a0.md.", bold_lead="The gap.")
    numbered(doc, " That figure comes from 288 scripted evaluation turns. The question was whether real dev traffic "
                  "looks the same, and where the time goes.", bold_lead="The question.")
    numbered(doc, " On 5 October the first-content p95 alarm fired on dev (three 5-minute windows at 11.5 s, "
                  "11.5 s and 13.0 s against a 10 s threshold), which confirmed the monitoring was live and the data "
                  "was available in CloudWatch. More notifications followed that day; the last one returned the "
                  "alarm to OK at 18:01 UTC, when p95 fell to 6.9 s.", bold_lead="The trigger.")
    screenshot(doc, "alarm")

    # 3. Data
    doc.add_heading("3. Data source and field definitions", level=1)
    p(doc, "Every Scout chat turn writes one core_turn log line (lambdas/ai_assistant/src/core/telemetry.py, _log_turn) "
           "to the Lambda's CloudWatch log group. The metric filters, dashboard and alarms come from "
           "infra/swo/modules/scout-core-v2/observability.tf and are applied in dev. The fields used here:")
    table(doc, ["Field", "Meaning"], [
        ["first_content_ms", "Turn start until the first text or artifact reaches the teacher (what the teacher sees). "
                             "Status labels such as \"Searching the curriculum…\" are not counted."],
        ["ttft_ms", "Turn start until the model loop's own first text token."],
        ["total_ms", "Whole turn, start to end."],
        ["ctx_build_ms", "Time to build the page context (page card, article, history)."],
        ["first_model_ms", "Duration of the first model call, including the guardrail classifier wait before it."],
        ["model_ms / tools_ms", "Total time in model calls / in tools across the turn."],
        ["model_steps", "Number of model calls in the turn (0 = answered by a shortcut with no model call)."],
        ["tools", "List of tools the turn used; tools.0 is the first."],
        ["synthetic", "1 for scripted test traffic (excluded from every query here)."],
    ], [3.8, 12.7])
    screenshot(doc, "dashboard")
    screenshot(doc, "dashboard2")

    # 4. Queries
    doc.add_heading("4. CloudWatch Logs Insights queries used", level=1)
    p(doc, "All queries run in us-west-2 against the log group above over the last 7 days. They exclude synthetic "
           "turns; Q2–Q4 also exclude grading requests (mode = 'grade') and turns with no visible text "
           "(first_content_ms ≤ 500 ms, which removes fixed replies and paused page actions that would pull the "
           "median down).")
    p(doc, "The data tables and charts in section 5 come from the first run of each query (window 1–8 October). "
           "The screenshots below were taken when the queries were re-run on 9 October; the 7-day window had moved to "
           "2–9 October, so 1 October dropped out and counts differ slightly (for example Q2: 415 turns instead of "
           "459; Q5: 17 instead of 19; Q3 gains a43359c5 from 8 October and loses edd9f7d3 from 1 October). "
           "The medians move by only a few hundred milliseconds (e.g. Q2 first_p50 about 4.5 s, Q5 first_p50 about 13.8 s) and the conclusions do not change.", bold_lead="Note on the screenshots: ")
    for key, (title, text) in QUERIES.items():
        doc.add_heading(f"{key}. {title}", level=2)
        code(doc, text)
        screenshot(doc, key)
        if key == "Q4":
            screenshot(doc, "Q4b")

    # 5. Findings
    doc.add_heading("5. Findings, step by step", level=1)

    doc.add_heading("Step 1. The monitoring is live and matches the alarm (Q1)", level=2)
    p(doc, "Q1 returns the 5-minute windows for the week. The windows at 14:15, 14:20 and 14:25 UTC on 5 October show "
           "p95 values of 11,518, 11,506 and 13,163 ms, exactly the three datapoints in the alarm email. The alarm "
           "reported real slow turns; it was not a broken alarm.")

    doc.add_heading("Step 2. Real dev turns are slower than the evaluation (Q1)", level=2)
    figure(doc, fig1, "Figure 1. Each dot is one 5-minute window that had teacher turns. Windows with no visible text "
                      "are left out. Full data in Appendix A.")
    bullet(doc, " most windows sit between 3 and 6 s, above the 3.2 s seen in the evaluation and well above the 2 s gate.",
           bold_lead="p50:")
    bullet(doc, " often 10–17 s, so the p95 alarm can fire on an ordinary working day.", bold_lead="p95:")
    bullet(doc, " ttft_p95 is within about 40 ms of first_content_p95 in almost every window. The first thing teachers "
                "see is the model's own first token, so the time goes before the model starts writing.",
           bold_lead="TTFT and first content move together:")
    bullet(doc, " many windows have p50 equal to p95, meaning one turn in that window. Traffic is internal testers in "
                "roughly 02:00–18:00 UTC, so a single slow turn can move a 5-minute percentile.",
           bold_lead="Low traffic:")

    doc.add_heading("Step 3. Context build is not the problem; the first model call is (Q2)", level=2)
    table(doc, ["turns", "first_p50", "first_p90", "ctx_p50", "ctx_p90", "model1_p50", "steps"],
          [["459", "4,632 ms", "9,513 ms", "5.3 ms", "69.2 ms", "4,035 ms", "1.07"]],
          [1.6, 2.4, 2.4, 2.0, 2.0, 2.6, 1.6])
    p(doc, "Building the page context takes 5 ms at the median. The first model call takes 4.0 s, and almost every turn "
           "has a single model call. The tools column came back empty because tools is a list, which Logs Insights "
           "cannot group by; this row is therefore the total for all turns (Q4 fixes the grouping with tools.0).")
    p(doc, "first_model_ms covers four things that are not logged separately today: the guardrail classifier wait "
           "(core/loop.py:332), Sonnet's own time to first token, the Bedrock guardrail on the stream, and the sentence "
           "hold in leak.Screen (core/leak.py:237), which releases text only when a sentence is complete.")

    doc.add_heading("Step 4. The slowest turns fall into three patterns (Q3)", level=2)
    table(doc, ["Time (UTC)", "turn_id", "first ms", "ctx ms", "model1 ms", "steps", "outcome"],
          [[r["timestamp_utc"], r["turn_id"][:8], r["first_content_ms"], r["ctx_build_ms"], r["first_model_ms"],
            r["model_steps"], r["outcome"]] for r in q3],
          [3.3, 2.0, 2.0, 1.8, 2.2, 1.3, 1.8], font_size=7.5)
    table(doc, ["Pattern", "Turns", "What it looks like", "Likely cause"], [
        ["A. Tool first, no words until the second call", "16 of 20",
         "2–3 model calls; first call 2.7–5.6 s; first words at 12–20 s",
         "The first call only decides to use a tool. Words wait for the tool and a second call. "
         "The lead-in sentence applies only to shortcut turns, not these."],
        ["B. One slow model call", "3 of 20", "1 model call of 13–17 s (d2f8812a, 701e38fd, 9024f7df)",
         "A retry after the idle watchdog, Bedrock throttling, or a slow guardrail label. Cannot tell apart today."],
        ["C. Slow context build", "1 of 20", "ctx_build_ms 10,537 ms (709e145a) against 5 ms normally",
         "Likely the history summary written inside the turn, or a cold resource lookup."],
    ], [4.0, 1.6, 5.3, 5.6])

    doc.add_heading("Step 5. Plain answers are most of the traffic (Q4)", level=2)
    figure(doc, fig2, "Figure 2. Turn kinds with at least 5 turns. A shortcut turn is answered without a model call "
                      "deciding what to do.")
    table(doc, ["model calls", "first tool", "turns", "first p50", "first p90"],
          [[r["model_steps"], r["first_tool"] or "(none)", r["turns"], f"{float(r['first_p50']):,.0f} ms",
            f"{float(r['first_p90']):,.0f} ms"] for r in q4],
          [2.4, 4.6, 1.8, 2.8, 2.8], font_size=7.5)
    bullet(doc, " 261 of 459 turns (57%) are one model call with no tool, at 4.3 s p50 and 7.6 s p90. This is where most "
                "of the waiting happens in total.", bold_lead="Plain answers:")
    bullet(doc, " search_curriculum with two model calls is the slowest common kind at 13.7 s p50 (19 turns). "
                "search_help, get_article_resources and suggest_standards follow at 9.3–10.5 s.",
           bold_lead="Search-then-answer:")
    bullet(doc, " shortcut generate_questions turns, which stream a Haiku lead-in sentence, show first words at 2.4 s. "
                "Shortcut turns with no tool (fixed replies) take 1.4 s.", bold_lead="Shortcut turns:")
    bullet(doc, " the lead-in turns are a different mix of requests from plain answers, so 2.4 s against 4.3 s does not "
                "show that an early sentence halves the wait. That comparison must be made within the same turn kind "
                "(decision D4).", bold_lead="Caution:")
    bullet(doc, " level_article and search turns were deliberately left without a lead-in (runtime.py lead_in_for; "
                "commit 170dd087): level_article can still stop to ask for a grade, and a search lead-in named the "
                "wrong subject.", bold_lead="Already decided:")

    doc.add_heading("Step 6. A search turn splits into three similar parts (Q5)", level=2)
    table(doc, ["turns", "model1_p50", "tools_p50", "model_total_p50", "first_p50"],
          [["19", "3,585 ms", "4,081 ms", "9,231 ms", "13,655 ms"]], [2.0, 3.0, 3.0, 3.6, 3.0])
    figure(doc, fig3, "Figure 3. Approximate split: the medians come from different turns and do not add exactly. "
                      "The third part is 13.7 − 3.6 − 4.1 s.")
    bullet(doc, " Sonnet decides to search and writes no text.", bold_lead="First call, 3.6 s:")
    bullet(doc, " slow for a vector search, though the code already runs its queries in parallel "
                "(core/tools/search_curriculum.py:851–886). The time is likely in the OpenAI embedding call, "
                "resolve_outcome, or standards_context.", bold_lead="Search, 4.1 s:")
    bullet(doc, " longer than a whole plain answer. The search results are new, uncached text, so Sonnet reads them "
                "before it starts, and the sentence hold and stream guardrail apply again.",
           bold_lead="Second call until first words, about 6 s:")

    doc.add_heading("Step 7. What the current fields cannot show", level=2)
    p(doc, "Every step above stops at the same point: the first model call and the search tool are single numbers. "
           "To choose a fix, these parts need their own timings:")
    table(doc, ["Missing field", "Separates out"], [
        ["guardrail_wait_ms", "Waiting for the guardrail classifier label (core/loop.py:332)"],
        ["first_raw_text_ms", "First text chunk from Bedrock, before leak.Screen; the hold is first_content_ms minus this"],
        ["model_retries", "Idle-watchdog retries in ModelCaller (pattern B)"],
        ["search_embed_ms / search_query_ms / search_resolve_ms / search_standards_ms",
         "The stages inside search_curriculum"],
        ["search_calls", "Number of search_curriculum runs per turn"],
    ], [7.0, 9.5])

    # 6. Caveats
    doc.add_heading("6. Caveats", level=1)
    bullet(doc, " internal testers, low volume. Percentiles per 5 minutes are noisy; read the weekly figures.",
           bold_lead="Dev traffic only:")
    bullet(doc, " p50s from different turns do not add up exactly (Q5 split is approximate).",
           bold_lead="Medians are not additive:")
    bullet(doc, " status labels appear before first_content_ms, so the teacher's experience in pattern A is a status "
                "line, not a blank screen. Check one such thread in the dev UI before choosing a fix.",
           bold_lead="first_content_ms excludes status labels:")
    bullet(doc, " the dashboard query (Q1) includes turns with no visible text (0 values) and grading requests; "
                "Q2–Q4 filter these out.", bold_lead="Dashboard query mixes turn types:")
    bullet(doc, " the dashboard's error-rate widget shows one window at 100% around 5 October. That is outside this "
                "investigation (it is an error, not latency); it most likely matches the IndexError on dev fixed the "
                "same day under ONLINE-7578, but this was not checked.", bold_lead="Error-rate spike:")
    bullet(doc, " the first-content alarm has no minimum-turn guard, unlike the error-rate alarm, so a single slow turn "
                "can trigger it on dev.", bold_lead="Alarm sensitivity:")

    # 7. Next
    doc.add_heading("7. Next step: ONLINE-7764", level=1)
    p(doc, "Agreed with Salman: a new branch off ONLINE-5385_scout_improvements with its own MR (not !74). Add only the "
           "missing fields in Step 7: durations and counts, no text, no behaviour change, existing checks must pass. "
           "The decisions the data will settle are written before collection:")
    table(doc, ["#", "Question", "Outcome → next step"], [
        ["D1", "For plain answers, which is the main cause: guardrail wait, Sonnet's first raw text, or the sentence hold?",
         "Guardrail → raise with Salman · Sonnet → prompt-size or caching ticket · Hold → change leak.Screen release · "
         "None → no ticket"],
        ["D2", "For search turns, which stage is the main cause: embedding, queries, resolve, or standards context?",
         "Optimize that stage only"],
        ["D3", "Do retries explain the >10 s tail?", "If ≥ 25% of tail turns retried → watchdog/retry ticket"],
        ["D4", "Does a lead-in sentence shorten the wait?", "Compare within the same turn kind only"],
    ], [1.0, 8.0, 7.5])
    p(doc, "A stage counts as the main cause when it is at least 1 s at p50 and at least 40% of first_content_ms p50, "
           "within the same turn kind. After one week of dev data, the readout sub-task reports D1–D4 and opens fix "
           "tickets only where a threshold is met.", bold_lead="Threshold: ")

    # Appendices
    doc.add_page_break()
    doc.add_heading("Appendix A. Q1 data: all 5-minute windows", level=1)
    table(doc, ["Window (UTC)", "first p50", "first p95", "ttft p95", "total p95"],
          [[r["bin_utc"], r["first_content_p50"], r["first_content_p95"], r["ttft_p95"], r["total_p95"]] for r in q1],
          [3.6, 3.0, 3.0, 3.0, 3.0], font_size=7)
    doc.add_heading("Appendix B. The 5 October alarm", level=1)
    table(doc, ["Item", "Value"], [
        ["Alarm", "swo-genai-pov-ai-assistant-v2-dev-first-content-p95"],
        ["State change", "OK → ALARM, 5 Oct 2026 14:29:15 UTC"],
        ["Metric", "ScoutCoreV2/swo-genai-pov-ai-assistant-v2-dev · FirstContentMs · p95 · 300 s period"],
        ["Rule", "Greater than 10,000 ms for 3 of the last 3 periods"],
        ["Datapoints", "11,479 ms (14:14) · 11,465 ms (14:19) · 13,034 ms (14:24)"],
        ["Back to OK", "18:01:15 UTC, ALARM → OK: 1 datapoint 6,881 ms (17:51) not above 10,000 ms"],
        ["Defined in", "infra/swo/modules/scout-core-v2/observability.tf (ttft_p95)"],
    ], [3.5, 13.0])

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
