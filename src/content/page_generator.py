# src/content/page_generator.py
"""
AI-powered page generator.
Takes a ContentBrief and generates a full, SEO-optimized HTML page
using an LLM (OpenAI, Google Gemini, or Ollama).

The generated page includes:
  - Proper HTML structure with correct heading hierarchy
  - Optimized meta title and description
  - JSON-LD schema markup (Article, FAQPage, BreadcrumbList)
  - Internal links to existing site pages
  - Semantic HTML with targeted keyword density
"""

import json
import re
from src.content.content_brief import ContentBrief


def generate_page(brief: ContentBrief, llm_config: dict, existing_pages: list = None) -> dict:
    """
    Generate a complete SEO-optimized HTML page from a ContentBrief.

    Args:
        brief: ContentBrief with keyword, headings, LSI terms, etc.
        llm_config: dict with keys: provider, api_key, model
        existing_pages: list of {url, title} for internal links

    Returns:
        dict with: html, slug, meta_title, meta_description, schema
    """

    provider = llm_config.get("provider", "openai").lower()

    prompt = _build_prompt(brief, existing_pages or [])

    if provider == "openai":
        content = _call_openai(prompt, llm_config)
    elif provider == "gemini":
        content = _call_gemini(prompt, llm_config)
    elif provider == "ollama":
        content = _call_ollama(prompt, llm_config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    html = _wrap_in_page(content, brief)
    schema = _build_schemas(brief)

    return {
        "slug": brief.url_slug,
        "meta_title": brief.page_title,
        "meta_description": brief.meta_description,
        "html": html,
        "schema": schema,
        "word_count": len(content.split())
    }


def _build_prompt(brief: ContentBrief, existing_pages: list) -> str:
    internal_links_str = "\n".join(
        f"- {p.get('title', p.get('url'))} ({p.get('url')})"
        for p in existing_pages[:10]
    )
    faqs_str = "\n".join(f"- {q}" for q in brief.faq_questions)
    headings_str = "\n".join(f"- {h}" for h in brief.headings)
    lsi_str = ", ".join(brief.lsi_terms)

    return f"""You are an expert SEO content writer. Write a comprehensive, high-ranking article for the following brief.

TARGET KEYWORD: {brief.target_keyword}
TITLE: {brief.page_title}
TARGET WORD COUNT: {brief.word_count_target} words

REQUIRED H2 SUBHEADINGS (use all of these):
{headings_str}

LSI TERMS TO INCLUDE NATURALLY (sprinkle throughout):
{lsi_str}

FAQ QUESTIONS TO ANSWER (include a section with these):
{faqs_str}

EXISTING SITE PAGES (add relevant internal links to these where natural):
{internal_links_str}

RULES:
1. Write ONLY the article body HTML (no <html>, <head>, <body> tags)
2. Start with an engaging introduction paragraph
3. Use exactly ONE <h1> with the title: "{brief.page_title}"
4. Use the listed subheadings as <h2> tags
5. Write detailed, original, helpful content — at least {brief.word_count_target} words
6. Add a FAQ section at the end using <h2>Frequently Asked Questions</h2>
7. Include all LSI terms naturally — never keyword stuff
8. Add internal links where relevant using <a href="URL">anchor text</a> format
9. Use <strong> for key phrases (2-3 per section)
10. Write in a clear, authoritative, helpful tone

Write the article now:"""


def _wrap_in_page(body_content: str, brief: ContentBrief) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{brief.page_title}</title>
    <meta name="description" content="{brief.meta_description}">
    <meta property="og:title" content="{brief.page_title}">
    <meta property="og:description" content="{brief.meta_description}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{brief.page_title}">
    <meta name="twitter:description" content="{brief.meta_description}">
    <link rel="canonical" href="/{brief.url_slug}">
</head>
<body>
<article>
{body_content}
</article>
</body>
</html>"""


def _build_schemas(brief: ContentBrief) -> list:
    schemas = []

    # Article schema
    schemas.append({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": brief.page_title,
        "description": brief.meta_description,
        "keywords": brief.target_keyword,
    })

    # FAQ schema if we have questions
    if brief.faq_questions:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"Learn more about {brief.target_keyword} and {q.lower().replace('?', '')}."
                    }
                }
                for q in brief.faq_questions
            ]
        })

    return schemas


# ─────────────────────────────────────────────────────────
# LLM PROVIDER IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────

def _call_openai(prompt: str, config: dict) -> str:
    try:
        import openai
        client = openai.OpenAI(api_key=config.get("api_key", ""))
        model = config.get("model", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")


def _call_gemini(prompt: str, config: dict) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.get("api_key", ""))
        model_name = config.get("model", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except ImportError:
        raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")


def _call_ollama(prompt: str, config: dict) -> str:
    import httpx
    host = config.get("ollama_host", "http://localhost:11434")
    model = config.get("model", "llama3")
    response = httpx.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()
