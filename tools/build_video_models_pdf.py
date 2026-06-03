# -*- coding: utf-8 -*-
"""
Сборка PDF-техпроекта по видео-AI моделям для MarquisPro из готового ресёрча.
Стек: reportlab Platypus. Кириллица через системный Arial. Без эмодзи.
Текстовые метки: [РЕКОМЕНДАЦИЯ] / [ВНИМАНИЕ] / [НАЙДЕНО] / [ОПРОВЕРГНУТО].
Запуск: python tools/build_video_models_pdf.py
Выход: outputs/video-models-comparison-2026.pdf
"""
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, PageBreak, NextPageTemplate, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "video-models-comparison-2026.pdf")
WIN_FONTS = r"C:\Windows\Fonts"

# --- шрифты (кириллица) ---
pdfmetrics.registerFont(TTFont("AR", os.path.join(WIN_FONTS, "arial.ttf")))
pdfmetrics.registerFont(TTFont("ARB", os.path.join(WIN_FONTS, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("ARI", os.path.join(WIN_FONTS, "ariali.ttf")))
pdfmetrics.registerFontFamily("AR", normal="AR", bold="ARB", italic="ARI", boldItalic="ARB")

# --- палитра ---
NAVY   = colors.HexColor("#1f3a5f")
BLUE   = colors.HexColor("#2b5797")
LIGHT  = colors.HexColor("#eef2f8")
STRIPE = colors.HexColor("#f6f8fc")
GREY   = colors.HexColor("#6b7280")
LINE   = colors.HexColor("#c9d3e0")
GREEN  = colors.HexColor("#157f3b")
RED    = colors.HexColor("#b3261e")
AMBER  = colors.HexColor("#b26a00")
WARNBG = colors.HexColor("#fff4f2")
WARNBR = colors.HexColor("#e0b4ae")
RECBG  = colors.HexColor("#eef7f0")
RECBR  = colors.HexColor("#aacfb5")

# --- стили ---
def S(name, **kw):
    base = dict(fontName="AR", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#1a1a1a"))
    base.update(kw); return ParagraphStyle(name, **base)

st_body   = S("body", alignment=TA_JUSTIFY, spaceAfter=5)
st_bullet = S("bullet", alignment=TA_LEFT, spaceAfter=3, leftIndent=10, bulletIndent=0)
st_h1     = S("H1", fontName="ARB", fontSize=15, leading=19, textColor=NAVY, spaceBefore=10, spaceAfter=7)
st_h2     = S("H2", fontName="ARB", fontSize=11.5, leading=15, textColor=BLUE, spaceBefore=8, spaceAfter=4)
st_title  = S("title", fontName="ARB", fontSize=26, leading=30, textColor=NAVY, alignment=TA_LEFT)
st_sub    = S("sub", fontSize=12, leading=16, textColor=GREY, alignment=TA_LEFT)
st_meta   = S("meta", fontSize=9.5, leading=14, textColor=colors.HexColor("#333333"))
st_small  = S("small", fontSize=8, leading=11, textColor=GREY)
st_cell   = S("cell", fontSize=7.6, leading=9.8)
st_cellc  = S("cellc", fontSize=7.6, leading=9.8, alignment=TA_CENTER)
st_cellh  = S("cellh", fontName="ARB", fontSize=7.8, leading=10, textColor=colors.white, alignment=TA_CENTER)
st_ecell  = S("ecell", fontSize=8.6, leading=11.5)
st_ecellc = S("ecellc", fontSize=8.6, leading=11.5, alignment=TA_CENTER)
st_ecellh = S("ecellh", fontName="ARB", fontSize=9, leading=12, textColor=colors.white, alignment=TA_CENTER)
st_toc1   = S("toc1", fontName="ARB", fontSize=10.5, leading=18, textColor=NAVY)
st_toc2   = S("toc2", fontSize=9.5, leading=15, textColor=colors.HexColor("#333333"), leftIndent=14)

# теги
def tag(t):
    c = {"[РЕКОМЕНДАЦИЯ]": GREEN, "[НАЙДЕНО]": GREEN, "[ВНИМАНИЕ]": RED,
         "[ОПРОВЕРГНУТО]": RED, "[ТРЕБУЕТ ПРОВЕРКИ]": AMBER}.get(t, GREY)
    return '<font name="ARB" color="#%s">%s</font>' % (c.hexval()[2:], t)

YES = '<font name="ARB" color="#157f3b">да</font>'
NO  = '<font name="ARB" color="#b3261e">нет</font>'

def P(txt, style=st_body):  return Paragraph(txt, style)

story = []

# --- DocTemplate с поддержкой авто-оглавления ---
class DocT(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, "style") and getattr(flowable, "_toc", False):
            lvl = 0 if flowable.style.name == "H1" else 1
            key = "h%d-%d" % (lvl, self.page)
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (lvl, flowable.getPlainText(), self.page, key))

def H1(text):
    p = Paragraph(text, st_h1); p._toc = True; return p
def H2(text):
    p = Paragraph(text, st_h2); p._toc = True; return p

# --- рамки страниц: портрет (текст) + ландшафт (широкие таблицы) ---
PW, PH = A4
LW, LH = landscape(A4)
M = 42
frame_p = Frame(M, M, PW - 2*M, PH - 2*M, id="portrait")
frame_l = Frame(M, M, LW - 2*M, LH - 2*M, id="land")

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("AR", 7.5); canvas.setFillColor(GREY)
    w = doc.pagesize[0]
    canvas.drawString(M, 22, "MarquisPro — техпроект видео-AI моделей · ресёрч 2026-06-03")
    canvas.drawRightString(w - M, 22, "стр. %d" % doc.page)
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.5)
    canvas.line(M, 32, w - M, 32)
    canvas.restoreState()

doc = DocT(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M,
           title="MarquisPro — сравнение видео-AI моделей 2026", author="claude-agents")
doc.addPageTemplates([
    PageTemplate(id="P", frames=[frame_p], pagesize=A4, onPage=footer),
    PageTemplate(id="L", frames=[frame_l], pagesize=landscape(A4), onPage=footer),
])

# ====== ТИТУЛ ======
story += [Spacer(1, 70)]
story += [Paragraph("Техпроект: выбор видео-AI моделей", st_title)]
story += [Paragraph("для SaaS MarquisPro (карточки Wildberries / Ozon)", st_title)]
story += [Spacer(1, 10)]
story += [Paragraph("Сравнение по цене и качеству генерации видео-обложек · pay-as-you-go", st_sub)]
story += [Spacer(1, 26)]
meta_tbl = Table([
    ["Целевой ролик", "8 сек · вертикаль · 1080p · без звука · MP4 · image-to-video (анимация фото товара)"],
    ["Модель оплаты", "pay-as-you-go, нагрузка непредсказуема (единицы — сотни роликов/день)"],
    ["Текущий стек", "видео через агрегатор Polza (модели Kling)"],
    ["Дата ресёрча", "2026-06-03 (цены на видео-AI меняются за недели — пересверять)"],
    ["Метод", "multi-agent ресёрч (8 агентов на семейства + агрегаторы) + adversarial-перепроверка цен"],
], colWidths=[95, PW - 2*M - 95])
meta_tbl.setStyle(TableStyle([
    ("FONT", (0,0), (0,-1), "ARB", 9), ("FONT", (1,0), (1,-1), "AR", 9),
    ("TEXTCOLOR", (0,0), (0,-1), NAVY), ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("BACKGROUND", (0,0), (0,-1), LIGHT), ("LINEBELOW", (0,0), (-1,-2), 0.4, LINE),
    ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7),
]))
story += [meta_tbl, Spacer(1, 18)]
legend = ('<b>Метки:</b>  %s — подтверждено страницей провайдера и независимой перепроверкой (расхождение &lt;20%%).  '
          '%s — инженерный вывод.  %s — важное предупреждение.  '
          '%s — ресёрч-утверждение опровергнуто верификатором.  %s — один источник / страница за antibot / цена в RUB по примерному курсу.') % (
          tag("[НАЙДЕНО]"), tag("[РЕКОМЕНДАЦИЯ]"), tag("[ВНИМАНИЕ]"), tag("[ОПРОВЕРГНУТО]"), tag("[ТРЕБУЕТ ПРОВЕРКИ]"))
