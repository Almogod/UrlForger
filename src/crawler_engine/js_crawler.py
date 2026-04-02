import asyncio
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .graph import CrawlGraph


class JSCrawler:
    """
    Headless browser crawler for JS-rendered websites.
    Used when normal HTTP crawler cannot discover links.
    """

    def __init__(self, start_url, limit=50, concurrency=3, delay=2.0, check_robots=True, headers=None, crawl_assets=False, broken_links_only=False):
        self.start_url = start_url
        self.limit = limit
        self.concurrency = concurrency
        self.delay = delay
        self.check_robots = check_robots
        self.headers = headers or {}
        self.crawl_assets = crawl_assets
        self.broken_links_only = broken_links_only

        self.visited = set()
        self.to_visit = {start_url}
        self.results = []
        self.graph = CrawlGraph()

        self.domain = urlparse(start_url).netloc
        self.base_path = ""
        path = urlparse(start_url).path
        if path and path != "/":
            self.base_path = path

        self.rp = None
        if self.check_robots:
            try:
                robots_url = f"{urlparse(start_url).scheme}://{self.domain}/robots.txt"
                self.rp = RobotFileParser()
                self.rp.set_url(robots_url)
                self.rp.read()
            except Exception as e:
                print(f"Warning: Could not fetch robots.txt for JS crawler: {e}")

    async def _scroll_page(self, page):
        """Scrolls the page to trigger lazy loading."""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)

    async def crawl(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            semaphore = asyncio.Semaphore(self.concurrency)

            async def worker():
                page = await browser.new_page()

                while self.to_visit and len(self.results) < self.limit:
                    try:
                        url = self.to_visit.pop()
                    except KeyError:
                        return

                    if url in self.visited:
                        continue
                    
                    if self.rp and not self.rp.can_fetch("*", url):
                        print(f"JS Crawler skipping {url} due to robots.txt")
                        continue

                    async with semaphore:
                        if self.delay > 0:
                            await asyncio.sleep(self.delay)

                        try:
                            if self.headers:
                                await page.set_extra_http_headers(self.headers)
                                
                            response = await page.goto(
                                url,
                                timeout=30000,
                                wait_until="networkidle"
                            )
                            
                            status = response.status if response else 0
                            
                            # Auto-scroll for infinite scroll sites
                            if status == 200:
                                await self._scroll_page(page)
                                await asyncio.sleep(1) # Wait for potential lazy loads

                            html = await page.content()
                            self.visited.add(url)
                            
                            extracted = self.extract_metadata(html, url)

                            page_data = {
                                "url": url,
                                "status": status,
                                "html": html,
                                "hreflangs": extracted["hreflangs"],
                                "images": extracted["images"],
                                "videos": extracted["videos"],
                                "meta": extracted.get("meta", {}),
                                "headings": extracted.get("headings", {}),
                                "canonical": extracted.get("canonical", ""),
                                "custom": {}
                            }

                            # Filter based on broken_links_only
                            # Always include starting URL for baseline context
                            is_start = url == self.start_url
                            if self.broken_links_only:
                                if is_start or (status and status not in [200, 304]):
                                    self.results.append(page_data)
                            else:
                                self.results.append(page_data)

                            # Link & Graph Discovery
                            for link in extracted["links"]:
                                self.graph.add_edge(url, link)
                                if link not in self.visited:
                                    self.to_visit.add(link)

                            if self.crawl_assets:
                                for asset in extracted["assets"]:
                                    self.graph.add_edge(url, asset)
                                    # Optimization: normally we don't visit assets in JS mode to save time
                                    # but we record them in the graph.

                        except Exception as e:
                            print(f"Error crawling {url}: {e}")
                            continue

                await page.close()

            workers = [worker() for _ in range(self.concurrency)]
            await asyncio.gather(*workers)
            await browser.close()

        return self.results, self.graph

    def extract_metadata(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        
        links = []
        hreflangs = []
        images = []
        videos = []
        assets = []
        
        # 1. Links
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.netloc == self.domain:
                if self.base_path and not parsed.path.startswith(self.base_path) and parsed.path != self.base_path:
                    continue
                links.append(absolute)
                
        # 2. Hreflang
        for link in soup.find_all("link", rel="alternate", hreflang=True, href=True):
            hreflangs.append({
                "rel": "alternate",
                "hreflang": link["hreflang"],
                "href": urljoin(base_url, link["href"])
            })
            
        # 3. Images
        for img in soup.find_all("img", src=True):
            images.append({
                "loc": urljoin(base_url, img["src"]),
                "title": img.get("alt", ""),
                "caption": img.get("title", "")
            })
            assets.append(urljoin(base_url, img["src"]))
            
        # 4. Videos
        for video in soup.find_all(["video", "source"], src=True):
            videos.append({
                "content_loc": urljoin(base_url, video["src"]),
                "title": "Video Content"
            })
            assets.append(urljoin(base_url, video["src"]))

        # 5. Metadata & Headings (Added missing extraction)
        meta = {}
        title = soup.find("title")
        if title: meta["title"] = title.text.strip()
        
        desc = soup.find("meta", attrs={"name": "description"})
        if desc: meta["description"] = desc.get("content", "")
        
        canon = soup.find("link", rel="canonical")
        canonical_url = urljoin(base_url, canon["href"]) if canon and canon.get("href") else ""

        headings = {}
        for h in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headings[h] = [tag.text.strip() for tag in soup.find_all(h)]

        # 6. Scripts & CSS (Assets)
        for s in soup.find_all("script", src=True):
            assets.append(urljoin(base_url, s["src"]))
        for link in soup.find_all("link", rel="stylesheet", href=True):
            assets.append(urljoin(base_url, link["href"]))

        return {
            "links": list(set(links)),
            "hreflangs": hreflangs,
            "images": images,
            "videos": videos,
            "assets": list(set(assets)),
            "meta": meta,
            "headings": headings,
            "canonical": canonical_url
        }


def crawl_js_sync(start_url, limit=50, delay=2.0, check_robots=True, headers=None, crawl_assets=False, broken_links_only=False):
    """
    Synchronous wrapper for FastAPI usage. Safe for Windows threads.
    """
    crawler = JSCrawler(
        start_url, 
        limit, 
        delay=delay, 
        check_robots=check_robots, 
        headers=headers, 
        crawl_assets=crawl_assets, 
        broken_links_only=broken_links_only
    )
    try:
        return asyncio.run(crawler.crawl())
    except RuntimeError:
        # Fallback if a loop is already running in this thread
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(crawler.crawl())
