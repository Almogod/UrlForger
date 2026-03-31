# src/content/page_generator.py
"""
AI-powered page generator with API-independent fallback.

Takes a ContentBrief and generates a full, SEO-optimized HTML page using
either an LLM (OpenAI, Google Gemini, Ollama) or the built-in template
engine.  The built-in engine produces publication-quality content that
reads naturally and ranks well on Google — no API key required.

The generated page includes:
  - Proper HTML structure with correct heading hierarchy
  - Optimized meta title and description
  - JSON-LD schema markup (Article, FAQPage, BreadcrumbList)
  - Internal links to existing site pages
  - Semantic HTML with targeted keyword density
  - Human-touch writing style with varied sentence lengths
  - E-E-A-T signals and reader engagement patterns
"""

import json
import re
import random
import hashlib
from datetime import datetime
from src.content.content_brief import ContentBrief
from src.utils.logger import logger


def generate_page(brief: ContentBrief, llm_config: dict, existing_pages: list = None) -> dict:
    """
    Generate a complete SEO-optimized HTML page from a ContentBrief.

    Strategy:
      1. If a valid LLM API key is provided, use the LLM with improved prompts.
      2. If the LLM call fails, fall back to built-in generation.
      3. If no API key is provided at all, use built-in generation directly.

    Args:
        brief: ContentBrief with keyword, headings, LSI terms, etc.
        llm_config: dict with keys: provider, api_key, model
        existing_pages: list of {url, title} for internal links

    Returns:
        dict with: html, slug, meta_title, meta_description, schema, word_count
    """
    existing_pages = existing_pages or []
    content = None
    generation_method = "builtin"

    # Check if we have a usable API key
    has_api = bool(llm_config.get("api_key"))
    provider = llm_config.get("provider", "").lower()

    # Ollama doesn't need an API key, just a host
    if provider == "ollama":
        has_api = True

    if has_api:
        try:
            prompt = _build_prompt(brief, existing_pages)
            if provider == "openai":
                content = _call_openai(prompt, llm_config)
            elif provider == "gemini":
                content = _call_gemini(prompt, llm_config)
            elif provider == "ollama":
                content = _call_ollama(prompt, llm_config)
            else:
                logger.warning(f"Unknown LLM provider '{provider}', falling back to built-in generator")

            if content:
                generation_method = provider
                logger.info(f"Content generated via {provider} ({len(content.split())} words)")
        except Exception as e:
            logger.warning(f"LLM call failed ({provider}): {e} — falling back to built-in generator")
            content = None

    # Fallback (or primary if no API)
    if not content:
        content = _generate_builtin(brief, existing_pages)
        generation_method = "builtin"
        logger.info(f"Content generated via built-in engine ({len(content.split())} words)")

    html = _wrap_in_page(content, brief)
    schema = _build_schemas(brief)

    return {
        "slug": brief.url_slug,
        "meta_title": brief.page_title,
        "meta_description": brief.meta_description,
        "html": html,
        "schema": schema,
        "word_count": len(content.split()),
        "generation_method": generation_method,
    }


# ─────────────────────────────────────────────────────────────────────
# BUILT-IN CONTENT GENERATOR (API-independent)
# ─────────────────────────────────────────────────────────────────────

# Transition phrases for natural flow between sections
_TRANSITIONS = [
    "Now, let's take a closer look at",
    "With that foundation in place, let's explore",
    "Building on that idea,",
    "Here's where things get interesting.",
    "You might be wondering about",
    "This brings us to an important point:",
    "Let's break this down further.",
    "There's more to this than meets the eye.",
    "Here's what most people miss:",
    "Moving on to something equally important —",
    "So what does this look like in practice?",
    "This is where the rubber meets the road.",
    "Let me walk you through this.",
    "The next piece of the puzzle is",
    "But wait — there's a nuance here.",
]

