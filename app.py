import os
import concurrent.futures
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

# Core modules
from src.crawler import crawl
from src.js_crawler import crawl_js_sync  # optional fallback
from src.extractor import extract_metadata
from src.normalizer import normalize
from src.filter import is_valid
from src.generator import generate_sitemaps
from src.sitemap_parser import get_sitemap_urls
# Audit modules
from src.audit import generate_audit_report
from src.fixer import fix_urls, generate_fix_report

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# -----------------------------
# URL CLEANING LOGIC (IMPROVED)
# -----------------------------
def build_clean_urls(pages, fix_canonical=False):
    clean = set()

    for p in pages:
        meta = extract_metadata(p)

        if not is_valid(meta):
            continue

        chosen = meta["url"]

        if fix_canonical:
            canonical = meta.get("canonical")
            if canonical and canonical.startswith("http"):
                chosen = canonical

        # remove query params (important for SEO)
        chosen = chosen.split("?")[0]

        try:
            clean.add(normalize(chosen))
        except:
            continue

    return list(clean)


# -----------------------------
# HOME ROUTE
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -----------------------------
# MAIN GENERATE ROUTE
# -----------------------------
@app.post("/generate", response_class=HTMLResponse)
def generate(
    request: Request,
    domain: str = Form(...),
    limit: int = Form(50),
    use_js: bool = Form(False),
    fix_canonical: bool = Form(False),
):
    try:
        # 1. Crawl
        pages = crawl(domain, limit=limit)

        # 2. Add sitemap URLs
        sitemap_urls = get_sitemap_urls(domain)
        for url in sitemap_urls:
            pages.append({
                "url": url,
                "status": 200,
                "html": ""
            })

        # 3. Clean URLs
        clean_urls = build_clean_urls(pages, fix_canonical)

        # ✅ 4. GENERATE AUDIT (THIS WAS MISSING / WRONG)
        audit = generate_audit_report(pages, clean_urls)

        # 5. Apply fixes
        fixed_urls = fix_urls(clean_urls)

        # 6. Generate sitemap
        files = generate_sitemaps(fixed_urls, base_url=domain)

        # ✅ 7. GENERATE FIXES LIST
        fixes_applied = generate_fix_report(audit)

        # 🔥 DEBUG PRINT (you will see this in terminal)
        print("AUDIT:", audit)
        print("FIXES:", fixes_applied)

        return templates.TemplateResponse("index.html", {
            "request": request,
            "files": files,
            "count": len(fixed_urls),
            "audit": audit,
            "fixes": fixes_applied,
            "debug": "WORKING"
        })

    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": str(e)
        })


# -----------------------------
# DOWNLOAD ROUTE
# -----------------------------
@app.get("/download")
def download_file(file: str):
    file_path = os.path.abspath(file)
    return FileResponse(file_path, filename=os.path.basename(file_path))
