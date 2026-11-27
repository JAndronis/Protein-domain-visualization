"""Build the static GUI: gui.html plus the package sources, as one self-contained site/index.html.

    uv run python scripts/build_site.py -o site/ [--pyodide-url URL]

The page runs the package in Pyodide. Serve site/ from any static host, or open index.html from disk.
Standard library only.
"""

import argparse
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "src" / "protein_domains"
# Python 3.14, released 2026-09-14; jsDelivr sends Access-Control-Allow-Origin: *
PYODIDE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js"


def build(out_dir, pyodide_url=PYODIDE):
    html = (PKG / "gui.html").read_text(encoding="utf-8")
    assert html.count("<script>") == 1, "gui.html must have exactly one inline script"
    sources = {p.name: p.read_text(encoding="utf-8") for p in sorted(PKG.glob("*.py"))}
    # "<\/" parses back to "</" in JSON but cannot close the script element early
    payload = json.dumps(sources).replace("</", "<\\/")
    inject = (
        f'<script src="{pyodide_url}"></script>\n'
        f'<script id="py-sources" type="application/json">{payload}</script>\n'
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    index = out / "index.html"
    index.write_text(html.replace("<script>", inject + "<script>", 1), encoding="utf-8")
    return index


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "-o", "--out", default="site", help="output directory (default site)"
    )
    ap.add_argument(
        "--pyodide-url",
        default=PYODIDE,
        help="pyodide.js to load (default: the pinned CDN build)",
    )
    a = ap.parse_args(argv)
    print(build(a.out, a.pyodide_url))


if __name__ == "__main__":
    main()
