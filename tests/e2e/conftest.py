import functools
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest
from playwright.sync_api import sync_playwright

import build_site
from paths import DATA
from protein_domains.gui import Handler

UNIPROT = "https://rest.uniprot.org/"
CORS = {"Access-Control-Allow-Origin": "*"}


def serve(handler):
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    ).start()
    return httpd, f"http://127.0.0.1:{httpd.server_port}/"


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope="session")
def static_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build_site.build(out)
    return out


@pytest.fixture(params=["server"])
def app_url(request, static_site):
    """URL of the GUI in each way it is served."""
    if request.param == "server":
        httpd, url = serve(Handler)
    else:
        handler = functools.partial(
            SimpleHTTPRequestHandler, directory=str(static_site)
        )
        httpd, url = serve(handler)
    yield url
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(accept_downloads=True)
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    yield pg
    ctx.close()


@pytest.fixture
def uniprot_stub(page):
    """Answer rest.uniprot.org with the mini entry, recording what was asked."""
    seen = []

    def answer(route):
        seen.append(route.request.url)
        route.fulfill(
            status=200,
            headers=CORS,
            content_type="application/json",
            body=(DATA / "mini_uniprot.json").read_text(encoding="utf-8"),
        )

    page.route(UNIPROT + "**", answer)
    return seen