story += [Paragraph(legend, st_small)]
story += [PageBreak()]

# ====== ОГЛАВЛЕНИЕ ======
story += [Paragraph("Оглавление", st_h1)]
toc = TableOfContents()
toc.levelStyles = [st_toc1, st_toc2]
story += [toc, PageBreak()]

# ====== 1. ЦЕЛЬ ======
story += [H1("1. Цель и требования маркетплейсов")]
story += [P("Выбрать <b>основную</b> и <b>резервную</b> модель генерации видео-обложек карточек WB/Ozon "
            "по критерию цена/качество для pay-as-you-go SaaS и определить <b>стратегию закупки</b> "
            "(агрегатор vs прямой API-пакет vs подписка) под непредсказуемую нагрузку, с точками безубыточности.")]
story += [P("Привязка к требованиям площадок (см. marketplace-requirements-2026.md):")]
for b in [
    "<b>WB видеообложка:</b> 3:4, 810x1080, от 1080p, оптим. 15-30 сек; 8-секундный хук критичен.",
    "<b>Ozon видеообложка:</b> первые ~8 сек БЕЗ звука (отсюда жёсткое 8s no-audio), MP4/MOV, от 1080p.",
    "Звук в видеообложке в большинстве случаев не нужен → всегда генерировать audio-off (на ряде моделей это вдвое дешевле).",
]:
    story += [P("• " + b, st_bullet)]

