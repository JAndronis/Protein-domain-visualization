import sys
import importlib.util

import pytest

# the browser tests need the e2e dependency group; a plain dev environment skips them
collect_ignore = [] if importlib.util.find_spec("playwright") else ["e2e"]


@pytest.fixture
def estimate(monkeypatch):
    """Force the text-width estimate so output does not depend on this machine's fonts."""
    # submodules already imported would still satisfy `from matplotlib.x import y`
    for name in [m for m in sys.modules if m.startswith("matplotlib.")]:
        monkeypatch.delitem(sys.modules, name)
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
