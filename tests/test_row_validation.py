import xml.etree.ElementTree as ET

import pytest

from paths import DATA
from protein_domains.api import handle
from protein_domains.features import csv_rows
from protein_domains.render import layout


def rows_with(**cells):
    rows = csv_rows((DATA / "mini.csv").read_text(encoding="utf-8"))
    rows[4].update(cells)  # the "disordered region" bar
    return rows


def render(rows, **opts):
    return handle("/api/render", {"rows": rows, "tag_rows": True, "opts": opts})


def attribute_names(svg):
    return {k for el in ET.fromstring(svg).iter() for k in el.attrib}


@pytest.mark.parametrize("shape", ["bar", "box", "lollipop", "bracket", "ss"])
def test_colour_cannot_inject_an_attribute(estimate, shape):
    out = render(rows_with(shape=shape, color='#123456" onmouseover="alert(1)'))
    assert out["error"] == (
        "Sequence1 Region 'disordered\nregion': color "
        "'#123456\" onmouseover=\"alert(1)' is not #RRGGBB"
    )


@pytest.mark.parametrize("color", ["red", "#F00", "rgb(1,2,3)"])
def test_colour_other_than_rrggbb_is_a_message_not_a_crash(estimate, color):
    out = render(rows_with(shape="box", color=color))
    assert out["error"].endswith(f"color '{color}' is not #RRGGBB")


def test_rrggbb_colour_in_either_case_is_drawn(estimate):
    out = render(rows_with(color=" #a1B2c3 "))
    assert "error" not in out
    assert 'fill="#a1B2c3"' in out["svg"]


def test_unknown_shape_is_reported_instead_of_dropped(estimate):
    out = render(rows_with(shape="circle"))
    assert out["error"] == (
        "Sequence1 Region 'disordered\nregion': shape 'circle' is not one of "
        "box, bar, lollipop, bracket, ss"
    )


@pytest.mark.parametrize("column", ["start", "end"])
def test_non_numeric_position_names_the_row(estimate, column):
    out = render(rows_with(**{column: "ten"}))
    assert out["error"] == (
        f"Sequence1 Region 'disordered\nregion': {column} 'ten' is not a number"
    )


def test_font_name_cannot_inject_an_attribute(estimate):
    rows = csv_rows((DATA / "mini.csv").read_text(encoding="utf-8"))
    svg = layout(rows, font='Arial" onload="alert(1)').svg
    assert "onload" not in attribute_names(svg)
    assert 'font-family="Arial&quot; onload=&quot;alert(1)"' in svg


def test_hidden_row_is_not_checked(estimate):
    shown = render(rows_with(show="0"))
    hidden_junk = render(rows_with(show="0", start="", shape="weird", color="red"))
    assert hidden_junk == shown


def test_protein_row_needs_only_a_numeric_end(estimate):
    rows = rows_with()
    rows[0].update(shape="Protein", start="", color="whatever", label="  Demo  ")
    assert "error" not in render(rows)
    rows[0]["end"] = "n/a"
    assert (
        render(rows)["error"]
        == "Sequence1 Protein '  Demo  ': end 'n/a' is not a number"
    )


def test_infinite_position_names_the_row(estimate):
    out = render(rows_with(start="inf"))
    assert out["error"] == (
        "Sequence1 Region 'disordered\nregion': start 'inf' is not a number"
    )
