# src/modules/page_experience.py
"""
Detects page experience signals:
- Missing HTTPS (http:// URLs)
- Intrusive interstitials (popup patterns)
- Missing security headers (as hints)
"""

from bs4 import BeautifulSoup
from urllib.parse import urlparse


def run(context):
    pages = context["pages"]

    issues = []
    suggestions = {}

    for page in pages:
        url = page.get("url")
        html = page.get("html")
        headers = page.get("headers", {})

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")
        page_suggestions = []

        # ─────────────────────────────────────
        # Non-HTTPS URL
        # ─────────────────────────────────────
        if url.startswith("http://"):
            issues.append({"url": url, "issue": "not_https"})
            page_suggestions.append({
                "type": "force_https",
                "action": "redirect_http_to_https_or_update_base_url"
            })

        # ─────────────────────────────────────
        # Internal links using http://
        # ─────────────────────────────────────
        http_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if a["href"].startswith("http://")
        ]
        if http_links:
            issues.append({
                "url": url,
                "issue": "insecure_internal_links",
                "links": http_links[:5]
            })
            page_suggestions.append({
                "type": "fix_insecure_links",
                "action": "replace http:// with https:// in all internal links"
            })

        # ─────────────────────────────────────
        # Intrusive interstitials (common popup patterns)
        # ─────────────────────────────────────
        popup_indicators = soup.find_all(
            lambda tag: tag.get("class") and any(
                cls in " ".join(tag.get("class", [])).lower()
                for cls in ["popup", "modal", "overlay", "interstitial", "cookie-banner"]
            )
        )
        if popup_indicators:
            issues.append({
                "url": url,
                "issue": "intrusive_interstitial_detected",
                "elements": len(popup_indicators)
            })
            page_suggestions.append({
                "type": "review_interstitial",
                "action": "ensure_popup_is_not_blocking_content_on_mobile"
            })

        # ─────────────────────────────────────
        # Missing X-Frame-Options / CSP (from response headers)
        # ─────────────────────────────────────
        if headers:
            if "x-frame-options" not in {k.lower() for k in headers}:
                issues.append({"url": url, "issue": "missing_x_frame_options"})
                page_suggestions.append({
                    "type": "add_security_header",
                    "header": "X-Frame-Options: SAMEORIGIN",
                    "action": "configure_in_server_or_cdn"
                })

        # ─────────────────────────────────────
        # Images served over HTTP on HTTPS page
        # ─────────────────────────────────────
        if url.startswith("https://"):
            mixed_imgs = [
                img["src"] for img in soup.find_all("img", src=True)
                if img["src"].startswith("http://")
            ]
            if mixed_imgs:
                issues.append({
                    "url": url,
                    "issue": "mixed_content_images",
                    "images": mixed_imgs[:5]
                })
                page_suggestions.append({
                    "type": "fix_mixed_content",
                    "action": "replace http:// image src with https://"
                })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }
