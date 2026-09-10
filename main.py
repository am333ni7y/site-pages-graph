#!/usr/bin/env python3
"""
AMEEEN SEO - Site Pages Graph & Link Architecture Visualizer
Primary entry point featuring interactive TUI, sitemap-first engine,
pre-flight WAF checks, and graceful partial export on Ctrl+C.
"""

import argparse
import sys
from urllib.parse import urlparse

try:
    from lib import url_helper as mozurl
except ImportError:
    try:
        import url as mozurl
    except ImportError:
        import url_helper as mozurl

from settings import MAX_THREADS, NETWORK_TIMEOUT
from lib.crawler import (
    UA_PRESETS,
    resolve_user_agent,
    create_crawler_session,
    preflight_check,
    handle_403_recovery_interactive,
    crawl_site,
)
from lib.output import output_filename, write_csv, write_sqlite, write_html_graph

ASCII_BANNER = r"""
    _    __  __ _____ _____ _____ _   _   ____  _____ ___  
   / \  |  \/  | ____| ____| ____| \ | | / ___|| ____/ _ \ 
  / _ \ | |\/| |  _| |  _| |  _| |  \| | \___ \|  _|| | | |
 / ___ \| |  | | |___| |___| |___| |\  |  ___) | |__| |_| |
/_/   \_\_|  |_|_____|_____|_____|_| \_| |____/|_____\___/ 
             Technical SEO Architecture & Link Visualizer - AMEEEN.IR
"""


def format_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    return str(mozurl.parse(raw_url).defrag().abspath())


def run_interactive_wizard() -> tuple:
    print(ASCII_BANNER)
    print("=" * 66)
    print("  🚀 Welcome to AMEEEN SEO Link Architecture & Visualizer")
    print("=" * 66)

    # 1. Target URL
    while True:
        target = input("\n🌐 Enter Target Domain / URL (e.g. https://WEBSITE.COM): ").strip()
        if target:
            target_url = format_url(target)
            break
        print("❌ URL cannot be empty. Please try again.")

    # 2. User-Agent Selection
    print("\n🕵️  Select User-Agent Preset:")
    print("  [1] Screaming Frog SEO Spider (Screaming Frog SEO Spider/20.0)")
    print("  [2] Googlebot Smartphone (Googlebot/2.1 Mobile)")
    print("  [3] Googlebot Desktop (Googlebot/2.1 Desktop)")
    print("  [4] Modern Desktop Chrome (macOS Chrome 130 - Recommended)")
    print("  [5] Custom User-Agent (manual text input)")

    ua_choice = input("\nEnter choice [1-5] (default: 4): ").strip() or "4"
    if ua_choice == "1":
        user_agent = UA_PRESETS["screaming-frog"]
    elif ua_choice == "2":
        user_agent = UA_PRESETS["googlebot-mobile"]
    elif ua_choice == "3":
        user_agent = UA_PRESETS["googlebot-desktop"]
    elif ua_choice == "5":
        custom_ua = input("Enter custom User-Agent: ").strip()
        user_agent = custom_ua if custom_ua else UA_PRESETS["chrome"]
    else:
        user_agent = UA_PRESETS["chrome"]

    # 3. Concurrency
    threads_input = input(f"\n⚡ Concurrent Threads [1-20] (default: {MAX_THREADS}): ").strip()
    try:
        threads = int(threads_input) if threads_input else MAX_THREADS
        threads = max(1, min(threads, 30))
    except ValueError:
        threads = MAX_THREADS

    return target_url, user_agent, threads, None


