import asyncio

from .frontier import URLFrontier
from .parser import extract_links
from .scheduler import run_workers


def crawl(start_url, limit=200):

    frontier = URLFrontier()
    frontier.add(start_url)

    pages = asyncio.run(
        run_workers(frontier, extract_links, limit=limit)
    )

    return pages
