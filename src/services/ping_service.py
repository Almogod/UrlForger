import httpx
from src.utils.logger import logger

async def ping_search_engines(sitemap_url: str):
    """
    Submits the sitemap to Google and Bing.
    """
    engines = [
        {"name": "Google", "url": f"http://www.google.com/ping?sitemap={sitemap_url}"},
        {"name": "Bing", "url": f"http://www.bing.com/ping?sitemap={sitemap_url}"}
    ]
    
    async with httpx.AsyncClient() as client:
        for engine in engines:
            try:
                r = await client.get(engine["url"], timeout=10)
                if r.status_code == 200:
                    logger.info(f"Successfully pinged {engine['name']} with {sitemap_url}")
                else:
                    logger.warning(f"Failed to ping {engine['name']}. Status: {r.status_code}")
            except Exception as e:
                logger.error(f"Error pinging {engine['name']}: {e}")
