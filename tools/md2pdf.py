# -*- coding: utf-8 -*-
"""
md2pdf — универсальный конвертер Markdown -> PDF с поддержкой кириллицы.

Вход:  путь к .md файлу.
Выход: валидный .pdf (рядом с .md или по заданному пути).

Возможности разметки:
  - заголовки  # .. ######
  - **жирный**, *курсив*, `inline code`, [текст](url)
  - списки маркированные (-, *, +) и нумерованные (1.)
  - блоки кода ```...```
  - таблицы GFM  | a | b |
  - цитаты  > ...
  - горизонтальная линия  ---

Шрифты: Arial (Windows) с кросс-платформенным фолбэком (Segoe/Tahoma/Verdana,
DejaVu/Liberation на Linux). Если кириллический TTF не найден — падает обратно
на встроенный Helvetica с предупреждением (кириллица будет квадратами).

Использование:
    python tools/md2pdf.py input.md [output.pdf]
    from tools.md2pdf import convert; convert("input.md", "output.pdf")

Зависимости: reportlab. Без внешних бинарей (poppler/wkhtmltopdf не нужны).
"""
import os
import sys
import re
import html
import argparse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, Preformatted, HRFlowable, ListFlowable, ListItem)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ───────────────────────── Блок 1. Шрифты ─────────────────────────

# Кандидаты по ролям. Первый существующий путь побеждает. Кросс-платформенно.
_WIN = r"C:\Windows\Fonts"
_LINUX_DV = "/usr/share/fonts/truetype/dejavu"
_LINUX_LIB = "/usr/share/fonts/truetype/liberation"
_MAC = "/Library/Fonts"

_FONT_CANDIDATES = {
    "regular": [
        os.path.join(_WIN, "arial.ttf"),
        os.path.join(_WIN, "segoeui.ttf"),
        os.path.join(_WIN, "tahoma.ttf"),
        os.path.join(_WIN, "verdana.ttf"),
        os.path.join(_LINUX_DV, "DejaVuSans.ttf"),
        os.path.join(_LINUX_LIB, "LiberationSans-Regular.ttf"),
        os.path.join(_MAC, "Arial.ttf"),
    ],
    "bold": [
        os.path.join(_WIN, "arialbd.ttf"),
        os.path.join(_WIN, "segoeuib.ttf"),
        os.path.join(_WIN, "tahomabd.ttf"),
        os.path.join(_WIN, "verdanab.ttf"),
        os.path.join(_LINUX_DV, "DejaVuSans-Bold.ttf"),
        os.path.join(_LINUX_LIB, "LiberationSans-Bold.ttf"),
        os.path.join(_MAC, "Arial Bold.ttf"),
    ],
    "italic": [
        os.path.join(_WIN, "ariali.ttf"),
        os.path.join(_WIN, "segoeuii.ttf"),
        os.path.join(_WIN, "verdanai.ttf"),
        os.path.join(_LINUX_DV, "DejaVuSans-Oblique.ttf"),
        os.path.join(_LINUX_LIB, "LiberationSans-Italic.ttf"),
        os.path.join(_MAC, "Arial Italic.ttf"),
    ],
    "mono": [
        os.path.join(_WIN, "consola.ttf"),
        os.path.join(_WIN, "cour.ttf"),
        os.path.join(_LINUX_DV, "DejaVuSansMono.ttf"),
        os.path.join(_LINUX_LIB, "LiberationMono-Regular.ttf"),
        os.path.join(_MAC, "Courier New.ttf"),
    ],
}

# Имена шрифтов в reportlab. Заполняются register_fonts().
FONTS = {"regular": "Helvetica", "bold": "Helvetica-Bold",
         "italic": "Helvetica-Oblique", "mono": "Courier"}


