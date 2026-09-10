import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
try:
    from lib import url_helper as mozurl
    from lib.url_helper import is_valid_page_url, sanitize_url
except ImportError:
    try:
        import url_helper as mozurl
        from url_helper import is_valid_page_url, sanitize_url
    except ImportError:
        import url as mozurl
        def is_valid_page_url(u): return True
        def sanitize_url(u): return u


def find_links(html: str) -> list:
    soup = BeautifulSoup(html, "html5lib")
    links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            links.append(href)
    return links


def normalize_links(links: list, base_url: str) -> list:
    normalized_links = []
    for link in links:
        if not link or not isinstance(link, str):
            continue
        link = link.strip()
        if not is_valid_page_url(link):
            continue

        # relative links to absolute
        if not re.match(r'https?\:\/\/', link, flags=re.I):
            try:
                link = mozurl.parse(base_url).relative(link)
            except (ValueError, Exception):
                continue

        # normalize link, remove query params and #anchor
        try:
            link = sanitize_url(link)
            if not is_valid_page_url(link):
                continue
            link = str(mozurl.parse(link).defrag().abspath())
        except (ValueError, Exception):
            continue

        normalized_links.append(link)
    return normalized_links


def is_internal_link(link: str, base_url: str) -> bool:
    if not link:
        return False
    base_host = re.sub(r'^www\.', '', urlparse(base_url).netloc, flags=re.I)
    base_host = re.escape(base_host)
    if re.match(r'https?\:\/\/(?:www\.)?' + base_host, link, flags=re.I):
        return True
    return False


def filter_links(links: list, base_url: str) -> list:
    links = list(set(links))
    filtered_links = []
    for link in links:
        # filter external links, media files, and query action loops
        if is_internal_link(link, base_url) and is_valid_page_url(link):
            filtered_links.append(link)
    return filtered_links