import io
import json
import urllib.error
import urllib.request

import pytest

from conftest import DATA
from protein_domains.uniprot import fetch_uniprot, read_uniprot_response, uniprot_url

ENTRY = (DATA / "mini_uniprot.json").read_text(encoding="utf-8")


def exit_message(fn, *args):
    with pytest.raises(SystemExit) as e:
        fn(*args)
    return e.value.code


def test_url_names_the_accession_json_endpoint():
    assert uniprot_url("P68871") == "https://rest.uniprot.org/uniprotkb/P68871.json"


def test_200_returns_the_entry():
    assert read_uniprot_response("P00001", 200, ENTRY) == json.loads(ENTRY)


def test_400_reports_uniprot_messages():
    body = json.dumps({"messages": ["bad accession", "two"]})
    assert (
        exit_message(read_uniprot_response, "X12345", 400, body)
        == "X12345: bad accession; two (HTTP 400)"
    )


@pytest.mark.parametrize(
    "status, body, reason",
    [
        (500, "<html>oops</html>", "Internal Server Error"),
        (404, '{"url": "x"}', "Not Found"),
        (400, '{"messages": "not a list of strings"}', "Bad Request"),
    ],
    ids=["html-body", "json-without-messages", "messages-wrong-type"],
)
def test_other_errors_fall_back_to_the_status_reason(status, body, reason):
    assert (
        exit_message(read_uniprot_response, "X12345", status, body)
        == f"X12345: {reason} (HTTP {status})"
    )


def test_status_zero_means_unreachable():
    assert (
        exit_message(read_uniprot_response, "X12345", 0, "Failed to fetch")
        == "X12345: could not reach UniProt (Failed to fetch)"
    )


def fake_urlopen(monkeypatch, exc=None, body=None):
    def urlopen(url, timeout):
        assert url == uniprot_url("X12345")
        if exc:
            raise exc
        return io.BytesIO(body)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


def test_fetch_uniprot_returns_the_entry(monkeypatch):
    fake_urlopen(monkeypatch, body=ENTRY.encode())
    assert fetch_uniprot("X12345") == json.loads(ENTRY)


@pytest.mark.parametrize(
    "exc, expected",
    [
        (
            urllib.error.HTTPError(
                "u",
                400,
                "Bad Request",
                {},
                io.BytesIO(b'{"messages": ["bad accession", "two"]}'),
            ),
            "X12345: bad accession; two (HTTP 400)",
        ),
        (
            urllib.error.HTTPError(
                "u", 500, "Internal Server Error", {}, io.BytesIO(b"<html>")
            ),
            "X12345: Internal Server Error (HTTP 500)",
        ),
        (
            urllib.error.URLError("no route"),
            "X12345: could not reach UniProt (no route)",
        ),
        (TimeoutError("timed out"), "X12345: could not reach UniProt (timed out)"),
    ],
    ids=["400-messages", "500-reason", "urlerror", "timeout"],
)
def test_fetch_uniprot_messages_are_unchanged(monkeypatch, exc, expected):
    fake_urlopen(monkeypatch, exc=exc)
    assert exit_message(fetch_uniprot, "X12345") == expected
