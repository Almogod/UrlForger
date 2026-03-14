import asyncio
import httpx
from .fetcher import fetch


async def run_workers(frontier, parser, graph, limit=200, concurrency=10):

    results = []

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

                async with semaphore:
                    page = await fetch(client, url)

                if not page:
                    continue

                results.append(page)

                links = parser(page["html"], page["url"])

                for link in links:
                    graph.add_edge(page["url"], link)
                    frontier.add(link)

        workers = [worker() for _ in range(concurrency)]

        await asyncio.gather(*workers)

    return results
