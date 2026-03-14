import os
import sys
import asyncio
import time
import uuid
import concurrent.futures
from typing import Optional, Union

from fastapi import FastAPI, Form, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Core modules
from src.config import config
from src.crawler_engine.crawler import crawl
from src.crawler_engine.js_crawler import crawl_js_sync
from src.utils.url_utils import build_clean_urls
from src.services.task_store import task_store
from src.services.sitemap_parser import get_sitemap_urls
from src.services.generator import generate_sitemaps
from src.engine.engine import run_engine
from src.automation.automation_engine import run_automation
from src.plugin.plugin_runner import run_plugin

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title=config.APP_NAME)
templates = Jinja2Templates(directory="templates")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )

@app.get("/progress")
def get_progress(task_id: str):
    task_info = task_store.get_status(task_id)
    return {
        "status": task_info.get("status_msg", "Starting..."),
        "state": task_info.get("status", "running"),
        "error": task_info.get("error", None)
    }

def run_analysis_task(task_id: str, domain: str, limit: int, use_js: bool, fix_canonical: bool):
    try:
        task_store.set_status(task_id, "Crawling website pages...")
        
        if use_js:
            pages = crawl_js_sync(domain, limit=limit)
            graph = None
        else:
            pages, graph = crawl(domain, limit=limit)
        
        task_store.set_status(task_id, "Checking existing sitemap...")
        sitemap_urls = get_sitemap_urls(domain)
        for url in sitemap_urls:
            pages.append({"url": url, "status": 200, "html": ""})

        pages.sort(key=lambda x: x.get("url", ""))

        task_store.set_status(task_id, "Cleaning URLs...")
        clean_urls, domain_detected, graph_parsed = build_clean_urls(pages, fix_canonical)

        def engine_progress(msg):
            task_store.set_status(task_id, msg)

        # 1. Run Engine (Now includes all 20 modules via updated registry/planner)
        engine_result = run_engine(pages, clean_urls, domain, graph_parsed, progress_callback=engine_progress)

        # 2. Run Automation
        task_store.set_status(task_id, "Running Automations...")
        actions = engine_result.get("actions", [])
        
        automation_config = {
            "platform": config.AUTOMATION_PLATFORM,
            "github_token": config.GITHUB_TOKEN,
            "repo": config.GITHUB_REPO,
            "branch": config.GITHUB_BRANCH
        }
        automation_result = run_automation(actions, automation_config)

        # 3. Generate Files
        task_store.set_status(task_id, "Finalizing...")
        fixed_urls = engine_result.get("fixed_urls", [])
        files = generate_sitemaps(fixed_urls, base_url=domain)

        # 4. Save Results
        final_results = {
            "files": files,
            "count": len(clean_urls),
            "engine_result": engine_result,
            "automation_result": automation_result
        }
        task_store.save_results(task_id, final_results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        task_store.set_status(task_id, f"Error: {str(e)}", error=str(e))

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
def generate(
    background_tasks: BackgroundTasks,
    domain: str = Form(...),
    limit: int = Form(50),
    use_js: bool = Form(False),
    task_id: Optional[str] = Form(None)
):
    if not task_id:
        task_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_analysis_task, 
        task_id=task_id, 
        domain=domain, 
        limit=limit, 
        use_js=use_js, 
        fix_canonical=False
    )
    return JSONResponse(content={"status": "started", "task_id": task_id})

# ─────────────────────────────────────────────────────────
# PLUGIN ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.post("/plugin/run")
def run_plugin_task(
    background_tasks: BackgroundTasks,
    site_url: str = Form(...),
    competitors: str = Form(""),
    limit: int = Form(100),
    openai_key: Optional[str] = Form(None),
    gemini_key: Optional[str] = Form(None),
    ollama_host: Optional[str] = Form(None),
    task_id: Optional[str] = Form(None)
):
    if not task_id:
        task_id = str(uuid.uuid4())[:10]
    task_store.set_status(task_id, "In Progress")
    
    comp_list = [c.strip() for c in competitors.split(",") if c.strip()]
    
    # Configure LLM
    llm_config = {
        "provider": "openai" if openai_key else ("gemini" if gemini_key else "ollama"),
        "api_key": openai_key or gemini_key,
        "ollama_host": ollama_host or "http://localhost:11434"
    }

    background_tasks.add_task(
        run_plugin, 
        site_url=site_url, 
        task_id=task_id,
        competitors=comp_list,
        llm_config=llm_config,
        crawl_options={"limit": limit},
        deploy_config={} # Empty until approved
    )
    
    return JSONResponse(content={"status": "started", "task_id": task_id})

