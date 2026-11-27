import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

import protein_domains.gui as gui
from paths import DATA
from protein_domains.api import handle_json
from protein_domains.features import csv_rows


def post(base, path, body):
    req = urllib.request.Request(base + path, data=body.encode(), method="POST")
    with urllib.request.urlopen(req) as r:
        return r.status, r.headers["Content-Type"], r.read().decode()


def test_get_root_serves_the_page_bytes(server):
    with urllib.request.urlopen(server + "/") as r:
        assert r.status == 200
        assert r.read() == Path(gui.__file__).with_name("gui.html").read_bytes()


def test_other_get_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/nope")
    assert e.value.code == 404


@pytest.mark.parametrize(
    "route", ["/api/render", "/api/csv", "/api/fetch-plan", "/api/load"]
)
def test_post_body_is_what_handle_json_returns(server, estimate, route):
    rows = csv_rows((DATA / "mini.csv").read_text(encoding="utf-8"))
    bodies = {
        "/api/render": {"rows": rows, "opts": {}, "tag_rows": True},
        "/api/csv": {"rows": rows},
        "/api/fetch-plan": {"accessions": ["P68871"]},
        "/api/load": {"files": [{"name": "x.txt", "text": ""}]},
    }
    body = json.dumps(bodies[route])
    status, ctype, out = post(server, route, body)
    assert (status, ctype) == (200, "application/json")
    assert out == handle_json(route, body)


def test_error_is_still_http_200_with_an_envelope(server):
    status, _, out = post(server, "/api/fetch-plan", '{"accessions": []}')
    assert status == 200
    assert json.loads(out) == {"error": "enter a UniProt ID"}


@pytest.mark.parametrize("length", [None, "abc", "-1"])
def test_post_without_a_usable_content_length_is_411(server, length):
    conn = http.client.HTTPConnection(urllib.parse.urlsplit(server).netloc, timeout=5)
    conn.putrequest("POST", "/api/render")
    if length is not None:
        conn.putheader("Content-Length", length)
    conn.endheaders()
    assert conn.getresponse().status == 411


@pytest.mark.parametrize("path", ["/api/nope", "/api/fetch"])
def test_unknown_post_path_is_404(server, path):
    with pytest.raises(urllib.error.HTTPError) as e:
        post(server, path, "{}")
    assert e.value.code == 404
