# src/modules/content_quality.py
"""
Detects content quality issues:
- Thin content (< 300 words)
- Duplicate content (hash-based similarity)
- Keyword density analysis (too low or stuffed)
"""

from bs4 import BeautifulSoup
from collections import Counter
import re
import hashlib

from src.content.stopwords import STOPWORDS


MIN_WORD_COUNT = 300
KEYWORD_STUFFING_THRESHOLD = 0.04   # > 4% = stuffed
LOW_KEYWORD_DENSITY_THRESHOLD = 0.005  # < 0.5% = under-optimized


def run(context):
    pages = context["pages"]

    issues = []
    suggestions = {}
    content_hashes = {}

    for page in pages:
        url = page.get("url")
        html = page.get("html")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        # Strip nav, header, footer, script, style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)
        words = _tokenize(text)
        word_count = len(words)

        page_suggestions = []

        # ─────────────────────────────────────
        # Thin content
        # ─────────────────────────────────────
        if word_count < MIN_WORD_COUNT:
            issues.append({
                "url": url,
                "issue": "thin_content",
                "word_count": word_count
            })
            page_suggestions.append({
                "type": "expand_content",
                "current_words": word_count,
                "target_words": MIN_WORD_COUNT,
                "action": "generate_additional_content_for_page"
            })

        # ─────────────────────────────────────
        # Duplicate content detection
        # ─────────────────────────────────────
        content_hash = _hash_content(text)
        if content_hash in content_hashes:
            issues.append({
                "url": url,
                "issue": "duplicate_content",
                "duplicate_of": content_hashes[content_hash]
            })
            page_suggestions.append({
                "type": "fix_duplicate_content",
                "action": "rewrite_content_or_add_canonical"
            })
        else:
            content_hashes[content_hash] = url

        # ─────────────────────────────────────
        # Keyword density analysis
        # ─────────────────────────────────────
        if word_count > 0:
            counter = Counter(words)
            top_word, top_count = counter.most_common(1)[0] if counter else ("", 0)
            density = top_count / word_count

            if density > KEYWORD_STUFFING_THRESHOLD:
                issues.append({
                    "url": url,
                    "issue": "keyword_stuffing",
                    "keyword": top_word,
                    "density": round(density * 100, 2)
                })
                page_suggestions.append({
                    "type": "reduce_keyword_density",
                    "keyword": top_word,
                    "action": "replace_some_instances_with_synonyms"
                })

            elif density < LOW_KEYWORD_DENSITY_THRESHOLD and word_count >= MIN_WORD_COUNT:
                issues.append({
                    "url": url,
                    "issue": "low_keyword_density",
                    "keyword": top_word,
                    "density": round(density * 100, 2)
                })
                page_suggestions.append({
                    "type": "increase_keyword_density",
                    "keyword": top_word,
                    "action": "naturally_include_target_keyword_more_often"
                })

        if page_suggestions:
            suggestions[url] = page_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions
    }


def _tokenize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 3 and t not in STOPWORDS]


def _hash_content(text):
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()
