# src/plugin/plugin_runner.py
"""
Orchestrates the full autonomous SEO plugin lifecycle:
  1. CRAWL  — crawl all pages of the target site
  2. ANALYZE — run all SEO analysis modules
  3. FIX    — apply all fixes to page HTML via html_rewriter
  4. GENERATE — create new pages for keyword gaps using the AI engine
  5. DEPLOY  — push all changes to the target platform
  6. REPORT  — produce a structured results/report object
"""

import uuid
from datetime import datetime
from src.engine.engine import run_engine
from src.services.html_rewriter import apply_fixes
from src.services.deployer import deploy
from src.services.task_store import TaskStore
from src.utils.logger import logger


task_store = TaskStore()


def run_plugin(
    site_url: str,
    task_id: str,
    deploy_config: dict,
    llm_config: dict,
    competitors: list,
    crawl_options: dict
):
    """
    Full autonomous SEO plugin run.

    Args:
        site_url:      Root URL of the target site
        task_id:       Unique ID for progress tracking
        deploy_config: Platform config for deployer (platform, credentials, etc.)
        llm_config:    LLM config for page generation (provider, api_key, model)
        competitors:   List of competitor domain URLs
        crawl_options: dict with: use_js, limit, timeout
    """

    def progress(msg):
        logger.info("[plugin:%s] %s", task_id, msg)
        task_store.set_status(task_id, msg)

    report = {
        "task_id": task_id,
        "site_url": site_url,
        "started_at": datetime.utcnow().isoformat(),
        "fixes_applied": [],
        "suggested_actions": [],
        "pages_generated": [],
        "deploy_results": [],
        "seo_score_before": None,
        "seo_score_after": None,
        "engine_result": None,
        "errors": [],
        "state": "pending_approval"
    }

    try:
        # ─────────────────────────────────────
        # STEP 1: CRAWL
        # ─────────────────────────────────────
        progress("Crawling site...")
        pages, clean_urls, domain, graph = _crawl(site_url, crawl_options)
        progress(f"Crawled {len(pages)} pages")

        # ─────────────────────────────────────
        # STEP 2: ANALYZE (run engine with all modules)
        # ─────────────────────────────────────
        progress("Running SEO analysis engine...")
        results = run_engine(
            pages=pages,
            clean_urls=clean_urls,
            domain=domain,
            graph=graph,
            competitors=competitors,
            progress_callback=progress
        )
        report["seo_score_before"] = results.get("seo_score", 0)
        report["engine_result"] = results
        
        # Collect all suggested actions for user review
        report["suggested_actions"] = results.get("actions", [])
        
        progress(f"SEO score analyzed: {report['seo_score_before']}")

        # ─────────────────────────────────────
        # STEP 3: GENERATE content briefs (don't deploy yet)
        # ─────────────────────────────────────
        keyword_gaps = _extract_keyword_gaps(results, competitors)
        existing_pages_list = [{"url": p["url"], "title": _get_title(p)} for p in pages]

        if keyword_gaps and (llm_config.get("api_key") or llm_config.get("provider") == "ollama"):
            progress(f"Analyzing {len(keyword_gaps)} keyword gaps for content generation...")
            from src.content.competitor_analyzer import analyze_competitors
            from src.content.page_generator import generate_page

            for keyword in keyword_gaps[:5]:  # cap at 5 new pages per run
                try:
                    progress(f"Generating content for keyword: {keyword}")
                    brief = analyze_competitors(competitors, keyword, domain)
                    brief.internal_links = existing_pages_list[:10]
                    generated = generate_page(brief, llm_config, existing_pages_list)

                    # Add to suggested pages list
                    report["pages_generated"].append({
                        "keyword": keyword,
                        "slug": generated["slug"],
                        "title": generated["meta_title"],
                        "word_count": generated["word_count"],
                        "html": generated["html"], # Store for deployment later
                        "approved": True
                    })

                except Exception as e:
                    report["errors"].append({"keyword": keyword, "error": str(e)})

        progress("Analysis complete. Waiting for user approval.")
        task_store.set_status(task_id, "Pending Approval")
        task_store.save_results(task_id, report)

    except Exception as e:
        logger.error("Plugin run failed: %s", str(e))
        report["errors"].append({"error": str(e)})
        task_store.set_status(task_id, f"Error: {str(e)}")
        task_store.save_results(task_id, report)


