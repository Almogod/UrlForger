# src/modules/open_graph.py
"""
Detects missing Open Graph and Twitter Card meta tags.
Auto-generates them from existing meta/title/image tags.
"""

from bs4 import BeautifulSoup


def run(context):
    pages = context["pages"]
    domain = context.get("domain", "")

    issues = []
    suggestions = {}

    for page in pages:
        url = page.get("url")
        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")
        page_suggestions = []

        # ─────────────────────────────────────
        # Extract existing values
        # ─────────────────────────────────────
        title = _get_meta(soup, "og:title") or _get_title(soup)
        description = _get_meta(soup, "og:description") or _get_meta(soup, "description") or ""
        image = _get_meta(soup, "og:image") or _get_first_image(soup)

        # ─────────────────────────────────────
        # Open Graph checks
        # ─────────────────────────────────────
        og_required = {
            "og:title": title,
            "og:description": description[:155] if description else "",
            "og:url": url,
            "og:type": "website",
            "og:image": image or ""
        }

        for prop, content in og_required.items():
            if not _get_meta(soup, prop):
                issues.append({"url": url, "issue": f"missing_{prop.replace(':', '_')}"})
                if content:
                    page_suggestions.append({
                        "type": "add_og_tag",
                        "tag": f'<meta property="{prop}" content="{content}">',
                        "action": "inject_into_head"
                    })

        # ─────────────────────────────────────
        # Twitter Card checks
        # ─────────────────────────────────────
        twitter_required = {
            "twitter:card": "summary_large_image",
            "twitter:title": title or "",
            "twitter:description": description[:155] if description else "",
            "twitter:image": image or ""
        }

        for name, content in twitter_required.items():
            if not _get_meta(soup, name):
                issues.append({"url": url, "issue": f"missing_{name.replace(':', '_')}"})
                if content:
                    page_suggestions.append({
                        "type": "add_twitter_tag",
                        "tag": f'<meta name="{name}" content="{content}">',
                        "action": "inject_into_head"
                    })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _get_meta(soup, key):
    """Get content from either property= or name= meta tag."""
    tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
    if tag:
        return tag.get("content", "").strip()
    return None


def _get_title(soup):
    tag = soup.find("title")
    if tag:
        return tag.text.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.text.strip()
    return ""


def _get_first_image(soup):
    img = soup.find("img", src=True)
    if img:
        return img["src"]
    return ""
