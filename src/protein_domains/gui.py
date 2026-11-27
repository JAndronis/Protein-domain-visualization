"""
protein-domains-gui -- live preview and click-to-edit for protein-domains, in the browser.

Serves one page on localhost and opens it. Load an InterProScan / UniProt JSON or a
feature CSV, or fetch a UniProt entry by ID (e.g. P68871 or HBB_HUMAN). Set the same
options as the CLI, click any drawn element to change its label or colour, and add
your own features. Every edit re-renders with the same layout as the CLI, and the
page downloads the SVG and the edited feature CSV.

Standard library only. Stop with Ctrl+C.
"""

import argparse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .api import ROUTES, handle_json

PAGE = Path(__file__).with_name("gui.html")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self.send_error(404)
        self._send("text/html; charset=utf-8", PAGE.read_bytes())

    def do_POST(self):
        if self.path not in ROUTES:
            return self.send_error(404)
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        self._send("application/json", handle_json(self.path, body).encode())

    def _send(self, ctype, data):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--port", type=int, default=0, help="port to serve on (default: any free port)"
    )
    ap.add_argument(
        "--no-browser",
        action="store_true",
        help="print the address instead of opening it",
    )
    a = ap.parse_args()
    server = HTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"protein-domains GUI at {url}  (Ctrl+C to stop)", flush=True)
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