# Hook starters for introductions
_INTRO_HOOKS = {
    "question": [
        "Have you ever wondered why {keyword} matters so much?",
        "What if everything you thought you knew about {keyword} was only half the story?",
        "Why do so many people struggle with {keyword} — and what can you actually do about it?",
        "Ever noticed how the best results come from understanding {keyword} deeply?",
    ],
    "statistic": [
        "Here's a fact that might surprise you: most people approach {keyword} the wrong way.",
        "Studies consistently show that {keyword} can make or break your results.",
        "The difference between good and great often comes down to how well you understand {keyword}.",
    ],
    "story": [
        "When I first started learning about {keyword}, I made every mistake in the book.",
        "A few years ago, I came across {keyword} and it completely changed my approach.",
        "I used to overlook {keyword} — until I saw the impact it had firsthand.",
    ],
    "bold": [
        "Let's be honest: {keyword} isn't just another buzzword.",
        "If you're serious about results, {keyword} is non-negotiable.",
        "{keyword} is one of those topics that seems simple on the surface — but the details matter enormously.",
    ],
}

# Sentence connectors for natural writing
_CONNECTORS = [
    "In other words,", "Put simply,", "That said,", "Here's the thing:",
    "To put it another way,", "What this means is", "The bottom line?",
    "In practice,", "From experience,", "The key takeaway here is",
    "Think of it this way:", "One thing to keep in mind:",
    "It's worth noting that", "Interestingly,", "On a practical level,",
]

# Paragraph enders for variety
_PARAGRAPH_ENDERS = [
    "That's a crucial distinction to understand.",
    "This alone can make a significant difference.",
    "And that's something worth remembering.",
    "It's one of those things that's easy to overlook but hard to ignore once you see it.",
    "The results speak for themselves.",
    "This is exactly why attention to detail matters.",
    "And honestly? Most people skip this step.",
    "Keep this in mind as we move forward.",
]

# FAQ answer templates by type
_FAQ_ANSWER_PATTERNS = [
    "Great question. {answer_body} The key thing to remember is that {keyword} {closing}.",
    "{answer_body} In simple terms, {keyword} {closing}.",
    "This is something a lot of people ask about. {answer_body} When it comes to {keyword}, {closing}.",
    "Short answer: {brief_answer}. But let me explain. {answer_body} Understanding {keyword} {closing}.",
    "{answer_body} The important thing is that {keyword} {closing}.",
]


def _generate_builtin(brief: ContentBrief, existing_pages: list) -> str:
    """
    Generate a complete article body using template-driven composition.
    Produces human-quality prose with varied sentence lengths, natural
    transitions, rhetorical questions, and SEO-conscious keyword placement.
    """
    rng = random.Random(hashlib.md5(brief.target_keyword.encode()).hexdigest())
    kw = brief.target_keyword
    kw_title = kw.title()
    sections = []

    # ── 1. Title ──────────────────────────────────────────────────────
    sections.append(f"<h1>{brief.page_title}</h1>")

    # ── 2. Introduction (2-3 paragraphs) ──────────────────────────────
    sections.append(_build_intro(brief, rng))

    # ── 3. Body sections from headings ────────────────────────────────
    headings = brief.headings or _generate_fallback_headings(kw, brief.search_intent)
    lsi_pool = list(brief.lsi_terms)
    entity_pool = list(brief.entity_mentions)
    internal_links = list(existing_pages)

    for i, heading in enumerate(headings):
        section_html = _build_section(
            heading=heading,
            keyword=kw,
            lsi_pool=lsi_pool,
            entity_pool=entity_pool,
            internal_links=internal_links,
            brief=brief,
            section_index=i,
            total_sections=len(headings),
            rng=rng,
        )
        sections.append(section_html)

    # ── 4. FAQ section ────────────────────────────────────────────────
    if brief.faq_questions:
        sections.append(_build_faq_section(brief, rng))

    # ── 5. Conclusion ─────────────────────────────────────────────────
    sections.append(_build_conclusion(brief, rng))

    return "\n\n".join(sections)


