"""Serve registered local images to Chromium without copying them."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
from secrets import token_urlsafe
import shutil
from threading import Thread


@contextmanager
def serve_media():
    routes: dict[str, Path] = {}
    token = token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = routes.get(self.path)
            if path is None:
                self.send_error(404)
                return
            try:
                stream = path.open("rb")
            except OSError:
                self.send_error(404)
                return
            with stream:
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(stream.seek(0, 2)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                stream.seek(0)
                try:
                    shutil.copyfileobj(stream, self.wfile)
                except ConnectionError:
                    pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def register(path):
            route = f"/{token}/{len(routes)}{path.suffix.lower()}"
            routes[route] = path
            return f"http://127.0.0.1:{server.server_port}{route}"

        try:
            yield register
        finally:
            server.shutdown()
            thread.join()
