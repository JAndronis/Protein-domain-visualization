"""What only the static page promises: bytes equal to the CLI's, a closed network, file:// works."""

import statistics

import pytest

from paths import DATA, GOLDEN
from protein_domains.api import handle
from protein_domains.features import csv_rows
from test_gui import FIGURE, open_app

pytestmark = pytest.mark.e2e

PYODIDE_PREFIX = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/"


def test_static_page_says_text_widths_are_estimated(page, static_url):
    open_app(page, static_url)
    page.set_input_files("#file", DATA / "mini.csv")
    page.wait_for_selector(FIGURE)
    assert "text widths estimated" in page.locator("#status").inner_text()


def test_downloaded_svg_equals_the_cli_without_matplotlib(page, static_url, estimate):
    open_app(page, static_url)
    page.set_input_files("#file", DATA / "mini.csv")
    page.wait_for_selector(FIGURE)
    with page.expect_download() as d:
        page.click("#dl-svg")
    svg = open(d.value.path(), encoding="utf-8").read()
    assert svg == (GOLDEN / "mini.svg").read_text(encoding="utf-8")
    rows = csv_rows((DATA / "mini.csv").read_text(encoding="utf-8"))
    opts = {
        "width": 400,
        "font": "Arial",
        "fs": 8,
        "label_angle": -90,
        "min_label_scale": 0.7,
        "axis": "full",
        "numbers": False,
        "sizes": {},
    }
    assert (
        svg
        == handle("/api/render", {"rows": rows, "opts": opts, "tag_rows": False})["svg"]
    )


def test_downloaded_feature_csv_round_trips(page, static_url):
    open_app(page, static_url)
    page.set_input_files("#file", DATA / "mini_iprscan.json")
    page.wait_for_selector(FIGURE)
    with page.expect_download() as d:
        page.click("#dl-csv")
    assert open(d.value.path(), encoding="utf-8").read() == (
        GOLDEN / "mini_iprscan_features.csv"
    ).read_text(encoding="utf-8")


def test_page_talks_only_to_the_cdn_and_uniprot(page, static_url, uniprot_stub):
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    open_app(page, static_url)
    page.set_input_files("#file", DATA / "mini.csv")
    page.wait_for_selector(FIGURE)
    page.fill("#acc", "P00001")
    page.click("#fetch button")
    page.wait_for_function(
        "document.querySelector('#source').textContent.includes('UniProt')"
    )
    outside = [
        u
        for u in asked
        if not u.startswith(
            (static_url, PYODIDE_PREFIX, "https://rest.uniprot.org/", "data:", "blob:")
        )
    ]
    assert outside == []
    assert any(u.startswith(PYODIDE_PREFIX) for u in asked)


@pytest.mark.parametrize("fixture", ["mini.csv", "mini_iprscan.json"])
def test_render_time(page, static_url, fixture, request):
    """Measurement, not a gate: per-edit /api/render round trip inside the page (run with -s)."""
    open_app(page, static_url)
    page.set_input_files("#file", DATA / fixture)
    page.wait_for_selector(FIGURE)
    ms = page.evaluate(
        """async () => {
          const out = [];
          for (let i = 0; i < 30; i++) {
            const t = performance.now();
            await api('/api/render', {rows: state.rows, opts: renderOpts(), tag_rows: true});
            out.push(performance.now() - t);
          }
          return out;
        }"""
    )
    warm = ms[5:]
    print(
        f"\nrender {fixture}: median {statistics.median(warm):.1f} ms, "
        f"max {max(warm):.1f} ms over {len(warm)} warm renders (first {ms[0]:.1f} ms)"
    )


@pytest.mark.network
def test_page_opened_from_disk_boots_and_renders(page, static_site):
    open_app(page, (static_site / "index.html").as_uri())
    page.set_input_files("#file", DATA / "mini.csv")
    page.wait_for_selector(FIGURE)
    assert page.errors == []
