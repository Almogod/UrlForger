from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def extract_links(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    
    links = []
    hreflangs = []
    images = []
    videos = []
    
    # 1. Links
    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"])
        if urlparse(url).scheme.startswith("http"):
            links.append(url)
            
    # 2. Hreflang
    for link in soup.find_all("link", rel="alternate", hreflang=True, href=True):
        hreflangs.append({
            "rel": "alternate",
            "hreflang": link["hreflang"],
            "href": urljoin(base_url, link["href"])
        })
        
    # 3. Images
    for img in soup.find_all("img", src=True):
        img_url = urljoin(base_url, img["src"])
        images.append({
            "loc": img_url,
            "title": img.get("alt", ""),
            "caption": img.get("title", "")
        })
        
    # 4. Videos (basic support for <video> and <iframe>)
    for video in soup.find_all(["video", "source"], src=True):
        videos.append({
            "content_loc": urljoin(base_url, video["src"]),
            "title": "Video Content" # Placeholder or can be improved
        })
        
    return {
        "links": list(set(links)),
        "hreflangs": hreflangs,
        "images": images,
        "videos": videos
    }
