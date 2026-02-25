import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def crawl_js(start_url, limit=200):
    visited = set()
    to_visit = set([start_url])
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while to_visit and len(visited) < limit:
            url = to_visit.pop()

            if url in visited:
                continue

            try:
                await page.goto(url, timeout=15000, wait_until="networkidle")
                html = await page.content()

                visited.add(url)

                results.append({
                    "url": url,
                    "status": 200,
                    "html": html
                })

                soup = BeautifulSoup(html, "lxml")

                for link in soup.find_all("a", href=True):
                    new_url = urljoin(url, link["href"])

                    if urlparse(new_url).netloc == urlparse(start_url).netloc:
                        to_visit.add(new_url)

            except:
                continue

        await browser.close()

    return results


def crawl_js_sync(start_url, limit=200):
    return asyncio.run(crawl_js(start_url, limit))
