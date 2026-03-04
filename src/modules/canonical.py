def fix_canonical_tags(context):
    # Placeholder (real fix later via HTML rewriting / CMS)
    urls = context["urls"]

    # For now, just ensure uniqueness
    return list(set(urls))