def _build_intro(brief: ContentBrief, rng: random.Random) -> str:
    """Build an engaging 2-3 paragraph introduction."""
    kw = brief.target_keyword
    kw_title = kw.title()
    lsi_sample = brief.lsi_terms[:5]
    power = brief.power_words[:3] if brief.power_words else ["essential", "practical", "proven"]

    # Pick a hook style
    hook_style = rng.choice(list(_INTRO_HOOKS.keys()))
    hook = rng.choice(_INTRO_HOOKS[hook_style]).format(keyword=kw)

    # Build context paragraph
    lsi_mention = ""
    if lsi_sample:
        lsi_mention = f" — from {lsi_sample[0]} to {lsi_sample[1]}" if len(lsi_sample) >= 2 else f" including {lsi_sample[0]}"

    context_templates = [
        f"<p>{hook} In this {power[0]} guide, we'll walk you through everything "
        f"you need to know about <strong>{kw}</strong>{lsi_mention}. Whether you're "
        f"just getting started or looking to sharpen your approach, you'll find "
        f"actionable insights that you can put to work right away.</p>",

        f"<p>{hook} The truth is, <strong>{kw}</strong> is one of those areas "
        f"where the right knowledge can save you hours of trial and error. We've "
        f"put together this {power[0]} resource to give you a clear roadmap"
        f"{lsi_mention}. No fluff — just the stuff that actually works.</p>",

        f"<p>{hook} Understanding <strong>{kw}</strong> isn't just useful — "
        f"it's {power[0]}. In this guide, we'll cover the key concepts"
        f"{lsi_mention}, with {power[1] if len(power) > 1 else 'practical'} "
        f"examples and real-world applications. Let's dive in.</p>",
    ]
    intro_p1 = rng.choice(context_templates)

    # Second paragraph — set expectations
    cta = brief.cta_suggestions[0] if brief.cta_suggestions else "Let's get into it."
    heading_preview = ""
    if brief.headings and len(brief.headings) >= 3:
        heading_preview = (
            f" We'll cover topics like <em>{brief.headings[0].lower()}</em>, "
            f"<em>{brief.headings[1].lower()}</em>, and "
            f"<em>{brief.headings[2].lower()}</em> — among others."
        )

    intro_p2 = (
        f"<p>By the end of this guide, you'll have a solid understanding of "
        f"<strong>{kw}</strong> and how to apply it effectively.{heading_preview} "
        f"{cta}</p>"
    )

    return intro_p1 + "\n\n" + intro_p2


def _build_section(heading, keyword, lsi_pool, entity_pool,
                   internal_links, brief, section_index, total_sections, rng) -> str:
    """Build a single content section with 3-5 paragraphs."""
    parts = []

    # Transition (skip for first section)
    if section_index > 0:
        transition = rng.choice(_TRANSITIONS)
        parts.append(f"<p>{transition}</p>")

    parts.append(f"<h2>{heading}</h2>")

    # Pick LSI terms to weave into this section
    section_lsi = []
    if lsi_pool:
        count = min(3, len(lsi_pool))
        section_lsi = [lsi_pool.pop(0) for _ in range(count) if lsi_pool]

    # Pick entities
    section_entities = []
    if entity_pool:
        count = min(2, len(entity_pool))
        section_entities = [entity_pool.pop(0) for _ in range(count) if entity_pool]

    # Generate 3-5 paragraphs
    num_paragraphs = rng.randint(3, 5)
    for p_idx in range(num_paragraphs):
        para = _build_paragraph(
            heading=heading,
            keyword=keyword,
            lsi_terms=section_lsi,
            entities=section_entities,
            para_index=p_idx,
            total_paras=num_paragraphs,
            brief=brief,
            rng=rng,
        )
        parts.append(para)

    # Maybe add an internal link
    if internal_links and rng.random() > 0.5:
        link = internal_links.pop(0)
        url = link.get("url", "#")
        title = link.get("title", keyword)
        parts.append(
            f'<p>For more on this topic, check out our article on '
            f'<a href="{url}">{title}</a>.</p>'
        )

    # Maybe add a callout/tip box (every 2-3 sections)
    if section_index % 2 == 1 and brief.power_words:
        pw = rng.choice(brief.power_words) if brief.power_words else "key"
        parts.append(
            f'<blockquote><strong>💡 Pro Tip:</strong> The most {pw} approach to '
            f'{heading.lower()} is to start small, measure your results, and iterate. '
            f"Don't try to do everything at once.</blockquote>"
        )

    return "\n".join(parts)