# ====== 2. СРАВНИТЕЛЬНАЯ ТАБЛИЦА (ландшафт) ======
story += [Spacer(1, 6), NextPageTemplate("L"), PageBreak()]
story += [H1("2. Сравнительная таблица моделей")]
story += [P("Ролик 8s / вертикаль / 1080p / без звука / image-to-video. Цена — самый дешёвый подтверждённый "
            "pay-as-you-go путь через агрегатор. Отсортировано по цене за ролик.", st_small)]
story += [Spacer(1, 4)]

hdr = [Paragraph(h, st_cellh) for h in
       ["Модель", "Цена/ролик<br/>8s 1080p (no-audio)", "9:16", "3:4<br/>(WB 810x1080)",
        "i2v", "Макс. длина", "Разрешение", "Доступность (агрегаторы)"]]

# (модель, цена, 9:16, 3:4, i2v, макс.длина, разрешение, агрегаторы, флаг-строки)
rows = [
 ("MiniMax Hailuo 2.3 Fast Pro", "$0.33 — но 1080p только 6s", YES, "да (из фото)", YES,
  "1080p=6s; 768p=10s", "1080p (6s) / 768p", "fal.ai, Replicate, Kie.ai", "dq"),
 ("Seedance 1.0 Pro Fast  [основная]", "$0.389  (per-sec, точный 8s)", YES,
  '<font name="ARB" color="#157f3b">да (нативно)</font>', YES, ">=8s, per-sec", "1080p (нативно)",
  "fal.ai, Replicate, Kie.ai", "rec"),
 ("Google Veo 3.1 Lite", "$0.40  (no-audio)", YES, NO + " &rarr; кроп", YES,
  "8s (для 1080p)", "1080p", "fal.ai, Replicate, Kie.ai", ""),
 ("Kling 2.6 Pro", "$0.56  (per-sec)", YES, "API: 16:9/9:16/1:1", YES,
  "3-15s, per-sec", "1080p", "fal.ai, Replicate, Kie.ai, Polza", "res"),
 ("Kling 3.0 Std", "$0.672  (per-sec)", YES, NO + " (пресет)", YES,
  "3-15s, per-sec", "1080p", "fal.ai, Kie.ai, Polza", ""),
 ("Runway Gen-4 Turbo", "~$0.70  (720p + апскейл)", YES, "да (нативно, 720p)", YES,
  "5s / 10s (8s нет)", "720p нативно (1080p апскейл)", "Runway API, Segmind, Kie.ai", "res"),
 ("Wan 2.5", "$0.80 (Kie) / $1.20 (fal)", YES, "треб. проверки", YES,
  "до 10s", "1080p (нативно)", "Kie.ai, fal.ai, Replicate, Polza", ""),
 ("Google Veo 3.1 Fast", "$0.80  (no-audio)", YES, NO + " &rarr; кроп", YES,
  "8s (для 1080p)", "1080p", "fal.ai, Replicate, Kie.ai", "res"),
 ("Kling 3.0 Pro", "$0.896  (per-sec)", YES, NO + " (пресет)", YES,
  "3-15s, per-sec", "1080p", "fal.ai, Kie.ai", ""),
 ("Seedance 1.0 Pro", "$0.97 - 1.17", YES,
  '<font name="ARB" color="#157f3b">да (нативно)</font>', YES, ">=8s, per-sec", "1080p (нативно)",
  "fal.ai, Replicate, Kie.ai", "res"),
 ("Google Veo 3.1 Std", "$1.60  (no-audio)", YES, NO + " &rarr; кроп", YES,
  "8s (для 1080p)", "1080p", "fal.ai, Replicate, Kie.ai", ""),
]