def _first_existing(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def register_fonts():
    """Регистрирует TTF по ролям с фолбэком. Возвращает (FONTS, warnings[])."""
    warnings = []
    names = {"regular": "MDR", "bold": "MDB", "italic": "MDI", "mono": "MDM"}
    builtin = {"regular": "Helvetica", "bold": "Helvetica-Bold",
               "italic": "Helvetica-Oblique", "mono": "Courier"}

    for role, ttf_name in names.items():
        path = _first_existing(_FONT_CANDIDATES[role])
        if path:
            try:
                pdfmetrics.registerFont(TTFont(ttf_name, path))
                FONTS[role] = ttf_name
            except Exception as e:                       # битый/несовместимый TTF
                FONTS[role] = builtin[role]
                warnings.append("шрифт %s (%s) не зарегистрирован: %s — фолбэк %s"
                                % (role, path, e, builtin[role]))
        else:
            FONTS[role] = builtin[role]
            warnings.append("TTF для роли '%s' не найден — фолбэк %s (без кириллицы!)"
                            % (role, builtin[role]))

    # bold/italic фолбэк на regular, если regular зарегистрировался, а они нет
    if FONTS["regular"] == "MDR":
        for role in ("bold", "italic"):
            if FONTS[role] in builtin.values():
                FONTS[role] = "MDR"

    # Семейство — чтобы <b>/<i> внутри Paragraph брали правильные начертания
    try:
        pdfmetrics.registerFontFamily(
            FONTS["regular"], normal=FONTS["regular"], bold=FONTS["bold"],
            italic=FONTS["italic"], boldItalic=FONTS["bold"])
    except Exception:
        pass

    return FONTS, warnings


# ───────────────────────── Блок 2. Стили ─────────────────────────

# Палитра (сдержанная, печать-дружественная)
INK    = colors.HexColor("#1a1a1a")
NAVY   = colors.HexColor("#1f3a5f")
BLUE   = colors.HexColor("#2b5797")
GREY   = colors.HexColor("#6b7280")
LINE   = colors.HexColor("#c9d3e0")
CODEBG = colors.HexColor("#f4f6f8")
CODEFG = colors.HexColor("#9b2c2c")
QUOTE  = colors.HexColor("#586374")
QUOTEBG = colors.HexColor("#f6f8fc")
THEAD  = colors.HexColor("#1f3a5f")
TSTRIPE = colors.HexColor("#f6f8fc")

# Кегли заголовков h1..h6
_H_SIZES = {1: 19, 2: 15, 3: 12.5, 4: 11, 5: 10, 6: 9.5}


def build_styles():
    """Собирает словарь ParagraphStyle на текущих FONTS. Вызывать после register_fonts()."""
    R, B, I, M = FONTS["regular"], FONTS["bold"], FONTS["italic"], FONTS["mono"]
    S = {}

    S["body"] = ParagraphStyle("body", fontName=R, fontSize=10, leading=14.5,
                               textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
    S["li"] = ParagraphStyle("li", parent=S["body"], alignment=TA_LEFT,
                             spaceAfter=3, leading=14)

    for lvl, size in _H_SIZES.items():
        S["h%d" % lvl] = ParagraphStyle(
            "h%d" % lvl, fontName=B, fontSize=size, leading=size * 1.25,
            textColor=NAVY if lvl <= 2 else BLUE,
            spaceBefore=12 if lvl <= 2 else 9, spaceAfter=5 if lvl <= 2 else 3)

    S["code"] = ParagraphStyle("code", fontName=M, fontSize=8.5, leading=11.5,
                               textColor=INK, backColor=CODEBG, borderPadding=(6, 6, 6, 6),
                               leftIndent=2, spaceBefore=4, spaceAfter=8)
    S["quote"] = ParagraphStyle("quote", fontName=I, fontSize=10, leading=14,
                                textColor=QUOTE, leftIndent=12, spaceBefore=4, spaceAfter=8)
    S["thcell"] = ParagraphStyle("thcell", fontName=B, fontSize=8.6, leading=11,
                                 textColor=colors.white, alignment=TA_LEFT)
    S["tcell"] = ParagraphStyle("tcell", fontName=R, fontSize=8.4, leading=11, textColor=INK)
    S["small"] = ParagraphStyle("small", fontName=R, fontSize=8, leading=11, textColor=GREY)
    return S


# ───────────────────── Блок 3. Inline-разметка ─────────────────────

_RE_CODE  = re.compile(r"`([^`]+)`")
_RE_LINK  = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_RE_IMG   = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
_RE_BOLD  = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_RE_ITAL  = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_RE_STRK  = re.compile(r"~~(.+?)~~")


def inline(text):
    """Markdown inline -> безопасный reportlab mini-HTML (с подстановкой шрифтов FONTS)."""
    codes, links = [], []

    # 1. защитить inline-код
    def _code(m):
        codes.append(m.group(1)); return "\x00C%d\x00" % (len(codes) - 1)
    text = _RE_CODE.sub(_code, text)

    # 2. картинки -> [img: alt] (встраивание не поддерживаем), затем ссылки
    text = _RE_IMG.sub(lambda m: "[img: %s]" % (m.group(1) or "image"), text)

    def _link(m):
        links.append((m.group(1), m.group(2))); return "\x00L%d\x00" % (len(links) - 1)
    text = _RE_LINK.sub(_link, text)

    # 3. экранировать спецсимволы базового текста
    text = html.escape(text, quote=False)

    # 4. emphasis (bold до italic)
    text = _RE_BOLD.sub(lambda m: "<b>%s</b>" % (m.group(1) or m.group(2)), text)
    text = _RE_ITAL.sub(lambda m: "<i>%s</i>" % (m.group(1) or m.group(2)), text)
    text = _RE_STRK.sub(lambda m: "<strike>%s</strike>" % m.group(1), text)

    # 5. вернуть ссылки (кликабельные)
    def _unlink(m):
        label, url = links[int(m.group(1))]
        return '<a href="%s" color="#2b5797"><u>%s</u></a>' % (
            html.escape(url, quote=True), html.escape(label, quote=False))
    text = re.sub(r"\x00L(\d+)\x00", _unlink, text)

    # 6. вернуть код (моно-шрифт, акцентный цвет)
    def _uncode(m):
        return '<font face="%s" color="#9b2c2c">%s</font>' % (
            FONTS["mono"], html.escape(codes[int(m.group(1))], quote=False))
    text = re.sub(r"\x00C(\d+)\x00", _uncode, text)

    return text


# ──────────────────── Блок 4. Блочный парсер ────────────────────

_RE_H      = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_RE_HR     = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_RE_FENCE  = re.compile(r"^\s*(```|~~~)(.*)$")
_RE_QUOTE  = re.compile(r"^\s*>\s?(.*)$")
_RE_ULI    = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_RE_OLI    = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_RE_TROW   = re.compile(r"^\s*\|?.*\|.*$")
_RE_TSEP   = re.compile(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$")


def _is_table_sep(line):
    return bool(_RE_TSEP.match(line)) and "-" in line


def md_to_flowables(md_text, S):
    """Парсит markdown-текст в список Platypus-flowables."""
    lines = md_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    flow, para = [], []
    i, n = 0, len(lines)

    def flush_para():
        if para:
            flow.append(Paragraph(inline(" ".join(para)), S["body"]))
            para.clear()

    while i < n:
        line = lines[i]

        # пустая строка — конец абзаца
        if not line.strip():
            flush_para(); i += 1; continue

        # fenced code block
        mf = _RE_FENCE.match(line)
        if mf:
            fence = mf.group(1); flush_para()
            buf, i = [], i + 1
            while i < n and not lines[i].strip().startswith(fence):
                buf.append(lines[i]); i += 1
            i += 1  # пропустить закрывающий fence
            flow.append(Preformatted("\n".join(buf) or " ", S["code"]))
            continue

        # горизонтальная линия
        if _RE_HR.match(line):
            flush_para()
            flow.append(Spacer(1, 3))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=LINE,
                                   spaceBefore=2, spaceAfter=8))
            i += 1; continue

        # заголовок
        mh = _RE_H.match(line)
        if mh:
            flush_para()
            lvl = len(mh.group(1))
            flow.append(Paragraph(inline(mh.group(2)), S["h%d" % lvl]))
            i += 1; continue

        # таблица GFM (текущая строка с '|' и следующая — separator)
        if "|" in line and i + 1 < n and _is_table_sep(lines[i + 1]):
            flush_para()
            tbl_lines, i = [], i
            while i < n and "|" in lines[i] and lines[i].strip():
                tbl_lines.append(lines[i]); i += 1
            flow.append(_build_table(tbl_lines, S))
            flow.append(Spacer(1, 6))
            continue

        # цитата
        if _RE_QUOTE.match(line):
            flush_para()
            qbuf = []
            while i < n and _RE_QUOTE.match(lines[i]):
                qbuf.append(_RE_QUOTE.match(lines[i]).group(1)); i += 1
            flow.append(_build_quote(qbuf, S))
            continue

        # список (маркированный или нумерованный)
        if _RE_ULI.match(line) or _RE_OLI.match(line):
            flush_para()
            li_buf = []
            while i < n and (_RE_ULI.match(lines[i]) or _RE_OLI.match(lines[i])
                             or (lines[i].strip() and lines[i].startswith((" ", "\t"))
                                 and li_buf)):
                li_buf.append(lines[i]); i += 1
            flow.append(_build_list(li_buf, S))
            flow.append(Spacer(1, 4))
            continue

        # обычный текст абзаца
        para.append(line.strip()); i += 1

    flush_para()
    return flow


# ─────────── Блок 5. Таблицы / цитаты / списки ───────────

MARGIN = 42                       # поля страницы, pt
_CONTENT_W = A4[0] - 2 * MARGIN   # доступная ширина контента (портрет A4)

_RE_PIPE = re.compile(r"(?<!\\)\|")


def _split_row(line):
    s = line.strip()
    if s.startswith("|"): s = s[1:]
    if s.endswith("|"):   s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in _RE_PIPE.split(s)]


