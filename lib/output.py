import csv
import sqlite3
import os
import sys

try:
    from lib import url_helper as mozurl
except ImportError:
    try:
        import url as mozurl
    except ImportError:
        import url_helper as mozurl

from lib.visualize import write_interactive_graph


def output_filename(url: str, main_file: str, extension: str) -> str:
    host = mozurl.parse(url).host
    # Ensure extension does not contain leading dot
    extension = extension.lstrip('.')
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(main_file)), 
        'output'
    )
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{host}.{extension}")


def write_csv(csv_file: str, done_urls: dict) -> None:
    """
    Write a clean, standard UTF-8 CSV table with URL crawl metrics.
    Headers: url,status,clicks_from_root,internal_inlinks,redirect_to
    """
    os.makedirs(os.path.dirname(os.path.abspath(csv_file)), exist_ok=True)
    with open(csv_file, mode='w', encoding='utf-8', newline='') as csv_fh:
        csv_writer = csv.writer(csv_fh)
        csv_writer.writerow([
            'url',
            'status',
            'clicks_from_root',
            'internal_inlinks',
            'redirect_to'
        ])
        for url in done_urls:
            info = done_urls[url]
            csv_writer.writerow([
                url,
                info.get('status', ''),
                info.get('clicks', ''),
                info.get('internal_links', 0),
                info.get('redirect_to', '') or '',
            ])
        csv_fh.flush()


def write_sqlite(sqlite_file: str, done_urls: dict) -> bool:
    """
    Write crawl data to a SQLite3 database table.
    Safely wrapped to handle external drive locking or permissions issues gracefully.
    """
    conn = None
    cursor = None
    try:
        os.makedirs(os.path.dirname(os.path.abspath(sqlite_file)), exist_ok=True)
        conn = sqlite3.connect(sqlite_file, timeout=20.0)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS urls")
        cursor.execute("""
            CREATE TABLE urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                status INTEGER,
                clicks_from_root INTEGER,
                internal_inlinks INTEGER,
                redirect_to TEXT
            )
        """)

        for url in done_urls:
            info = done_urls[url]
            cursor.execute(
                """
                INSERT INTO 
                    urls(url, status, clicks_from_root, internal_inlinks, redirect_to) 
                    VALUES (?, ?, ?, ?, ?)
                """, 
                (
                    url,
                    info.get('status'),
                    info.get('clicks'),
                    info.get('internal_links', 0),
                    info.get('redirect_to') or None,
                )
            )

        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ Warning: Could not write SQLite database to {sqlite_file}: {e}", file=sys.stderr)
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def write_html_graph(html_file: str, graph, start_url: str, done_urls: dict) -> str:
    """
    Generate an interactive Vis.js graph visualization in HTML.
    """
    return write_interactive_graph(graph, start_url, done_urls, html_file)
