# -*- coding: utf-8 -*-
"""Generalized branded A4 PDF report engine (data-driven).

Usage:
    python build_report_pdf.py <spec.json> [out.pdf]

Reads a JSON spec (see ../report_schema.md) and renders a branded A4 PDF:
cover with colored bands, intro, summary table, detail cards, observations,
sources and a per-page footer. All sections except `title` are optional —
a missing key means the section is skipped.

The engine is intentionally data-driven: NEVER hardcode report content here.
Pass everything through the JSON spec. To change look-and-feel, edit the
styles/colors in THIS file once — do not fork the script per report.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --- Brand palette (single source of truth for visual identity) ---
BRAND = colors.HexColor("#1E3A8A")   # deep blue
ACCENT = colors.HexColor("#D97706")  # amber
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#D1D5DB")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")

# --- Fonts (Cyrillic-capable). Wrapped so the engine still runs if Arial
#     is missing — falls back to Helvetica family (no Cyrillic, but no crash). ---
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BOLDITALIC = "Helvetica-BoldOblique"


def _register_fonts() -> None:
    """Register Arial (Cyrillic) if present; otherwise keep Helvetica defaults."""
    global FONT, FONT_BOLD, FONT_ITALIC, FONT_BOLDITALIC
    faces = {
        "Arial": "C:/Windows/Fonts/arial.ttf",
        "Arial-Bold": "C:/Windows/Fonts/arialbd.ttf",
        "Arial-Italic": "C:/Windows/Fonts/ariali.ttf",
        "Arial-BoldItalic": "C:/Windows/Fonts/arialbi.ttf",
    }
    try:
        if all(Path(p).exists() for p in faces.values()):
            for name, path in faces.items():
                pdfmetrics.registerFont(TTFont(name, path))
            registerFontFamily(
                "Arial", normal="Arial", bold="Arial-Bold",
                italic="Arial-Italic", boldItalic="Arial-BoldItalic",
            )
            FONT, FONT_BOLD = "Arial", "Arial-Bold"
            FONT_ITALIC, FONT_BOLDITALIC = "Arial-Italic", "Arial-BoldItalic"
    except Exception as exc:  # pragma: no cover - defensive
        print(f"WARN: font registration failed, using Helvetica: {exc}")


_register_fonts()


def _styles():
    getSampleStyleSheet()  # warm up reportlab default styles registry

    def S(name, **kw):
        d = dict(fontName=FONT, fontSize=10, leading=14, textColor=TEXT)
        d.update(kw)
        return ParagraphStyle(name, **d)

    return {
        "cover_title": S("CoverTitle", fontName=FONT_BOLD, fontSize=26, leading=32,
                         alignment=TA_CENTER, textColor=BRAND),
        "cover_sub": S("CoverSub", fontSize=14, leading=20, alignment=TA_CENTER,
                       textColor=MUTED),
        "cover_date": S("CoverDate", fontName=FONT_BOLD, fontSize=12,
                        alignment=TA_CENTER, textColor=ACCENT),
        "cover_note": S("CoverNote", fontSize=9, leading=12, alignment=TA_CENTER,
                        textColor=MUTED, fontName=FONT_ITALIC),
        "h1": S("H1", fontName=FONT_BOLD, fontSize=18, leading=24, textColor=BRAND,
                spaceBefore=6, spaceAfter=10),
        "h2": S("H2", fontName=FONT_BOLD, fontSize=14, leading=20, textColor=BRAND,
                spaceBefore=10, spaceAfter=6),
        "body": S("Body", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=4),
        "bullet": S("Bullet", fontSize=10, leading=14, leftIndent=12, spaceAfter=2),
        "note": S("Note", fontSize=9, leading=12, textColor=MUTED, fontName=FONT_ITALIC),
        "source": S("Source", fontSize=9, leading=12, leftIndent=10, spaceAfter=1),
    }


def _make_footer(footer_text: str):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        if footer_text:
            canvas.drawString(15 * mm, 10 * mm, footer_text)
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"стр. {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
        canvas.restoreState()

    return on_page


def on_cover(canvas, doc):
    canvas.saveState()
    # top band
    canvas.setFillColor(BRAND)
    canvas.rect(0, A4[1] - 40 * mm, A4[0], 40 * mm, stroke=0, fill=1)
    # bottom band
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, A4[0], 20 * mm, stroke=0, fill=1)
    canvas.restoreState()


def _esc(value) -> str:
    """Escape XML-special chars for reportlab Paragraph markup."""
    s = "" if value is None else str(value)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _summary_table(spec_table: dict, st) -> Table:
    columns = spec_table.get("columns", [])
    rows = spec_table.get("rows", [])
    body = st["body"]

    data = [[Paragraph(f"<b>{_esc(c)}</b>", body) for c in columns]]
    for r in rows:
        data.append([Paragraph(_esc(cell), body) for cell in r])

    page_width = A4[0] - 36 * mm  # margins 18mm each side
    n = max(1, len(columns))
    col_widths = [page_width / n] * n

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _card(c: dict, st):
    body = st["body"]
    rank = c.get("rank", "")
    name = _esc(c.get("name", ""))
    subtitle = _esc(c.get("subtitle", ""))

    header = Table(
        [[Paragraph(f'<font color="white" size="14"><b>{_esc(rank)}</b></font>', body),
          Paragraph(f'<font color="#1E3A8A" size="13"><b>{name}</b></font>'
                    + (f'<br/><font color="#4B5563" size="9">{subtitle}</font>'
                       if subtitle else ""), body)]],
        colWidths=[12 * mm, 160 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRAND),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    flow = [header]
    fields = c.get("fields", {})
    if fields:
        info_data = [
            [Paragraph(f"<b>{_esc(k)}</b>", body), Paragraph(_esc(v), body)]
            for k, v in fields.items()
        ]
        info = Table(info_data, colWidths=[34 * mm, 138 * mm])
        info.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")),
        ]))
        flow.append(info)
    flow.append(Spacer(1, 8))
    return KeepTogether(flow)


def build_pdf(spec: dict, out_path: Path) -> Path:
    st = _styles()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title = spec.get("title", "Отчёт")
    footer = spec.get("footer", title)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title=title, author="Claude Code — report skill",
    )

    story = []

    # --- Cover ---
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph(_esc(title), st["cover_title"]))
    if spec.get("subtitle"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(_esc(spec["subtitle"]), st["cover_sub"]))
    if spec.get("date"):
        story.append(Spacer(1, 35 * mm))
        story.append(Paragraph(f"Отчёт от {_esc(spec['date'])}", st["cover_date"]))
    if spec.get("note"):
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(_esc(spec["note"]), st["cover_note"]))
    story.append(PageBreak())

    # --- Intro ---
    if spec.get("intro"):
        story.append(Paragraph("О подборке", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
        story.append(Paragraph(_esc(spec["intro"]), st["body"]))
        if spec.get("note"):
            story.append(Spacer(1, 4))
            story.append(Paragraph(_esc(spec["note"]), st["note"]))

    # --- Summary table ---
    if spec.get("summary_table"):
        story.append(Spacer(1, 10))
        story.append(Paragraph("Сводная таблица", st["h2"]))
        story.append(_summary_table(spec["summary_table"], st))

    # --- Cards ---
    cards = spec.get("cards", [])
    if cards:
        story.append(PageBreak())
        story.append(Paragraph("Подробные карточки", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))
        for c in cards:
            story.append(_card(c, st))

    # --- Observations ---
    observations = spec.get("observations", [])
    if observations:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Ключевые наблюдения", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
        for i, o in enumerate(observations, 1):
            story.append(Paragraph(f"<b>{i}.</b> {_esc(o)}", st["bullet"]))
            story.append(Spacer(1, 2))

    # --- Sources ---
    sources = spec.get("sources", [])
    if sources:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Источники", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
        for s in sources:
            s_title = _esc(s.get("title", ""))
            url = _esc(s.get("url", ""))
            line = f"• {s_title}"
            if url:
                line += f' — <font color="#1E3A8A"><u>{url}</u></font>'
            story.append(Paragraph(line, st["source"]))

    doc.build(story, onFirstPage=on_cover, onLaterPages=_make_footer(footer))
    return out_path


def main(argv) -> int:
    if len(argv) < 2:
        print("Usage: python build_report_pdf.py <spec.json> [out.pdf]")
        return 2

    spec_path = Path(argv[1])
    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}")
        return 1

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if "title" not in spec:
        print("ERROR: spec must contain at least a 'title' key")
        return 1

    if len(argv) >= 3:
        out_path = Path(argv[2])
    else:
        out_path = spec_path.with_suffix(".pdf")

    built = build_pdf(spec, out_path)
    n_cards = len(spec.get("cards", []))
    n_rows = len(spec.get("summary_table", {}).get("rows", []))
    print(f"OK: {built}")
    print(f"cards: {n_cards}  summary_rows: {n_rows}  "
          f"size: {built.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
