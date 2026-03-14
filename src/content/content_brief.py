# src/content/content_brief.py
"""
Data model for a content brief — the spec given to the page generator.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContentBrief:
    target_keyword: str
    url_slug: str
    page_title: str
    meta_description: str
    word_count_target: int = 1000
    headings: List[str] = field(default_factory=list)
    lsi_terms: List[str] = field(default_factory=list)
    competitor_urls: List[str] = field(default_factory=list)
    faq_questions: List[str] = field(default_factory=list)
    internal_links: List[dict] = field(default_factory=list)
    schema_type: str = "Article"
    category: Optional[str] = None

    def to_dict(self):
        return {
            "target_keyword": self.target_keyword,
            "url_slug": self.url_slug,
            "page_title": self.page_title,
            "meta_description": self.meta_description,
            "word_count_target": self.word_count_target,
            "headings": self.headings,
            "lsi_terms": self.lsi_terms,
            "competitor_urls": self.competitor_urls,
            "faq_questions": self.faq_questions,
            "internal_links": self.internal_links,
            "schema_type": self.schema_type,
            "category": self.category
        }
