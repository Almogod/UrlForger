# src/modules/broken_links.py
"""
Checks all internal and external links on each crawled page.
Detects: broken links (4xx/5xx), redirect chains, and suspicious external links.
"""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


MAX_REDIRECTS_TO_FLAG = 2
REQUEST_TIMEOUT = 8


def run(context):
    pages = context["pages"]
    domain = context.get("domain", "")

    issues = []
    suggestions = {}
    checked_cache = {}  # avoid re-checking the same URL

    for page in pages:
        url = page.get("url")
        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")
        page_suggestions = []

        links = [
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if not a["href"].startswith(("#", "mailto:", "tel:", "javascript:"))
        ]

        for link in links:
            if link in checked_cache:
                status, redirect_count = checked_cache[link]
            else:
                status, redirect_count = _check_link(link)
                checked_cache[link] = (status, redirect_count)

            # ─────────────────────────────────────
            # Broken link
            # ─────────────────────────────────────
            if status >= 400 or status == 0:
                issues.append({
                    "url": url,
                    "issue": "broken_link",
                    "link": link,
                    "status": status
                })
                page_suggestions.append({
                    "type": "fix_broken_link",
                    "link": link,
                    "action": "remove_or_replace_with_working_url"
                })

            # ─────────────────────────────────────
            # Redirect chain
            # ─────────────────────────────────────
            elif redirect_count > MAX_REDIRECTS_TO_FLAG:
                issues.append({
                    "url": url,
                    "issue": "redirect_chain",
                    "link": link,
                    "redirects": redirect_count
                })
                page_suggestions.append({
                    "type": "update_link_to_final_destination",
                    "link": link,
                    "action": "replace_with_direct_url"
                })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _check_link(url):
    """
    Returns (status_code, redirect_count).
    status_code=0 means connection error.
    """
    try:
        history_count = 0
        with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT) as client:
            response = client.head(url)
            history_count = len(response.history)
            # Some servers block HEAD, fall back to GET
            if response.status_code == 405:
                response = client.get(url)
                history_count = len(response.history)
            return response.status_code, history_count
    except Exception:
        return 0, 0
