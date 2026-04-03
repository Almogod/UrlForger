# src/content/faq_generator.py
"""
AI FAQ Generator for sitewide SERP optimization.
Extracts core topics from crawled pages and generates high-value Q&A 
to help secure Featured Snippets and Answer Engine citations.
"""

import re
from collections import Counter
from src.utils.logger import logger
from src.content.stopwords import STOPWORDS

def generate_site_faqs(pages, domain, llm_config):
    """
    Generate a list of 5-10 FAQs based on the site's content.
    """
    logger.info(f"Generating site FAQs for {domain}")
    
    # 1. Extract topics from page titles and headings
    topics = []
    for p in pages:
        titles = f"{p.get('title', '')} {' '.join(p.get('headings', []))}"
        words = re.sub(r"[^a-zA-Z0-9\s]", " ", titles).lower().split()
        filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]
        topics.extend(filtered)
    
    top_topics = [t for t, count in Counter(topics).most_common(10)]
    if not top_topics:
        top_topics = ["services", "solutions", "technology", "support"]

    faqs = []
    has_api = bool(llm_config.get("api_key")) or llm_config.get("provider") == "ollama"

    if has_api:
        faqs = _generate_faqs_with_llm(top_topics, domain, llm_config)
    
    if not faqs:
        faqs = _generate_faqs_builtin(top_topics, domain)

    return faqs

def _generate_faqs_with_llm(topics, domain, llm_config):
    """Call LLM to generate professional FAQs based on topics."""
    from src.content.page_generator import _call_openai, _call_gemini, _call_ollama
    
    prompt = f"""
    Generate 6 professional FAQ questions and answers for the website '{domain}'.
    The website focuses on these top topics: {', '.join(topics)}.
    
    Aim for Questions that secure "Featured Snippets" and "People Also Ask" rankings.
    Format your response as a JSON array of objects with "question" and "answer" keys.
    """
    
    provider = llm_config.get("provider", "openai").lower()
    raw = None
    try:
        if provider == "openai":
            raw = _call_openai(prompt, llm_config)
        elif provider == "gemini":
            raw = _call_gemini(prompt, llm_config)
        elif provider == "ollama":
            raw = _call_ollama(prompt, llm_config)
            
        if raw:
            import json
            # Minimal JSON extraction logic
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"FAQ LLM generation failed: {e}")
    return []

def _generate_faqs_builtin(topics, domain):
    """Fallback heuristic-based FAQ generation."""
    faqs = []
    # Mix topics to create believable questions
    templates = [
        ("What is {topic} and how does it benefit {domain} users?", "Our {topic} solutions provide industrial-grade reliability and efficiency for all our clients."),
        ("How can I get started with {topic} on this site?", "You can get started by reaching out to our support team or visiting the {topic} documentation page."),
        ("Why is {topic} important for modern businesses?", "{topic} is a critical component for scaling operations and maintaining a competitive edge in today's market."),
        ("Does {domain} offer custom {topic} solutions?", "Yes, we specialize in tailoring our {topic} offerings to meet your specific organizational needs."),
        ("What are the key features of your {topic} integration?", "Our {topic} features include seamless setup, real-time monitoring, and comprehensive data analytics."),
        ("Is {topic} security guaranteed?", "We use industry-standard encryption and security protocols to ensure your {topic} data remains protected.")
    ]
    
    for i, (q_tpl, a_tpl) in enumerate(templates):
        topic = topics[i % len(topics)].capitalize()
        faqs.append({
            "question": q_tpl.format(topic=topic, domain=domain),
            "answer": a_tpl.format(topic=topic, domain=domain)
        })
    return faqs