@app.post("/plugin/approve")
def approve_plugin_fixes(
    background_tasks: BackgroundTasks,
    task_id: str = Form(...),
    approved_actions: str = Form(""), # comma separated IDs
    approved_pages: str = Form(""),   # comma separated keywords
    github_token: str = Form(None),
    ftp_host: str = Form(None),
    ftp_user: str = Form(None),
    ftp_pass: str = Form(None),
    webhook_url: str = Form(None)
):
    action_ids = [a.strip() for a in approved_actions.split(",") if a.strip()]
    page_keywords = [p.strip() for p in approved_pages.split(",") if p.strip()]
    
    deploy_config = {
        "github_token": github_token,
        "ftp_host": ftp_host,
        "ftp_user": ftp_user,
        "ftp_pass": ftp_pass,
        "webhook_url": webhook_url
    }
    
    from src.plugin.plugin_runner import apply_approved_plugin_fixes
    background_tasks.add_task(
        apply_approved_plugin_fixes,
        task_id=task_id,
        approved_action_ids=action_ids,
        approved_page_keywords=page_keywords,
        deploy_config=deploy_config
    )
    
    return JSONResponse(content={"status": "deployment_started", "task_id": task_id})

@app.get("/results", response_class=HTMLResponse)
def show_results(request: Request, task_id: str):
    task_info = task_store.get_status(task_id)
    
    if task_info.get("status") == "error":
        return templates.TemplateResponse("index.html", {"request": request, "error": task_info.get("error")})
        
    results = task_store.get_results(task_id)
    if not results:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Results not found or task incomplete."})

    is_plugin = "seo_score_before" in results
    engine_result = results.get("engine_result", {}) if is_plugin else results.get("engine_result", {})
    modules = engine_result.get("modules", {})
    
    ctx = {
        "request": request,
        "task_id": task_id,
        "is_plugin": is_plugin,
        "plugin_report": results if is_plugin else None,
        "engine_result": engine_result,
        "seo_score": results.get("seo_score_after") or engine_result.get("seo_score", 0),
        "actions": results.get("suggested_actions") or engine_result.get("actions", []),
        "meta_issues": modules.get("meta", {}).get("issues", []),
        "image_issues": modules.get("image_seo", {}).get("issues", []),
        "core_issues": modules.get("core_web_vitals", {}).get("issues", []),
        "speed_issues": modules.get("page_speed", {}).get("issues", []),
        "heading_issues": modules.get("heading_structure", {}).get("issues", []),
        "og_issues": modules.get("open_graph", {}).get("issues", []),
        "quality_issues": modules.get("content_quality", {}).get("issues", []),
        "mobile_issues": modules.get("mobile_seo", {}).get("issues", []),
        "experience_issues": modules.get("page_experience", {}).get("issues", []),
        "schema_issues": modules.get("structured_data_validator", {}).get("issues", []),
        "hreflang_issues": modules.get("hreflang", {}).get("issues", []),
        "link_issues": modules.get("broken_links", {}).get("issues", []),
        "keyword_gap": modules.get("keyword_gap", {}).get("keyword_gap", {}),
        "site_keywords": modules.get("keyword_gap", {}).get("site_keywords", []),
        "pages_generated": results.get("pages_generated", [])
    }
    
    return templates.TemplateResponse("index.html", ctx)

@app.get("/plugin/download_report")
def download_plugin_report(task_id: str):
    results = task_store.get_results(task_id)
    if not results:
        return JSONResponse(status_code=404, content={"error": "Report not found"})
    
    from src.utils.pdf_generator import generate_seo_pdf
    report_file = f"seo_report_{task_id}.pdf"
    file_path = os.path.join(os.getcwd(), report_file)
    
    generate_seo_pdf(results, file_path)
    return FileResponse(file_path, filename=report_file)

@app.get("/download")
def download_file(file: str):
    return FileResponse(os.path.abspath(file), filename=os.path.basename(file))