def _build_paragraph(heading, keyword, lsi_terms, entities, para_index,
                     total_paras, brief, rng) -> str:
    """Build a single paragraph with varied sentence lengths and natural tone."""
    kw = keyword
    heading_lower = heading.lower()
    sentences = []

    # Determine paragraph role
    if para_index == 0:
        # Opening paragraph — introduce the subtopic
        openers = [
            f"When it comes to {heading_lower}, there are a few things worth understanding from the start.",
            f"Let's talk about {heading_lower}. It's an area that often doesn't get the attention it deserves.",
            f"{heading.rstrip('.')} is something that can significantly impact your results with {kw}.",
            f"Understanding {heading_lower} is one of the foundations of working effectively with {kw}.",
            f"If there's one area of {kw} that deserves your attention, it's {heading_lower}.",
        ]
        sentences.append(rng.choice(openers))
    elif para_index == total_paras - 1:
        # Closing paragraph — wrap up the section
        connector = rng.choice(_CONNECTORS)
        sentences.append(f"{connector} getting {heading_lower} right is about consistency and attention to detail.")
    else:
        # Middle paragraphs — add detail, examples, nuance
        mid_openers = [
            "There's an important nuance here.",
            "Let me expand on that.",
            "Here's a practical example.",
            "In real-world scenarios, this looks a bit different.",
            "This is where experience really matters.",
            "But there's more to the story.",
        ]
        sentences.append(rng.choice(mid_openers))

    # Add 2-4 more sentences with varied lengths
    detail_count = rng.randint(2, 4)
    for i in range(detail_count):
        sentence = _generate_detail_sentence(
            keyword=kw, heading=heading_lower,
            lsi_terms=lsi_terms, entities=entities,
            brief=brief, rng=rng,
        )
        sentences.append(sentence)

    # Occasionally add a rhetorical question (human touch)
    if rng.random() > 0.65:
        questions = [
            f"So what does this mean for your approach to {kw}?",
            "Why does this matter?",
            f"How can you apply this to {heading_lower}?",
            "Sound familiar?",
            "Makes sense, right?",
        ]
        sentences.insert(rng.randint(1, len(sentences)), rng.choice(questions))

    # Occasionally add a short, punchy sentence (rhythm variation)
    if rng.random() > 0.6:
        punchy = [
            "It's that simple.",
            "And it works.",
            "Don't skip this.",
            "Trust the process.",
            "Results follow effort.",
            "Details matter.",
            "That's a game changer.",
        ]
        sentences.insert(rng.randint(1, len(sentences)), rng.choice(punchy))

    # Sometimes bold a key phrase
    text = " ".join(sentences)
    if kw.lower() in text.lower() and rng.random() > 0.5:
        # Bold only the first occurrence in this paragraph
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f"<strong>{kw}</strong>", text, count=1)

    return f"<p>{text}</p>"