def main():
    parser = argparse.ArgumentParser(
        description="AMEEEN SEO - Site Pages Graph & Link Visualizer",
        add_help=True
    )
    parser.add_argument("url", nargs="?", help="Target website root URL (e.g. https://WEBSITE.COM)")
    parser.add_argument(
        "--ua", "--user-agent",
        dest="ua",
        default=None,
        help="User-Agent string or preset (screaming-frog, googlebot-mobile, googlebot-desktop, chrome)"
    )
    parser.add_argument("--threads", type=int, default=None, help=f"Concurrent crawling threads (default: {MAX_THREADS})")
    parser.add_argument("--timeout", type=int, default=NETWORK_TIMEOUT, help=f"Request timeout in seconds (default: {NETWORK_TIMEOUT})")
    parser.add_argument("--cookie", type=str, default=None, help="Custom Cookie header for authentication or WAF bypass")
    parser.add_argument("--no-banner", action="store_true", help="Suppress ASCII banner")

    args = parser.parse_args()

    # Interactive mode if no URL provided
    if not args.url:
        try:
            start_url, user_agent, threads, cookie = run_interactive_wizard()
        except KeyboardInterrupt:
            print("\n🛑 Setup cancelled by user. Exiting.")
            sys.exit(0)
        timeout = args.timeout
    else:
        if not args.no_banner:
            print(ASCII_BANNER)
        start_url = format_url(args.url)
        user_agent = resolve_user_agent(args.ua) if args.ua else UA_PRESETS["chrome"]
        threads = args.threads if args.threads is not None else MAX_THREADS
        timeout = args.timeout
        cookie = args.cookie

    print("\n📋 Execution Configuration:")
    print(f"  • Target URL:    {start_url}")
    print(f"  • User-Agent:    {user_agent[:60]}...")
    print(f"  • Threads:       {threads}")
    print(f"  • Timeout:       {timeout}s")
    print("-" * 66)

    # Initialize crawler session
    session = create_crawler_session(user_agent=user_agent, cookie=cookie)

    # Pre-flight Check
    print("🔍 Performing Pre-flight check on homepage...")
    try:
        success, resp, err = preflight_check(start_url, session, timeout=timeout)
    except KeyboardInterrupt:
        print("\n🛑 Pre-flight cancelled by user.")
        sys.exit(0)

    if not success:
        if resp is not None and resp.status_code in (403, 429):
            # 403 / 429 WAF trigger
            try:
                session = handle_403_recovery_interactive(start_url, session, timeout=timeout)
            except KeyboardInterrupt:
                print("\n🛑 Recovery cancelled by user.")
                sys.exit(0)
            if not session:
                print("🛑 Execution stopped.")
                sys.exit(1)
        else:
            print(f"⚠️ Pre-flight warning: {err or 'Non-200 response'}. Proceeding cautiously...")
    else:
        print(f"✅ Pre-flight check passed! (HTTP {resp.status_code if resp else 200})")

    # Full crawl with graceful KeyboardInterrupt handling
    try:
        graph, done_urls = crawl_site(
            start_url=start_url,
            session=session,
            max_threads=threads,
            timeout=timeout
        )
    except KeyboardInterrupt:
        print("\n\n⚠️ Crawl interrupted by user (Ctrl+C).")
        graph = None
        done_urls = {}

    if not done_urls:
        print("❌ No pages could be crawled. Exiting.")
        sys.exit(1)

    # Reports export (generates partial reports if crawl was stopped)
    print("\n📦 Generating export files...")
    csv_file = output_filename(start_url, __file__, 'csv')
    write_csv(csv_file, done_urls)

    sqlite_file = output_filename(start_url, __file__, 'sqlite3')
    write_sqlite(sqlite_file, done_urls)

    html_file = output_filename(start_url, __file__, 'html')
    write_html_graph(html_file, graph, start_url, done_urls)

    total_pages = len(done_urls)
    total_edges = graph.number_of_edges() if graph else 0
    orphans = sum(1 for n in graph.nodes() if graph.in_degree(n) == 0 and n != start_url) if graph else 0

    print("\n" + "=" * 66)
    print("🎉 Crawl & Graph Generation Complete!")
    print(f"  • Discovered Pages: {total_pages}")
    print(f"  • In-Content Edges: {total_edges}")
    print(f"  • Orphan Pages:     {orphans}")
    print("-" * 66)
    print(f"📁 CSV Table:       {csv_file}")
    print(f"🗄️ SQLite DB:       {sqlite_file}")
    print(f"🌐 Interactive HTML: {html_file}")
    print("=" * 66 + "\n")


if __name__ == '__main__':
    main()
