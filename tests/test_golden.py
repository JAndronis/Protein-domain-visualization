"""Characterisation: today's SVG and feature-table bytes on the estimate path."""

import sys

import pytest

from paths import DATA, GOLDEN
from protein_domains import cli
from protein_domains.inputs import load_inputs
from protein_domains.render import layout

# golden name -> (fixture, CLI flags)
CASES = {
    "mini": ("mini.csv", []),
    "mini_uniprot": ("mini_uniprot.json", []),
    "mini_iprscan": ("mini_iprscan.json", []),
    "mini_iprscan_numbers": ("mini_iprscan.json", ["--numbers"]),
}


@pytest.mark.parametrize("name", CASES)
def test_layout_svg_matches_golden(estimate, name):
    fixture, flags = CASES[name]
    rows = load_inputs([str(DATA / fixture)], None)
    fig = layout(rows, numbers="--numbers" in flags)
    assert fig.metrics == "estimate"
    assert fig.svg == (GOLDEN / f"{name}.svg").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", CASES)
def test_cli_writes_golden_svg_and_feature_table(estimate, tmp_path, monkeypatch, name):
    fixture, flags = CASES[name]
    out = tmp_path / "fig.svg"
    monkeypatch.setattr(
        sys, "argv", ["protein-domains", str(DATA / fixture), "-o", str(out), *flags]
    )
    cli.main()
    assert out.read_text(encoding="utf-8") == (GOLDEN / f"{name}.svg").read_text(
        encoding="utf-8"
    )
    table = tmp_path / "fig_features.csv"
    golden_table = GOLDEN / f"{name}_features.csv"
    if fixture.endswith(".csv"):
        assert not table.exists()
    else:
        assert table.read_bytes() == golden_table.read_bytes()