def _generate_detail_sentence(keyword, heading, lsi_terms, entities, brief, rng) -> str:
    """Generate a single detail sentence, naturally weaving in LSI/entities."""
    templates = []

    # LSI-infused sentences
    if lsi_terms:
        lsi = rng.choice(lsi_terms)
        templates.extend([
            f"One aspect that connects directly to {heading} is {lsi} — and understanding that relationship gives you an edge.",
            f"When you consider {lsi} alongside {keyword}, the picture becomes much clearer.",
            f"Experts in this space often emphasize the role of {lsi} when discussing {heading}.",
            f"The interplay between {lsi} and {keyword} is something that separates beginners from professionals.",
            f"If you look at {lsi} closely, you'll notice patterns that directly relate to {heading}.",
            f"Many overlook the connection between {lsi} and {keyword}, but it's worth paying attention to.",
        ])

    # Entity-infused sentences
    if entities:
        entity = rng.choice(entities)
        templates.extend([
            f"Tools and frameworks like {entity} have shown how {heading} can be approached systematically.",
            f"Industry leaders, including {entity}, have adopted approaches that prioritize {heading}.",
            f"Looking at how {entity} handles this gives practical insight into effective {keyword} strategies.",
        ])

    # Generic detail sentences
    templates.extend([
        f"The key to making {heading} work lies in understanding the underlying principles rather than just following rules.",
        f"In practice, the most successful approach to {heading} involves a combination of strategy, execution, and continuous refinement.",
        f"What many people get wrong about {heading} is treating it as a one-time task rather than an ongoing process.",
        f"The best results come when you approach {heading} with both a strategic mindset and attention to tactical details.",
        f"Research consistently supports the idea that a thoughtful approach to {heading} yields better long-term outcomes.",
        f"One practical way to improve your {heading} is to audit what you're currently doing and identify the gaps.",
        f"From a {keyword} perspective, {heading} isn't optional — it's foundational.",
        f"Small improvements in {heading} can compound over time, leading to significant gains in your overall {keyword} results.",
        f"The difference between average and excellent often comes down to how thoroughly you address {heading}.",
        f"Don't underestimate the impact of getting {heading} right — it affects everything downstream.",
    ])

    return rng.choice(templates)


def _build_faq_section(brief: ContentBrief, rng: random.Random) -> str:
    """Build an FAQ section with direct, helpful answers."""
    parts = ["<h2>Frequently Asked Questions</h2>"]
    kw = brief.target_keyword

    # Answer closings
    closings = [
        "requires both understanding and practice",
        "is ultimately about getting the fundamentals right",
        "depends on your specific situation and goals",
        "is an evolving field, so staying current is important",
        "benefits from a strategic, long-term perspective",
        "works best when combined with consistent effort",
    ]

    # Brief answer prefixes for the short-answer pattern
    brief_answers = [
        "Yes, absolutely",
        "It depends on your situation",
        "Generally speaking, yes",
        "The short answer is yes",
        "In most cases, yes",
    ]

    for q in brief.faq_questions:
        q_clean = q.strip().rstrip("?") + "?"

        # Generate a substantive answer body
        answer_bodies = [
            f"This is a common question, and the answer involves understanding how {kw} works in practice. "
            f"The core idea is that {q_clean.lower().replace('?', '')} connects directly to the broader topic of {kw}. "
            f"When you break it down, there are a few factors at play — context, execution, and consistency.",

            f"To answer this properly, we need to look at {kw} from a practical standpoint. "
            f"The reality is that {q_clean.lower().replace('?', '')} isn't a simple yes-or-no situation. "
            f"It depends on your goals, your current setup, and how much effort you're willing to invest.",

            f"This comes up a lot, and for good reason. {kw.title()} touches on so many areas that "
            f"it's natural to have questions. The practical answer is that you should focus on "
            f"understanding the principles first, then move to implementation.",

            f"Let's address this head-on. {q_clean.lower().replace('?', '').capitalize()} "
            f"is closely tied to how well you understand {kw}. The good news is that once "
            f"you grasp the fundamentals, the rest falls into place more naturally.",
        ]

        pattern = rng.choice(_FAQ_ANSWER_PATTERNS)
        answer = pattern.format(
            answer_body=rng.choice(answer_bodies),
            keyword=kw,
            closing=rng.choice(closings),
            brief_answer=rng.choice(brief_answers),
        )

        parts.append(f"<h3>{q_clean}</h3>")
        parts.append(f"<p>{answer}</p>")

    return "\n".join(parts)


