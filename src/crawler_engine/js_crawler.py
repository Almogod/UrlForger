import asyncio
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class JSCrawler:
    """
    Headless browser crawler for JS-rendered websites.
    Used when normal HTTP crawler cannot discover links.
    """

    def __init__(self, start_url, limit=50, concurrency=3, delay=2.0, check_robots=True, headers=None):
        self.start_url = start_url
        self.limit = limit
        self.concurrency = concurrency
        self.delay = delay
        self.check_robots = check_robots
        self.headers = headers or {}

        self.visited = set()
        self.to_visit = {start_url}
        self.results = []

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
                    
                    # Robots.txt check
                    if self.rp and not self.rp.can_fetch("*", url):
                        print(f"JS Crawler skipping {url} due to robots.txt")
                        continue

                    async with semaphore:
                        # Rate limiting
                        if self.delay > 0:
                            await asyncio.sleep(self.delay)

                        try:
                            if self.headers:
                                await page.set_extra_http_headers(self.headers)
                                
                            await page.goto(
                                url,
                                timeout=30000,
                                wait_until="networkidle"
                            )
                            
                            # Auto-scroll for infinite scroll sites
                            await self._scroll_page(page)
                            await asyncio.sleep(1) # Wait for potential lazy loads

                            html = await page.content()

                            self.visited.add(url)
                            
                            extracted = self.extract_metadata(html, url)

                            page_data = {
                                "url": url,
                                "status": 200,
                                "html": html,
                                "hreflangs": extracted["hreflangs"],
                                "images": extracted["images"],
                                "videos": extracted["videos"]
                            }

                            self.results.append(page_data)

                            for link in extracted["links"]:
                                if link not in self.visited:
                                    self.to_visit.add(link)

                        except Exception as e:
                            print(f"Error crawling {url}: {e}")
                            continue

                await page.close()

            workers = [worker() for _ in range(self.concurrency)]

            await asyncio.gather(*workers)

            await browser.close()

        return self.results

    def extract_metadata(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        
        links = []
        hreflangs = []
        images = []
        videos = []
        
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
            
        # 4. Videos
        for video in soup.find_all(["video", "source"], src=True):
            videos.append({
                "content_loc": urljoin(base_url, video["src"]),
                "title": "Video Content"
            })

        return {
            "links": list(set(links)),
            "hreflangs": hreflangs,
            "images": images,
            "videos": videos
        }


def crawl_js_sync(start_url, limit=50, delay=2.0, check_robots=True, headers=None):
    """
    Synchronous wrapper for FastAPI usage. Safe for Windows threads.
    """
    crawler = JSCrawler(start_url, limit, delay=delay, check_robots=check_robots, headers=headers)
    try:
        return asyncio.run(crawler.crawl())
    except RuntimeError:
        # Fallback if a loop is already running in this thread
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(crawler.crawl())
