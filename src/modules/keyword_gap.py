# src/modules/keyword_gap.py

from bs4 import BeautifulSoup
from collections import Counter
import re
import httpx

from src.content.stopwords import STOPWORDS


def run(context):

    pages = context["pages"]
    competitors = context.get("competitors", [])

    site_keywords = extract_site_keywords(pages)

    competitor_keywords = {}

    for competitor in competitors:

        try:
            competitor_pages = fetch_competitor_pages(competitor)
            competitor_keywords[competitor] = extract_site_keywords(competitor_pages)
        except Exception:
            competitor_keywords[competitor] = []

    keyword_gap = {}

    for competitor, keywords in competitor_keywords.items():

        gap = [k for k in keywords if k not in site_keywords]

        keyword_gap[competitor] = gap[:20]

    return {
        "site_keywords": site_keywords[:50],
        "competitor_keywords": competitor_keywords,
        "keyword_gap": keyword_gap
    }


def extract_site_keywords(pages):

    words = []

    for page in pages:

        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        text = soup.get_text(" ")

        tokens = tokenize(text)

        words.extend(tokens)

    counter = Counter(words)

    return [w for w, _ in counter.most_common(200)]


def tokenize(text):

    text = text.lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)

    tokens = text.split()

    tokens = [t for t in tokens if len(t) > 3 and t not in STOPWORDS]

    return tokens


def fetch_competitor_pages(domain):

    urls = [
        domain,
        f"{domain}/blog",
        f"{domain}/articles"
    ]

    pages = []

    for url in urls:

        try:

            r = httpx.get(url, timeout=10)

            pages.append({
                "url": url,
                "html": r.text,
                "status": r.status_code
            })

        except Exception:
            continue

    return pages
