import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from src.utils.security import is_safe_url
from src.utils.logger import logger


def _fetch_sitemap(url: str, timeout: int = 10) -> str | None:
    """Fetch a sitemap URL and return its text content, or None on failure."""
    try:
        if not is_safe_url(url):
            return None
        r = httpx.get(url, timeout=timeout, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SitemapBot/1.0)"
        })
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.warning(f"Could not fetch sitemap {url}: {e}")
    return None


def _parse_sitemap(text: str, base_url: str, depth: int = 0, max_depth: int = 3) -> list[str]:
    """
    Parse a sitemap XML and return all page URLs.
    Handles both sitemapindex (recursive) and urlset documents.
    """
    if depth > max_depth:
        return []

    urls = []
    try:
        soup = BeautifulSoup(text, "xml")

        # Sitemap index — contains references to other sitemaps
        sitemap_tags = soup.find_all("sitemap")
        if sitemap_tags:
            for tag in sitemap_tags:
                loc = tag.find("loc")
                if loc:
                    sub_url = loc.text.strip()
                    if not sub_url.endswith((".xml", ".xml.gz", ".txt")):
                        continue  # Skip non-sitemap entries
                    sub_text = _fetch_sitemap(sub_url)
                    if sub_text:
                        urls.extend(_parse_sitemap(sub_text, sub_url, depth + 1, max_depth))
        else:
            # Regular urlset — contains actual page URLs
            for loc in soup.find_all("loc"):
                url = loc.text.strip()
                parsed = urlparse(url)
                # Only include http/https, non-sitemap URLs
                if parsed.scheme.startswith("http") and not url.endswith((".xml", ".xml.gz")):
                    urls.append(url)

    except Exception as e:
        logger.warning(f"Error parsing sitemap: {e}")

    return urls


def get_sitemap_urls(domain: str, limit: int = 5000) -> list[str]:
    """
    Fetch and fully expand a site's sitemap, returning up to `limit` page URLs.
    Tries: /sitemap.xml, /sitemap_index.xml, /sitemap-index.xml, robots.txt Sitemap directive.
    """
    base = domain.rstrip("/")
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # Candidate sitemap locations
    candidates = [
        f"{base}/sitemap.xml",
        f"{origin}/sitemap.xml",
        f"{origin}/sitemap_index.xml",
        f"{origin}/sitemap-index.xml",
    ]

    # Also check robots.txt for Sitemap: directive
    try:
        robots_text = _fetch_sitemap(f"{origin}/robots.txt")
        if robots_text:
            for line in robots_text.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url not in candidates:
                        candidates.insert(0, sitemap_url)  # Prioritise robots.txt hint
    except Exception:
        pass

    all_urls = []
    seen = set()

    for candidate in candidates:
        text = _fetch_sitemap(candidate)
        if not text:
            continue
        found = _parse_sitemap(text, candidate)
        for url in found:
            if url not in seen:
                seen.add(url)
                all_urls.append(url)
        if all_urls:
            logger.info(f"Sitemap seeded {len(all_urls)} URLs from {candidate}")
            break  # Stop at first successful sitemap

    return all_urls[:limit]
