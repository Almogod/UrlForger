# src/engine.py

from src.audit import generate_audit_report
from src.fixer import fix_urls
from src.modules.sitemap import fix_sitemap
from src.modules.canonical import fix_canonical_tags
from src.modules.robots import fix_robots


def run_engine(pages, clean_urls, domain):
    audit = generate_audit_report(pages, clean_urls)

    plan = build_fix_plan(audit)

    context = {
        "urls": clean_urls,
        "domain": domain,
        "pages": pages
    }

    # Apply modular fixes
    if "sitemap" in plan:
        context["urls"] = fix_sitemap(context["urls"])

    if "canonical" in plan:
        context["urls"] = fix_canonical_tags(context)

    if "robots" in plan:
        fix_robots(context)

    # Generic URL fixes
    context["urls"] = fix_urls(context["urls"])

    return {
        "audit": audit,
        "plan": plan,
        "fixed_urls": context["urls"]
    }


def build_fix_plan(audit):
    plan = []

    if audit["issues"]["duplicates"]:
        plan.append("sitemap")

    if audit["issues"]["has_query_params"]:
        plan.append("sitemap")

    if audit["issues"]["not_https"]:
        plan.append("sitemap")

    # Future modules
    plan.append("canonical")
    plan.append("robots")

    return plan