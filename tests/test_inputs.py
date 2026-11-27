import json

import pytest

from paths import DATA
from protein_domains.inputs import load_inputs, rows_from_text


def text(name):
    return (DATA / name).read_text(encoding="utf-8")


def test_csv_text_gives_the_table_rows():
    rows = rows_from_text("mini.csv", text("mini.csv"))
    assert [r["label"] for r in rows if r["type"] == "Protein"] == ["Demo"]
    assert len(rows) == 5


def test_uniprot_json_gives_protein_and_features():
    rows = rows_from_text("entry.json", text("mini_uniprot.json"))
    assert rows[0]["type"] == "Protein"
    assert rows[0]["label"] == "DEMO1"
    assert {r["type"] for r in rows} == {
        "Protein",
        "Domain",
        "Modified residue",
        "Disulfide bond",
    }


def test_interproscan_json_gives_grouped_fragments():
    rows = rows_from_text("scan.json", text("mini_iprscan.json"))
    assert rows[0]["label"] == "Sequence1"
    assert any(r["group"] for r in rows)


def test_suffix_is_case_insensitive():
    assert rows_from_text("MINI.CSV", text("mini.csv"))


@pytest.mark.parametrize(
    "doc",
    ['{"hello": 1}', "[1, 2]", "[]", '"str"', "null", '{"results": []}'],
    ids=["object", "list", "empty-list", "string", "null", "empty-results"],
)
def test_unrecognised_json_exits_naming_the_upload(doc):
    with pytest.raises(SystemExit) as e:
        rows_from_text("mine.json", doc)
    assert str(e.value.code).startswith("mine.json: not a recognised")


def test_invalid_json_exits_naming_the_upload():
    with pytest.raises(SystemExit) as e:
        rows_from_text("broken.json", "{nope")
    assert str(e.value.code).startswith("broken.json:")


@pytest.mark.parametrize("name", ["x.txt", "noext", "x.csv.bak"])
def test_other_suffix_exits_naming_the_upload(name):
    with pytest.raises(SystemExit) as e:
        rows_from_text(name, "")
    assert str(e.value.code) == f"{name}: expected a .json or .csv file"


@pytest.mark.parametrize(
    "fixture", ["mini.csv", "mini_uniprot.json", "mini_iprscan.json"]
)
def test_load_inputs_on_a_path_equals_rows_from_text(fixture):
    path = DATA / fixture
    assert load_inputs([str(path)], None) == rows_from_text(
        str(path), path.read_text(encoding="utf-8")
    )


def test_load_inputs_error_names_the_path(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([1]))
    with pytest.raises(SystemExit) as e:
        load_inputs([str(p)], None)
    assert str(e.value.code) == f"{p}: not a recognised UniProt or InterProScan JSON"


def test_load_inputs_names_override_protein_labels():
    rows = load_inputs([str(DATA / "mini_uniprot.json")], ["Mine"])
    assert rows[0]["label"] == "Mine"


def test_load_inputs_rejects_unknown_input():
    with pytest.raises(SystemExit) as e:
        load_inputs(["../etc"], None)
    assert str(e.value.code) == "don't know what to do with input '../etc'"
