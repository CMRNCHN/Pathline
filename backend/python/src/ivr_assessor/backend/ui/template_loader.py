from __future__ import annotations

from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
TEMPLATE_INDEX = FRONTEND_DIR / "templates" / "index.html"


def render_index(default_stream_url: str | None, to_wss_fn) -> bytes:
    """Read the index template and inject the default stream URL placeholder."""
    content = TEMPLATE_INDEX.read_text(encoding="utf-8")
    if default_stream_url:
        wss = to_wss_fn(default_stream_url) or ""
        content = content.replace("__DEFAULT_STREAM_URL__", wss)
    else:
        content = content.replace("__DEFAULT_STREAM_URL__", "")
    return content.encode("utf-8")
