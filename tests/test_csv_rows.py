import pytest

from paths import DATA
from protein_domains.features import COLUMNS, csv_rows, read_csv

QUOTED = 'protein,label\r\nP1,"two\nlines"\r\nP2,plain\r\n'


def test_csv_rows_matches_read_csv_on_fixture():
    text = (DATA / "mini.csv").read_text(encoding="utf-8")
    assert csv_rows(text) == read_csv(DATA / "mini.csv")


@pytest.mark.parametrize(
    "raw",
    [
        b"\xef\xbb\xbfprotein,label\nP1,a\n",
        b"protein,label\r\nP1,a\r\nP2,b\r\n",
        QUOTED.encode(),
        b"protein,label,extra\nP1,a,ignored\n",
    ],
    ids=["bom", "crlf", "quoted-newline", "extra-column"],
)
def test_csv_rows_equals_read_csv_on_same_bytes(tmp_path, raw):
    p = tmp_path / "t.csv"
    p.write_bytes(raw)
    assert csv_rows(raw.decode("utf-8")) == read_csv(p)


def test_csv_rows_fills_every_column_and_keeps_newlines():
    rows = csv_rows(QUOTED)
    assert [list(r) for r in rows] == [COLUMNS, COLUMNS]
    assert rows[0]["label"] == "two\nlines"
    assert rows[1]["start"] == ""


def test_read_csv_keeps_crlf_inside_quoted_field(tmp_path):
    p = tmp_path / "t.csv"
    p.write_bytes(b'protein,label\r\nP1,"a\r\nb"\r\n')
    assert read_csv(p)[0]["label"] == "a\r\nb"
