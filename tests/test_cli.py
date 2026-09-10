import csv
import os
import sqlite3
import sys
import tempfile
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import format_url
from lib.url_helper import is_valid_page_url, sanitize_url, EXCLUDED_EXTENSIONS
from lib.crawler import (
    UA_PRESETS,
    resolve_user_agent,
    create_crawler_session,
    preflight_check,
    handle_403_recovery_interactive,
    parse_sitemap_xml,
)
from lib.output import write_csv, write_sqlite


def test_format_url():
    assert format_url("example.com") == "https://example.com/"
    assert format_url("http://test.com/path#anchor") == "http://test.com/path"
    assert format_url("https://mysite.ir/page/") == "https://mysite.ir/page/"


def test_resolve_user_agent():
    assert resolve_user_agent("screaming-frog") == UA_PRESETS["screaming-frog"]
    assert resolve_user_agent("googlebot-mobile") == UA_PRESETS["googlebot-mobile"]
    assert resolve_user_agent("chrome") == UA_PRESETS["chrome"]
    assert resolve_user_agent("CustomBot/1.0") == "CustomBot/1.0"


def test_create_crawler_session():
    ua = "CustomSpider/2.0"
    session = create_crawler_session(ua, cookie="auth_token=secret123")
    assert session.headers["User-Agent"] == ua
    assert session.headers["Cookie"] == "auth_token=secret123"
    assert "fa,en-US" in session.headers["Accept-Language"]
    assert "Chromium" in session.headers["Sec-Ch-Ua"]


def test_url_sanitization_and_asset_blocking():
    # Valid pages
    assert is_valid_page_url("https://example.com/about/") is True
    assert is_valid_page_url("https://example.com/blog/article-1") is True

    # Media & Asset blocklist
    assert is_valid_page_url("https://example.com/wp-content/uploads/photo.jpg") is False
    assert is_valid_page_url("https://example.com/assets/style.css") is False
    assert is_valid_page_url("https://example.com/script.js") is False
    assert is_valid_page_url("https://example.com/document.pdf") is False
    assert is_valid_page_url("https://example.com/archive.zip") is False
    assert is_valid_page_url("https://example.com/icon.svg") is False

    # Action & Query loops
    assert is_valid_page_url("https://example.com/shop/?add-to-cart=123") is False
    assert is_valid_page_url("https://example.com/shop/?min_price=10&max_price=50") is False
    assert is_valid_page_url("https://example.com/products/?orderby=date") is False
    assert is_valid_page_url("https://example.com/?utm_source=google") is False

    # Non-HTTP schemes
    assert is_valid_page_url("mailto:info@example.com") is False
    assert is_valid_page_url("tel:+989123456789") is False
    assert is_valid_page_url("javascript:void(0);") is False
    assert is_valid_page_url("whatsapp://send?phone=123") is False

    # Query & Hash sanitization
    assert sanitize_url("https://example.com/shop/?color=blue&size=m#section1") == "https://example.com/shop/"
    assert sanitize_url("https://example.com/page#top") == "https://example.com/page"


def test_preflight_check_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    success, resp, err = preflight_check("https://example.com/", mock_session)
    assert success is True
    assert resp.status_code == 200
    assert err is None


def test_preflight_check_403():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    success, resp, err = preflight_check("https://waf-blocked.com/", mock_session)
    assert success is False
    assert resp.status_code == 403
    assert "Forbidden" in err


def test_handle_403_recovery_interactive():
    current_session = create_crawler_session("Python-urllib/3.13")

    # Simulate user choosing option 1: Screaming Frog
    with patch("builtins.input", side_effect=["1"]):
        with patch("lib.crawler.preflight_check", return_value=(True, MagicMock(status_code=200), None)):
            recovered_session = handle_403_recovery_interactive("https://target.com", current_session)
            assert recovered_session is not None
            assert recovered_session.headers["User-Agent"] == UA_PRESETS["screaming-frog"]


def test_sitemap_xml_parsing():
    sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://example.com/page-1</loc>
      </url>
      <url>
        <loc>https://example.com/page-2/</loc>
      </url>
      <url>
        <loc>https://example.com/image.jpg</loc>
      </url>
    </urlset>
    """
    mock_session = MagicMock()
    pages = parse_sitemap_xml(sample_xml, "https://example.com", mock_session)
    assert "https://example.com/page-1" in pages
    assert "https://example.com/page-2/" in pages
    # Ensure media is filtered out
    assert "https://example.com/image.jpg" not in pages


def test_csv_output_integrity_and_headers():
    done_urls = {
        "https://example.com/": {
            "status": 200,
            "clicks": 0,
            "internal_links": 3,
            "redirect_to": None,
        },
        "https://example.com/about": {
            "status": 200,
            "clicks": 1,
            "internal_links": 2,
            "redirect_to": None,
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = os.path.join(tmpdir, "test.csv")
        write_csv(csv_file, done_urls)

        assert os.path.exists(csv_file)
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["url", "status", "clicks_from_root", "internal_inlinks", "redirect_to"]
            row1 = next(reader)
            assert row1 == ["https://example.com/", "200", "0", "3", ""]
            row2 = next(reader)
            assert row2 == ["https://example.com/about", "200", "1", "2", ""]


def test_sqlite_output_integrity():
    done_urls = {
        "https://example.com/": {
            "status": 200,
            "clicks": 0,
            "internal_links": 5,
            "redirect_to": None,
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_file = os.path.join(tmpdir, "test.sqlite3")
        ok = write_sqlite(sqlite_file, done_urls)
        assert ok is True
        assert os.path.exists(sqlite_file)

        # Connect and query sqlite to ensure proper database format
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        cursor.execute("SELECT url, status, clicks_from_root, internal_inlinks FROM urls")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0] == ("https://example.com/", 200, 0, 5)
        conn.close()
