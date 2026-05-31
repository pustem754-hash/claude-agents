"""Deeper inspect: find date/author markup on tass.com."""
import asyncio
from playwright.async_api import async_playwright

URL = "https://tass.com/politics/2117115"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(locale="en-US")
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)

        js = r"""
        () => {
          const out = {};
          // all meta
          out.all_meta = [];
          document.querySelectorAll('meta').forEach(m => {
            const k = m.getAttribute('property') || m.getAttribute('name') || m.getAttribute('itemprop');
            const v = m.getAttribute('content');
            if (k && v) out.all_meta.push({k, v: v.slice(0,160)});
          });
          // date-like text: find all elements with text matching a date pattern
          const all = document.querySelectorAll('body *');
          const dateCandidates = [];
          all.forEach(e => {
            if (e.children.length > 0) return;
            const t = (e.textContent||'').trim();
            if (t.length > 100) return;
            if (/\d{1,2}\s+[A-Za-z]{3,9},\s+\d{1,2}:\d{2}/.test(t) ||
                /\d{4}-\d{2}-\d{2}/.test(t) ||
                /updated at/i.test(t)) {
              dateCandidates.push({
                tag: e.tagName,
                cls: e.className,
                id: e.id,
                parent: e.parentElement ? e.parentElement.tagName+'.'+e.parentElement.className : null,
                text: t.slice(0,100)
              });
            }
          });
          out.date_candidates = dateCandidates.slice(0,15);
          // .news-header children
          const hdr = document.querySelector('.news-header');
          out.news_header_html = hdr ? hdr.outerHTML.slice(0,1500) : null;
          return out;
        }
        """
        data = await page.evaluate(js)
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False)[:6000])
        await browser.close()


asyncio.run(main())
