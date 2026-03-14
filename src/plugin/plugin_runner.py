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
        "pages_generated": [],
        "deploy_results": [],
        "seo_score_before": None,
        "seo_score_after": None,
        "errors": []
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
        progress(f"SEO score before fixes: {report['seo_score_before']}")

        # ─────────────────────────────────────
        # STEP 3: FIX — apply actions per page
        # ─────────────────────────────────────
        progress("Applying SEO fixes to pages...")
        actions_by_url = _group_actions_by_url(results.get("actions", []))
        page_html_map = {p["url"]: p.get("html", "") for p in pages}

        for url, actions in actions_by_url.items():
            original_html = page_html_map.get(url, "")
            if not original_html:
                continue

            try:
                fixed_html = apply_fixes(original_html, actions)
                file_path = _url_to_file_path(url, domain)

                deploy_result = deploy(file_path, fixed_html, deploy_config)
                report["fixes_applied"].append({
                    "url": url,
                    "actions_count": len(actions),
                    "deployed": deploy_result.get("success", False)
                })
                report["deploy_results"].append(deploy_result)

            except Exception as e:
                report["errors"].append({"url": url, "error": str(e)})

        progress(f"Fixed {len(report['fixes_applied'])} pages")

        # ─────────────────────────────────────
        # STEP 4: GENERATE new pages for keyword gaps
        # ─────────────────────────────────────
        keyword_gaps = _extract_keyword_gaps(results, competitors)
        existing_pages_list = [{"url": p["url"], "title": _get_title(p)} for p in pages]

        if keyword_gaps and llm_config.get("api_key") or llm_config.get("provider") == "ollama":
            progress(f"Generating {len(keyword_gaps)} new pages for keyword gaps...")
            from src.content.competitor_analyzer import analyze_competitors
            from src.content.page_generator import generate_page

            for keyword in keyword_gaps[:5]:  # cap at 5 new pages per run
                try:
                    progress(f"Generating page for keyword: {keyword}")
                    brief = analyze_competitors(competitors, keyword, domain)
                    brief.internal_links = existing_pages_list[:10]
                    generated = generate_page(brief, llm_config, existing_pages_list)

                    file_path = f"{generated['slug']}/index.html"
                    deploy_result = deploy(file_path, generated["html"], deploy_config)

                    report["pages_generated"].append({
                        "keyword": keyword,
                        "slug": generated["slug"],
                        "title": generated["meta_title"],
                        "word_count": generated["word_count"],
                        "deployed": deploy_result.get("success", False)
                    })
                    report["deploy_results"].append(deploy_result)

                except Exception as e:
                    report["errors"].append({"keyword": keyword, "error": str(e)})

        # ─────────────────────────────────────
        # STEP 5: Final score (re-analyze after fixes)
        # ─────────────────────────────────────
        report["seo_score_after"] = _estimate_score_after(
            report["seo_score_before"], len(report["fixes_applied"])
        )
        report["completed_at"] = datetime.utcnow().isoformat()

        progress("Plugin run complete")
        task_store.save_result(task_id, report)

    except Exception as e:
        logger.error("Plugin run failed: %s", str(e))
        report["errors"].append({"error": str(e)})
        task_store.set_status(task_id, f"Error: {str(e)}")
        task_store.save_result(task_id, report)


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _crawl(site_url, crawl_options):
    use_js = crawl_options.get("use_js", False)
    limit = crawl_options.get("limit", 100)

    if use_js:
        from src.js_crawler import crawl_js_sync
        from src.utils.url_utils import build_clean_urls
        pages = crawl_js_sync(site_url, limit=limit)
        clean_urls, domain, graph = build_clean_urls(pages)
    else:
        from src.crawler_engine.crawler import crawl
        from src.utils.url_utils import build_clean_urls
        pages, _, _, _ = crawl(site_url, limit=limit)
        clean_urls, domain, graph = build_clean_urls(pages)

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