def apply_approved_plugin_fixes(task_id, approved_action_ids, approved_page_keywords, deploy_config):
    """
    Second phase of the plugin: apply only WHAT the user approved.
    """
    from urllib.parse import urlparse

    task_store = TaskStore()
    report = task_store.get_results(task_id)
    if not report:
        return

    def progress(msg):
        logger.info("[plugin-apply:%s] %s", task_id, msg)
        task_store.set_status(task_id, msg)

    report["state"] = "deploying"
    
    try:
        # 1. Apply HTML Fixes
        suggested = report.get("suggested_actions", [])
        # We use the loop index (str) as the ID provided by the UI
        actions = []
        for idx_str in approved_action_ids:
            try:
                idx = int(idx_str)
                if 0 <= idx < len(suggested):
                    actions.append(suggested[idx])
            except ValueError:
                continue

        # Get pages from engine_result
        engine_result = report.get("engine_result", {})
        pages = engine_result.get("pages", [])
        page_html_map = {p["url"]: p.get("html", "") for p in pages}
        domain = urlparse(report["site_url"]).netloc

        progress(f"Deploying {len(actions)} approved fixes...")
        
        actions_by_url = _group_actions_by_url(actions)
        for url, url_actions in actions_by_url.items():
            original_html = page_html_map.get(url, "")
            if not original_html:
                # If HTML is missing from engine_result, we can't apply fixes locally
                # In a real scenario, we might re-fetch, but for this plugin we assume engine_result has it
                continue
            
            fixed_html = apply_fixes(original_html, url_actions)
            file_path = _url_to_file_path(url, domain)
            deploy_result = deploy(file_path, fixed_html, deploy_config)
            report["fixes_applied"].append({"url": url, "actions": len(url_actions)})

        # 2. Deploy Generated Pages
        pages_to_gen = [p for p in report.get("pages_generated", []) if p["keyword"] in approved_page_keywords]
        progress(f"Deploying {len(pages_to_gen)} new pages...")
        
        for pg in pages_to_gen:
            file_path = f"{pg['slug']}/index.html"
            deploy(file_path, pg["html"], deploy_config)
            pg["deployed"] = True

        report["state"] = "completed"
        report["completed_at"] = datetime.utcnow().isoformat()
        progress("Deployment finished successfully.")
        task_store.save_results(task_id, report)

    except Exception as e:
        logger.error("Deployment failed: %s", str(e))
        task_store.set_status(task_id, f"Deployment Error: {str(e)}")
        # Save the partial report even on error
        task_store.save_results(task_id, report)


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _crawl(site_url, crawl_options):
    from urllib.parse import urlparse
    from src.utils.url_utils import build_clean_urls
    
    use_js = crawl_options.get("use_js", False)
    limit = crawl_options.get("limit", 100)
    domain = urlparse(site_url).netloc

    if use_js:
        from src.crawler_engine.js_crawler import crawl_js_sync
        from src.crawler_engine.graph import CrawlGraph
        pages = crawl_js_sync(site_url, limit=limit)
        graph = CrawlGraph()
    else:
        from src.crawler_engine.crawler import crawl
        pages, graph = crawl(site_url, limit=limit)
        
    clean_urls = build_clean_urls(pages)

    return pages, clean_urls, domain, graph


def _group_actions_by_url(actions):
    by_url = {}
    for action in actions:
        url = action.get("url")
        if url:
            by_url.setdefault(url, []).append(action)
    return by_url


def _url_to_file_path(url, domain):
    path = url.replace(domain, "").strip("/")
    if not path:
        return "index.html"
    if not path.endswith(".html"):
        path = f"{path}/index.html"
    return path


def _extract_keyword_gaps(results, competitors):
    if not competitors:
        return []
    keyword_gap_result = results.get("modules", {}).get("keyword_gap", {})
    gaps = keyword_gap_result.get("keyword_gap", {})
    all_gaps = []
    for kw_list in gaps.values():
        all_gaps.extend(kw_list)
    # Deduplicate
    seen = set()
    unique = []
    for kw in all_gaps:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _get_title(page):
    from bs4 import BeautifulSoup
    html = page.get("html", "")
    if not html:
        return page.get("url", "")
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("title")
    return title.text.strip() if title else page.get("url", "")


def _estimate_score_after(score_before, fixes_count):
    """Estimate improved score — each fix gives a small boost."""
    if score_before is None:
        return None
    improvement = min(fixes_count * 2, 30)  # cap at +30 points
    return min(score_before + improvement, 100)
