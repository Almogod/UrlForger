import os
from datetime import datetime
from xml.sax.saxutils import escape

MAX_URLS_PER_SITEMAP = 50000

def stream_sitemap(pages, filename):
    """
    Streams sitemap to disk to handle large sites with minimal memory.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" ')
        f.write('xmlns:xhtml="http://www.w3.org/1999/xhtml" ')
        f.write('xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" ')
        f.write('xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n')
        
        for page in pages:
            f.write('  <url>\n')
            f.write(f'    <loc>{escape(page["url"])}</loc>\n')
            f.write(f'    <lastmod>{datetime.utcnow().date().isoformat()}</lastmod>\n')
            
            # Hreflang
            for hr in page.get("hreflangs", []):
                f.write(f'    <xhtml:link rel="{escape(hr["rel"])}" hreflang="{escape(hr["hreflang"])}" href="{escape(hr["href"])}"/>\n')
                
            # Images
            for img in page.get("images", []):
                f.write('    <image:image>\n')
                f.write(f'      <image:loc>{escape(img["loc"])}</image:loc>\n')
                if img.get("title"):
                    f.write(f'      <image:title>{escape(img["title"])}</image:title>\n')
                f.write('    </image:image>\n')
                
            # Videos
            for vid in page.get("videos", []):
                f.write('    <video:video>\n')
                f.write(f'      <video:content_loc>{escape(vid["content_loc"])}</video:content_loc>\n')
                f.write(f'      <video:title>{escape(vid.get("title", "Video"))}</video:title>\n')
                f.write(f'      <video:thumbnail_loc>{escape(page["url"])}</video:thumbnail_loc>\n')
                f.write(f'      <video:description>{escape(vid.get("description", "Video on page"))}</video:description>\n')
                f.write('    </video:video>\n')
                
            f.write('  </url>\n')
            
        f.write('</urlset>')

def generate_sitemaps(pages_iterator, base_url, output_prefix="sitemap"):
    """
    Enterprise-grade sitemap generator.
    Handles streaming input to support millions of URLs.
    """
    sitemap_files = []
    chunk_index = 1
    current_chunk = []
    
    for page in pages_iterator:
        current_chunk.append(page)
        if len(current_chunk) >= MAX_URLS_PER_SITEMAP:
            filename = f"{output_prefix}_{chunk_index}.xml"
            stream_sitemap(current_chunk, filename)
            sitemap_files.append(filename)
            current_chunk = []
            chunk_index += 1
            
    if current_chunk:
        filename = f"{output_prefix}_{chunk_index}.xml"
        stream_sitemap(current_chunk, filename)
        sitemap_files.append(filename)
        
    if len(sitemap_files) > 1:
        index_file = f"{output_prefix}_index.xml"
        create_sitemap_index(sitemap_files, base_url, index_file)
        return [index_file] + sitemap_files
        
    return sitemap_files

def create_sitemap_index(sitemap_files, base_url, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for sf in sitemap_files:
            f.write('  <sitemap>\n')
            f.write(f'    <loc>{base_url.rstrip("/")}/{sf}</loc>\n')
            f.write(f'    <lastmod>{datetime.utcnow().date().isoformat()}</lastmod>\n')
            f.write('  </sitemap>\n')
        f.write('</sitemapindex>')
