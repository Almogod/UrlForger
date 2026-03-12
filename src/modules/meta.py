# src/modules/meta.py

from bs4 import BeautifulSoup


def run(context):
    """
    Standard module interface.
    Receives context from engine and returns structured result.
    """

    pages = context["pages"]

    issues = {
        "missing_title": [],
        "missing_description": [],
        "missing_h1": [],
        "multiple_h1": []
    }

    fixes = {}

    for page in pages:

        html = page.get("html")
        url = page.get("url")

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        title_tag = soup.find("title")
        desc_tag = soup.find("meta", attrs={"name": "description"})
        h1_tags = soup.find_all("h1")

        # -----------------------------
        # TITLE ANALYSIS
        # -----------------------------
        if not title_tag or not title_tag.text.strip():
            issues["missing_title"].append(url)
            title = generate_title(url, soup)
        else:
            title = title_tag.text.strip()

        # -----------------------------
        # DESCRIPTION ANALYSIS
        # -----------------------------
        if not desc_tag or not desc_tag.get("content"):
            issues["missing_description"].append(url)
            description = generate_description(soup)
        else:
            description = desc_tag.get("content")

        # -----------------------------
        # H1 ANALYSIS
        # -----------------------------
        if not h1_tags:
            issues["missing_h1"].append(url)

        if len(h1_tags) > 1:
            issues["multiple_h1"].append(url)

        # -----------------------------
        # FIX SUGGESTION
        # -----------------------------
        fixes[url] = {
            "title": title[:60],
            "description": description[:155]
        }

    return {
        "issues": issues,
        "fixes": fixes
    }


# ------------------------------------
# TITLE GENERATOR
# ------------------------------------
def generate_title(url, soup):

    h1 = soup.find("h1")

    if h1 and h1.text.strip():
        return h1.text.strip()

    slug = url.rstrip("/").split("/")[-1]
    slug = slug.replace("-", " ").replace("_", " ")

    if slug:
        return slug.title()

    return "Untitled Page"


# ------------------------------------
# DESCRIPTION GENERATOR
# ------------------------------------
def generate_description(soup):

    paragraph = soup.find("p")

    if paragraph and paragraph.text.strip():
        text = paragraph.text.strip()
        return text[:155]

    return "Learn more about this page."
