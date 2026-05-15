from __future__ import annotations


from .template_loader import FRONTEND_DIR

STATIC_DIR = FRONTEND_DIR / "static"

_MIME = {
    ".css": "text/css; charset=utf-8",
    ".js":  "application/javascript; charset=utf-8",
}


def load_static(rel_path: str) -> tuple[int, str, bytes]:
    """Resolve a static asset path and return (status, content_type, body).

    Returns (403, "", b"") on traversal attempt, (404, "", b"") if missing.
    """
    path = (STATIC_DIR / rel_path).resolve()
    try:
        path.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return 403, "", b""
    if not path.is_file():
        return 404, "", b""
    return 200, _MIME.get(path.suffix, "application/octet-stream"), path.read_bytes()
