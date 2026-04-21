import asyncio
import httpx
import json
from src.crawler_engine.fetcher import fetch
from src.utils.text_processor import clean_html, chunk_text
from src.content.page_generator import _call_openai, _call_gemini, _call_ollama, _extract_json_from_llm
from src.config import config
from src.utils.logger import logger

async def process_site_homepage(url: str):
    """
    Scrapes the homepage, cleans it, chunks it, and structures the business analysis.
    """
    logger.info(f"Analysis Pipeline: Starting process for {url}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        result = await fetch(client, url)
        
    if result.get("status") != 200:
        logger.error(f"Failed to fetch {url}: {result.get('error')}")
        return {"error": f"Failed to fetch: {result.get('status')}"}
    
    html = result.get("html", "")
    return await process_html_content(url, html)

async def process_html_content(url: str, html: str):
    """
    Cleans, chunks, and structures the business analysis from provided HTML.
    """
    clean_text = clean_html(html)
    chunks = chunk_text(clean_text, chunk_size=4000)
    
    logger.info(f"Extracted {len(chunks)} chunks for analysis.")
    
    structured_data = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
        extracted = await structure_business_chunk(chunk)
        if extracted:
            structured_data.append(extracted)
            
    return {
        "url": url,
        "raw_text_length": len(clean_text),
        "chunk_count": len(chunks),
        "structured_data": structured_data
    }

async def structure_business_chunk(chunk: str):
    """
    Sends a chunk to the LLM to extract business-specific data points.
    """
    prompt = f"""### BUSINESS DATA EXTRACTION TASK ###
Analyze the following website content chunk and extract key business information in STRICT JSON format.

CHUNK CONTENT:
{chunk}

STRICT JSON OUTPUT:
{{
  "core_services": ["list of services offered"],
  "value_propositions": ["unique selling points"],
  "target_audience": ["who is this for?"],
  "technologies_mentioned": ["tools, stacks, or tech"],
  "company_info": {{
    "name": "extracted company name",
    "mission": "philosophy or mission",
    "contact_info": ["emails, phones, etc."]
  }},
  "key_findings": ["any other important business facts"]
}}
"""
    
    llm_config = {
        "provider": config.LLM_PROVIDER,
        "api_key": config.OPENAI_API_KEY.get_secret_value() if config.OPENAI_API_KEY else None,
        "gemini_key": config.GEMINI_API_KEY.get_secret_value() if config.GEMINI_API_KEY else None,
        "model": "gpt-4o-mini" if config.LLM_PROVIDER == "openai" else "gemini-1.5-flash"
    }

    # Ensure provider key is set for the call functions Expectation
    if llm_config["provider"] == "gemini":
        llm_config["api_key"] = llm_config["gemini_key"]

    try:
        raw_res = ""
        if llm_config["provider"] == "openai":
            raw_res = _call_openai(prompt, llm_config)
        elif llm_config["provider"] == "gemini":
            raw_res = _call_gemini(prompt, llm_config)
        elif llm_config["provider"] == "ollama":
            raw_res = _call_ollama(prompt, llm_config)
            
        return _extract_json_from_llm(raw_res)
    except Exception as e:
        logger.error(f"Chunk structuring failed: {e}")
        return None
