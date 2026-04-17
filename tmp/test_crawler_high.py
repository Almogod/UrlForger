"""
Direct scheduler test with sitemap seeding.
Run from UrlForge root: python -m tmp.test_crawler_high
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crawler_engine.frontier import URLFrontier
from src.crawler_engine.parser import extract_links
from src.crawler_engine.scheduler import run_workers
from src.crawler_engine.graph import CrawlGraph
from src.services.sitemap_parser import get_sitemap_urls

TARGET = "https://www.qcecuring.com/"
LIMIT = 30

async def main():
    frontier = URLFrontier(base_domain=TARGET)
    frontier.add(TARGET)
    graph = CrawlGraph()

    # Seed from sitemap (critical for SPA sites)
    sitemap_urls = get_sitemap_urls(TARGET)
    print(f"Sitemap returned {len(sitemap_urls)} URLs")
    for url in sitemap_urls[:LIMIT]:
        frontier.add(url)
    print(f"Frontier size after sitemap seed: {frontier.size()}")

    def progress(msg):
        print(f"[PROGRESS] {msg}")

    print(f"\nStarting crawl: {TARGET}, limit={LIMIT}")
    pages = await run_workers(
        frontier, extract_links, graph,
        start_url=TARGET,
        progress_callback=progress,
        limit=LIMIT,
        delay=0.3,
        concurrency=5,
        check_robots=False,
    )
    print(f"\n=== RESULT: {len(pages)} pages fetched ===")
    for p in pages[:20]:
        print(f"  {p['status']} {p['url']}")

if __name__ == "__main__":
    asyncio.run(main())
