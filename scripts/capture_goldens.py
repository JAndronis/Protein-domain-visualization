"""Regenerate tests/golden/ from the CLI on the estimate path. Review the diff before committing."""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from test_golden import CASES  # noqa: E402

PROG = (
    "import sys; sys.modules['matplotlib'] = None; "
    "from protein_domains.cli import main; main()"
)

for name, (fixture, flags) in CASES.items():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "fig.svg"
        subprocess.run(
            [
                sys.executable,
                "-c",
                PROG,
                str(ROOT / "tests/data" / fixture),
                "-o",
                str(out),
                *flags,
            ],
            check=True,
            capture_output=True,
        )
        (ROOT / "tests/golden" / f"{name}.svg").write_bytes(out.read_bytes())
        table = Path(d) / "fig_features.csv"
        if table.exists():
            (ROOT / "tests/golden" / f"{name}_features.csv").write_bytes(
                table.read_bytes()
            )
