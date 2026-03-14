def build_fix_plan(audit):

    issues = audit.get("issues", {})

    plan = []

    if issues.get("duplicates"):
        plan.append("sitemap")

    if issues.get("has_query_params"):
        plan.append("sitemap")

    if issues.get("not_https"):
        plan.append("sitemap")

    if issues.get("missing_title") or issues.get("missing_description"):
        plan.append("meta")

    # Core modules always included
    plan.append("internal_links")
    plan.append("crawl_budget")
    plan.append("canonical")
    plan.append("robots")
    plan.append("schema")
    plan.append("image_seo")
    plan.append("core_web_vitals")
    plan.append("keyword_gap")

    # New performance and advanced modules
    plan.append("page_speed")
    plan.append("heading_structure")
    plan.append("open_graph")
    plan.append("canonical_advanced")
    plan.append("broken_links")
    plan.append("content_quality")
    plan.append("mobile_seo")
    plan.append("page_experience")
    plan.append("structured_data_validator")
    plan.append("hreflang")

    return plan
