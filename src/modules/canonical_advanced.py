# src/modules/canonical_advanced.py
"""
Advanced canonical link analysis:
- Detects missing canonical tags
- Flags self-canonical mismatches
- Detects pagination issues (missing rel=prev/next)
- Flags cross-domain canonical conflicts
"""

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


def run(context):
    pages = context["pages"]
    urls = context.get("urls", [])

    issues = []
    suggestions = {}

    for page in pages:
        url = page.get("url")
        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")
        page_suggestions = []

        canonical = soup.find("link", rel="canonical")

        # ─────────────────────────────────────
        # Missing canonical tag
        # ─────────────────────────────────────
        if not canonical:
            issues.append({"url": url, "issue": "missing_canonical"})
            page_suggestions.append({
                "type": "add_canonical",
                "tag": f'<link rel="canonical" href="{url}">',
                "action": "inject_into_head"
            })
        else:
            href = canonical.get("href", "").strip()

            # ─────────────────────────────────────
            # Self-canonical mismatch
            # ─────────────────────────────────────
            normalized_url = url.rstrip("/")
            normalized_href = href.rstrip("/")

            if normalized_href and normalized_href != normalized_url:
                parsed_url = urlparse(url)
                parsed_href = urlparse(href)

                if parsed_href.netloc and parsed_href.netloc != parsed_url.netloc:
                    # Cross-domain canonical — flag it
                    issues.append({
                        "url": url,
                        "issue": "cross_domain_canonical",
                        "canonical": href
                    })
                    page_suggestions.append({
                        "type": "confirm_or_fix_canonical",
                        "action": f"verify cross-domain canonical points to: {href}"
                    })
                else:
                    issues.append({
                        "url": url,
                        "issue": "canonical_mismatch",
                        "expected": url,
                        "found": href
                    })
                    page_suggestions.append({
                        "type": "fix_canonical",
                        "tag": f'<link rel="canonical" href="{url}">',
                        "action": "replace_existing_canonical"
                    })

        # ─────────────────────────────────────
        # Pagination: look for prev/next links in numbered URLs
        # ─────────────────────────────────────
        is_paginated = _is_paginated_url(url)
        if is_paginated:
            has_prev = soup.find("link", rel="prev")
            has_next = soup.find("link", rel="next")

            if not has_prev and not has_next:
                issues.append({"url": url, "issue": "missing_pagination_links"})
                page_suggestions.append({
                    "type": "add_pagination_hints",
                    "action": "inject rel=prev and rel=next into head"
                })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _is_paginated_url(url):
    import re
    return bool(re.search(r"[?&/](page|p|pg)=?\d+", url, re.IGNORECASE))