def _build_conclusion(brief: ContentBrief, rng: random.Random) -> str:
    """Build a compelling conclusion with summary and CTA."""
    kw = brief.target_keyword
    kw_title = kw.title()
    power = brief.power_words[0] if brief.power_words else "effective"
    cta = brief.cta_suggestions[-1] if brief.cta_suggestions else "Start putting these ideas into action today."

    conclusions = [
        f"""<h2>Wrapping Up: Your Path Forward with {kw_title}</h2>
<p>We've covered a lot of ground in this guide — from the fundamentals of <strong>{kw}</strong> to the nuanced strategies that set top performers apart. The most important takeaway? Knowledge without execution is just information. The {power} approach is to pick one or two insights from this guide and start implementing them now.</p>
<p>Remember, mastering {kw} isn't about perfection from day one. It's about consistent, intentional progress. Each small improvement compounds over time, and before you know it, you'll be seeing real, measurable results.</p>
<p><strong>{cta}</strong> If you found this guide helpful, consider bookmarking it for future reference — you'll likely want to revisit specific sections as you put these strategies into practice.</p>""",

        f"""<h2>Final Thoughts on {kw_title}</h2>
<p>If you've made it this far, you already have a significant advantage. Most people skim articles about <strong>{kw}</strong> without ever putting the ideas into practice. You now have a structured framework to work with — use it.</p>
<p>The landscape of {kw} continues to evolve, but the core principles we've discussed remain constant. Focus on quality, stay consistent, and don't be afraid to experiment. The best strategy is the one you actually follow through on.</p>
<p><strong>{cta}</strong> The gap between where you are and where you want to be is simply a matter of applied knowledge and persistence.</p>""",

        f"""<h2>Key Takeaways and Next Steps</h2>
<p>Let's bring it all together. <strong>{kw_title}</strong> is a topic with real depth — and now you have the tools and understanding to navigate it confidently. Whether you're applying these ideas for the first time or refining an existing approach, the principles remain the same: strategy first, execution second, optimization always.</p>
<p>Don't try to do everything at once. Pick the area that will have the biggest impact for your specific situation and start there. Build momentum, track your progress, and adjust as you learn.</p>
<p><strong>{cta}</strong></p>""",
    ]

    return rng.choice(conclusions)


def _generate_fallback_headings(keyword: str, intent: str) -> list:
    """Generate sensible section headings when none were found from competitors."""
    kw = keyword
    if intent == "how-to":
        return [
            f"What Is {kw.title()} and Why Does It Matter?",
            f"Preparing for {kw.title()}: What You'll Need",
            f"Step-by-Step Guide to {kw.title()}",
            f"Common Mistakes to Avoid with {kw.title()}",
            f"Advanced Tips for {kw.title()}",
            f"Measuring Your {kw.title()} Results",
        ]
    elif intent == "commercial":
        return [
            f"What to Look for in {kw.title()}",
            f"Our Top Picks for {kw.title()}",
            f"How We Evaluated Each Option",
            f"Pros and Cons Breakdown",
            f"Which {kw.title()} Is Right for You?",
        ]
    else:
        return [
            f"Understanding {kw.title()}: The Fundamentals",
            f"Why {kw.title()} Matters More Than Ever",
            f"Key Components of {kw.title()}",
            f"Best Practices for {kw.title()}",
            f"Common Challenges and How to Overcome Them",
            f"The Future of {kw.title()}",
        ]


# ─────────────────────────────────────────────────────────────────────
# IMPROVED LLM PROMPT
# ─────────────────────────────────────────────────────────────────────

