# src/modules/mobile_seo.py
"""
Detects mobile SEO issues:
- Missing viewport meta tag
- Touch elements too small
- Font sizes below 16px
- Horizontal overflow risk
"""

from bs4 import BeautifulSoup
import re


MIN_FONT_SIZE = 16  # px
MIN_TOUCH_TARGET = 44  # px (Apple / Google recommendation)


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
        # Missing viewport meta
        # ─────────────────────────────────────
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            issues.append({"url": url, "issue": "missing_viewport"})
            page_suggestions.append({
                "type": "add_viewport",
                "tag": '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "action": "inject_into_head"
            })
        else:
            content = viewport.get("content", "")
            if "width=device-width" not in content:
                issues.append({"url": url, "issue": "invalid_viewport"})
                page_suggestions.append({
                    "type": "fix_viewport",
                    "tag": '<meta name="viewport" content="width=device-width, initial-scale=1">',
                    "action": "replace_existing_viewport"
                })

        # ─────────────────────────────────────
        # Small font sizes in inline styles
        # ─────────────────────────────────────
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            match = re.search(r"font-size\s*:\s*(\d+)px", style)
            if match:
                size = int(match.group(1))
                if size < MIN_FONT_SIZE:
                    issues.append({
                        "url": url,
                        "issue": "small_font_size",
                        "size": size,
                        "tag": str(tag)[:100]
                    })
                    page_suggestions.append({
                        "type": "fix_font_size",
                        "action": f"increase inline font-size from {size}px to {MIN_FONT_SIZE}px"
                    })

        # ─────────────────────────────────────
        # Small touch targets (buttons/links with explicit size)
        # ─────────────────────────────────────
        for tag in soup.find_all(["a", "button"]):
            style = tag.get("style", "")
            w_match = re.search(r"width\s*:\s*(\d+)px", style)
            h_match = re.search(r"height\s*:\s*(\d+)px", style)
            if w_match and h_match:
                w = int(w_match.group(1))
                h = int(h_match.group(1))
                if w < MIN_TOUCH_TARGET or h < MIN_TOUCH_TARGET:
                    issues.append({
                        "url": url,
                        "issue": "small_touch_target",
                        "element": tag.name,
                        "width": w,
                        "height": h
                    })
                    page_suggestions.append({
                        "type": "fix_touch_target",
                        "action": f"set min-width/min-height to {MIN_TOUCH_TARGET}px on {tag.name}"
                    })

        # ─────────────────────────────────────
        # Horizontal scroll risk (fixed-width elements wider than viewport)
        # ─────────────────────────────────────
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            match = re.search(r"width\s*:\s*(\d+)px", style)
            if match:
                w = int(match.group(1))
                if w > 768:
                    issues.append({
                        "url": url,
                        "issue": "horizontal_overflow_risk",
                        "width": w
                    })
                    page_suggestions.append({
                        "type": "fix_fixed_width",
                        "action": f"replace width:{w}px with max-width:100% or responsive units"
                    })
                    break  # only flag once per page

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }
