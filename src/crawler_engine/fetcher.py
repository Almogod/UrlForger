import httpx

async def fetch(client, url):
    try:
        r = await client.get(url, follow_redirects=True)
        return {
            "url": url,
            "status": r.status_code,
            "html": r.text,
            "headers": r.headers
        }
    except httpx.ConnectError:
        return {"url": url, "status": 0, "html": "", "error": "Connection refused / Host unreachable"}
    except httpx.TimeoutException:
        return {"url": url, "status": 0, "html": "", "error": "Request timed out"}
    except httpx.HTTPStatusError as e:
        return {"url": url, "status": e.response.status_code, "html": "", "error": f"HTTP Error {e.response.status_code}"}
    except Exception as e:
        return {"url": url, "status": 0, "html": "", "error": str(e)}
