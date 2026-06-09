"""Minimal static preview server for the analyst frontend."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

FRONTEND = Path(__file__).parent / "analyst" / "frontend"
TEMPLATES = FRONTEND / "templates"
STATIC = FRONTEND / "static"

MIME = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            data = (TEMPLATES / "index.html").read_bytes()
            self.send(200, "text/html", data)
        elif path.startswith("/static/"):
            file_path = STATIC / path[len("/static/"):]
            if file_path.exists():
                ext = file_path.suffix
                self.send(200, MIME.get(ext, "application/octet-stream"), file_path.read_bytes())
            else:
                self.send(404, "text/plain", b"Not found")
        else:
            self.send(404, "text/plain", b"Not found")

    def send(self, code, ct, body):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    port = 8099
    print(f"Preview → http://127.0.0.1:{port}/")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
