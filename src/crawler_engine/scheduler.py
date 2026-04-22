import asyncio
import httpx
import base64
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin
from .fetcher import fetch
from src.config import config
from src.utils.logger import logger


class USER_AGENTS:
    chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    googlebot = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    googlebot_mobile = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    bingbot = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"


async def run_workers(
    frontier, parser, graph,
    start_url=None, progress_callback=None,
    limit=200, concurrency=10, delay=1.0,
    check_robots=True, extra_headers=None,
    broken_links_only=False, max_depth=10,
    crawl_assets=False, custom_selectors=None,
    user_agent="chrome"
):
    from .frontier import ensure_scheme, is_internal_domain

    # --- GitHub Surgical Filtering ---
    is_github = "github.com" in (start_url or "").lower()
    
    # Ensure we use a scheme-aware URL for ID extraction
    start_url_norm = ensure_scheme(start_url) if start_url else ""
    github_repo_path = urlparse(start_url_norm).path.strip("/") if is_github else ""
    
    # Only keep the first 2 parts of the path for repo identification (user/repo), lowercased
    github_repo_id = "/".join(github_repo_path.split("/")[:2]).lower() if is_github else ""

    results = []
    comp_url = ensure_scheme(start_url) if start_url else None

    # --- Robots.txt ---
    rp = None
    if check_robots:
        try:
            first_url = frontier.peek() if hasattr(frontier, "peek") else None
            if first_url:
                parsed = urlparse(first_url)
                robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
                async with httpx.AsyncClient(timeout=10) as rc:
                    resp = await rc.get(robots_url)
                    if resp.status_code == 200:
                        rp = RobotFileParser()
                        rp.parse(resp.text.splitlines())
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")

    # --- HTTP client headers ---
    headers = {}
    if config.CRAWLER_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {config.CRAWLER_BEARER_TOKEN}"
    elif config.CRAWLER_BASIC_AUTH:
        encoded = base64.b64encode(config.CRAWLER_BASIC_AUTH.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    headers["User-Agent"] = getattr(USER_AGENTS, user_agent, USER_AGENTS.chrome)
    if extra_headers:
        headers.update(extra_headers)

    mounts = {}
    if config.CRAWLER_PROXY:
        mounts = {"all://": httpx.AsyncHTTPTransport(proxy=config.CRAWLER_PROXY)}

    # --- Shared state ---
    # asyncio is single-threaded: no locks needed between non-awaited operations
    queue = asyncio.Queue()
    seen_urls = set()
    dispatched = 0  # total items ever enqueued (enforces limit)

    def enqueue(url, depth, priority):
        """Enqueue only if unseen and within limit. Safe - no await between check and add."""
        nonlocal dispatched
        
        # URL normalization for 'seen' check (GitHub is mostly case-insensitive for paths)
        url_check = url.lower() if is_github else url
        
        if url_check in seen_urls or dispatched >= limit:
            return

        # --- GitHub Surgical Filtering ---
        if is_github:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Ensure we stay within the same repo (surgical match)
            if github_repo_id not in path:
                logger.debug(f"[CRAWL_FILTER] Skipping {url} - out of repo scope ({github_repo_id})")
                return
                
            # Block noisy GitHub paths
            noise_patterns = [
                '/pulls', '/issues', '/commits', '/search', '/stargazers', 
                '/network', '/watchers', '/releases', '/actions', '/projects',
                '/wiki', '/security', '/pulse', '/graphs', '/settings', '/branches', '/tags'
            ]
            if any(p in path for p in noise_patterns):
                logger.debug(f"[CRAWL_FILTER] Skipping {url} - noisy GitHub path")
                return
            
            # If it's a file view (blob), allow common code and config extensions
            if '/blob/' in path:
                valid_exts = [
                    '.html', '.css', '.js', '.jsx', '.tsx', '.md', '.json', '.htm',
                    '.py', '.go', '.sh', '.yml', '.yaml', '.txt', '.c', '.cpp', '.h', '.rs',
                    '.xml', '.php', '.java', '.rb', '.ts', '.sql'
                ]
                if not any(path.endswith(ext) for ext in valid_exts):
                    logger.debug(f"[CRAWL_FILTER] Skipping {url} - non-relevant file extension")
                    return

        seen_urls.add(url_check)
        dispatched += 1
        queue.put_nowait({"url": url, "depth": depth, "priority": priority})

    # Seed from frontier
    while frontier.size() > 0:
        item = frontier.get()
        if item:
            enqueue(item["url"], item.get("depth", 0), item.get("priority", 0))

    async def worker(client):
        """
        Runs forever until cancelled. Blocks on queue.get().
        Never returns early — only exits via CancelledError from queue.join() cleanup.
        """
        while True:
            item = await queue.get()  # Block until an item is available
            url = item["url"]
            depth = item["depth"]
            priority = item.get("priority", 0)

            try:
                # Robots check — use a flag, not return/continue, to stay in the loop
                skip = False

                if rp and not rp.can_fetch("*", url):
                    logger.warning(f"Skipping {url} (robots.txt)")
                    skip = True

                if not skip:
                    if delay > 0:
                        await asyncio.sleep(delay)

                    page = await fetch(client, url, follow_redirects=False)

                    if page:
                        status = page.get("status")
                        final_url = page.get("final_url", url)
                        parsed_final = urlparse(final_url)

                        is_external = (
                            frontier.base_domain
                            and parsed_final.netloc
                            and not is_internal_domain(parsed_final.netloc, frontier.base_domain)
                        )

                        page.update({
                            "meta": {}, "headings": {}, "images": [], "videos": [],
                            "hreflangs": [], "custom": {}, "canonical": ""
                        })

                        # Redirects
                        if status in [301, 302, 303, 307, 308]:
                            location = page.get("headers", {}).get("location")
                            if location:
                                target_url = urljoin(url, location)
                                pt = urlparse(target_url)
                                target_ext = (
                                    frontier.base_domain
                                    and pt.netloc
                                    and not is_internal_domain(pt.netloc, frontier.base_domain)
                                )
                                if target_ext:
                                    page["redirect_to_external"] = target_url
                                else:
                                    frontier.add(target_url, depth=depth, priority=priority + 1)
                                    enqueue(target_url, depth, priority + 1)

                        # Record result
                        if broken_links_only:
                            if (comp_url and url == comp_url) or (status and status not in [200, 304]):
                                results.append(page)
                                logger.info(f"Fetched {url} ({status}). Broken: {len(results)}")
                            else:
                                logger.info(f"Fetched {url} ({status}). OK — skipped.")
                        else:
                            results.append(page)
                            count = len(results)
                            logger.info(f"Fetched {url} ({status}). Total: {count}/{limit}")
                            if progress_callback and count % 2 == 0:
                                display_url = url.replace("https://", "").replace("http://", "")[:35] + "..." if len(url) > 35 else url
                                progress_callback(f"Crawling: {count}/{limit} pages ({display_url})")

                        # Special Handling: GitHub UI Noise reduction
                        if "github.com" in parsed_final.netloc:
                            # Skip common UI paths that don't contain source code or relevant SEO content
                            ui_noise = ["/issues", "/pulls", "/actions", "/projects", "/wiki", "/security", "/pulse", "/network", "/settings", "/commits", "/branches", "/tags", "/stargazers", "/watchers", "/find/", "/search"]
                            if any(noise in final_url for noise in ui_noise):
                                logger.info(f"Skipping GitHub UI noise: {final_url}")
                                continue
                            
                            # Only crawl blobs (files) or trees (directories)
                            if "/blob/" not in final_url and "/tree/" not in final_url and final_url.count('/') > 4:
                                # This is a sub-page that isn't a file or folder (like a specific commit view)
                                continue

                        # Extract & enqueue links from successful HTML pages
                        if status == 200 and page.get("html") and not is_external and depth < max_depth:
                            extracted = parser(page["html"], page["url"], custom_selectors=custom_selectors)
                            page.update({
                                "hreflangs": extracted.get("hreflangs", []),
                                "images": extracted.get("images", []),
                                "videos": extracted.get("videos", []),
                                "canonical": extracted.get("canonical", ""),
                                "meta": extracted.get("meta", {}),
                                "headings": extracted.get("headings", {}),
                                "custom": extracted.get("custom", {}),
                            })

                            raw_links = extracted.get("links", [])
                            enqueued_count = 0
                            for link in raw_links:
                                graph.add_edge(page["url"], link)
                                pl = urlparse(link)
                                link_ext = (
                                    frontier.base_domain
                                    and pl.netloc
                                    and not is_internal_domain(pl.netloc, frontier.base_domain)
                                )
                                if not link_ext:
                                    before = len(seen_urls)
                                    frontier.add(link, depth=depth + 1, priority=10)
                                    enqueue(link, depth + 1, 10)
                                    if len(seen_urls) > before:
                                        enqueued_count += 1

                            logger.info(f"[DIAG] {url}: found {len(raw_links)} links, {enqueued_count} new internal queued. Q={queue.qsize()} dispatched={dispatched}/{limit}")
                            if crawl_assets:
                                for asset in extracted.get("assets", []):
                                    graph.add_edge(page["url"], asset)
                                    frontier.add(asset, depth=max_depth + 1, force_add=True, priority=5)
                                    enqueue(asset, max_depth + 1, 5)

            except asyncio.CancelledError:
                # Properly handle cancellation — mark done then re-raise
                queue.task_done()
                raise
            except Exception as e:
                logger.error(f"Worker error for {url}: {e}")
            finally:
                # Always mark the item as done so queue.join() can track progress
                # Note: CancelledError re-raises after task_done() above, won't reach here
                try:
                    queue.task_done()
                except Exception:
                    pass  # task_done() already called in CancelledError handler

    async with httpx.AsyncClient(
        timeout=config.CRAWL_TIMEOUT, headers=headers, mounts=mounts, follow_redirects=False
    ) as client:
        worker_tasks = [asyncio.create_task(worker(client)) for _ in range(concurrency)]

        # Wait until all queued items (including dynamically added ones) are processed
        await queue.join()

        # Cancel the workers now idling on queue.get()
        for t in worker_tasks:
            t.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    return results
