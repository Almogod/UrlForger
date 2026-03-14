from src.services.extractor import extract_metadata
from src.services.normalizer import normalize
from src.services.filter import is_valid
from src.utils.logger import logger

def build_clean_urls(pages, fix_canonical=False):
    """
    Extracts, validates, and normalizes URLs from the raw crawled pages.
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
                    
            chosen = chosen.split("?")[0]
            normalized = normalize(chosen)
            if normalized:
                clean.add(normalized)
        except Exception as e:
            logger.error(f"Error processing URL {p.get('url', 'unknown')}: {str(e)}")
            continue
            
    return sorted(list(clean))
