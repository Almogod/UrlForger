# src/modules/page_speed.py
"""
Detects page speed issues: unminified assets, missing preloads,
render-blocking resources, and missing resource hints.
"""

from bs4 import BeautifulSoup
import re


MIN_JS_SIZE_TO_FLAG = 5000   # bytes (inline script)
MIN_CSS_SIZE_TO_FLAG = 2000  # bytes (inline style)


def run(context):
    pages = context["pages"]

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
        # Unminified inline JS
        # ─────────────────────────────────────
        for script in soup.find_all("script"):
            if script.get("src"):
                continue
            content = script.string or ""
            if len(content) > MIN_JS_SIZE_TO_FLAG and not _is_minified(content):
                issues.append({"url": url, "issue": "unminified_inline_js"})
                page_suggestions.append({
                    "type": "minify_inline_js",
                    "action": "minify_or_move_to_external_file"
                })
                break

        # ─────────────────────────────────────
        # Unminified inline CSS
        # ─────────────────────────────────────
        for style in soup.find_all("style"):
            content = style.string or ""
            if len(content) > MIN_CSS_SIZE_TO_FLAG and not _is_minified(content):
                issues.append({"url": url, "issue": "unminified_inline_css"})
                page_suggestions.append({
                    "type": "minify_inline_css",
                    "action": "minify_or_move_to_external_stylesheet"
                })
                break

        # ─────────────────────────────────────
        # Missing preload for LCP image
        # ─────────────────────────────────────
        images = soup.find_all("img")
        has_preload_img = any(
            link.get("rel") == ["preload"] and link.get("as") == "image"
            for link in soup.find_all("link")
        )
        if images and not has_preload_img:
            lcp_candidate = images[0].get("src", "")
            if lcp_candidate:
                issues.append({"url": url, "issue": "missing_lcp_preload"})
                page_suggestions.append({
                    "type": "add_preload",
                    "tag": f'<link rel="preload" as="image" href="{lcp_candidate}">',
                    "action": "inject_into_head"
                })

        # ─────────────────────────────────────
        # Missing dns-prefetch for external domains
        # ─────────────────────────────────────
        external_domains = set()
        for tag in soup.find_all(["script", "link", "img"], src=True):
            src = tag.get("src", "")
            if src.startswith("http") and not _is_same_domain(src, url):
                domain = _extract_domain(src)
                if domain:
                    external_domains.add(domain)

        existing_prefetch = {
            link.get("href", "")
            for link in soup.find_all("link", rel="dns-prefetch")
        }

        for domain in external_domains:
            if domain not in existing_prefetch:
                issues.append({"url": url, "issue": "missing_dns_prefetch", "domain": domain})
                page_suggestions.append({
                    "type": "add_dns_prefetch",
                    "tag": f'<link rel="dns-prefetch" href="{domain}">',
                    "action": "inject_into_head"
                })

        # ─────────────────────────────────────
        # Missing <meta charset>
        # ─────────────────────────────────────
        if not soup.find("meta", attrs={"charset": True}):
            issues.append({"url": url, "issue": "missing_charset"})
            page_suggestions.append({
                "type": "add_charset",
                "tag": '<meta charset="UTF-8">',
                "action": "inject_into_head_first"
            })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _is_minified(content):
    """Heuristic: minified code has very long lines."""
    lines = content.strip().splitlines()
    if not lines:
        return True
    avg_len = sum(len(l) for l in lines) / len(lines)
    return avg_len > 200


def _is_same_domain(src, page_url):
    from urllib.parse import urlparse
    src_domain = urlparse(src).netloc
    page_domain = urlparse(page_url).netloc
    return src_domain == page_domain


def _extract_domain(src):
    from urllib.parse import urlparse
    parsed = urlparse(src)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None