data = [hdr]
for m, price, v916, v34, i2v, ln, res, agg, flag in rows:
    mp = Paragraph(("<b>%s</b>" % m) if flag in ("rec",) else m, st_cell)
    data.append([mp, Paragraph(price, st_cell), Paragraph(v916, st_cellc),
                 Paragraph(v34, st_cellc), Paragraph(i2v, st_cellc),
                 Paragraph(ln, st_cell), Paragraph(res, st_cell), Paragraph(agg, st_cell)])

cw = [108, 92, 34, 78, 30, 86, 96, 138]
ct = Table(data, colWidths=cw, repeatRows=1)
cstyle = [
    ("BACKGROUND", (0,0), (-1,0), NAVY),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("GRID", (0,0), (-1,-1), 0.4, LINE),
    ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
]
# подсветка строк по флагам
for i, r in enumerate(rows, start=1):
    flag = r[8]
    if flag == "dq":
        cstyle += [("BACKGROUND", (0,i), (-1,i), colors.HexColor("#f3eceb")),
                   ("TEXTCOLOR", (0,i), (-1,i), GREY)]
    elif flag == "rec":
        cstyle += [("BACKGROUND", (0,i), (-1,i), RECBG),
                   ("LINEBEFORE", (0,i), (0,i), 2.4, GREEN)]
    elif i % 2 == 0:
        cstyle += [("BACKGROUND", (0,i), (-1,i), STRIPE)]
ct.setStyle(TableStyle(cstyle))
story += [ct, Spacer(1, 5)]
story += [P("Строка Hailuo 2.3 Fast Pro показана серой: ценник самый низкий, но 1080p у всей линейки "
            "Hailuo капается 6 секундами — ролик 8s @1080p недостижим. Подробнее в разделе 3.", st_small)]

# ====== 3. ОПРОВЕРЖЕНИЯ / ПОДВОДНЫЕ КАМНИ ======
story += [NextPageTemplate("P"), PageBreak()]
story += [H1("3. Подводные камни и опровержения")]
story += [P("Что выявила adversarial-перепроверка — эти пункты ломают «наивный» выбор по одному ценнику.", st_small)]

