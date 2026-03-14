# src/content/competitor_analyzer.py
"""
Analyzes competitor pages for a given keyword to build a content brief.
Fetches top competitor pages, extracts headings, keywords, word count,
LSI terms, and FAQ patterns to create an authoritative content brief.
"""

import httpx
from bs4 import BeautifulSoup
from collections import Counter
import re
from src.content.content_brief import ContentBrief


STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "was", "were",
    "have", "has", "had", "you", "your", "about", "into", "their", "they",
    "them", "will", "would", "could", "should", "there", "here", "what",
    "when", "where", "which", "while", "also", "more", "most", "such",
    "http", "https", "www", "com", "html"
}


def analyze_competitors(competitor_urls: list, target_keyword: str, domain: str) -> ContentBrief:
    """
    Fetches competitor pages and builds a content brief
    for a new page targeting `target_keyword`.
    """
    all_headings = []
    all_words = []
    all_faqs = []
    word_counts = []

    for url in competitor_urls[:5]:  # cap at 5 competitors
        try:
            page_data = _fetch_page(url)
            if not page_data:
                continue

            soup = BeautifulSoup(page_data, "lxml")

            all_headings.extend(_extract_headings(soup))
            all_words.extend(_tokenize(soup.get_text(" ", strip=True)))
            all_faqs.extend(_extract_faq_questions(soup))
            word_count = len(soup.get_text(" ", strip=True).split())
            word_counts.append(word_count)

        except Exception:
            continue

    # ─────────────────────────────────────
    # Build frequency-ranked headings (deduplicated)
    # ─────────────────────────────────────
    heading_counter = Counter(h.lower() for h in all_headings)
    top_headings = [h for h, _ in heading_counter.most_common(8)]

    # ─────────────────────────────────────
    # Build LSI keyword list
    # ─────────────────────────────────────
    word_counter = Counter(all_words)
    keyword_tokens = set(target_keyword.lower().split())
    lsi_terms = [
        w for w, _ in word_counter.most_common(50)
        if w not in keyword_tokens and len(w) > 4
    ][:20]

    # ─────────────────────────────────────
    # Determine target word count
    # ─────────────────────────────────────
    target_wc = int(sum(word_counts) / len(word_counts)) if word_counts else 1000
    target_wc = max(target_wc, 800)

    # ─────────────────────────────────────
    # Build title and meta from keyword
    # ─────────────────────────────────────
    title = _generate_title(target_keyword)
    meta = _generate_meta(target_keyword, lsi_terms)
    slug = target_keyword.lower().replace(" ", "-")

    return ContentBrief(
        target_keyword=target_keyword,
        url_slug=slug,
        page_title=title,
        meta_description=meta,
        word_count_target=target_wc,
        headings=top_headings,
        lsi_terms=lsi_terms,
        competitor_urls=competitor_urls[:5],
        faq_questions=list(set(all_faqs))[:8],
        schema_type="Article"
    )


def _fetch_page(url: str) -> str | None:
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True,
                       headers={"User-Agent": "Mozilla/5.0 (SEO-Analyzer)"})
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def _extract_headings(soup) -> list:
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 5:
            headings.append(text)
    return headings


def _extract_faq_questions(soup) -> list:
    questions = []
    # dt/dd pattern
    for dt in soup.find_all("dt"):
        text = dt.get_text(strip=True)
        if text:
            questions.append(text)
    # headings ending in ?
    for h in soup.find_all(["h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        if text.endswith("?"):
            questions.append(text)
    return questions


def _tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 4 and t not in STOPWORDS]


def _generate_title(keyword: str) -> str:
    return f"{keyword.title()} — Complete Guide"


def _generate_meta(keyword: str, lsi_terms: list) -> str:
    supporting = ", ".join(lsi_terms[:3]) if lsi_terms else keyword
    return f"Learn everything about {keyword}. Covering {supporting} and more. Updated guide."[:155]
