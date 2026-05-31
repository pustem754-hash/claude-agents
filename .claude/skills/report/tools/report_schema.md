# Report skill — JSON spec schemas

Both engines are **data-driven**: you hand them a JSON spec, they render the file.
Never edit the Python to inject content — only the spec changes. To change the
*look* (colors, fonts, layout), edit the engine once.

- PDF engine: `tools/build_report_pdf.py <spec.json> [out.pdf]`
- XLSX engine: `tools/build_report_xlsx.py <spec.json> [out.xlsx]`

If `[out]` is omitted, the output is written next to the spec with the matching
extension. Working examples live in `../examples/`.

---

## PDF spec (`build_report_pdf.py`)

Branded A4 PDF: cover with colored bands -> intro -> summary table -> detail
cards -> key observations -> sources, plus a per-page footer with page numbers.

**Only `title` is required.** Any other key may be omitted — the corresponding
section is simply skipped.

```jsonc
{
  // Cover + metadata
  "title":    "Топ-10 агентств недвижимости",     // REQUIRED. Big cover heading.
  "subtitle": "Аренда квартир — лучшие компании", // Cover subheading (grey).
  "date":     "12 апреля 2026 г.",                // Rendered as "Отчёт от <date>".
  "footer":   "Топ-10 агентств — аренда",          // Footer text on every page.
                                                   //   Defaults to title if absent.
  "note":     "Рейтинги могут меняться.",          // Small italic line (cover + intro).

  // Intro paragraph (section "О подборке")
  "intro":    "Абзац-введение о методологии и охвате подборки.",

  // Summary table — equal-width columns, header band, zebra rows
  "summary_table": {
    "columns": ["#", "Агентство", "Рейтинг", "Телефон", "Сайт"],
    "rows": [
      ["1", "Этажи", "4.9 / 5", "+7 (843) ...", "example.test"],
      ["2", "Самолёт Плюс", "4.9 / 5", "+7 (962) ...", "example.test"]
    ]
  },

  // Detail cards — one block each: header (rank + name + subtitle) + key/value table.
  // `fields` is an ordered object: key = label (bold, left col), value = text.
  "cards": [
    {
      "rank": 1,
      "name": "Этажи",
      "subtitle": "Федеральная риэлторская компания",
      "fields": {
        "Телефон": "+7 (843) ...",
        "Сайт": "example.test",
        "Рейтинг": "4.9 / 5",
        "Специализация": "Долгосрочная аренда, купля-продажа, ипотека."
      }
    }
  ],

  // Numbered key takeaways
  "observations": [
    "Лидеры по аренде — A и B: крупнейшие базы объектов.",
    "Премиум-сегмент — C."
  ],

  // Sources — title + optional url (url is underlined blue)
  "sources": [
    {"title": "Каталог агентств — пример", "url": "https://example.test/agencies"},
    {"title": "Без ссылки тоже можно"}
  ]
}
```

Notes:
- All text is XML-escaped automatically — `&`, `<`, `>` in your data are safe.
- Cyrillic renders via Arial (registered from `C:/Windows/Fonts`). If Arial is
  missing, the engine falls back to Helvetica (Latin only) without crashing.
- `rank` may be a number or a string.

---

## XLSX spec (`build_report_xlsx.py`)

Styled spreadsheet: title band -> optional source subtitle -> header row -> data
rows, with per-column number formats / alignment / widths, conditional
formatting, color scales, optional Summary sheet, autofilter and freeze panes.

**`columns` is required** (defines the table shape). Everything else is optional.

```jsonc
{
  "title":      "Top 50 Cryptocurrencies",        // REQUIRED. Merged title band (row 1).
  "source":     "Source: CoinGecko · USD",         // Italic subtitle (row 2). If
                                                    //   omitted, header moves up to row 2.
  "sheet_name": "Data",                            // Main sheet name (default "Data").

  // Column definitions — order defines column order (A, B, C, ...)
  "columns": [
    {"name": "#",     "width": 5,  "align": "center"},
    {"name": "Name",  "width": 22, "align": "left"},
    {"name": "Price", "width": 15, "align": "right", "number_format": "$#,##0.00"},
    {"name": "24h %", "width": 14, "align": "right", "number_format": "0.00\" %\""}
  ],
  //   name           — header text
  //   width          — column width (optional; Excel default if absent)
  //   align          — "center" | "left" | "right" (default "left")
  //   number_format  — Excel format code (optional), e.g. "$#,##0", "0.00%", "#,##0 ₽"

  // Data rows — each is an array aligned to `columns` by position.
  // Keep numbers as numbers (not strings) so formats/conditionals work.
  "rows": [
    [1, "Bitcoin",  65000.0,  2.45],
    [2, "Ethereum", 3200.5,  -1.10]
  ],

  // Conditional formatting. type "sign": green fill if >0, red fill if <0.
  // `col` is a column letter ("D") or 1-based index (4).
  "conditional": [
    {"col": "D", "type": "sign"}
  ],

  // Color scale (white -> light blue -> deep blue by magnitude) on these columns.
  "colorscale": ["C"],

  // Optional second sheet "Summary": array of [label, value] pairs.
  "summary": [
    ["Coins in report", 50],
    ["Gainers (24h)", 31],
    ["Losers (24h)", 19]
  ],

  "autofilter": true,     // add Excel autofilter over header + data (default false)
  "freeze":     "A4"      // freeze panes anchor (default: first data row, "A<n>")
}
```

Notes:
- Header lands on row 3 when `source` is present, otherwise row 2. `freeze` and
  conditional ranges are computed from the actual header position, so just set
  `freeze` to the first data cell (e.g. `"A4"` when `source` is present).
- `col` references in `conditional` / `colorscale` accept either a letter
  (`"G"`) or a 1-based index (`7`).
- Cyrillic and `₽`/`$`/`%` symbols are stored as UTF-8 and round-trip cleanly.
