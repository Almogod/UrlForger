# src/modules/structured_data_validator.py
"""
Validates existing JSON-LD structured data and detects new opportunities:
- Validates Article, Product, FAQ, WebPage schemas for missing required fields
- Detects FAQ opportunities (pages with Q&A-style content)
- Detects BreadcrumbList opportunities
"""

from bs4 import BeautifulSoup
import json
import re


REQUIRED_FIELDS = {
    "Article": ["headline", "datePublished", "author", "image"],
    "Product": ["name", "description", "image", "offers"],
    "FAQPage": ["mainEntity"],
    "WebPage": ["name", "url"],
    "BreadcrumbList": ["itemListElement"],
    "Organization": ["name", "url"],
}


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
        # Validate existing JSON-LD
        # ─────────────────────────────────────
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
                schema_type = data.get("@type", "")

                required = REQUIRED_FIELDS.get(schema_type, [])
                missing = [f for f in required if not data.get(f)]

                if missing:
                    issues.append({
                        "url": url,
                        "issue": "incomplete_schema",
                        "schema_type": schema_type,
                        "missing_fields": missing
                    })
                    page_suggestions.append({
                        "type": "fix_schema",
                        "schema_type": schema_type,
                        "missing_fields": missing,
                        "action": "add_missing_fields_to_existing_schema"
                    })

            except json.JSONDecodeError:
                issues.append({"url": url, "issue": "invalid_json_ld"})
                page_suggestions.append({
                    "type": "fix_json_ld",
                    "action": "correct_json_syntax_in_schema_script"
                })

        # ─────────────────────────────────────
        # FAQ opportunity detection
        # ─────────────────────────────────────
        has_faq_schema = any(
            "FAQPage" in (script.string or "")
            for script in soup.find_all("script", {"type": "application/ld+json"})
        )

        qa_pairs = _detect_qa_patterns(soup)

        if qa_pairs and not has_faq_schema:
            issues.append({"url": url, "issue": "faq_schema_opportunity"})
            faq_schema = _build_faq_schema(qa_pairs, url)
            page_suggestions.append({
                "type": "inject_faq_schema",
                "schema": faq_schema,
                "action": "inject_faq_json_ld_into_head"
            })

        # ─────────────────────────────────────
        # BreadcrumbList opportunity
        # ─────────────────────────────────────
        has_breadcrumb_schema = any(
            "BreadcrumbList" in (script.string or "")
            for script in soup.find_all("script", {"type": "application/ld+json"})
        )
        path_parts = [p for p in url.replace(domain, "").split("/") if p]

        if len(path_parts) >= 2 and not has_breadcrumb_schema:
            breadcrumb_schema = _build_breadcrumb_schema(path_parts, domain, url)
            page_suggestions.append({
                "type": "inject_breadcrumb_schema",
                "schema": breadcrumb_schema,
                "action": "inject_breadcrumb_json_ld_into_head"
            })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _detect_qa_patterns(soup):
    """Detect question-answer pairs from common HTML patterns."""
    qa_pairs = []

    # Pattern 1: dt/dd pairs
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            qa_pairs.append({
                "question": dt.get_text(strip=True),
                "answer": dd.get_text(strip=True)
            })

    # Pattern 2: headings followed by paragraphs that look like questions
    for h in soup.find_all(["h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        if text.endswith("?"):
            next_p = h.find_next_sibling("p")
            if next_p:
                qa_pairs.append({
                    "question": text,
                    "answer": next_p.get_text(strip=True)
                })

    return qa_pairs[:10]  # cap at 10


def _build_faq_schema(qa_pairs, url):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": q["answer"]
                }
            }
            for q in qa_pairs
        ]
    }


def _build_breadcrumb_schema(path_parts, domain, url):
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": domain}]
    current = domain
    for i, part in enumerate(path_parts, 2):
        current = f"{current}/{part}"
        items.append({
            "@type": "ListItem",
            "position": i,
            "name": part.replace("-", " ").title(),
            "item": current
        })
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items
    }
