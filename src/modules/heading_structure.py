# src/modules/heading_structure.py
"""
Validates heading hierarchy across all crawled pages.
Detects skipped levels, missing H2s, and improper structure.
"""

from bs4 import BeautifulSoup


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

        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        heading_levels = [int(h.name[1]) for h in headings]

        # ─────────────────────────────────────
        # No H1
        # ─────────────────────────────────────
        if 1 not in heading_levels:
            issues.append({"url": url, "issue": "missing_h1"})
            page_suggestions.append({
                "type": "add_h1",
                "action": "generate_h1_from_title_or_slug"
            })

        # ─────────────────────────────────────
        # Multiple H1s
        # ─────────────────────────────────────
        if heading_levels.count(1) > 1:
            issues.append({"url": url, "issue": "multiple_h1", "count": heading_levels.count(1)})
            page_suggestions.append({
                "type": "fix_multiple_h1",
                "action": "demote_extra_h1_to_h2"
            })

        # ─────────────────────────────────────
        # Skipped heading levels (e.g. H1 → H3)
        # ─────────────────────────────────────
        for i in range(1, len(heading_levels)):
            prev = heading_levels[i - 1]
            curr = heading_levels[i]
            if curr > prev + 1:
                issues.append({
                    "url": url,
                    "issue": "skipped_heading_level",
                    "from": f"h{prev}",
                    "to": f"h{curr}"
                })
                page_suggestions.append({
                    "type": "fix_heading_skip",
                    "action": f"change h{curr} to h{prev + 1}"
                })

        # ─────────────────────────────────────
        # No H2 sub-sections (thin structure signal)
        # ─────────────────────────────────────
        if heading_levels and 2 not in heading_levels:
            issues.append({"url": url, "issue": "no_h2_subsections"})
            page_suggestions.append({
                "type": "add_h2_sections",
                "action": "generate_h2_subheadings_from_content"
            })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }
