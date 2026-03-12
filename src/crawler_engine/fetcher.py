import httpx

async def fetch(client, url):

    try:
        r = await client.get(url)

        return {
            "url": url,
            "status": r.status_code,
            "html": r.text,
            "headers": r.headers
        }

    except Exception:
        return None
