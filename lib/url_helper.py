import posixpath
import urllib.parse as _up

# Media and static asset blocklist
EXCLUDED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp', '.tiff', '.avif',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.7z', '.tar', '.gz',
    '.mp4', '.mp3', '.webm', '.avi', '.mov', '.css', '.js', '.json', '.xml',
    '.woff', '.woff2', '.ttf', '.eot', '.otf'
}

# Infinite WooCommerce query loops, actions, and tracking tags
BLOCKED_QUERY_PATTERNS = {
    'add-to-cart', 'min_price', 'max_price', 'orderby', 'per_page',
    'shop_view', 'login', 'redirect_to', 'utm_', 'gclid', 'fbclid',
    'wc-ajax', 'action='
}


def is_valid_page_url(raw_url: str) -> bool:
    """
    Check if a URL is an HTML page and not a media asset, query loop, or non-http scheme.
    """
    if not raw_url or not isinstance(raw_url, str):
        return False

    lower = raw_url.lower().strip()

    # Discard non-HTTP schemes
    if lower.startswith(('mailto:', 'tel:', 'javascript:', 'whatsapp:', 'data:', 'sms:', 'callto:')):
        return False

    try:
        parsed = _up.urlparse(raw_url)
    except Exception:
        return False

    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return False

    # Check blocked query parameters or actions
    query = (parsed.query or '').lower()
    for pattern in BLOCKED_QUERY_PATTERNS:
        if pattern in query:
            return False

    # Check media / asset extensions in path
    path = (parsed.path or '').lower()
    for ext in EXCLUDED_EXTENSIONS:
        if path.endswith(ext):
            return False

    return True


def sanitize_url(raw_url: str) -> str:
    """
    Strip hash fragments (#...) and query parameters for clean link architecture analysis.
    """
    if not raw_url or not isinstance(raw_url, str):
        return ""
    defragged, _ = _up.urldefrag(raw_url)
    cleaned = defragged.split('?')[0].strip()
    return cleaned


try:
    import url as _mozurl

    def parse(url_str: str):
        return _mozurl.parse(url_str)

except (ImportError, ModuleNotFoundError):
    class _MozUrlFallback:
        def __init__(self, raw: str):
            self.raw = str(raw)
            self.parsed = _up.urlparse(self.raw)
            if not self.parsed.scheme and not self.raw.startswith('//'):
                self.parsed = _up.urlparse('http://' + self.raw)

        @property
        def host(self) -> str:
            netloc = self.parsed.netloc or ''
            return netloc.split(':')[0]

        def defrag(self):
            clean, _ = _up.urldefrag(_up.urlunparse(self.parsed))
            return _MozUrlFallback(clean)

        def abspath(self):
            path = self.parsed.path or '/'
            had_slash = path.endswith('/')
            norm = posixpath.normpath(path)
            if had_slash and not norm.endswith('/'):
                norm += '/'
            clean = self.parsed._replace(path=norm)
            return _MozUrlFallback(_up.urlunparse(clean))

        def relative(self, rel: str) -> str:
            return _up.urljoin(_up.urlunparse(self.parsed), rel)

        def __str__(self) -> str:
            return _up.urlunparse(self.parsed)

        def __repr__(self) -> str:
            return f"Url('{_up.urlunparse(self.parsed)}')"

    def parse(url_str: str):
        return _MozUrlFallback(url_str)
