"""Shared layout helpers for the Scout PDFs: styles, code blocks, figures, callouts, tables and the page template."""
import os
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "fig")
BOOK = {"title": "Scout", "header": "Scout", "subject": ""}

D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", D + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", D + "DejaVuSans-Bold.ttf"))
import matplotlib  # ships DejaVu Sans Oblique, which the system fonts lack
MPL_FONTS = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("Sans-It", os.path.join(MPL_FONTS, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("Mono", D + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("Mono-Bold", D + "DejaVuSansMono-Bold.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-It", boldItalic="Sans-Bold")

NAVY = colors.HexColor("#1F3A5F")
TEAL = colors.HexColor("#2A9D8F")
ORANGE = colors.HexColor("#E76F51")
INK = colors.HexColor("#222222")
MUTED = colors.HexColor("#5F6B7A")
CODEBG = colors.HexColor("#F4F6F8")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
WIDTH = PAGE_W - 2 * MARGIN

st = {
    "body": ParagraphStyle("body", fontName="Sans", fontSize=10, leading=15, textColor=INK, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="Sans-Bold", fontSize=22, leading=27, textColor=NAVY, spaceAfter=4),
    "kicker": ParagraphStyle("kicker", fontName="Sans-Bold", fontSize=10, leading=13, textColor=TEAL, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Sans-Bold", fontSize=14, leading=18, textColor=NAVY, spaceBefore=10,
                         spaceAfter=5, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Sans-Bold", fontSize=11, leading=15, textColor=INK, spaceBefore=6,
                         spaceAfter=3, keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName="Sans", fontSize=10, leading=14.5, textColor=INK, leftIndent=14,
                             bulletIndent=3, spaceAfter=2.5),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=10.2, textColor=INK),
    "ref": ParagraphStyle("ref", fontName="Mono-Bold", fontSize=7.4, leading=10, textColor=TEAL),
    "caption": ParagraphStyle("caption", fontName="Sans-It", fontSize=8.6, leading=11.5, textColor=MUTED,
                              alignment=TA_CENTER, spaceAfter=8),
    "callout": ParagraphStyle("callout", fontName="Sans", fontSize=9.5, leading=14, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=8.8, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Sans-Bold", fontSize=8.8, leading=12, textColor=colors.white),
    "cellmono": ParagraphStyle("cellmono", fontName="Mono", fontSize=7.8, leading=11, textColor=INK),
    "toc1": ParagraphStyle("toc1", fontName="Sans-Bold", fontSize=11, leading=20, textColor=NAVY),
    "cover_t": ParagraphStyle("ct", fontName="Sans-Bold", fontSize=34, leading=40, textColor=colors.white),
    "cover_s": ParagraphStyle("cs", fontName="Sans", fontSize=14, leading=20, textColor=colors.white),
    "cover_m": ParagraphStyle("cm", fontName="Sans", fontSize=10, leading=15, textColor=colors.HexColor("#CFE3F5")),
}

story = []
chapter_no = [0]


# ---------------------------------------------------------------- helpers
def P(text, style="body"):
    story.append(Paragraph(text, st[style]))


def bullets(items, style="bullet"):
    for it in items:
        story.append(Paragraph(it, st[style], bulletText="•"))


def chapter(title, kicker):
    chapter_no[0] += 1
    story.append(PageBreak())
    p = Paragraph(f"Chapter {chapter_no[0]}", st["kicker"])
    story.append(p)
    h = Paragraph(title, st["h1"])
    h._toc = f"{chapter_no[0]}.  {title}"
    story.append(h)
    story.append(Paragraph(kicker, ParagraphStyle("k2", parent=st["body"], textColor=MUTED, fontName="Sans-It")))
    story.append(Spacer(1, 4))


def h2(text):
    story.append(CondPageBreak(55 * mm))
    P(text, "h2")


def h3(text):
    story.append(CondPageBreak(35 * mm))
    P(text, "h3")


def code(snippet, ref, note=""):
    """A code block with its file reference on top; long blocks split across pages and repeat the reference."""
    lines = snippet.strip("\n").split("\n")
    header = Paragraph(escape(ref) + (f'<font name="Sans-It" color="#5F6B7A" size="7.4">  — {escape(note)}</font>'
                                      if note else ""), st["ref"])
    chunks = ["\n".join(lines[i:i + 3]) for i in range(0, len(lines), 3)]
    rows = [[header]] + [[Preformatted(chunk, st["code"])] for chunk in chunks]
    t = Table(rows, colWidths=[WIDTH], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F3F1")),
        ("BACKGROUND", (0, 1), (-1, -1), CODEBG),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 0), ("BOTTOMPADDING", (0, 1), (-1, -1), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 5), ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))
    story.append(CondPageBreak(30 * mm))
    story.append(Spacer(1, 3))
    story.append(t)
    story.append(Spacer(1, 7))


def figure(name, caption, width=WIDTH, max_h=150 * mm):
    path = os.path.join(FIG, name)
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    h = width * ih / iw
    if h > max_h:
        width, h = width * max_h / h, max_h
    lead = []
    if story and isinstance(story[-1], Paragraph) and story[-1].style.name in ("h2", "h3"):
        lead = [story.pop()]
    story.append(KeepTogether(lead + [Spacer(1, 4), Image(path, width=width, height=h),
                                      Paragraph(caption, st["caption"])]))


def callout(kind, text):
    palette = {"simple": ("In simple words", TEAL, "#E6F3F1"), "warn": ("Watch out", ORANGE, "#FBEAE5"),
               "try": ("Try it yourself", NAVY, "#E7EDF5"), "why": ("Why it is built this way", colors.HexColor("#6D5BD0"), "#EEEBFB")}
    label, line, bg = palette[kind]
    t = Table([[Paragraph(f'<b><font color="{line.hexval().replace("0x", "#")}">{label}</font></b><br/>{text}',
                          st["callout"])]], colWidths=[WIDTH])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, line),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.append(Spacer(1, 3))
    story.append(t)
    story.append(Spacer(1, 7))


