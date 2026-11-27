"""The GUI in a real browser, once per way of serving it."""

import json

import pytest

from paths import DATA

pytestmark = pytest.mark.e2e

FIGURE = "#preview svg [data-row]"


def open_app(page, url):
    page.goto(url)
    page.wait_for_selector("#file", state="attached")


def test_uploading_a_csv_draws_its_features(page, app_url):
    open_app(page, app_url)
    page.set_input_files("#file", DATA / "mini.csv")
    page.wait_for_selector(FIGURE, timeout=120_000)
    assert page.locator("#source").inner_text().startswith("mini.csv")
    assert page.locator(FIGURE).count() >= 3
    assert page.errors == []


def test_uploading_a_bad_file_names_it_in_the_status(page, app_url):
    open_app(page, app_url)
    page.set_input_files(
        "#file",
        {"name": "notes.json", "mimeType": "application/json", "buffer": b"[1]"},
    )
    page.wait_for_selector("#status .chip.err", timeout=120_000)
    assert (
        "notes.json: not a recognised UniProt or InterProScan JSON"
        in page.locator("#status").inner_text()
    )


def test_fetching_an_accession_loads_the_entry(page, app_url, uniprot_stub):
    open_app(page, app_url)
    page.fill("#acc", "P00001")
    page.click("#fetch button")
    page.wait_for_selector(FIGURE, timeout=120_000)
    assert uniprot_stub == ["https://rest.uniprot.org/uniprotkb/P00001.json"]
    assert "UniProt P00001" in page.locator("#source").inner_text()
    assert page.errors == []


def test_a_rejected_accession_never_reaches_uniprot(page, app_url, uniprot_stub):
    open_app(page, app_url)
    page.fill("#acc", "../etc")
    page.click("#fetch button")
    page.wait_for_selector("#status .chip.err", timeout=120_000)
    assert "'../etc' is not a UniProt accession" in page.locator("#status").inner_text()
    assert uniprot_stub == []


def test_a_uniprot_error_shows_its_message(page, app_url):
    page.route(
        "https://rest.uniprot.org/**",
        lambda r: r.fulfill(
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
            content_type="application/json",
            body=json.dumps({"messages": ["bad accession"]}),
        ),
    )
    open_app(page, app_url)
    page.fill("#acc", "X12345")
    page.click("#fetch button")
    page.wait_for_selector("#status .chip.err", timeout=120_000)
    assert "X12345: bad accession (HTTP 400)" in page.locator("#status").inner_text()


def test_an_unreachable_uniprot_shows_that(page, app_url):
    page.route("https://rest.uniprot.org/**", lambda r: r.abort())
    open_app(page, app_url)
    page.fill("#acc", "X12345")
    page.click("#fetch button")
    page.wait_for_selector("#status .chip.err", timeout=120_000)
    assert "X12345: could not reach UniProt" in page.locator("#status").inner_text()