warn_items = [
 ("[ОПРОВЕРГНУТО]", "Hailuo не делает 8s @1080p",
  "По всей линейке MiniMax Hailuo (02 и 2.3) 1080p ограничен 6 секундами; 10s доступны только в 768p. "
  "Дешёвый $0.33 (Hailuo 2.3 Fast Pro) — это 6-сек 1080p ролик. Под спецификацию 8s @1080p не подходит. "
  "Подтверждено fal.ai, Replicate, theplanettools.ai, wavespeed.ai."),
 ("[ОПРОВЕРГНУТО]", "Veo 3.1 не поддерживает нативную 3:4",
  "Ресёрч заявил 3:4 на fal Veo 3.1 Lite — верификатор опроверг: официальный API enum = {auto, 16:9, 9:16}, "
  "3:4 отсутствует. Для WB-обложки 3:4 (810x1080) на Veo нужен кроп/пэд из 9:16. Цена при этом подтверждена."),
 ("[ОПРОВЕРГНУТО]", "Runway Gen-4 нативно только 720p",
  "Gen-4 Turbo и Gen-4 Video выдают 720p; 1080p — только отдельным upscale-пассом (+2 cr/s). Длительности "
  "лишь 5s/10s (8s нет, биллинг по 10s). Внутрикадровый текст/логотипы/ценники часто плывут — реролы. "
  "Эффективная цена и риск выше, чем кажется по $0.50."),
 ("[ВНИМАНИЕ]", "3:4 (формат обложки WB) — общий дефицит",
  "Нативную 3:4 в 1080p даёт по сути только Seedance (1.0 Pro / Pro Fast). У Wan 2.2 и Runway 3:4 есть, но 720p. "
  "У Kling 1080p-эндпоинты — лишь 16:9/9:16/1:1. Вывод: для WB 3:4 либо Seedance нативно, либо пайплайн "
  "9:16 &rarr; центр-кроп/пэд &rarr; 810x1080."),
 ("[ВНИМАНИЕ]", "Seedance 1.0 Pro — расхождение цены на fal",
  "Страница fal противоречива: один блок $2.5/1M токенов (&rarr; $0.97/8s), другой $3.0/1M (&rarr; ~$1.17/8s). "
  "Цену Pro считать диапазоном $0.97-1.17. Pro Fast ($0.389) этим не затронут — подтверждён точно."),
 ("[ВНИМАНИЕ]", "Polza дороже на целевой спеке + цены в RUB",
  "Polza per-clip в рублях по примерному курсу 80-90 руб/$. Для 8s @1080p Polza дороже fal в 2-7 раз "
  "(Kling 3.0 ~$0.94-1.69, Seedance-2 ~$2.61). Оправдана как платёжный слой для рос. карт, не как ценовой бэкенд."),
 ("[ВНИМАНИЕ]", "ToS на перепродажу + лимиты прямого API",
  "Потребительские подписки (Kling, MiniMax, Runway, Google AI) дают лицензию на использование вывода, но не на "
  "перепродажу генераций как-сервиса. Veo в preview запрещает коммерческое использование + требует SynthID-watermark. "
  "Прямой Kling API: депозит $4200/3 мес + лимит ~5 конкурентных задач. Сверять resale-клаузы письменно."),
]
for tg, title, body in warn_items:
    inner = [
        Paragraph("%s &nbsp; <b>%s</b>" % (tag(tg), title), S("wt", fontSize=10, leading=13)),
        Spacer(1, 2),
        Paragraph(body, S("wb", fontSize=8.8, leading=12, alignment=TA_JUSTIFY)),
    ]
    box = Table([[inner]], colWidths=[PW - 2*M])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), WARNBG),
        ("BOX", (0,0), (-1,-1), 0.6, WARNBR),
        ("LEFTPADDING", (0,0), (-1,-1), 9), ("RIGHTPADDING", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LINEBEFORE", (0,0), (0,-1), 2.6, RED if tg=="[ОПРОВЕРГНУТО]" else AMBER),
    ]))
    story += [box, Spacer(1, 6)]

# ====== 4. ЭКОНОМИКА ======
story += [PageBreak()]
story += [H1("4. Экономика: точки безубыточности")]
story += [P("Допущения: ролик 8s / 1080p / no-audio / i2v. PAYG-якорь = Seedance 1.0 Pro Fast на fal = "
            "<b>$0.389/ролик</b>. Прямой пакет = Kling official API (единственный реальный prepay в данных): "
            "30 000 units / $4200 / 3 мес = <b>$1400/мес обязательный пол</b>, Pro 0.8 unit/s &rarr; 8s = 6.4 units = "
            "<b>$0.896/ролик</b> маржинально; лимит ~5 конкурентных задач. Подписка = n/a (ToS запрещает перепродажу).")]

ehdr = [Paragraph(h, st_ecellh) for h in
        ["Объём / мес", "Pay-as-you-go<br/>(fal · Seedance Pro Fast)", "Прямой пакет<br/>(Kling official API)",
         "Подписка", "Дешевле"]]
edata = [ehdr,
 [Paragraph("50", st_ecellc), Paragraph("<b>$19.45</b><br/>(50 &times; $0.389)", st_ecell),
  Paragraph("$1400/мес (пол)<br/>факт. usage $44.80 &rarr; $28.00/ролик", st_ecell),
  Paragraph("n/a (ToS)", st_ecellc), Paragraph("PAYG ~<b>72&times;</b>", st_ecellc)],
 [Paragraph("200", st_ecellc), Paragraph("<b>$77.80</b><br/>(200 &times; $0.389)", st_ecell),
  Paragraph("$1400/мес (пол)<br/>usage $179.20 &lt; пол", st_ecell),
  Paragraph("n/a (ToS)", st_ecellc), Paragraph("PAYG ~<b>18&times;</b>", st_ecellc)],
 [Paragraph("1000", st_ecellc), Paragraph("<b>$389.00</b><br/>(1000 &times; $0.389)", st_ecell),
  Paragraph("$1400/мес (пол)<br/>usage $896 &lt; пол; и $896 &gt; $389", st_ecell),
  Paragraph("n/a (ToS)", st_ecellc), Paragraph("PAYG ~<b>3.6&times;</b>", st_ecellc)],
]
et = Table(edata, colWidths=[62, 150, 165, 70, 70], repeatRows=1)
et.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("GRID", (0,0), (-1,-1), 0.4, LINE),
    ("BACKGROUND", (0,2), (-1,2), STRIPE),
    ("BACKGROUND", (4,1), (4,-1), RECBG),
    ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
]))
story += [et, Spacer(1, 8)]
story += [H2("Анализ точек безубыточности")]
story += [P("Чтобы prepay-пакет Kling обогнал PAYG, нужно пройти <b>оба</b> порога — а с самой дешёвой "
            "PAYG-моделью достижим максимум один, поэтому пакет не выигрывает никогда на этой спеке:")]
