"""Everything the GUI page can ask of Python, as one route table and one error envelope.

The page speaks JSON to `handle_json`: over HTTP in gui.py, or called directly inside Pyodide in
the static build. No route touches a filesystem or a socket, so both transports behave alike.
"""

import dataclasses
import json
import sys
from collections.abc import Callable

from .features import csv_text
from .inputs import rows_from_text
from .render import layout
from .uniprot import UNIPROT_ID, parse_uniprot, read_uniprot_response, uniprot_url

Body = dict
Route = Callable[[Body], dict]


def load(files):
    """Uploaded {name, text} documents -> feature rows, through the CLI's own format detection."""
    return {"rows": [r for f in files for r in rows_from_text(f["name"], f["text"])]}


def plan_fetch(accessions):
    """UniProt IDs -> the URLs the page should fetch. The page owns the network, Python owns the rules."""
    if not accessions:
        sys.exit("enter a UniProt ID")
    for a in accessions:
        if not UNIPROT_ID.fullmatch(a):
            sys.exit(f"'{a}' is not a UniProt accession or entry name")
    return {"requests": [{"acc": a, "url": uniprot_url(a)} for a in accessions]}


def uniprot(responses):
    """What the page's fetches returned, [{acc, status, text}] -> feature rows."""
    return {
        "rows": [
            r
            for x in responses
            for r in parse_uniprot(
                read_uniprot_response(x["acc"], x["status"], x["text"])
            )
        ]
    }


def render(body):
    return dataclasses.asdict(
        layout(body["rows"], tag_rows=body["tag_rows"], **body["opts"])
    )


ROUTES: dict[str, Route] = {
    "/api/load": lambda body: load(body["files"]),
    "/api/fetch-plan": lambda body: plan_fetch(body["accessions"]),
    "/api/uniprot": lambda body: uniprot(body["responses"]),
    "/api/render": render,
    "/api/csv": lambda body: {"csv": csv_text(body["rows"])},
}


def handle(route, body):
    """Run a route. Never raises: bad input becomes {"error": message}."""
    try:
        fn = ROUTES.get(route)
        if fn is None:
            return {"error": f"unknown route {route}"}
        return fn(body)
    # the parsers and layout report bad input with sys.exit(message)
    except SystemExit as e:
        return {"error": str(e.code)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def handle_json(route, body_json):
    try:
        body = json.loads(body_json)
    except ValueError as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
    return json.dumps(handle(route, body))