def _pad(row, ncol):
    row = list(row)
    if len(row) < ncol: row += [""] * (ncol - len(row))
    return row[:ncol]


def _build_table(tbl_lines, S):
    rows = [_split_row(l) for l in tbl_lines]
    header = rows[0]
    aligns = rows[1] if len(rows) > 1 else []
    body = rows[2:]
    ncol = max(1, len(header))

    col_align = []
    for k in range(ncol):
        spec = aligns[k].strip() if k < len(aligns) else ""
        if spec.startswith(":") and spec.endswith(":"): col_align.append("CENTER")
        elif spec.endswith(":"):                        col_align.append("RIGHT")
        else:                                           col_align.append("LEFT")

    data = [[Paragraph(inline(c), S["thcell"]) for c in _pad(header, ncol)]]
    for r in body:
        data.append([Paragraph(inline(c), S["tcell"]) for c in _pad(r, ncol)])

    cw = [_CONTENT_W / ncol] * ncol
    t = Table(data, colWidths=cw, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), THEAD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TSTRIPE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for k, a in enumerate(col_align):
        style.append(("ALIGN", (k, 0), (k, -1), a))
    t.setStyle(TableStyle(style))
    return t


def _build_quote(qbuf, S):
    txt = "<br/>".join(inline(x) for x in qbuf) or " "
    p = Paragraph(txt, S["quote"])
    t = Table([[p]], colWidths=[_CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), QUOTEBG),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _make_list(items, S):
    """items: [(indent, ordered, text)] -> ListFlowable с вложенностью по отступу."""
    if not items:
        return Spacer(0, 0)
    base = min(it[0] for it in items)
    ordered_base = items[0][1]
    flow_items, k = [], 0
    while k < len(items):
        ind, od, tx = items[k]
        j = k + 1
        nested = []
        while j < len(items) and items[j][0] > base:
            nested.append(items[j]); j += 1
        body = [Paragraph(inline(tx), S["li"])]
        if nested:
            body.append(_make_list(nested, S))
        flow_items.append(ListItem(body, leftIndent=10))
        k = j
    return ListFlowable(
        flow_items, bulletType=("1" if ordered_base else "bullet"),
        bulletFontName=FONTS["regular"], bulletFontSize=9,
        leftIndent=16, bulletColor=INK, spaceBefore=0, spaceAfter=0)


