"""
Resilient Web Crawler, Sitemap-First Engine & Pre-flight 403 WAF Recovery for site-pages-graph.
Equipped with realistic browser headers, connection pooling, SSL resilience,
strict asset filtering, and graceful KeyboardInterrupt handling.
"""

import concurrent.futures
from itertools import repeat
from random import sample
import re
import sys
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import networkx as nx

from lib.link_helpers import find_links, normalize_links, filter_links, is_internal_link
from lib.url_helper import is_valid_page_url, sanitize_url

UA_PRESETS = {
    "screaming-frog": "Screaming Frog SEO Spider/20.0",
    "googlebot-mobile": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "googlebot-desktop": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}


def resolve_user_agent(preset_or_custom: str) -> str:
    """Resolve preset name (e.g. 'chrome', 'screaming-frog') or return custom string."""
    key = preset_or_custom.strip().lower()
    return UA_PRESETS.get(key, preset_or_custom.strip())


def create_crawler_session(user_agent: str, cookie: Optional[str] = None) -> requests.Session:
    """
    Create a requests.Session pre-configured with realistic browser headers,
    connection pooling, SSL resilience, and automatic backoff.
    """
    session = requests.Session()
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if "Mobile" in user_agent or "Android" in user_agent:
        headers["Sec-Ch-Ua-Mobile"] = "?1"
        headers["Sec-Ch-Ua-Platform"] = '"Android"'

    if cookie:
        headers["Cookie"] = cookie

    session.headers.update(headers)

    # Resilient adapter with automatic backoff to prevent SSL resets and pool exhaustion
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def preflight_check(
    url: str, session: requests.Session, timeout: int = 15
) -> Tuple[bool, Optional[requests.Response], Optional[str]]:
    """
    Execute a pre-flight test GET request on the target URL.
    Returns (success, response, error_message).
    """
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code in (403, 429):
            return False, resp, f"HTTP {resp.status_code} Forbidden / WAF Protected"
        return True, resp, None
    except Exception as e:
        return False, None, str(e)


def handle_403_recovery_interactive(
    url: str, current_session: requests.Session, timeout: int = 15
) -> Optional[requests.Session]:
    """
    Interactive recovery menu when target returns 403 Forbidden.
    """
    print("\n⚠️  [WAF / Anti-Bot Alert] Server responded with HTTP 403 Forbidden.")
    print("Select recovery option:")
    print("[1] Retry automatically with Screaming Frog User-Agent")
    print("[2] Retry automatically with Googlebot-Smartphone")
    print("[3] Input custom Cookie / Session Header")
    print("[4] Abort")

    while True:
        choice = input("\nEnter choice [1-4]: ").strip()
        if choice == '1':
            ua = UA_PRESETS['screaming-frog']
            print(f"🔄 Retrying with User-Agent: {ua}")
            new_session = create_crawler_session(ua)
            success, resp, err = preflight_check(url, new_session, timeout)
            if success:
                print("✅ Pre-flight passed with Screaming Frog User-Agent!")
                return new_session
            print(f"❌ Still blocked: {err}. Please try another option.")
        elif choice == '2':
            ua = UA_PRESETS['googlebot-mobile']
            print(f"🔄 Retrying with User-Agent: {ua}")
            new_session = create_crawler_session(ua)
            success, resp, err = preflight_check(url, new_session, timeout)
            if success:
                print("✅ Pre-flight passed with Googlebot-Smartphone!")
                return new_session
            print(f"❌ Still blocked: {err}. Please try another option.")
        elif choice == '3':
            cookie_val = input("Paste Cookie string: ").strip()
            current_session.headers["Cookie"] = cookie_val
            success, resp, err = preflight_check(url, current_session, timeout)
            if success:
                print("✅ Pre-flight passed with custom Cookie!")
                return current_session
            print(f"❌ Still blocked: {err}. Please try another option.")
        elif choice == '4':
            print("🛑 Crawl aborted by user.")
            return None
        else:
            print("Invalid choice, please enter 1, 2, 3, or 4.")


