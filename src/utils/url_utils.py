import socket
import ipaddress
from urllib.parse import urlparse
from src.services.extractor import extract_metadata
from src.services.normalizer import normalize
from src.services.filter import is_valid
from src.utils.logger import logger

def is_ssrf_safe(url: str) -> bool:
    """
    Checks if a URL is safe from SSRF by validating the resolved IP is not private/local.
    """
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False
            
        # Resolve hostname to IP
        ip_addr = socket.gethostbyname(parsed.hostname)
        ip_obj = ipaddress.ip_address(ip_addr)
        
        # Block private, loopback, and link-local addresses
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            logger.warning(f"SSRF Attempt Blocked: {url} resolved to {ip_addr}")
            return False
            
        return True
    except Exception as e:
        logger.debug(f"SSRF validation failed for {url}: {e}")
        return False

def build_clean_urls(pages, fix_canonical=False):
    """
    Extracts, validates, and normalizes URLs with SSRF protection.
    """
    clean = set()
    for p in pages:
        try:
            meta = extract_metadata(p)
            if not is_valid(meta):
                continue
            
            chosen = meta["url"]
            if fix_canonical:
                canonical = meta.get("canonical")
                if canonical and canonical.startswith("http"):
                    chosen = canonical
            
            # 1. Basic Protocol Check
            if not chosen.startswith(('http://', 'https://')):
                continue
                
            # 2. SSRF Protection
            if not is_ssrf_safe(chosen):
                continue

            # 3. Normalization
            normalized = normalize(chosen.split("?")[0])
            if normalized:
                clean.add(normalized)
        except Exception as e:
            logger.error(f"Error processing URL {p.get('url', 'unknown')}: {str(e)}")
            continue
            
    return sorted(list(clean))
