from xml.etree.ElementTree import Element, SubElement, ElementTree
from datetime import datetime

def generate_sitemap(urls, filename="sitemap.xml"):
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for url in urls:
        url_el = SubElement(urlset, "url")

        loc = SubElement(url_el, "loc")
        loc.text = url

        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = datetime.utcnow().date().isoformat()

    tree = ElementTree(urlset)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