def _build_prompt(brief: ContentBrief, existing_pages: list) -> str:
    """Build a comprehensive prompt that produces human-quality, rankable content."""
    internal_links_str = "\n".join(
        f"- {p.get('title', p.get('url'))} ({p.get('url')})"
        for p in existing_pages[:10]
    )
    faqs_str = "\n".join(f"- {q}" for q in brief.faq_questions)
    headings_str = "\n".join(f"- {h}" for h in brief.headings)
    lsi_str = ", ".join(brief.lsi_terms)
    entities_str = ", ".join(brief.entity_mentions) if brief.entity_mentions else "N/A"
    power_str = ", ".join(brief.power_words) if brief.power_words else "N/A"
    variants_str = ", ".join(brief.target_keyword_variants[:5]) if brief.target_keyword_variants else "N/A"

    tone_instructions = {
        "conversational": "Write like you're explaining to a smart friend over coffee — warm, direct, and engaging. Use contractions (you'll, it's, don't). Ask rhetorical questions. Share opinions.",
        "authoritative": "Write with confident expertise. Use data-backed claims and precise language. Be direct and assertive, but not arrogant. Sound like a trusted industry advisor.",
        "educational": "Write clearly and patiently. Explain concepts step-by-step. Use analogies and examples. Make complex ideas accessible without dumbing them down.",
        "persuasive": "Write to convince. Lead with benefits, address objections, and build urgency. Use power words and clear calls-to-action. Every paragraph should move the reader toward a decision.",
    }
    tone_guide = tone_instructions.get(brief.tone, tone_instructions["conversational"])

    return f"""You are a world-class SEO content writer with years of experience creating content that ranks #1 on Google. Write a comprehensive article that reads like it was written by a thoughtful human expert — NOT an AI.

═══════════════════════════════════════════
CONTENT BRIEF
═══════════════════════════════════════════

TARGET KEYWORD: {brief.target_keyword}
TITLE: {brief.page_title}
SEARCH INTENT: {brief.search_intent}
CONTENT STRUCTURE: {brief.content_structure}
TARGET WORD COUNT: {brief.word_count_target} words (minimum)
READABILITY TARGET: Grade {brief.readability_target} (Flesch-Kincaid)

═══════════════════════════════════════════
SEMANTIC ELEMENTS
═══════════════════════════════════════════

REQUIRED H2 SUBHEADINGS:
{headings_str}

LSI TERMS TO INCLUDE NATURALLY:
{lsi_str}

KEYWORD VARIANTS TO USE:
{variants_str}

ENTITIES TO MENTION WHERE RELEVANT:
{entities_str}

POWER WORDS TO WEAVE IN:
{power_str}

FAQ QUESTIONS TO ANSWER:
{faqs_str}

EXISTING PAGES FOR INTERNAL LINKS:
{internal_links_str}

═══════════════════════════════════════════
WRITING STYLE & TONE
═══════════════════════════════════════════

{tone_guide}

CRITICAL ANTI-AI-DETECTION RULES:
1. Vary your sentence length dramatically — mix short punchy sentences (5-8 words) with longer explanatory ones (20-30 words). Never write 3+ sentences of similar length in a row.
2. Use contractions liberally: "you'll", "it's", "don't", "won't", "they're".
3. Include 2-3 personal opinions or experience-based observations (e.g., "In my experience...", "I've found that...", "Honestly,").
4. Use rhetorical questions — at least 3-4 throughout the article.
5. Include at least one mild disagreement with common advice (e.g., "Contrary to popular belief...", "While most guides tell you X, I'd argue Y...").
6. Start some sentences with "And", "But", "So", or "Because" — real writers do this.
7. Use em-dashes (—) instead of excessive commas in at least 3-4 places.
8. Include transitional phrases that feel natural, not robotic (avoid "Furthermore", "Moreover", "Additionally" — use "Here's the thing", "That said", "The bottom line").
9. Don't use the word "crucial" more than once. Don't use "landscape", "tapestry", "delve", "robust", "leverage", "utilize", "paradigm", or "synergy" — these are AI tells.
10. Write like you TALK. Read each paragraph aloud — if it sounds robotic, rewrite it.

═══════════════════════════════════════════
E-E-A-T SIGNALS (Experience, Expertise, Authority, Trust)
═══════════════════════════════════════════

- Show firsthand experience: reference practical applications, real scenarios, or "I've seen this work when..."
- Demonstrate expertise: be specific, use precise terminology (but explain it), cite principles
- Build authority: acknowledge other viewpoints, link to related content naturally
- Earn trust: be transparent about limitations, don't oversell, admit when "it depends"

═══════════════════════════════════════════
FORMATTING RULES
═══════════════════════════════════════════

1. Write ONLY the article body HTML (no <html>, <head>, <body> tags)
2. Start with an engaging hook — NO generic introductions
3. Use exactly ONE <h1> with the title: "{brief.page_title}"
4. Use the listed subheadings as <h2> tags
5. Write at least {brief.word_count_target} words of detailed, original content
6. Add a FAQ section at the end using <h2>Frequently Asked Questions</h2> with <h3> for each question
7. Include LSI terms naturally — keyword density should be 1.5-2.5% for the primary keyword
8. Add internal links where relevant using <a href="URL">descriptive anchor text</a>
9. Use <strong> for key phrases (2-3 per section max)
10. Use <blockquote> for important tips or callouts
11. Include a compelling conclusion with a call-to-action

Write the article now:"""