for b in [
  "<b>Маржинальный порог (per-clip):</b> Kling Pkg1 = $0.896/ролик, Pkg3 = $0.717/ролик — оба выше PAYG $0.389. "
  "Кроссовера нет ни при каком объёме (даже против более дорогой Kling 3.0 Std $0.672 пакет дороже).",
  "<b>Порог фикс-затрат (пол $1400/мес):</b> PAYG дойдёт до $1400 лишь на ~3599 роликов/мес. Но ёмкость "
  "Pkg1 = 1562 ролика/мес, и потолок конкурентности (5 задач) упирается задолго до этого.",
]:
    story += [P("• " + b, st_bullet)]
story += [P("<b>Итог:</b> кроссовер ~ никогда (нужно &gt;3599 роликов/мес <i>и</i> согласие на цену за ролик в "
            "1.8-2.3&times; выше PAYG, против лимита 5 конкурентных задач). Prepay/прямой пакет оправдан только при "
            "гарантированном, очень высоком и стабильном объёме — противоположность профилю MarquisPro "
            "«единицы-сотни, непредсказуемо». Подписка исключена из расчёта (ToS).")]

# ====== 5. РЕКОМЕНДАЦИЯ ======
story += [PageBreak()]
story += [H1("5. Итоговая рекомендация")]

rec_inner = [
  Paragraph("%s &nbsp; Основная модель: Seedance 1.0 Pro Fast (через fal.ai) — $0.389/ролик" % tag("[РЕКОМЕНДАЦИЯ]"),
            S("rh", fontName="ARB", fontSize=11, leading=14, textColor=NAVY)),
  Spacer(1, 3),
]
for b in [
  "Самый дешёвый <b>валидный</b> путь 8s/1080p в датасете (дешевле только дисквалифицированный Hailuo).",
  "<b>Нативная 3:4</b> (810x1080 WB-обложка) — без «налога на кроп», в отличие от Veo/Kling.",
  "Нативная 9:16, image-to-video — ядро модели, качество «very close to Pro», объёмное ощущение фото товара.",
  "Per-second биллинг &rarr; ровно 8s без округления; нет наценки за вертикаль; нативно немой вывод (нет аудио-надбавки).",
  "Очень хорошая стабильность с 1-й попытки на статичном фото товара с мягким движением.",
]:
    rec_inner += [Paragraph("• " + b, S("rb", fontSize=9, leading=12.5, leftIndent=8))]
recbox = Table([[rec_inner]], colWidths=[PW - 2*M])
recbox.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), RECBG), ("BOX", (0,0), (-1,-1), 0.6, RECBR),
    ("LINEBEFORE", (0,0), (0,-1), 2.8, GREEN),
    ("LEFTPADDING", (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
]))
story += [recbox, Spacer(1, 10)]

story += [H2("Резервные модели (fallback для реролов / hero-товаров)")]
for b in [
  "<b>Kling 2.6 Pro — $0.56.</b> Проверенный флагман i2v, высокая стабильность product-анимации. "
  "Для WB 3:4 — генерить 9:16 + кроп (API без 3:4).",
  "<b>Kling 3.0 Std — $0.672.</b> Лучшая стабильность линейки Kling (3D-реконструкция, меньше варпинга) — "
  "для hero-карточек, где важна максимальная чистота.",
  "<b>Veo 3.1 Lite — $0.40.</b> Дешёвая альтернатива, но 3:4 только кропом (нативный 3:4 опровергнут) и "
  "стабильность средняя (выше доля реролов).",
]:
    story += [P("• " + b, st_bullet)]
