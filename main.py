import argparse
from src.crawler_engine.crawler import crawl
from src.services.extractor import extract_metadata
from src.services.normalizer import normalize
from src.services.filter import is_valid
from src.services.generator import generate_sitemaps
from src.crawler_engine.js_crawler import crawl_js_sync
from src.utils.url_utils import build_clean_urls




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sitemap Fixer Tool")

    parser.add_argument("domain", help="Website URL (e.g., https://example.com)")
    parser.add_argument("--limit", type=int, default=200, help="Max pages to crawl")
    parser.add_argument("--output", default="sitemap.xml", help="Output file name")
    parser.add_argument("--fix-canonical", action="store_true", help="Use canonical URLs")
    parser.add_argument("--js", action="store_true", help="Enable JS rendering (Playwright)")
    args = parser.parse_args()

    print(f"Crawling {args.domain}...")
    
    # Updated Crawl Logic
    if args.js:
        print("Using JS crawler...")
        pages = crawl_js_sync(args.domain, limit=args.limit)
    else:
        print("Using standard crawler...")
        pages, graph = crawl(args.domain, limit=args.limit)

    print("Processing...")
    clean_urls = build_clean_urls(pages, fix_canonical=args.fix_canonical)

    print("Generating sitemap(s)...")
    files = generate_sitemaps(clean_urls, base_url=args.domain)

    print(f"Done. Generated {len(files)} sitemap file(s)")

    print(f"Done. Generated {args.output} with {len(clean_urls)} URLs")
