import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
import networkx as nx
import pytest

# Ensure project modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib import url_helper
from lib.visualize import write_interactive_graph, _get_url_slug
from lib.output import output_filename, write_csv, write_sqlite, write_html_graph
from lib.link_helpers import find_links, normalize_links, filter_links, is_internal_link


def test_url_helper():
    u = url_helper.parse("https://example.com/blog/article-1#heading")
    assert u.host == "example.com"
    defragged = u.defrag()
    assert "#" not in str(defragged)
    assert u.relative("../about") == "https://example.com/about"
    # Test chained defrag and abspath
    norm = u.defrag().abspath()
    assert str(norm) == "https://example.com/blog/article-1"


def test_url_slug_helper():
    assert _get_url_slug("https://example.com/") == "/"
    assert _get_url_slug("https://example.com/about/") == "/about"
    assert _get_url_slug("https://example.com/blog/post-1") == "/post-1"


def test_write_interactive_graph_generation():
    graph = nx.DiGraph()
    start_url = "https://example.com/"
    about_url = "https://example.com/about"
    contact_url = "https://example.com/contact"
    orphan_url = "https://example.com/lonely-orphan"

    # Add edges
    graph.add_edge(start_url, about_url)
    graph.add_edge(about_url, contact_url)
    graph.add_edge(contact_url, start_url)
    # Add orphan node (no inbound links)
    graph.add_node(orphan_url)

    done_urls = {
        start_url: {'status': 200, 'clicks': 0, 'internal_links': 1, 'redirect_to': None},
        about_url: {'status': 200, 'clicks': 1, 'internal_links': 1, 'redirect_to': None},
        contact_url: {'status': 200, 'clicks': 2, 'internal_links': 1, 'redirect_to': None},
        orphan_url: {'status': 200, 'clicks': -1, 'internal_links': 0, 'redirect_to': None},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "graph.html")
        result = write_interactive_graph(graph, start_url, done_urls, output_file)

        assert os.path.exists(result)
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check Vis.js and HTML structure
        assert "vis-network.min.js" in content
        assert "Site Graph Visualization - example.com" in content
        assert "#12131A" in content  # Dark canvas

        # Check features
        assert "stabilizationIterationsDone" in content  # Auto-freeze physics
        assert "freezePhysics()" in content
        assert "doubleClick" in content  # Double-click to open URL
        assert "window.open(node.fullUrl, '_blank')" in content
        assert "inspector-drawer" in content  # Inspector drawer
        assert "search-input" in content  # Search toolbar
        assert "toggleLayout()" in content  # Layout switcher
        assert "toggleLabels()" in content  # Label toggle
        assert "filterCategory('orphan')" in content  # Orphan filter

        # Check node categories and colors
        assert '"category": "root"' in content
        assert '"#F4A261"' in content  # Root color
        assert '"category": "orphan"' in content
        assert '"#E63946"' in content  # Orphan color
        assert '"category": "connected"' in content
        assert '"#2A9D8F"' in content  # Connected color


def test_output_module():
    graph = nx.DiGraph()
    start_url = "https://mysite.com/"
    page1 = "https://mysite.com/page1"
    graph.add_edge(start_url, page1)

    done_urls = {
        start_url: {'status': 200, 'clicks': 0, 'internal_links': 0, 'redirect_to': None},
        page1: {'status': 200, 'clicks': 1, 'internal_links': 1, 'redirect_to': None},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_main = os.path.join(tmpdir, "run.py")
        csv_path = output_filename(start_url, fake_main, "csv")
        sqlite_path = output_filename(start_url, fake_main, "sqlite3")
        html_path = output_filename(start_url, fake_main, "html")

        write_csv(csv_path, done_urls)
        assert os.path.exists(csv_path)

        write_sqlite(sqlite_path, done_urls)
        assert os.path.exists(sqlite_path)

        write_html_graph(html_path, graph, start_url, done_urls)
        assert os.path.exists(html_path)


def test_end_to_end_mocked_crawl():
    base_url = "https://testsite.local/"

    site_map = {
        "https://testsite.local/": '<html><body><a href="/about">About</a><a href="/services">Services</a></body></html>',
        "https://testsite.local/about": '<html><body><a href="/services">Services</a><a href="/">Home</a></body></html>',
        "https://testsite.local/services": '<html><body><a href="/">Home</a></body></html>',
    }

    def fake_get(url, timeout=30):
        resp = MagicMock()
        resp.url = url
        resp.history = []
        if url in site_map:
            resp.status_code = 200
            resp.text = site_map[url]
        else:
            resp.status_code = 404
            resp.text = "Not found"
        return resp

    with patch("requests.get", side_effect=fake_get):
        import requests
        from settings import NETWORK_TIMEOUT

        graph = nx.DiGraph()
        start_url = str(url_helper.parse(base_url).defrag().abspath())
        todo_urls = {start_url: 0}
        done_urls = {}

        while todo_urls:
            current_url = list(todo_urls.keys())[0]
            resp = requests.get(current_url, timeout=NETWORK_TIMEOUT)
            done_urls[current_url] = {
                'status': resp.status_code,
                'redirect_to': None,
            }
            del todo_urls[current_url]
            graph.add_node(current_url)

            links = find_links(resp.text)
            links = normalize_links(links, current_url)
            links = filter_links(links, current_url)

            for link in links:
                if link not in done_urls and link not in todo_urls:
                    todo_urls[link] = 0
                graph.add_edge(current_url, link)

        # Compute metrics
        for url in done_urls:
            done_urls[url]['clicks'] = nx.algorithms.shortest_path_length(graph, source=start_url, target=url)
            internal_links = sum(1 for node in graph if node != url and url in graph[node])
            done_urls[url]['internal_links'] = internal_links

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_main = os.path.join(tmpdir, "run.py")
            csv_file = output_filename(start_url, fake_main, 'csv')
            sqlite_file = output_filename(start_url, fake_main, 'sqlite3')
            html_file = output_filename(start_url, fake_main, 'html')

            write_csv(csv_file, done_urls)
            write_sqlite(sqlite_file, done_urls)
            write_html_graph(html_file, graph, start_url, done_urls)

            assert os.path.exists(csv_file)
            assert os.path.exists(sqlite_file)
            assert os.path.exists(html_file)
            assert os.path.getsize(html_file) > 1000

            # Verify node count in output html
            with open(html_file, 'r', encoding='utf-8') as f:
                html_data = f.read()
            assert "testsite.local" in html_data
            assert "/about" in html_data
            assert "/services" in html_data