def _build_list(li_buf, S):
    items = []
    for ln in li_buf:
        mu = _RE_ULI.match(ln); mo = _RE_OLI.match(ln)
        if mu:
            items.append((len(mu.group(1).replace("\t", "    ")), False, mu.group(2)))
        elif mo:
            items.append((len(mo.group(1).replace("\t", "    ")), True, mo.group(2)))
        elif items:                       # перенос строки внутри пункта
            ind, od, tx = items[-1]
            items[-1] = (ind, od, tx + " " + ln.strip())
    return _make_list(items, S)


# ──────────── Блок 6. Сборка документа, convert(), CLI ────────────

def _read_md(path):
    """Читает .md как UTF-8 (с BOM-фолбэком, затем cp1251). Бросает при провале."""
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # последний шанс — заменяя битые байты
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _make_footer(source_name):
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONTS["regular"], 7.5)
        canvas.setFillColor(GREY)
        w = doc.pagesize[0]
        canvas.drawString(MARGIN, 22, source_name)
        canvas.drawRightString(w - MARGIN, 22, "стр. %d" % doc.page)
        canvas.setStrokeColor(LINE); canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 32, w - MARGIN, 32)
        canvas.restoreState()
    return footer


def convert(md_path, pdf_path=None, verbose=True):
    """
    Конвертирует Markdown-файл в PDF.
    md_path  — путь к .md (обязателен, должен существовать).
    pdf_path — путь к .pdf (по умолчанию рядом, та же база имени).
    Возвращает абсолютный путь к созданному PDF. Бросает при ошибках.
    """
    if not md_path or not os.path.isfile(md_path):
        raise FileNotFoundError("Markdown-файл не найден: %r" % md_path)
    if pdf_path is None:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"

    out_dir = os.path.dirname(os.path.abspath(pdf_path)) or "."
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    md_text = _read_md(md_path)

    _, warns = register_fonts()
    for w in warns:
        sys.stderr.write("[md2pdf] WARNING: %s\n" % w)
    if verbose and FONTS["regular"] == "Helvetica":
        sys.stderr.write("[md2pdf] WARNING: кириллический шрифт не найден — "
                         "русский текст будет квадратами.\n")

    S = build_styles()
    try:
        flow = md_to_flowables(md_text, S)
    except Exception as e:
        raise RuntimeError("ошибка парсинга Markdown: %s" % e) from e
    if not flow:
        flow = [Paragraph("(пустой документ)", S["body"])]

    doc = BaseDocTemplate(
        pdf_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=os.path.basename(pdf_path), author="md2pdf")
    frame = Frame(MARGIN, MARGIN, A4[0] - 2 * MARGIN, A4[1] - 2 * MARGIN, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=_make_footer(os.path.basename(md_path)))])
    try:
        doc.build(flow)
    except Exception as e:
        raise RuntimeError("ошибка сборки PDF (reportlab): %s" % e) from e

    if verbose:
        sys.stderr.write("[md2pdf] OK: %s\n" % os.path.abspath(pdf_path))
    return os.path.abspath(pdf_path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="md2pdf", description="Универсальный конвертер Markdown -> PDF (кириллица).")
    ap.add_argument("input", help="путь к .md файлу")
    ap.add_argument("output", nargs="?", default=None,
                    help="путь к .pdf (по умолчанию рядом с .md)")
    ap.add_argument("-q", "--quiet", action="store_true", help="без сообщений в stderr")
    args = ap.parse_args(argv)
    try:
        out = convert(args.input, args.output, verbose=not args.quiet)
    except Exception as e:
        sys.stderr.write("[md2pdf] ERROR: %s\n" % e)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