# ─────────────────────────────────────────────────────────────────────
# HTML WRAPPER
# ─────────────────────────────────────────────────────────────────────

def _wrap_in_page(body_content: str, brief: ContentBrief) -> str:
    """Wrap article body in a complete HTML page with meta tags, OG, and schema."""
    schema_json = json.dumps(_build_schemas(brief), indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{brief.page_title}</title>
    <meta name="description" content="{brief.meta_description}">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="{brief.page_title}">
    <meta property="og:description" content="{brief.meta_description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="/{brief.url_slug}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{brief.page_title}">
    <meta name="twitter:description" content="{brief.meta_description}">
    <link rel="canonical" href="/{brief.url_slug}">
    <script type="application/ld+json">
{schema_json}
    </script>
</head>
<body>
<article>
{body_content}
</article>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────
# SCHEMA GENERATION
# ─────────────────────────────────────────────────────────────────────

def _build_schemas(brief: ContentBrief) -> list:
    """Build JSON-LD schemas for the generated page."""
    now = datetime.now().isoformat()
    schemas = []

    # Article schema
    schemas.append({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": brief.page_title,
        "description": brief.meta_description,
        "keywords": brief.target_keyword,
        "datePublished": now,
        "dateModified": now,
        "author": {
            "@type": "Organization",
            "name": "UrlForge",
        },
        "publisher": {
            "@type": "Organization",
            "name": "UrlForge",
        },
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
                        "text": (
                            f"This is a common question about {brief.target_keyword}. "
                            f"Understanding {q.lower().replace('?', '')} is important because "
                            f"it directly impacts how effectively you can apply {brief.target_keyword} "
                            f"strategies. The answer depends on your specific context, but the "
                            f"core principles remain consistent."
                        )
                    }
                }
                for q in brief.faq_questions
            ]
        })

    # Breadcrumb schema
    schemas.append({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": brief.category or brief.target_keyword.title(),
                "item": f"/{brief.url_slug}"
            }
        ]
    })

    return schemas


# ─────────────────────────────────────────────────────────────────────
# LLM PROVIDER IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────

def _call_openai(prompt: str, config: dict) -> str:
    try:
        import openai
        client = openai.OpenAI(api_key=config.get("api_key", ""))
        model = config.get("model", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SEO content writer who writes in a natural, human voice. Your content is engaging, well-researched, and optimized for search engines while being genuinely helpful to readers."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=6000,
            temperature=0.8,  # Slightly higher for more natural variation
            top_p=0.95,
            frequency_penalty=0.3,  # Reduce repetition
            presence_penalty=0.2,   # Encourage topic diversity
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")


def _call_gemini(prompt: str, config: dict) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.get("api_key", ""))
        model_name = config.get("model", "gemini-1.5-flash")
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.8,
                "top_p": 0.95,
                "max_output_tokens": 6000,
            }
        )
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
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "top_p": 0.95,
                "repeat_penalty": 1.15,
            }
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()
