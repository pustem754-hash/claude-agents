"""Inspect tass.com article markup to derive XPath selectors."""
import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://tass.com/politics/2117115",
    "https://tass.com/politics/2117113",
    "https://tass.com/politics/2117111",
]


async def inspect(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
            locale="en-US",
        )
        page = await ctx.new_page()
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)
        print(f"\n===== {url} | HTTP {resp.status} =====")

        js = r"""
        () => {
          const pick = (sel) => {
            const el = document.querySelector(sel);
            return el ? (el.outerHTML.slice(0, 220)) : null;
          };
          const out = {};
          // Title candidates
          out.h1 = Array.from(document.querySelectorAll('h1')).map(e => ({
            cls: e.className, text: (e.textContent||'').trim().slice(0,120)
          }));
          // meta tags
          const metas = ['og:title','og:description','article:published_time',
                         'article:author','author','datePublished','description'];
          out.meta = {};
          metas.forEach(m => {
            const el = document.querySelector(`meta[property="${m}"], meta[name="${m}"], meta[itemprop="${m}"]`);
            if (el) out.meta[m] = el.getAttribute('content');
          });
          // Time tags
          out.time = Array.from(document.querySelectorAll('time')).map(e => ({
            cls: e.className, dt: e.getAttribute('datetime'), text: (e.textContent||'').trim().slice(0,80)
          }));
          // article/p
          const arts = document.querySelectorAll('article');
          out.article_count = arts.length;
          out.article_cls = Array.from(arts).map(a=>a.className);
          // Paragraphs in article
          const ps = document.querySelectorAll('article p, div.text-content p, div.news-text p');
          out.p_count = ps.length;
          out.p_samples = Array.from(ps).slice(0,3).map(e=>({
            parent: e.parentElement ? e.parentElement.tagName+'.'+e.parentElement.className : null,
            cls: e.className,
            text: (e.textContent||'').trim().slice(0,120)
          }));
          // Author candidates
          out.author_candidates = [];
          document.querySelectorAll('[class*="author" i], [class*="Author"]').forEach(e=>{
            out.author_candidates.push({
              tag: e.tagName, cls: e.className, text: (e.textContent||'').trim().slice(0,100)
            });
          });
          // JSON-LD
          out.jsonld = [];
          document.querySelectorAll('script[type="application/ld+json"]').forEach(s=>{
            out.jsonld.push(s.textContent.slice(0, 500));
          });
          return out;
        }
        """
        data = await page.evaluate(js)
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False)[:6000])

        await browser.close()


async def main():
    for u in URLS[:1]:
        await inspect(u)


asyncio.run(main())
