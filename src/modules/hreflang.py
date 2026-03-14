# src/modules/hreflang.py
"""
Detects multi-language sites missing hreflang tags.
Generates correct hreflang tag sets based on detected language variants.
"""

from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re


# Common locale patterns in URLs (e.g. /en/, /fr/, /es-mx/)
LOCALE_PATTERN = re.compile(r"/([a-z]{2}(?:-[a-zA-Z]{2,4})?)/", re.IGNORECASE)
LANG_IN_DOMAIN = re.compile(r"^(en|fr|de|es|it|pt|nl|ru|zh|ja|ko|ar)\.", re.IGNORECASE)


def run(context):
    pages = context["pages"]
    domain = context.get("domain", "")

    issues = []
    suggestions = {}

    # Group pages by their detected locale
    locale_map = {}
    for page in pages:
        url = page.get("url")
        if not url:
            continue
        locale = _detect_locale(url)
        if locale:
            if locale not in locale_map:
                locale_map[locale] = []
            locale_map[locale].append(url)

    # Only process if we detect multiple locales
    if len(locale_map) < 2:
        return {"issues": [], "suggestions": {}}

    # Build the full hreflang tag set
    hreflang_tags = []
    for locale, urls in locale_map.items():
        for url in urls:
            hreflang_tags.append(
                f'<link rel="alternate" hreflang="{locale}" href="{url}">'
            )
    # x-default: point to first English URL or first overall
    default_url = locale_map.get("en", list(locale_map.values())[0])[0]
    hreflang_tags.append(f'<link rel="alternate" hreflang="x-default" href="{default_url}">')

    for page in pages:
        url = page.get("url")
        html = page.get("html")
        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        existing_hreflang = soup.find_all("link", rel="alternate", hreflang=True)
        if not existing_hreflang:
            issues.append({
                "url": url,
                "issue": "missing_hreflang",
                "detected_locales": list(locale_map.keys())
            })
            suggestions[url] = [{
                "type": "add_hreflang",
                "tags": hreflang_tags,
                "action": "inject_all_hreflang_tags_into_head"
            }]

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _detect_locale(url):
    """Extract locale code from URL path or subdomain."""
    parsed = urlparse(url)

    # Subdomain-based (e.g. fr.example.com)
    subdomain_match = LANG_IN_DOMAIN.match(parsed.netloc)
    if subdomain_match:
        return subdomain_match.group(1).lower()

    # Path-based (e.g. /en/ or /fr-ca/)
    path_match = LOCALE_PATTERN.search(parsed.path)
    if path_match:
        return path_match.group(1).lower()

    return None