story += [H2("Резерв по качеству (премиум-карточки)")]
story += [P("Seedance 1.0 Pro $0.97-1.17 или Veo 3.1 Fast $0.80 (no-audio) — когда клиент платит за "
            "«премиум-ролик» и важно минимум реролов.", st_body)]
story += [H2("Стратегия закупки и guardrails")]
for b in [
  "<b>Pay-as-you-go через fal.ai.</b> Чистая переменная стоимость: $0 в простое, линейно растёт со спросом, нет депозита под риском.",
  "<b>Polza</b> оставить только если приём оплаты рос. картами — жёсткое требование (платёжный слой), не как ценовой бэкенд.",
  "Всегда генерировать <b>audio-off</b> (на Veo/Kling вдвое дешевле; звук в обложке не нужен).",
  "Для <b>WB 3:4</b> — Seedance нативно; для остальных пайплайн 9:16 &rarr; центр-кроп/пэд &rarr; 810x1080.",
  "Для <b>Ozon</b> — первые 8 сек без звука уже выполняются; следить за MP4/H.264 и весом под лимиты площадки.",
  "<b>Не использовать Hailuo</b> под эту спеку (1080p только 6s). <b>Runway</b> — только если нужен нативный 3:4 720p + осознанный upscale.",
]:
    story += [P("• " + b, st_bullet)]

# ====== 6. ИСТОЧНИКИ ======
story += [PageBreak()]
story += [H1("6. Источники (ключевые, дата чтения 2026-06-03)")]
src = [
 ("Seedance", "fal.ai/models/.../seedance/v1/pro/fast/image-to-video; blog.segmind.com/seedance-pricing-comparison; geelark.com/blog/seedance-pro-vs-pro-fast-vs-lite; akool.com/blog-posts/seedance-1-0-cost-guide"),
 ("Kling", "fal.ai/models/.../kling-video/v2.6/pro/image-to-video; fal.ai/models/.../kling-video/v3/standard/image-to-video; replicate.com/kwaivgi/kling-v2.6; fal.ai/learn/tools/seedance-2-0-vs-kling-3-0"),
 ("Veo", "ai.google.dev/gemini-api/docs/pricing; ai.google.dev/gemini-api/docs/video; fal.ai/models/.../veo3.1/(image-to-video|fast|lite); costgoat.com/pricing/google-veo"),
 ("Wan", "fal.ai/models/.../wan-25-preview/image-to-video; kie.ai/wan-2-5; imagine.art/blogs/wan-ai-pricing-guide; wavespeed.ai/models/alibaba/wan-2.2/i2v-plus-1080p"),
 ("Runway", "docs.dev.runwayml.com/guides/pricing; runwayml.com/pricing; segmind.com/models/runway-gen4-turbo/pricing"),
 ("Hailuo", "fal.ai/models/.../minimax/hailuo-2.3(-fast)/pro/image-to-video; platform.minimax.io/docs/guides/pricing-video; theplanettools.ai/tools/minimax-hailuo-2-3; replicate.com/minimax/hailuo-02"),
 ("Агрегаторы", "polza.ai/models/*; fal.ai/pricing; kie.ai/v3-api-pricing; replicate.com/pricing; atlascloud.ai/blog/guides/cheapest-ai-video-generation-api-2026; evolink.ai/blog/best-ai-video-generation-models-2026-pricing-guide"),
]
sdata = [[Paragraph("Семейство", st_ecellh), Paragraph("URL (дата чтения 2026-06-03)", st_ecellh)]]
for fam, urls in src:
    sdata.append([Paragraph("<b>%s</b>" % fam, S("sf", fontSize=8.4, leading=11)),
                  Paragraph(urls, S("su", fontSize=7.8, leading=10.5))])
stb = Table(sdata, colWidths=[80, PW - 2*M - 80], repeatRows=1)
stb.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY), ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("GRID", (0,0), (-1,-1), 0.4, LINE),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, STRIPE]),
    ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
]))
story += [stb, Spacer(1, 8)]
story += [P("Примечание: цены на видео-AI меняются за недели. Перед прайс-решением и биллингом клиентов "
            "пересверять на живых страницах провайдеров. Цифры [ТРЕБУЕТ ПРОВЕРКИ] — RUB по примерному курсу "
            "или страница за antibot.", st_small)]

# build (multiBuild для оглавления с номерами страниц)
doc.multiBuild(story)
print("OK:", OUT)
