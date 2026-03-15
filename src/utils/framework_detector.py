from bs4 import BeautifulSoup
from typing import Dict, Optional

def detect_framework(headers: Dict[str, str], html: str) -> str:
    """
    Detects the web framework used by a site.
    """
    # 1. Check headers
    server = headers.get("Server", "").lower()
    powered_by = headers.get("X-Powered-By", "").lower()
    
    if "next.js" in powered_by or "next" in powered_by:
        return "next.js"
    if "nuxt" in powered_by:
        return "nuxt.js"
        
    # 2. Check HTML for specific footprint
    soup = BeautifulSoup(html, "lxml")
    
    # Next.js
    if soup.find("script", id="__NEXT_DATA__"):
        return "next.js"
        
    # Nuxt.js
    if soup.find("div", id="__nuxt"):
        return "nuxt.js"
        
    # Astro
    if soup.find("astro-island"):
        return "astro"
        
    return "unknown"

def detect_rendering_mode(html: str) -> str:
    """
    Heuristic to detect if a page is SSR, static, or client-side only.
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    if not body:
        return "unknown"
        
    # If body is mostly empty but has scripts, likely CSR
    text_content = body.get_text(strip=True)
    if len(text_content) < 100 and soup.find_all("script"):
        return "client-side-only"
        
    return "ssr-or-static"

def validate_i18n(html: str) -> Dict[str, bool]:
    """Checks for presence of hreflang or html lang attribute."""
    soup = BeautifulSoup(html, "lxml")
    return {
        "has_lang_attr": bool(soup.find("html", lang=True)),
        "has_hreflang": bool(soup.find("link", rel="alternate", hreflang=True))
    }
