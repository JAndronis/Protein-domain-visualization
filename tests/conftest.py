import sys
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def estimate(monkeypatch):
    """Force the text-width estimate so output does not depend on this machine's fonts."""
    monkeypatch.setitem(sys.modules, "matplotlib", None)
