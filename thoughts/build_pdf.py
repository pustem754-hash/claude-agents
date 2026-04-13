# -*- coding: utf-8 -*-
"""Build PDF report: Top-10 realtors in Kazan (rentals)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Fonts (Cyrillic-capable) ---
pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", "C:/Windows/Fonts/arialbi.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold",
                   italic="Arial-Italic", boldItalic="Arial-BoldItalic")

# --- Colors ---
BRAND = colors.HexColor("#1E3A8A")      # deep blue
ACCENT = colors.HexColor("#D97706")     # amber
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#D1D5DB")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")

# --- Styles ---
styles = getSampleStyleSheet()

def S(name, **kwargs):
    base = dict(fontName="Arial", fontSize=10, leading=14, textColor=TEXT)
    base.update(kwargs)
    return ParagraphStyle(name, **base)

cover_title = S("CoverTitle", fontName="Arial-Bold", fontSize=26, leading=32,
                alignment=TA_CENTER, textColor=BRAND)
cover_sub = S("CoverSub", fontSize=14, leading=20, alignment=TA_CENTER, textColor=MUTED)
cover_date = S("CoverDate", fontSize=12, alignment=TA_CENTER, textColor=ACCENT,
               fontName="Arial-Bold")

h1 = S("H1", fontName="Arial-Bold", fontSize=18, leading=24, textColor=BRAND,
       spaceBefore=6, spaceAfter=10)
h2 = S("H2", fontName="Arial-Bold", fontSize=14, leading=20, textColor=BRAND,
       spaceBefore=10, spaceAfter=6)
h3 = S("H3", fontName="Arial-Bold", fontSize=13, leading=18, textColor=ACCENT,
       spaceBefore=8, spaceAfter=4)
body = S("Body", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=4)
bullet = S("Bullet", fontSize=10, leading=14, leftIndent=12, spaceAfter=2)
label = S("Label", fontName="Arial-Bold", fontSize=10, leading=14, textColor=BRAND)
note = S("Note", fontSize=9, leading=12, textColor=MUTED, fontName="Arial-Italic")
source = S("Source", fontSize=9, leading=12, leftIndent=10, spaceAfter=1)

# --- Page frame: header/footer ---
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    # footer
    canvas.drawString(15 * mm, 10 * mm, "Топ-10 агентств недвижимости Казани — аренда")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"стр. {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
    canvas.restoreState()

def on_cover(canvas, doc):
    canvas.saveState()
    # top band
    canvas.setFillColor(BRAND)
    canvas.rect(0, A4[1] - 40 * mm, A4[0], 40 * mm, stroke=0, fill=1)
    # bottom band
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, A4[0], 20 * mm, stroke=0, fill=1)
    canvas.restoreState()

# --- Data ---
AGENCIES = [
    {
        "rank": 1, "name": "Этажи",
        "subtitle": "Федеральная риэлторская компания",
        "phone": "+7 (843) 210-07-70",
        "site": "kazan.etagi.com",
        "address": "Казань, ул. Чистопольская, 69, ТРЦ «Миллениум», 2 этаж",
        "rating": "4.9 / 5 (2ГИС, 1 187 отзывов); 4.9 / 5 (собств. сайт, 17 875 отзывов)",
        "spec": "Долгосрочная аренда квартир (раздел realty_rent), купля-продажа, ипотека, новостройки, коммерческая недвижимость. Член Российской гильдии риэлторов.",
        "reviews": "Хвалят за крупнейшую базу в Казани (37–50 тыс. ₽/мес), юридическое сопровождение, гарантийный сертификат, скорость подбора. Жалобы — на неоднородное качество отдельных агентов.",
    },
    {
        "rank": 2, "name": "Самолет Плюс Казань",
        "subtitle": "Сервис квартирных решений «под ключ»",
        "phone": "+7 (962) 564-10-44 / 8 800 301-62-10",
        "site": "samoletplus.ru/kazan",
        "address": "Казань, ул. Декабристов, 102; доп. офис — Сибирский тракт, 13",
        "rating": "4.9 / 5 (2ГИС, 354 оценки); 4.97 (markakachestva.ru)",
        "spec": "70+ услуг в одной экосистеме: аренда, купля-продажа, ипотека, страхование, дизайн, ремонт. Быстрорастущая федеральная сеть.",
        "reviews": "Хвалят за профессионализм, оперативность, полное сопровождение сделок, работу со сложными кейсами. Единичные жалобы на коммуникацию конкретных агентов.",
    },
    {
        "rank": 3, "name": "Мегалит",
        "subtitle": "На рынке Казани с 2004 года",
        "phone": "+7 (843) 555-55-53",
        "site": "ooomegalit.ru",
        "address": "Казань, пр. Ямашева, 61Б",
        "rating": "4.9 / 5 (2ГИС, 143 оценки); 4.8 / 5 (151 оценка, агрегатор)",
        "spec": "Жилая и коммерческая недвижимость, аренда квартир и комнат (469 объявлений), купля-продажа, консультации.",
        "reviews": "Клиенты отдельно отмечают работу риэлторов по сдаче квартир в аренду. Хвалят профессионализм и грамотное сопровождение. Жалобы — на отдельных менеджеров.",
    },
    {
        "rank": 4, "name": "ФЛЭТ",
        "subtitle": "Крупнейшее АН Казани, с 2003 года",
        "phone": "+7 (843) 567-10-00; 231-80-20; 231-84-74",
        "site": "anflat.ru",
        "address": "Казань, ул. Спартаковская, 2, оф. 212/231 (+ 5 офисов: Казань, Зеленодольск, Волжск)",
        "rating": "4.7 / 5 (2ГИС, 496 отзывов); №1 в Вахитовском р-не, №2 по Казани (2024)",
        "spec": "Отдельный раздел anflat.ru/rent/ — долгосрочная аренда квартир, комнат, домов, коммерции. Для собственника сдача квартиры — БЕСПЛАТНО, без комиссии.",
        "reviews": "Хвалят за большую базу арендного жилья, продажу выше ожиданий, курирование на всех этапах. Жалобы — на нарушение договорённостей отдельными риэлторами.",
    },
    {
        "rank": 5, "name": "Альтера",
        "subtitle": "Казань, Москва, СПб, Сочи — с 2015 года",
        "phone": "+7 (843) 203-26-20; +7 (927) 496-80-60",
        "site": "alteraestate.ru (+ altera-arenda.ru)",
        "address": "Казань, ул. Чистопольская, 85; пр. Ибрагимова, 63; пр. А. Камалеева, 32",
        "rating": "4.95 / 5 (markakachestva.ru); 3.1 / 5 (Zoon, смешанные)",
        "spec": "Продажа, покупка, аренда недвижимости. Отдельный поддомен altera-arenda.ru по аренде. На рынке 10+ лет.",
        "reviews": "Хвалят за подробное ведение сделки, быстрый сбор документов, помощь в одобрении ипотеки. Жалобы — риэлтор мог «забыть» о клиенте (до 2 мес. без связи).",
    },
    {
        "rank": 6, "name": "Перспектива 24",
        "subtitle": "Крупнейший в РФ реестр объектов, федеральная сеть",
        "phone": "+7 (843) 208-68-68; +7 (843) 240-77-51",
        "site": "kazan.perspektiva24.com",
        "address": "Казань, ул. Лево-Булачная, 24/20; пр. Ямашева, 69",
        "rating": "~4.5 / 5 (Фламп / 2ГИС); смешанные сотруднические отзывы",
        "spec": "Продажа и аренда, дистанционные сделки, крупнейший в РФ реестр объектов недвижимости.",
        "reviews": "Клиенты пишут, что агенты подбирают квартиру за 2–3 недели. Жалобы — на агрессивный sales-подход, серые условия найма (со стороны сотрудников).",
    },
    {
        "rank": 7, "name": "Центральное агентство недвижимости (ЦАН)",
        "subtitle": "На рынке с 2000 года",
        "phone": "+7 (843) 253-17-77",
        "site": "centragent.ru",
        "address": "Казань, ул. Шуртыгина, 3, оф. 35/1",
        "rating": "4.9 / 5 (markakachestva.ru); Топ-15 агентств Казани (народный рейтинг 2021)",
        "spec": "Раздел centragent.ru/services/rent/ — «ежемесячный доход с недвижимости без лишних забот». Купля-продажа, обмен, ипотека, юр. сопровождение.",
        "reviews": "Клиенты отмечают индивидуальный подход, сильную юридическую базу, корректное оформление договоров аренды. Критика — средние темпы подбора арендаторов на неликвид.",
    },
    {
        "rank": 8, "name": "TATNED",
        "subtitle": "50 специалистов, с 2010 года",
        "phone": "нет данных (форма на сайте, уточняется через 2ГИС)",
        "site": "tatned.tatre.ru",
        "address": "Казань, ул. Меридианная, 1 (Ново-Савиновский р-н); доп. — ул. Четаева, 28, 2 этаж",
        "rating": "4.5+ / 5 (Яндекс.Карты, Yell)",
        "spec": "Долгосрочная аренда квартир с документальным сопровождением, аренда и продажа коммерческой недвижимости, строительство коттеджей. Партнёр крупнейших застройщиков и банков Татарстана.",
        "reviews": "Хвалят за прозрачность сделок, профессионализм, умение слушать клиента, сопровождение в сжатые сроки. Значимых негативных отзывов в открытых источниках не найдено.",
    },
    {
        "rank": 9, "name": "Las Vegas (Лас Вегас)",
        "subtitle": "Агентство элитной недвижимости, с 2012 года",
        "phone": "+7 (929) 725-77-99; +7 (937) 626-77-99",
        "site": "anlasvegas.ru",
        "address": "Казань, ул. Адоратского, 2Б, ЖК «Ривьера», оф. 303; филиал — Сибирский тракт, 34к4",
        "rating": "4.7 / 5 (Yell, Zoon)",
        "spec": "АРЕНДА ЭЛИТНЫХ КВАРТИР В КАЗАНИ — ядро бизнеса. Также продажа премиум и бизнес-класса в Казани, Москве, СПб, Сочи.",
        "reviews": "Хвалят за большую закрытую базу элитного жилья, конфиденциальность, постоянное повышение квалификации сотрудников. Комиссия выше среднего (характерно для премиум-сегмента).",
    },
    {
        "rank": 10, "name": "Недвижимость и Закон",
        "subtitle": "АН + юридические услуги, с 2010 года",
        "phone": "+7 (843) 212-20-12",
        "site": "kzn-urist.ru",
        "address": "Казань, ул. Рихарда Зорге, 66В, ЖК «Олимп», 3 этаж",
        "rating": "4.55 / 5 (markakachestva.ru)",
        "spec": "Долгосрочная аренда квартир, коммерческая и загородная недвижимость, управление инвестициями, ремонт. Сильная правовая поддержка.",
        "reviews": "Положительные кейсы долгосрочной аренды в Московском районе, подбор за несколько дней. Благодарности за быстрые продажи (2 недели). Жалобы — задержки показов.",
    },
]

OBSERVATIONS = [
    "Лидеры по аренде — ФЛЭТ и Этажи: крупнейшие базы арендных объектов; у ФЛЭТ сдача квартиры для собственника без комиссии.",
    "Лучший сервис «под ключ» — Самолет Плюс (70+ услуг в одной экосистеме).",
    "Премиум-сегмент — Las Vegas: лидер элитной аренды в Казани.",
    "Юридическая устойчивость — Недвижимость и Закон, ЦАН: сильная правовая поддержка сделок.",
    "Типичная комиссия за аренду в Казани: 50–120% от месячной ставки для арендатора; для собственника у крупных игроков (ФЛЭТ) — бесплатно.",
    "Альтернативы без агентств: Яндекс.Аренда, Циан, МирКвартир, kzn.bezposrednikov.ru — прямая аренда от собственника.",
]

SOURCES = [
    ("ТОП-10 агентств недвижимости Казани 2025 — KP.RU", "https://www.kp.ru/russia/kazan/luchshie-agentstva-nedvizhimosti/"),
    ("ТОП-10 лучших агентств — kazanecc.ru", "https://kazanecc.ru/agentstva-nedvizhimosti-kazan/"),
    ("6 лучших агентств недвижимости Казани — markakachestva.ru", "https://markakachestva.ru/amenities/5083-luchshie-agentstva-nedvizhimosti-kazani-rejting.html"),
    ("Рейтинг агентств недвижимости Казани — ratingfirmporemontu.ru", "https://kazan.ratingfirmporemontu.ru/agentstva-nedvizhimosti/"),
    ("Агентства недвижимости в Казани — Yell.ru", "https://www.yell.ru/kazan/top/agentstva-nedvizhimosti/"),
    ("Агентства недвижимости Казани — DomClick", "https://agencies.domclick.ru/agencies/respublika-tatarstan-gorod-kazan"),
    ("Этажи — kazan.etagi.com", "https://kazan.etagi.com/"),
    ("Самолет Плюс — samoletplus.ru/kazan", "https://samoletplus.ru/kazan/"),
    ("Мегалит — ooomegalit.ru", "https://www.ooomegalit.ru/"),
    ("ФЛЭТ — anflat.ru", "https://anflat.ru/"),
    ("Альтера — alteraestate.ru", "https://alteraestate.ru/"),
    ("Перспектива 24 — kazan.perspektiva24.com", "https://kazan.perspektiva24.com/"),
    ("ЦАН — centragent.ru", "https://centragent.ru/"),
    ("TATNED — tatned.tatre.ru", "https://tatned.tatre.ru/"),
    ("Las Vegas — anlasvegas.ru", "https://anlasvegas.ru/"),
    ("Недвижимость и Закон — kzn-urist.ru", "https://kzn-urist.ru/"),
    ("Циан — аренда в Казани", "https://kazan.cian.ru/snyat-kvartiru/"),
    ("Яндекс Аренда — Казань", "https://arenda.yandex.ru/kazan/arendatoru/"),
]

# --- Build ---
out = r"C:\Users\Пользователь\OneDrive\Документы\claude-agents\thoughts\kazan-realtors-top10.pdf"
doc = SimpleDocTemplate(
    out, pagesize=A4,
    leftMargin=18 * mm, rightMargin=18 * mm,
    topMargin=20 * mm, bottomMargin=18 * mm,
    title="Топ-10 риелторов и агентств недвижимости Казани — аренда",
    author="Claude Code",
)

story = []

# Cover
story.append(Spacer(1, 55 * mm))
story.append(Paragraph("Топ-10 риелторов и агентств<br/>недвижимости Казани", cover_title))
story.append(Spacer(1, 6 * mm))
story.append(Paragraph("Аренда квартир — лучшие компании рынка", cover_sub))
story.append(Spacer(1, 35 * mm))
story.append(Paragraph("Отчёт от 12 апреля 2026 г.", cover_date))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph(
    "Источники рейтингов: 2ГИС, Яндекс.Карты, Zoon, Yell, Фламп,<br/>отраслевые агрегаторы markakachestva.ru и KP.RU",
    note))
story.append(PageBreak())

# Intro
story.append(Paragraph("О подборке", h1))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
story.append(Paragraph(
    "Рынок Казани насчитывает более 550 агентств недвижимости. "
    "В подборку вошли крупнейшие и наиболее рейтинговые компании с явно "
    "представленным направлением АРЕНДЫ (отдельный раздел на сайте, "
    "отдельный отдел или заявленная специализация). Сортировка — по "
    "совокупному рейтингу и популярности.",
    body))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Там, где данные не удалось верифицировать, указано «нет данных». "
    "Рейтинги актуальны на апрель 2026 г. и могут меняться.",
    note))

# Summary table
story.append(Spacer(1, 10))
story.append(Paragraph("Сводная таблица", h2))

table_data = [[
    Paragraph("<b>#</b>", body),
    Paragraph("<b>Агентство</b>", body),
    Paragraph("<b>Рейтинг</b>", body),
    Paragraph("<b>Телефон</b>", body),
    Paragraph("<b>Сайт</b>", body),
]]
for a in AGENCIES:
    table_data.append([
        Paragraph(str(a["rank"]), body),
        Paragraph(a["name"], body),
        Paragraph(a["rating"].split(";")[0], body),
        Paragraph(a["phone"].split(";")[0].split("/")[0].strip(), body),
        Paragraph(a["site"], body),
    ])

tbl = Table(table_data, colWidths=[10*mm, 45*mm, 45*mm, 35*mm, 39*mm], repeatRows=1)
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
    ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(tbl)
story.append(PageBreak())

# Cards
story.append(Paragraph("Подробные карточки агентств", h1))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

def card(a):
    # Header row: rank + name
    header = Table(
        [[Paragraph(f'<font color="white" size="14"><b>{a["rank"]}</b></font>', body),
          Paragraph(f'<font color="#1E3A8A" size="13"><b>{a["name"]}</b></font><br/>'
                    f'<font color="#4B5563" size="9">{a["subtitle"]}</font>', body)]],
        colWidths=[12*mm, 160*mm]
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRAND),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
    ]))

    rows = [
        ("Телефон", a["phone"]),
        ("Сайт", a["site"]),
        ("Адрес", a["address"]),
        ("Рейтинг", a["rating"]),
        ("Специализация", a["spec"]),
        ("Отзывы", a["reviews"]),
    ]
    info_data = []
    for lbl, val in rows:
        info_data.append([
            Paragraph(f'<b>{lbl}</b>', body),
            Paragraph(val, body),
        ])
    info = Table(info_data, colWidths=[30*mm, 142*mm])
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

    return KeepTogether([header, info, Spacer(1, 8)])

for a in AGENCIES:
    story.append(card(a))

story.append(PageBreak())

# Observations
story.append(Paragraph("Ключевые наблюдения", h1))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
for i, o in enumerate(OBSERVATIONS, 1):
    story.append(Paragraph(f"<b>{i}.</b> {o}", bullet))
    story.append(Spacer(1, 2))

story.append(Spacer(1, 10))

# Sources
story.append(Paragraph("Источники", h1))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
for title, url in SOURCES:
    story.append(Paragraph(
        f'• {title} — <font color="#1E3A8A"><u>{url}</u></font>',
        source
    ))

# Disclaimer
story.append(Spacer(1, 14))
story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
story.append(Paragraph(
    "Отчёт подготовлен 12 апреля 2026 г. Данные собраны из открытых источников "
    "(2ГИС, Яндекс.Карты, Zoon, Yell, Фламп, официальные сайты агентств). "
    "Перед заключением договора рекомендуется уточнять актуальные условия, "
    "комиссии и контакты напрямую у агентства.",
    note))


# Build with page templates
class _Doc(SimpleDocTemplate):
    def handle_pageBegin(self):
        self._handle_pageBegin()

doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
print(f"OK: {out}")