def table(rows, widths, mono_cols=()):
    data = []
    for r, row in enumerate(rows):
        cells = []
        for c, val in enumerate(row):
            style = "cellb" if r == 0 else ("cellmono" if c in mono_cols else "cell")
            cells.append(Paragraph(val, st[style]))
        data.append(cells)
    t = Table(data, colWidths=[w * WIDTH for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DAE0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 3))
    story.append(t)
    story.append(Spacer(1, 8))


def summary(points):
    rows = [[Paragraph('<font color="white"><b>Chapter summary</b></font>', st["callout"])]]
    for p in points:
        rows.append([Paragraph(p, st["bullet"], bulletText="✓")])
    t = Table(rows, colWidths=[WIDTH])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL),
                           ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#EEF7F5")),
                           ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 10))
    story.append(KeepTogether([t]))


def c(s):
    """Inline code."""
    return f'<font name="Mono" size="8.8" color="#1F3A5F">{escape(s)}</font>'


# ---------------------------------------------------------------- page decoration
class Doc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm,
                         bottomMargin=20 * mm, title=BOOK["title"],
                         author="Studies Weekly Online — AI team", subject=BOOK["subject"])
        frame = Frame(MARGIN, 20 * mm, WIDTH, PAGE_H - 42 * mm, id="f", leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id="c", leftPadding=0, rightPadding=0, topPadding=0,
                            bottomPadding=0)
        self.addPageTemplates([PageTemplate("cover", [cover_frame], onPage=self.cover),
                               PageTemplate("body", [frame], onPage=self.decorate)])

    def cover(self, canv, doc):
        canv.saveState()
        canv.setFillColor(NAVY)
        canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canv.setFillColor(TEAL)
        canv.rect(0, PAGE_H * 0.36, PAGE_W, 6, fill=1, stroke=0)
        canv.setFillColor(colors.HexColor("#2C4C75"))
        for i in range(7):
            canv.circle(PAGE_W - 40 - i * 34, 70 + (i % 2) * 22, 9 + i * 1.5, fill=1, stroke=0)
        canv.restoreState()

    def decorate(self, canv, doc):
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#D5DAE0"))
        canv.line(MARGIN, PAGE_H - 15 * mm, PAGE_W - MARGIN, PAGE_H - 15 * mm)
        canv.setFont("Sans", 8)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN, PAGE_H - 13 * mm, BOOK["header"])
        canv.drawRightString(PAGE_W - MARGIN, 12 * mm, f"{doc.page}")
        canv.drawString(MARGIN, 12 * mm, "Studies Weekly Online · swo-3.0 + rag")
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and hasattr(flowable, "_toc"):
            key = f"ch{self.seq.nextf('ch')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable._toc, key, 0)
            self.notify("TOCEntry", (0, flowable._toc, self.page, key))


