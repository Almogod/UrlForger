def fix_sitemap(urls):
    cleaned = set()

    for url in urls:
        url = url.split("?")[0]

        if url.startswith("http://"):
            url = url.replace("http://", "https://")

        cleaned.add(url.rstrip("/"))

    return list(cleaned)
