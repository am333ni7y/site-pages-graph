"""
Interactive HTML Graph Visualizer for site-pages-graph
Generates a standalone, dark-themed Vis.js interactive visualization with:
- forceAtlas2Based physics with automatic freeze on stabilization
- Color coding (Root, Connected, Orphan, Redirect/Error)
- Node sizing proportional to internal in-links
- Double-click to open URL in a new browser tab
- Single-click slide-out Inspector Drawer with clickable inlink/outlink lists
- Floating toolbar (Search, Layout switcher, Filter orphans, Physics controls, Zoom/Fit)
"""

import json
import os
import re
from urllib.parse import urlparse
import networkx as nx


def _get_url_slug(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path:
            return '/'
        parts = [p for p in path.split('/') if p]
        if not parts:
            return '/'
        slug = parts[-1]
        if parsed.query:
            slug += f"?{parsed.query}"
        return f"/{slug}" if not slug.startswith('/') else slug
    except Exception:
        return url[-25:]


def write_interactive_graph(
    graph: nx.DiGraph,
    start_url: str,
    done_urls: dict,
    output_html_path: str
) -> str:
    """
    Build and save an interactive HTML visualization for the crawled graph.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)

    nodes_data = []
    edges_data = []

    # Map node to in-edges and out-edges for quick inspector drawer lookup
    in_edges_map = {}
    out_edges_map = {}

    for node in graph.nodes():
        in_edges_map[node] = list(graph.predecessors(node))
        out_edges_map[node] = list(graph.successors(node))

    total_orphans = 0

    for node in graph.nodes():
        url_info = done_urls.get(node, {})
        status = url_info.get('status', 200)
        redirect_to = url_info.get('redirect_to')
        clicks = url_info.get('clicks', 'N/A')
        in_degree = len(in_edges_map[node])
        out_degree = len(out_edges_map[node])

        is_root = (node == start_url)
        is_orphan = (in_degree == 0 and not is_root)
        is_redirect = bool(redirect_to)
        is_error = (status is not None and (status >= 400 or status == 0))

        if is_orphan:
            total_orphans += 1

        # Node classification and colors
        if is_root:
            category = 'root'
            color_bg = '#F4A261'     # Warm Amber
            color_border = '#E76F51'
            size = 36
        elif is_orphan:
            category = 'orphan'
            color_bg = '#E63946'     # Alert Red
            color_border = '#D90429'
            size = 18
        elif is_redirect:
            category = 'redirect'
            color_bg = '#9D4EDD'     # Royal Purple
            color_border = '#7B2CBF'
            size = 20
        elif is_error:
            category = 'error'
            color_bg = '#D00000'     # Crimson
            color_border = '#9D0208'
            size = 20
        else:
            category = 'connected'
            color_bg = '#2A9D8F'     # Emerald Teal
            color_border = '#21867A'
            # Dynamic size based on in-degree: 16 to 48
            size = min(48, max(16, 16 + (in_degree * 3)))

        slug = _get_url_slug(node)

        tooltip = (
            f"<div style='padding:6px; font-family:system-ui, -apple-system, sans-serif; font-size:12px; line-height:1.5; color:#E2E8F0;'>"
            f"<div style='font-weight:700; color:#38BDF8; word-break:break-all; margin-bottom:4px;'>{node}</div>"
            f"<div><span style='color:#94A3B8;'>Status:</span> <b style='color:{'#10B981' if status == 200 else '#F59E0B'};'>{status}</b></div>"
            f"<div><span style='color:#94A3B8;'>Clicks from /:</span> <b>{clicks}</b></div>"
            f"<div><span style='color:#94A3B8;'>Internal In-links:</span> <b style='color:#38BDF8;'>{in_degree}</b></div>"
            f"<div><span style='color:#94A3B8;'>Internal Out-links:</span> <b>{out_degree}</b></div>"
            f"{f'<div><span style=\"color:#C084FC;\">Redirects to:</span> {redirect_to}</div>' if redirect_to else ''}"
            f"<div style='margin-top:4px; font-size:11px; color:#64748B;'>💡 Double-click node to open page</div>"
            f"</div>"
        )

        nodes_data.append({
            'id': node,
            'label': slug,
            'fullUrl': node,
            'slug': slug,
            'title': tooltip,
            'category': category,
            'size': size,
            'color': {
                'background': color_bg,
                'border': color_border,
                'highlight': {
                    'background': '#FCD34D',
                    'border': '#F59E0B'
                },
                'hover': {
                    'background': '#38BDF8',
                    'border': '#0284C7'
                }
            },
            'borderWidth': 2,
            'borderWidthSelected': 4,
            'font': {
                'color': '#CBD5E1',
                'size': 12,
                'face': 'system-ui, -apple-system, sans-serif'
            },
            'status': status,
            'clicks': clicks,
            'inDegree': in_degree,
            'outDegree': out_degree,
            'redirectTo': redirect_to,
            'inboundList': in_edges_map[node],
            'outboundList': out_edges_map[node],
        })

    for u, v in graph.edges():
        edges_data.append({
            'from': u,
            'to': v,
            'arrows': 'to',
            'color': {
                'color': 'rgba(148, 163, 184, 0.25)',
                'highlight': '#38BDF8',
                'hover': '#38BDF8'
            },
            'width': 1.2,
            'selectionWidth': 2.5,
            'smooth': {
                'type': 'continuous',
                'roundness': 0.15
            }
        })

    nodes_json = json.dumps(nodes_data)
    edges_json = json.dumps(edges_data)
    host_name = urlparse(start_url).netloc or start_url

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Site Graph Visualization - {host_name}</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg-canvas: #12131A;
      --bg-panel: rgba(26, 29, 41, 0.85);
      --bg-card: #222636;
      --border-color: rgba(255, 255, 255, 0.12);
      --text-main: #F1F5F9;
      --text-muted: #94A3B8;
      --accent-cyan: #38BDF8;
      --accent-green: #2A9D8F;
      --accent-amber: #F4A261;
      --accent-red: #E63946;
      --accent-purple: #9D4EDD;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-canvas);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }}

    #graph-container {{
      width: 100vw;
      height: 100vh;
      background: radial-gradient(circle at center, #1B1E2B 0%, #12131A 100%);
    }}

    /* Top Floating Toolbar */
    .top-toolbar {{
      position: absolute;
      top: 16px;
      left: 16px;
      right: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      pointer-events: none;
      z-index: 100;
    }}

    .toolbar-group {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 8px 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      pointer-events: auto;
    }}

    .app-title {{
      font-weight: 800;
      font-size: 15px;
      letter-spacing: -0.02em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .app-title span.badge {{
      font-size: 11px;
      font-weight: 600;
      color: var(--accent-cyan);
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 2px 8px;
      border-radius: 9999px;
    }}

    .search-box {{
      position: relative;
      display: flex;
      align-items: center;
    }}

    .search-box input {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px 6px 30px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      width: 220px;
      transition: width 0.2s ease, border-color 0.2s ease;
    }}

    .search-box input:focus {{
      width: 300px;
      border-color: var(--accent-cyan);
    }}

    .search-icon {{
      position: absolute;
      left: 9px;
      width: 14px;
      height: 14px;
      fill: var(--text-muted);
      pointer-events: none;
    }}

    button.tool-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      user-select: none;
    }}

    button.tool-btn:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.25);
    }}

    button.tool-btn.active {{
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
    }}

    /* Legend Bar (Bottom Left) */
    .legend-panel {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 100;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      font-size: 12px;
    }}

    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
      transition: opacity 0.15s;
    }}

    .legend-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
      flex-shrink: 0;
    }}

    .status-badge {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 8px 14px;
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 100;
    }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10B981;
      box-shadow: 0 0 8px #10B981;
    }}
    .pulse-dot.frozen {{
      background: #38BDF8;
      box-shadow: 0 0 8px #38BDF8;
    }}

    /* Slide-out Inspector Drawer */
    .drawer {{
      position: absolute;
      top: 0;
      right: -420px;
      width: 400px;
      height: 100vh;
      background: var(--bg-panel);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-left: 1px solid var(--border-color);
      box-shadow: -8px 0 32px rgba(0, 0, 0, 0.6);
      z-index: 200;
      transition: right 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
      padding: 24px;
      overflow-y: auto;
    }}

    .drawer.open {{
      right: 0;
    }}

    .drawer-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 20px;
    }}

    .drawer-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      word-break: break-all;
      line-height: 1.4;
    }}

    .drawer-close {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
      padding: 4px;
      border-radius: 6px;
    }}
    .drawer-close:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.1);
    }}

    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-bottom: 20px;
    }}

    .meta-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 10px 12px;
    }}

    .meta-card .label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }}

    .meta-card .value {{
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .section-header {{
      font-size: 13px;
      font-weight: 600;
      color: var(--accent-cyan);
      margin: 16px 0 8px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .link-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 160px;
      overflow-y: auto;
      padding-right: 4px;
    }}

    .link-list li {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
      word-break: break-all;
      transition: background 0.15s, border-color 0.15s;
    }}

    .link-list li:hover {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
    }}

    .open-page-btn {{
      margin-top: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      background: var(--accent-cyan);
      color: #0F172A;
      font-weight: 600;
      font-size: 13px;
      padding: 10px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      text-decoration: none;
      transition: opacity 0.15s;
    }}
    .open-page-btn:hover {{
      opacity: 0.9;
    }}
  </style>
</head>
<body>

  <!-- Top Toolbar -->
  <div class="top-toolbar">
    <div class="toolbar-group">
      <div class="app-title">
        🕸️ Site Graph
        <span class="badge">{host_name}</span>
      </div>
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24"><path d="M10 2a8 8 0 015.29 13.71l5 5a1 1 0 01-1.42 1.42l-5-5A8 8 0 1110 2zm0 2a6 6 0 100 12 6 6 0 000-12z"/></svg>
        <input type="text" id="search-input" placeholder="Search page URL or slug..." />
      </div>
    </div>

    <div class="toolbar-group">
      <button class="tool-btn active" id="btn-filter-all" onclick="filterCategory('all')">All ({len(nodes_data)})</button>
      <button class="tool-btn" id="btn-filter-orphan" onclick="filterCategory('orphan')">Orphans ({total_orphans})</button>
      <button class="tool-btn" id="btn-filter-connected" onclick="filterCategory('connected')">Connected</button>
      <button class="tool-btn" id="btn-toggle-labels" onclick="toggleLabels()">Labels: Slug</button>
      <button class="tool-btn" id="btn-layout" onclick="toggleLayout()">Layout: Force</button>
      <button class="tool-btn" id="btn-physics" onclick="togglePhysics()">Freeze</button>
      <button class="tool-btn" onclick="network.fit({{ animation: true }})">Fit View</button>
    </div>
  </div>

  <!-- Main Graph Canvas -->
  <div id="graph-container"></div>

  <!-- Bottom Legend Panel -->
  <div class="legend-panel">
    <div class="legend-row" onclick="filterCategory('root')">
      <span class="legend-dot" style="background:#F4A261;"></span>
      <span>Homepage / Root</span>
    </div>
    <div class="legend-row" onclick="filterCategory('connected')">
      <span class="legend-dot" style="background:#2A9D8F;"></span>
      <span>Connected Pages</span>
    </div>
    <div class="legend-row" onclick="filterCategory('orphan')">
      <span class="legend-dot" style="background:#E63946;"></span>
      <span>Orphan Pages (0 Inlinks)</span>
    </div>
    <div class="legend-row" onclick="filterCategory('redirect')">
      <span class="legend-dot" style="background:#9D4EDD;"></span>
      <span>Redirects / Special</span>
    </div>
  </div>

  <!-- Status Indicator -->
  <div class="status-badge" id="status-badge">
    <span class="pulse-dot" id="status-pulse"></span>
    <span id="status-text">Stabilizing physics...</span>
  </div>

  <!-- Slide-out Node Inspector -->
  <div class="drawer" id="inspector-drawer">
    <div class="drawer-header">
      <div class="drawer-title" id="drawer-url">https://mysite.com/page</div>
      <button class="drawer-close" onclick="closeDrawer()">&times;</button>
    </div>

    <div class="meta-grid">
      <div class="meta-card">
        <div class="label">HTTP Status</div>
        <div class="value" id="drawer-status">200</div>
      </div>
      <div class="meta-card">
        <div class="label">Clicks from /</div>
        <div class="value" id="drawer-clicks">1</div>
      </div>
      <div class="meta-card">
        <div class="label">Internal In-links</div>
        <div class="value" id="drawer-inlinks" style="color:var(--accent-cyan);">0</div>
      </div>
      <div class="meta-card">
        <div class="label">Internal Out-links</div>
        <div class="value" id="drawer-outlinks">0</div>
      </div>
    </div>

    <a href="#" target="_blank" class="open-page-btn" id="drawer-open-btn">
      Open Page in New Tab ↗
    </a>

    <div class="section-header">
      <span>Inbound Links (Who links here)</span>
      <span id="drawer-in-count" style="font-size:11px; color:var(--text-muted);">0</span>
    </div>
    <ul class="link-list" id="drawer-in-list"></ul>

    <div class="section-header">
      <span>Outbound Links (Links to)</span>
      <span id="drawer-out-count" style="font-size:11px; color:var(--text-muted);">0</span>
    </div>
    <ul class="link-list" id="drawer-out-list"></ul>
  </div>

  <script>
    const rawNodes = {nodes_json};
    const rawEdges = {edges_json};

    const nodesDataSet = new vis.DataSet(rawNodes);
    const edgesDataSet = new vis.DataSet(rawEdges);

    const container = document.getElementById('graph-container');
    const data = {{ nodes: nodesDataSet, edges: edgesDataSet }};

    let physicsEnabled = true;
    let currentLayout = 'force'; // 'force' or 'hierarchical'
    let currentLabelMode = 1; // 0 = none, 1 = slug, 2 = full url

    const defaultOptions = {{
      nodes: {{
        shape: 'dot',
        font: {{
          color: '#CBD5E1',
          size: 12,
          face: 'system-ui, -apple-system, sans-serif'
        }}
      }},
      edges: {{
        arrows: {{ to: {{ enabled: true, scaleFactor: 0.6 }} }},
        color: {{
          color: 'rgba(148, 163, 184, 0.25)',
          highlight: '#38BDF8',
          hover: '#38BDF8'
        }},
        smooth: {{
          type: 'continuous',
          roundness: 0.15
        }}
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 100,
        navigationButtons: false,
        keyboard: true
      }},
      physics: {{
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {{
          gravitationalConstant: -55,
          centralGravity: 0.012,
          springLength: 110,
          springConstant: 0.08,
          damping: 0.65,
          avoidOverlap: 0.85
        }},
        stabilization: {{
          enabled: true,
          iterations: 250,
          updateInterval: 25
        }}
      }}
    }};

    const network = new vis.Network(container, data, defaultOptions);

    // Auto-freeze physics once stabilized to prevent endless spinning
    function freezePhysics() {{
      if (physicsEnabled) {{
        physicsEnabled = false;
        network.setOptions({{ physics: false }});
        const pulse = document.getElementById('status-pulse');
        const text = document.getElementById('status-text');
        const btn = document.getElementById('btn-physics');
        pulse.classList.add('frozen');
        text.innerText = 'Stabilized (Physics Frozen)';
        btn.innerText = 'Unfreeze';
      }}
    }}

    network.on('stabilizationIterationsDone', function () {{
      freezePhysics();
    }});

    network.on('stabilized', function () {{
      freezePhysics();
    }});

    // Double-click on node opens page in a new browser tab
    network.on('doubleClick', function (params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        const node = nodesDataSet.get(nodeId);
        if (node && node.fullUrl) {{
          window.open(node.fullUrl, '_blank');
        }}
      }}
    }});

    // Single-click on node opens the Inspector Drawer
    network.on('click', function (params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        openDrawer(nodeId);
      }}
    }});

    function openDrawer(nodeId) {{
      const node = nodesDataSet.get(nodeId);
      if (!node) return;

      document.getElementById('drawer-url').innerText = node.fullUrl;
      document.getElementById('drawer-status').innerText = node.status !== undefined ? node.status : '200';
      document.getElementById('drawer-clicks').innerText = node.clicks !== undefined ? node.clicks : '-';
      document.getElementById('drawer-inlinks').innerText = node.inDegree;
      document.getElementById('drawer-outlinks').innerText = node.outDegree;
      document.getElementById('drawer-open-btn').href = node.fullUrl;

      // Inbound links list
      const inList = document.getElementById('drawer-in-list');
      inList.innerHTML = '';
      document.getElementById('drawer-in-count').innerText = node.inboundList.length;
      if (node.inboundList.length === 0) {{
        inList.innerHTML = '<li style=\"color:var(--text-muted); cursor:default;\">No inbound links (Orphan)</li>';
      }} else {{
        node.inboundList.forEach(url => {{
          const li = document.createElement('li');
          li.innerText = url;
          li.title = 'Click to focus node';
          li.onclick = () => focusNode(url);
          inList.appendChild(li);
        }});
      }}

      // Outbound links list
      const outList = document.getElementById('drawer-out-list');
      outList.innerHTML = '';
      document.getElementById('drawer-out-count').innerText = node.outboundList.length;
      if (node.outboundList.length === 0) {{
        outList.innerHTML = '<li style=\"color:var(--text-muted); cursor:default;\">No outbound links</li>';
      }} else {{
        node.outboundList.forEach(url => {{
          const li = document.createElement('li');
          li.innerText = url;
          li.title = 'Click to focus node';
          li.onclick = () => focusNode(url);
          outList.appendChild(li);
        }});
      }}

      document.getElementById('inspector-drawer').classList.add('open');
    }}

    function closeDrawer() {{
      document.getElementById('inspector-drawer').classList.remove('open');
    }}

    function focusNode(nodeId) {{
      if (nodesDataSet.get(nodeId)) {{
        network.focus(nodeId, {{
          scale: 1.2,
          animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
        }});
        network.selectNodes([nodeId]);
        openDrawer(nodeId);
      }}
    }}

    // Search input listener
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', function (e) {{
      const query = e.target.value.trim().toLowerCase();
      if (!query) return;

      const found = rawNodes.find(n => n.fullUrl.toLowerCase().includes(query) || n.slug.toLowerCase().includes(query));
      if (found) {{
        focusNode(found.id);
      }}
    }});

    // Toggle Physics button
    function togglePhysics() {{
      physicsEnabled = !physicsEnabled;
      network.setOptions({{ physics: physicsEnabled }});
      const pulse = document.getElementById('status-pulse');
      const text = document.getElementById('status-text');
      const btn = document.getElementById('btn-physics');

      if (physicsEnabled) {{
        pulse.classList.remove('frozen');
        text.innerText = 'Physics Active';
        btn.innerText = 'Freeze';
      }} else {{
        pulse.classList.add('frozen');
        text.innerText = 'Physics Frozen';
        btn.innerText = 'Unfreeze';
      }}
    }}

    // Toggle Label mode
    function toggleLabels() {{
      currentLabelMode = (currentLabelMode + 1) % 3;
      const btn = document.getElementById('btn-toggle-labels');
      const updates = [];

      rawNodes.forEach(node => {{
        let label = '';
        if (currentLabelMode === 1) label = node.slug;
        else if (currentLabelMode === 2) label = node.fullUrl;
        updates.push({{ id: node.id, label: label }});
      }});

      nodesDataSet.update(updates);
      const labelNames = ['Hidden', 'Slug', 'Full URL'];
      btn.innerText = 'Labels: ' + labelNames[currentLabelMode];
    }}

    // Toggle Layout: Force vs Hierarchical
    function toggleLayout() {{
      const btn = document.getElementById('btn-layout');
      if (currentLayout === 'force') {{
        currentLayout = 'hierarchical';
        btn.innerText = 'Layout: Tree';
        network.setOptions({{
          layout: {{
            hierarchical: {{
              enabled: true,
              direction: 'UD',
              sortMethod: 'directed',
              nodeSpacing: 160,
              levelSeparation: 150
            }}
          }},
          physics: {{ enabled: false }}
        }});
      }} else {{
        currentLayout = 'force';
        btn.innerText = 'Layout: Force';
        network.setOptions({{
          layout: {{ hierarchical: {{ enabled: false }} }},
          physics: {{
            enabled: true,
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {{
              gravitationalConstant: -55,
              centralGravity: 0.012,
              springLength: 110,
              springConstant: 0.08,
              damping: 0.65,
              avoidOverlap: 0.85
            }}
          }}
        }});
      }}
      network.fit({{ animation: true }});
    }}

    // Category Filtering
    function filterCategory(category) {{
      document.querySelectorAll('.top-toolbar button').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById('btn-filter-' + category);
      if (activeBtn) activeBtn.classList.add('active');

      const updates = [];
      rawNodes.forEach(node => {{
        let hidden = false;
        if (category === 'orphan' && node.category !== 'orphan') hidden = true;
        if (category === 'connected' && (node.category !== 'connected' && node.category !== 'root')) hidden = true;
        if (category === 'root' && node.category !== 'root') hidden = true;

        updates.push({{ id: node.id, hidden: hidden }});
      }});

      nodesDataSet.update(updates);
      network.fit({{ animation: true }});
    }}
  </script>
</body>
</html>
"""

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_html_path
