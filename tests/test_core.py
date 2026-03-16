import pytest
from src.utils.framework_detector import detect_framework
from src.services.auth import create_access_token

def test_framework_detection():
    html = '<script id="__NEXT_DATA__">{}</script>'
    headers = {"X-Powered-By": "Next.js"}
    assert detect_framework(headers, html, "https://example.com") == "next.js"

    # Test Next.js ISR detection
    isr_html = "<div>/api/revalidate</div>"
    assert detect_framework({"Server": "Vercel"}, isr_html, "https://example.com") == "next.js-isr"

def test_auth_token_creation():
    token = create_access_token({"sub": "admin", "role": "admin"})
    assert isinstance(token, str)
    assert len(token) > 20
