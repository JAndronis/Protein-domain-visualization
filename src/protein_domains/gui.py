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
import dataclasses
import json
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .features import csv_text
from .inputs import load_inputs
from .render import layout
from .uniprot import UNIPROT_ID

PAGE = Path(__file__).with_name("gui.html")
SUFFIXES = (".json", ".csv")


def load(files):
    """Uploaded {name, text} files -> feature rows, through the CLI's own format detection."""
    for f in files:
        if Path(f["name"]).suffix.lower() not in SUFFIXES:
            raise ValueError(f"{f['name']}: expected a .json or .csv file")
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for k, f in enumerate(files):
            p = Path(d) / f"{k}_{Path(f['name']).name}"
            p.write_text(f["text"], encoding="utf-8")
            paths.append(str(p))
        try:
            return {"rows": load_inputs(paths, None)}
        # name the uploaded file in the message, not its temporary copy
        except SystemExit as e:
            msg = str(e.code)
            for p, f in zip(paths, files):
                msg = msg.replace(p, f["name"])
            raise SystemExit(msg) from None


def fetch(accessions):
    """UniProt IDs -> feature rows. The ID check keeps load_inputs on its fetch branch, never a local path."""
    if not accessions:
        sys.exit("enter a UniProt ID")
    for a in accessions:
        if not UNIPROT_ID.fullmatch(a):
            sys.exit(f"'{a}' is not a UniProt accession or entry name")
    return {"rows": load_inputs(accessions, None)}


def figure(body):
    fig = layout(body["rows"], tag_rows=body["tag_rows"], **body["opts"])
    return dataclasses.asdict(fig)


ROUTES = {
    "/api/load": lambda body: load(body["files"]),
    "/api/fetch": lambda body: fetch(body["accessions"]),
    "/api/render": figure,
    "/api/csv": lambda body: {"csv": csv_text(body["rows"])},
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self.send_error(404)
        self._send("text/html; charset=utf-8", PAGE.read_bytes())

    def do_POST(self):
        route = ROUTES.get(self.path)
        if route is None:
            return self.send_error(404)
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            out = route(body)
        # the parsers and layout report bad input with sys.exit(message)
        except SystemExit as e:
            out = {"error": str(e.code)}
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
        self._send("application/json", json.dumps(out).encode())

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
