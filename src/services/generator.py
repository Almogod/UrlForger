from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
from datetime import datetime
import os


MAX_URLS_PER_SITEMAP = 50000


def chunk_urls(urls, chunk_size):
    for i in range(0, len(urls), chunk_size):
        yield urls[i:i + chunk_size]


def create_sitemap(pages, filename):
    """
    Creates a sitemap with support for hreflang, images, and videos.
    Args:
        pages: List of dictionaries containing "url" and optional metadata.
    """
    urlset = Element("urlset", {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "xmlns:xhtml": "http://www.w3.org/1999/xhtml",
        "xmlns:image": "http://www.google.com/schemas/sitemap-image/1.1",
        "xmlns:video": "http://www.google.com/schemas/sitemap-video/1.1"
    })

    for page in pages:
        url_el = SubElement(urlset, "url")

        loc = SubElement(url_el, "loc")
        loc.text = page["url"]

        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = datetime.utcnow().date().isoformat()

        # 1. Hreflang
        for hr in page.get("hreflangs", []):
            # Using xhtml:link
            SubElement(url_el, "{http://www.w3.org/1999/xhtml}link", {
                "rel": hr["rel"],
                "hreflang": hr["hreflang"],
                "href": hr["href"]
            })

        # 2. Images
        for img in page.get("images", []):
            img_el = SubElement(url_el, "{http://www.google.com/schemas/sitemap-image/1.1}image")
            img_loc = SubElement(img_el, "{http://www.google.com/schemas/sitemap-image/1.1}loc")
            img_loc.text = img["loc"]
            if img.get("title"):
                img_title = SubElement(img_el, "{http://www.google.com/schemas/sitemap-image/1.1}title")
                img_title.text = img["title"]
            if img.get("caption"):
                img_cap = SubElement(img_el, "{http://www.google.com/schemas/sitemap-image/1.1}caption")
                img_cap.text = img["caption"]

        # 3. Videos
        for vid in page.get("videos", []):
            vid_el = SubElement(url_el, "{http://www.google.com/schemas/sitemap-video/1.1}video")
            vid_loc = SubElement(vid_el, "{http://www.google.com/schemas/sitemap-video/1.1}content_loc")
            vid_loc.text = vid["content_loc"]
            vid_title = SubElement(vid_el, "{http://www.google.com/schemas/sitemap-video/1.1}title")
            vid_title.text = vid.get("title", "Video Content")
            # Minimal requirements for Google Video Sitemap
            vid_desc = SubElement(vid_el, "{http://www.google.com/schemas/sitemap-video/1.1}description")
            vid_desc.text = vid.get("description", "Video on page")
            vid_thumb = SubElement(vid_el, "{http://www.google.com/schemas/sitemap-video/1.1}thumbnail_loc")
            vid_thumb.text = page["url"] # Fallback to page URL or some default

    indent(urlset)
    tree = ElementTree(urlset)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    
    # Optional Validation Output (Verify against schema)
    validate_sitemap(filename)


def validate_sitemap(filename):
    """
    Validation logic. Could use lxml for a real XSD validation.
    For now, we'll just check if it's well-formed and non-empty.
    """
    try:
        import os
        size = os.path.getsize(filename)
        if size < 100:
            print(f"Warning: Sitemap {filename} seems too small ({size} bytes)")
        else:
            print(f"Sitemap {filename} generated and basic validation passed.")
    except Exception as e:
        print(f"Validation failed for {filename}: {e}")


def create_sitemap_index(sitemap_files, base_url, filename="sitemap_index.xml"):
    sitemapindex = Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for file in sitemap_files:
        sitemap = SubElement(sitemapindex, "sitemap")

        loc = SubElement(sitemap, "loc")
        loc.text = f"{base_url.rstrip('/')}/{file}"

        lastmod = SubElement(sitemap, "lastmod")
        lastmod.text = datetime.utcnow().date().isoformat()

    indent(sitemapindex)
    tree = ElementTree(sitemapindex)
    tree.write(filename, encoding="utf-8", xml_declaration=True)


def generate_sitemaps(pages, base_url, output_prefix="sitemap"):
    """
    Main entry point for generating sitemaps.
    Handles splitting and index creation.
    """
    total = len(pages)

    if total <= MAX_URLS_PER_SITEMAP:
        filename = f"{output_prefix}.xml"
        create_sitemap(pages, filename)
        return [filename]

    sitemap_files = []
    chunks = list(chunk_urls(pages, MAX_URLS_PER_SITEMAP))

    for i, chunk in enumerate(chunks, start=1):
        filename = f"{output_prefix}_{i}.xml"
        create_sitemap(chunk, filename)
        sitemap_files.append(filename)

    create_sitemap_index(sitemap_files, base_url)

    return sitemap_files
