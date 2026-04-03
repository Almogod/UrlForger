# src/content/faq_generator.py
"""
Keyword-driven FAQ Generator for sitewide SERP optimization.
Generates FAQs directly from the site's discovered prime keywords,
ensuring every question targets real search intent for that domain.
"""

import re
import json
from collections import Counter
from src.utils.logger import logger
from src.content.stopwords import STOPWORDS
from src.content.content_schema import FAQItem


def generate_site_faqs(site_keywords, domain, llm_config):
    """
    Generate 6-8 FAQs based on the actual keywords found on the site.
    
    Args:
        site_keywords: list of keyword strings (already ranked by importance)
        domain: the site's domain name
        llm_config: LLM configuration dict
    
    Returns:
        list of FAQItem objects
    """
    logger.info(f"Generating keyword-driven FAQs for {domain} from {len(site_keywords)} keywords")
    
    if not site_keywords:
        logger.warning("No site keywords provided for FAQ generation")
        return []

    faqs = []
    has_api = bool(llm_config.get("api_key")) or llm_config.get("provider") == "ollama"

    if has_api:
        faqs = _generate_faqs_with_llm(site_keywords, domain, llm_config)
    
    if not faqs:
        faqs = _generate_faqs_builtin(site_keywords, domain)

    # Validate and normalize all to strict FAQItem model
    robust_faqs = []
    for item in faqs:
        if isinstance(item, dict) and "question" in item and "answer" in item:
            q = str(item["question"]).strip()
            a = str(item["answer"]).strip()
            if len(q) > 10 and len(a) > 20:
                robust_faqs.append(FAQItem(question=q, answer=a))
    
    logger.info(f"Generated {len(robust_faqs)} validated FAQs for {domain}")
    return robust_faqs


def _generate_faqs_with_llm(keywords, domain, llm_config):
    """Call LLM with the actual site keywords for targeted FAQ generation."""
    from src.content.page_generator import _call_openai, _call_gemini, _call_ollama
    
    kw_list = ', '.join(keywords[:10])
    prompt = f"""You are an expert SEO content strategist.

The website '{domain}' has the following primary keywords discovered from its content:
{kw_list}

Generate exactly 7 FAQ questions and answers specifically about these keywords.
Each FAQ MUST directly reference one or more of the keywords above.

RULES:
- Questions must use "What", "How", "Why", "Is", "Can", "Does" patterns
- Answers must be 40-60 words, factual, and authoritative (E-E-A-T compliant)
- Each answer must naturally include the keyword it targets
- Do NOT generate generic business questions - every FAQ must be keyword-specific

Respond with ONLY a valid JSON array of objects with "question" and "answer" fields. No other text."""
    
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
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                logger.info(f"LLM generated {len(parsed)} FAQs for {domain}")
                return parsed
    except Exception as e:
        logger.warning(f"FAQ LLM generation failed for {domain}: {e}")
    return []


def _generate_faqs_builtin(keywords, domain):
    """
    Generate FAQs directly from the site's keywords using intent-aware templates.
    Each keyword gets its own targeted question.
    """
    faqs = []
    
    # Intent-aware question templates - each one targets a specific keyword
    question_patterns = [
        {
            "q": "What is {keyword} and why is it important for {domain}?",
            "a": "{keyword} is a core focus area for {domain}. It represents a key capability that drives value for users by providing specialized solutions, expert guidance, and measurable results in this domain."
        },
        {
            "q": "How does {domain} approach {keyword} differently?",
            "a": "{domain} takes a data-driven approach to {keyword}, combining industry best practices with proprietary techniques. This methodology ensures consistent, high-quality outcomes that exceed standard expectations in the field."
        },
        {
            "q": "Why should users choose {domain} for {keyword} solutions?",
            "a": "{domain} has built deep expertise in {keyword} through extensive practical experience. Users benefit from optimized workflows, transparent processes, and results that are specifically tailored to their unique requirements."
        },
        {
            "q": "Can {keyword} be customized for specific use cases at {domain}?",
            "a": "Yes, {domain} offers fully customizable {keyword} implementations. Every solution is adapted to match the client's specific industry, scale, and performance targets for maximum effectiveness and ROI."
        },
        {
            "q": "What results can users expect from {keyword} at {domain}?",
            "a": "Users implementing {keyword} through {domain} typically see measurable improvements in efficiency, performance, and user satisfaction. Results are tracked through comprehensive analytics and continuous optimization cycles."
        },
        {
            "q": "Is {keyword} support available for enterprise clients at {domain}?",
            "a": "{domain} provides enterprise-grade {keyword} support including dedicated account management, priority response times, custom integrations, and scalable infrastructure to handle any volume of operations."
        },
        {
            "q": "How does {keyword} integrate with other services offered by {domain}?",
            "a": "{keyword} seamlessly connects with the full suite of {domain} services. This integrated approach ensures data consistency, streamlined workflows, and a unified experience across all touchpoints and platforms."
        },
    ]
    
    # Assign each keyword to a question pattern
    for i, pattern in enumerate(question_patterns):
        kw = keywords[i % len(keywords)].capitalize()
        faqs.append({
            "question": pattern["q"].format(keyword=kw, domain=domain),
            "answer": pattern["a"].format(keyword=kw, domain=domain)
        })
        
        # Stop after covering enough keywords (max 7 FAQs)
        if len(faqs) >= min(7, max(len(keywords), 5)):
            break
    
    return faqs
