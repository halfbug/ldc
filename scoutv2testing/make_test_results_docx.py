"""Builds a ticket's QA test-results report (.docx) for Jira.

The styles, colours and helpers (shade, table, image) live here, shared by every ticket. The ticket's own
content (title, Summary, results tables, Findings, Screenshots, Notes) is <TICKET>/report_content.py, which runs
with these names in scope and writes into `doc`; images are read from <TICKET>/screenshots/.

    uv run -q --no-project --with python-docx python make_test_results_docx.py ONLINE-7526

writes <TICKET>/<TICKET>-test-results.docx. A new ticket copies ONLINE-7532/report_content.py and replaces only
the content.
"""

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

NAVY = RGBColor(0x1F, 0x38, 0x64)
GREEN = RGBColor(0x1E, 0x7B, 0x34)
GREY = RGBColor(0x59, 0x59, 0x59)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(0.75)

normal = doc.styles["Normal"]
normal.font.name = "Arial"
normal.font.size = Pt(11)
for name, size in (("Heading 1", 15), ("Heading 2", 12)):
    style = doc.styles[name]
    style.font.name = "Arial"
    style.font.size = Pt(size)
    style.font.color.rgb = NAVY


def shade(cell, fill):
    props = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def table(widths, header, rows):
    t = doc.add_table(rows=1, cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, text in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(10)
        shade(c, "DCE6F2")
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(text)
            run.font.size = Pt(10)
            if text == "PASS":
                run.bold = True
                run.font.color.rgb = GREEN
            elif text == "FAIL":
                run.bold = True
                run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            elif text in ("Pending", "Not covered"):
                run.bold = True
                run.font.color.rgb = GREY
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
    doc.add_paragraph()


def image(file, caption, width=6.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(f"{IMG}/{file}", width=Inches(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = c.add_run(caption)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = GREY


if len(sys.argv) != 2:
    sys.exit("usage: python make_test_results_docx.py <TICKET>   (e.g. ONLINE-7526)")
TICKET = sys.argv[1].strip("/")
DIR = Path(__file__).resolve().parent / TICKET
CONTENT = DIR / "report_content.py"
if not CONTENT.is_file():
    sys.exit(f"{CONTENT} not found")
IMG = str(DIR / "screenshots")
OUT = str(DIR / f"{TICKET}-test-results.docx")

exec(compile(CONTENT.read_text(), str(CONTENT), "exec"))

doc.save(OUT)
print("wrote", OUT)
