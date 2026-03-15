import asyncio
import httpx
import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from .fetcher import fetch


async def run_workers(frontier, parser, graph, limit=200, concurrency=10, delay=1.0, check_robots=True):
    results = []
    rp = None
    
    if check_robots:
        try:
            # We assume the domain is the netloc of the first URL in frontier
            first_url = frontier.peek() if hasattr(frontier, 'peek') else next(iter(frontier.visited), None)
            if first_url:
                parsed = urlparse(first_url)
                robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                # Note: read() is blocking, but robots.txt is usually small.
                # In a more robust system, we would fetch this asynchronously.
                rp.read()
        except Exception as e:
            print(f"Warning: Could not fetch robots.txt: {e}")

    async with httpx.AsyncClient(
        timeout=30, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    ) as client:

        semaphore = asyncio.Semaphore(concurrency)

        async def worker():
            while frontier.size() and len(results) < limit:
                url = frontier.get()
                if not url:
                    return

                # Robots.txt check
                if rp and not rp.can_fetch("*", url):
                    print(f"Skipping {url} due to robots.txt")
                    continue

                async with semaphore:
                    # Rate limiting
                    if delay > 0:
                        await asyncio.sleep(delay)
                    
                    page = await fetch(client, url)

                if not page:
                    continue

                results.append(page)

                # Parser now returns a dict
                extracted = parser(page["html"], page["url"])
                
                # Update page data with extra metadata
                page["hreflangs"] = extracted.get("hreflangs", [])
                page["images"] = extracted.get("images", [])
                page["videos"] = extracted.get("videos", [])

                for link in extracted.get("links", []):
                    graph.add_edge(page["url"], link)
                    frontier.add(link)

        workers = [worker() for _ in range(concurrency)]
        await asyncio.gather(*workers)

    return results
