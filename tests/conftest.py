import sys
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def estimate(monkeypatch):
    """Force the text-width estimate so output does not depend on this machine's fonts."""
    monkeypatch.setitem(sys.modules, "matplotlib", None)


@pytest.fixture
def server():
    """The GUI server on a free port, as a base URL."""
    import threading
    from http.server import HTTPServer

    from protein_domains.gui import Handler

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    ).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()
