import json

import pytest

from conftest import DATA
from protein_domains.api import ROUTES, handle, handle_json
from protein_domains.features import csv_rows, csv_text
from protein_domains.inputs import rows_from_text
from protein_domains.render import layout
from protein_domains.uniprot import parse_uniprot


def text(name):
    return (DATA / name).read_text(encoding="utf-8")


def mini_rows():
    return csv_rows(text("mini.csv"))


def test_routes_are_the_five_the_page_calls():
    assert set(ROUTES) == {
        "/api/load",
        "/api/fetch-plan",
        "/api/uniprot",
        "/api/render",
        "/api/csv",
    }


def test_load_returns_rows_from_every_file_in_order():
    out = handle(
        "/api/load",
        {
            "files": [
                {"name": "a.csv", "text": text("mini.csv")},
                {"name": "b.json", "text": text("mini_uniprot.json")},
            ]
        },
    )
    assert out == {
        "rows": mini_rows() + rows_from_text("b.json", text("mini_uniprot.json"))
    }


@pytest.mark.parametrize(
    "files, message",
    [
        ([{"name": "x.txt", "text": ""}], "x.txt: expected a .json or .csv file"),
        (
            [{"name": "my entry.json", "text": "[1]"}],
            "my entry.json: not a recognised UniProt or InterProScan JSON",
        ),
    ],
    ids=["bad-suffix", "unknown-json"],
)
def test_load_errors_name_the_upload_not_a_temporary_path(files, message):
    assert handle("/api/load", {"files": files}) == {"error": message}


def test_fetch_plan_gives_one_url_per_accession():
    assert handle("/api/fetch-plan", {"accessions": ["P68871", "HBB_HUMAN"]}) == {
        "requests": [
            {"acc": "P68871", "url": "https://rest.uniprot.org/uniprotkb/P68871.json"},
            {
                "acc": "HBB_HUMAN",
                "url": "https://rest.uniprot.org/uniprotkb/HBB_HUMAN.json",
            },
        ]
    }


@pytest.mark.parametrize(
    "accessions, message",
    [
        ([], "enter a UniProt ID"),
        ([""], "'' is not a UniProt accession or entry name"),
        (["../etc"], "'../etc' is not a UniProt accession or entry name"),
        (["P68871", "no good"], "'no good' is not a UniProt accession or entry name"),
    ],
)
def test_fetch_plan_rejects_bad_ids(accessions, message):
    assert handle("/api/fetch-plan", {"accessions": accessions}) == {"error": message}


def test_uniprot_turns_responses_into_rows_in_order():
    entry = text("mini_uniprot.json")
    out = handle(
        "/api/uniprot",
        {"responses": [{"acc": "P00001", "status": 200, "text": entry}] * 2},
    )
    assert out == {"rows": parse_uniprot(json.loads(entry)) * 2}


def test_uniprot_error_response_becomes_the_message():
    body = json.dumps({"messages": ["bad accession"]})
    out = handle(
        "/api/uniprot", {"responses": [{"acc": "X12345", "status": 400, "text": body}]}
    )
    assert out == {"error": "X12345: bad accession (HTTP 400)"}


def test_uniprot_unreachable_response_becomes_the_message():
    out = handle(
        "/api/uniprot",
        {"responses": [{"acc": "X12345", "status": 0, "text": "Failed to fetch"}]},
    )
    assert out == {"error": "X12345: could not reach UniProt (Failed to fetch)"}


def test_render_returns_the_figure_fields(estimate):
    out = handle(
        "/api/render",
        {"rows": mini_rows(), "opts": {"fs": 8, "numbers": True}, "tag_rows": False},
    )
    fig = layout(mini_rows(), fs=8, numbers=True)
    assert out == {
        "svg": fig.svg,
        "overlaps": fig.overlaps,
        "omitted": fig.omitted,
        "warnings": fig.warnings,
        "metrics": "estimate",
    }


def test_render_tag_rows_marks_each_row(estimate):
    out = handle("/api/render", {"rows": mini_rows(), "opts": {}, "tag_rows": True})
    assert 'data-row="1"' in out["svg"]
    out = handle("/api/render", {"rows": mini_rows(), "opts": {}, "tag_rows": False})
    assert "data-row" not in out["svg"]


def test_render_takes_the_page_option_names(estimate):
    opts = {
        "width": 300,
        "font": "Arial",
        "label_angle": -45,
        "axis": "none",
        "sizes": {"domain": 9},
        "min_label_scale": 1,
    }
    out = handle("/api/render", {"rows": mini_rows(), "opts": opts, "tag_rows": False})
    assert out["svg"] == layout(mini_rows(), **opts).svg


def test_csv_round_trips_through_the_table():
    rows = mini_rows()
    out = handle("/api/csv", {"rows": rows})
    assert out == {"csv": csv_text(rows)}
    assert csv_rows(out["csv"]) == rows


def test_render_error_from_layout_is_an_envelope(estimate):
    out = handle("/api/render", {"rows": [], "opts": {}, "tag_rows": False})
    assert "error" in out


@pytest.mark.parametrize(
    "route, body",
    [
        ("/api/nope", {}),
        ("/api/render", {}),
        (
            "/api/render",
            {"rows": mini_rows(), "opts": {"fs": "big"}, "tag_rows": False},
        ),
        ("/api/load", {"files": [{"name": "x.txt", "text": ""}]}),
    ],
    ids=["unknown-route", "missing-key", "bad-option", "system-exit"],
)
def test_handle_never_raises(estimate, route, body):
    out = handle(route, body)
    assert set(out) == {"error"} and out["error"]


def test_unknown_route_and_exception_messages():
    assert handle("/api/nope", {}) == {"error": "unknown route /api/nope"}
    assert handle("/api/render", {}) == {"error": "KeyError: 'rows'"}


def test_handle_json_is_json_in_json_out():
    body = json.dumps({"rows": mini_rows()})
    assert json.loads(handle_json("/api/csv", body)) == handle(
        "/api/csv", {"rows": mini_rows()}
    )


def test_handle_json_bad_json_is_an_envelope():
    out = json.loads(handle_json("/api/csv", "{nope"))
    assert set(out) == {"error"} and out["error"]