def find_redirect(response: requests.Response) -> Tuple[Optional[str], Optional[int]]:
    redirect_to = None
    redirect_status = None
    if response.history and response.history[0].status_code in (301, 302, 307, 308):
        redirect_to = response.url
        redirect_status = response.history[0].status_code
    return (redirect_to, redirect_status)


def parse_links(response: requests.Response, url: str) -> List[str]:
    links = find_links(response.text)
    links = normalize_links(links, url)
    links = filter_links(links, url)
    return links


def add_redirect_link(redirect_url: str, url: str) -> List[str]:
    if is_internal_link(redirect_url, url) and is_valid_page_url(redirect_url):
        return [sanitize_url(redirect_url)]
    return []


def _fetch_url(session: requests.Session, url: str, timeout: int) -> Tuple[str, Optional[requests.Response], Optional[Exception]]:
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        return (url, response, None)
    except (requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException) as e:
        return (url, None, e)
    except Exception as e:
        return (url, None, e)


def _strip_namespace(tag: str) -> str:
    return tag.split('}')[-1] if '}' in tag else tag


def parse_sitemap_xml(
    xml_content: bytes,
    base_url: str,
    session: requests.Session,
    timeout: int = 15,
    depth: int = 0
) -> List[str]:
    """
    Recursively extracts canonical page URLs from sitemap XML or sitemap indexes.
    """
    if depth > 3:
        return []

    discovered_pages: Set[str] = set()
    child_sitemaps: List[str] = []

    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return []

    root_tag = _strip_namespace(root.tag).lower()

    if root_tag in ('sitemapindex', 'sitemap'):
        for sitemap_node in root.iter():
            if _strip_namespace(sitemap_node.tag).lower() == 'loc':
                child_url = (sitemap_node.text or '').strip()
                if child_url and child_url.endswith('.xml'):
                    child_sitemaps.append(child_url)

    elif root_tag in ('urlset', 'url'):
        for url_node in root.iter():
            if _strip_namespace(url_node.tag).lower() == 'loc':
                page_url = (url_node.text or '').strip()
                if page_url and is_internal_link(page_url, base_url) and is_valid_page_url(page_url):
                    cleaned = sanitize_url(page_url)
                    discovered_pages.add(cleaned)

    # If child sitemaps were found, recursively fetch them
    for sitemap_url in child_sitemaps:
        try:
            resp = session.get(sitemap_url, timeout=timeout)
            if resp.status_code == 200 and resp.content:
                sub_pages = parse_sitemap_xml(
                    resp.content, base_url, session, timeout=timeout, depth=depth + 1
                )
                discovered_pages.update(sub_pages)
        except Exception:
            continue

    return list(discovered_pages)


