import os
import time
import uuid
import concurrent.futures
from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

# Core modules
from src.crawler_engine.crawler import crawl
from src.crawler_engine.js_crawler import crawl_js_sync
from src.utils.url_utils import build_clean_urls
from src.services.task_store import task_store
from src.config import config
from src.services.sitemap_parser import get_sitemap_urls
from src.services.generator import generate_sitemaps
from src.engine.engine import run_engine
from src.automation.automation_engine import run_automation
from src.plugin.plugin_runner import run_plugin

app = FastAPI(title=config.APP_NAME)
templates = Jinja2Templates(directory="templates")

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
    domain: str = Form(...),
    limit: int = Form(50),
    use_js: bool = Form(False),
    fix_canonical: bool = Form(False),
    task_id: str = Form(None),
    background_tasks: BackgroundTasks = None
):
    if not task_id:
        task_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_analysis_task, 
        task_id=task_id, 
        domain=domain, 
        limit=limit, 
        use_js=use_js, 
        fix_canonical=fix_canonical
    )
    return JSONResponse(content={"status": "started", "task_id": task_id})

# ─────────────────────────────────────────────────────────
# PLUGIN ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.post("/plugin/run")
def plugin_run(
    domain: str = Form(...),
    limit: int = Form(50),
    use_js: bool = Form(False),
    competitors: str = Form(""), # comma separated
    task_id: str = Form(None),
    background_tasks: BackgroundTasks = None
):
    if not task_id:
        task_id = str(uuid.uuid4())
    
    comp_list = [c.strip() for c in competitors.split(",") if c.strip()]
    
    deploy_config = {
        "platform": config.AUTOMATION_PLATFORM,
        "github_token": config.GITHUB_TOKEN,
        "github_repo": config.GITHUB_REPO,
        "github_branch": config.GITHUB_BRANCH,
        "ftp_host": config.FTP_HOST,
        "ftp_user": config.FTP_USER,
        "ftp_password": config.FTP_PASSWORD,
        "webhook_url": config.WEBHOOK_URL
    }
    
    llm_config = {
        "provider": config.LLM_PROVIDER,
        "api_key": config.OPENAI_API_KEY if config.LLM_PROVIDER == "openai" else config.GEMINI_API_KEY,
        "ollama_host": config.OLLAMA_HOST
    }
    
    crawl_options = {
        "use_js": use_js,
        "limit": limit,
        "timeout": config.CRAWL_TIMEOUT
    }
    
    background_tasks.add_task(
        run_plugin,
        site_url=domain,
        task_id=task_id,
        deploy_config=deploy_config,
        llm_config=llm_config,
        competitors=comp_list,
        crawl_options=crawl_options
    )
    
    return JSONResponse(content={"status": "started", "task_id": task_id})

@app.get("/results", response_class=HTMLResponse)
def show_results(request: Request, task_id: str):
    task_info = task_store.get_status(task_id)
    
    if task_info.get("status") == "error":
        return templates.TemplateResponse("index.html", {"request": request, "error": task_info.get("error")})
        
    results = task_store.get_results(task_id)
    if not results:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Results not found or task incomplete."})

    # The results from run_plugin are slightly different from run_analysis_task
    # We unify them for the template or pass them directly
    if "seo_score_before" in results:
        # This is a plugin run result
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "plugin_report": results,
                "seo_score": results.get("seo_score_after", 0),
                "is_plugin": True
            }
        )

    engine_result = results.get("engine_result", {})
    modules = engine_result.get("modules", {})
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "files": results.get("files", []),
            "count": results.get("count", 0),
            "engine_result": engine_result,
            "automation_result": results.get("automation_result", {}),
            # Modules
            "meta_issues": modules.get("meta", {}).get("issues", []),
            "image_issues": modules.get("image_seo", {}).get("issues", []),
            "core_issues": modules.get("core_web_vitals", {}).get("issues", []),
            "link_issues": modules.get("internal_links", {}).get("issues", {}),
            "speed_issues": modules.get("page_speed", {}).get("issues", []),
            "heading_issues": modules.get("heading_structure", {}).get("issues", []),
            "og_issues": modules.get("open_graph", {}).get("issues", []),
            "quality_issues": modules.get("content_quality", {}).get("issues", []),
            "mobile_issues": modules.get("mobile_seo", {}).get("issues", []),
            "experience_issues": modules.get("page_experience", {}).get("issues", []),
            "schema_issues": modules.get("structured_data_validator", {}).get("issues", []),
            "hreflang_issues": modules.get("hreflang", {}).get("issues", []),
            
            "keyword_gap": modules.get("keyword_gap", {}).get("keyword_gap", {}),
            "site_keywords": modules.get("keyword_gap", {}).get("site_keywords", []),
            
            "actions": engine_result.get("actions", []),
            "seo_score": engine_result.get("seo_score", 0)
        }
    )

@app.get("/download")
def download_file(file: str):
    return FileResponse(os.path.abspath(file), filename=os.path.basename(file))