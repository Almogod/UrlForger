import pytest
from src.utils.framework_detector import detect_framework, detect_rendering_mode
from src.services.auth import create_access_token

def test_framework_detection():
    html = '<script id="__NEXT_DATA__">{}</script>'
    headers = {"X-Powered-By": "Next.js"}
    assert detect_framework(headers, html) == "next.js"

def test_rendering_mode():
    html = '<body><div>Highly informative content with many words that should trigger SSR detection.</div></body>'
    assert detect_rendering_mode(html) == "ssr-or-static"
    
    csr_html = '<body><script src="bundle.js"></script></body>'
    assert detect_rendering_mode(csr_html) == "client-side-only"

def test_auth_token_creation():
    token = create_access_token({"sub": "admin", "role": "admin"})
    assert isinstance(token, str)
    assert len(token) > 20