def discover_sitemaps(
    base_url: str, session: requests.Session, timeout: int = 15
) -> Tuple[Optional[str], List[str]]:
    """
    Attempt to auto-discover XML sitemaps via robots.txt and standard endpoints.
    Returns (discovered_sitemap_url, list_of_page_urls).
    """
    print("\n🔍 Scanning for XML Sitemaps...")
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    candidate_sitemaps: List[str] = []

    # 1. Check robots.txt
    try:
        robots_url = urljoin(origin, "/robots.txt")
        resp = session.get(robots_url, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            matches = re.findall(r'^\s*Sitemap:\s*(\S+)', resp.text, flags=re.IGNORECASE | re.MULTILINE)
            for m in matches:
                candidate_sitemaps.append(m.strip())
    except Exception:
        pass

    # 2. Add standard sitemap endpoints if not present
    for common in ("/sitemap_index.xml", "/sitemap.xml", "/wp-sitemap.xml"):
        endpoint = urljoin(origin, common)
        if endpoint not in candidate_sitemaps:
            candidate_sitemaps.append(endpoint)

    # 3. Test candidates
    for sm_url in candidate_sitemaps:
        try:
            resp = session.get(sm_url, timeout=timeout)
            if resp.status_code == 200 and resp.content and b'<?xml' in resp.content[:150]:
                pages = parse_sitemap_xml(resp.content, base_url, session, timeout=timeout)
                if pages:
                    print(f"✅ Found sitemap: {sm_url} (Discovered {len(pages)} pages)")
                    return sm_url, pages
        except Exception:
            continue

    print("ℹ️  No XML sitemaps discovered. Proceeding with in-content crawling.")
    return None, []


def crawl_site(
    start_url: str,
    session: requests.Session,
    max_threads: int = 5,
    timeout: int = 30
) -> Tuple[nx.DiGraph, Dict[str, dict]]:
    """
    Concurrently crawls internal pages starting from start_url and builds directed graph.
    Supports sitemap pre-seeding, strict asset filtering, and graceful KeyboardInterrupt.
    """
    graph = nx.DiGraph()
    clean_start_url = sanitize_url(start_url)
    todo_urls: Dict[str, int] = {clean_start_url: 0}
    done_urls: Dict[str, dict] = {}

    # Step 1: Sitemap Auto-Discovery
    _, sitemap_pages = discover_sitemaps(clean_start_url, session, timeout=min(timeout, 15))
    for page in sitemap_pages:
        if page not in todo_urls:
            todo_urls[page] = 0

    print(f"\n🚀 Starting asynchronous crawl of {clean_start_url} ...")
    print("💡 Press Ctrl+C at any time to gracefully halt and export current progress.\n")

    interrupted = False

    while True:
        urls = [x for x in todo_urls.keys() if x not in done_urls]
        if not urls:
            break

        threads_count = min(max_threads, len(urls))
        threads_urls = sample(urls, min(threads_count * 5, len(urls)))

        executor = concurrent.futures.ThreadPoolExecutor(threads_count)
        try:
            futures = [
                executor.submit(_fetch_url, session, u, timeout)
                for u in threads_urls
            ]
            results = [f.result() for f in futures]
        except KeyboardInterrupt:
            interrupted = True
            print("\n\n⚠️  Crawl stopped by user (Ctrl+C).")
            print("📦 Exporting partial link graph from pages discovered so far...")
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except (TypeError, Exception):
                executor.shutdown(wait=False)
            break
        finally:
            if not interrupted:
                executor.shutdown(wait=True)

        for current_url, response, exc in results:
            try:
                if exc is not None:
                    raise exc

                # Response Header Guard: discard non-HTML content
                content_type = (response.headers.get("Content-Type") or "").lower()
                if "text/html" not in content_type:
                    # Ignore images, pdfs, audio, zip files that slipped through
                    if current_url in todo_urls:
                        del todo_urls[current_url]
                    continue

                if response.status_code > 499:
                    response.raise_for_status()

                redirect_to, redirect_status = find_redirect(response)
                done_urls[current_url] = {
                    'status': redirect_status if redirect_status is not None else response.status_code,
                    'redirect_to': redirect_to,
                }
                if current_url in todo_urls:
                    del todo_urls[current_url]
                print(f"Processed {current_url} (Status: {done_urls[current_url]['status']})")
            except Exception as exc_err:
                todo_urls[current_url] = todo_urls.get(current_url, 0) + 1
                if todo_urls[current_url] > 2:
                    try:
                        status = response.status_code if response else 0
                    except AttributeError:
                        status = 0
                    done_urls[current_url] = {
                        'status': status,
                        'redirect_to': None,
                    }
                    if current_url in todo_urls:
                        del todo_urls[current_url]
                print(f"⚠️  Skipped {current_url} (SSL/Connection issue: {type(exc_err).__name__})")
                continue

            graph.add_node(current_url)

            if redirect_to is not None:
                links = add_redirect_link(redirect_to, current_url)
            else:
                links = parse_links(response, current_url)

            for link in links:
                if link not in done_urls and link not in todo_urls:
                    todo_urls[link] = 0
                graph.add_edge(current_url, link)

    # Compute clicks and internal links
    print("\nComputing shortest paths and link metrics...")
    for idx, url in enumerate(done_urls):
        try:
            done_urls[url]['clicks'] = nx.algorithms.shortest_path_length(
                graph, source=clean_start_url, target=url
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            done_urls[url]['clicks'] = -1

        internal_links = sum(1 for node in graph if node != url and url in graph[node])
        done_urls[url]['internal_links'] = internal_links

        if idx % 5 == 0:
            print(".", end="", flush=True)
    print(" Done!")

    return graph, done_urls
