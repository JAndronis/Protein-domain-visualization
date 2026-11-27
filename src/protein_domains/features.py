"""The feature table: one row dict per feature, shared by every parser, the CSV and the renderer."""

import csv
import io
from pathlib import Path


MOD_ABBR = {
    "Phosphoserine": "pS",
    "Phosphothreonine": "pT",
    "Phosphotyrosine": "pY",
    "Phosphohistidine": "pH",
    "N6-acetyllysine": "acK",
    "N6-methyllysine": "meK",
    "N6,N6-dimethyllysine": "me2K",
    "N6,N6,N6-trimethyllysine": "me3K",
    "Omega-N-methylarginine": "meR",
    "Asymmetric dimethylarginine": "me2aR",
    "Symmetric dimethylarginine": "me2sR",
    "N-acetylmethionine": "acM",
    "N-acetylserine": "acS",
    "N-acetylalanine": "acA",
    "Citrulline": "Cit",
    "Pyrrolidone carboxylic acid": "pE",
    "Hydroxyproline": "Hyp",
    "4-hydroxyproline": "Hyp",
    "Sulfotyrosine": "sY",
}


COLUMNS = [
    "protein",
    "source",
    "accession",
    "type",
    "start",
    "end",
    "label",
    "shape",
    "show",
    "color",
    "group",
]


def row(**kw):
    r = {c: "" for c in COLUMNS}
    r.update({k: ("" if v is None else v) for k, v in kw.items()})
    return r


def site_label(ftype, desc, s, e, residue=""):
    first = desc.split(";")[0].strip()
    if ftype == "Modified residue":
        return f"{MOD_ABBR.get(first, first.split()[0] if first else 'mod')}{s}"
    if ftype == "Glycosylation":
        return (
            "N-gly"
            if first.startswith("N-")
            else "O-gly"
            if first.startswith("O-")
            else "gly"
        ) + str(s)
    if ftype == "Cross-link":
        for k, v in (("ubiquitin", "Ub"), ("SUMO", "SUMO"), ("NEDD8", "N8")):
            if k in desc:
                return f"{v}K{s}"
        return f"XL{s}"
    if residue and len(residue) == 1:
        return f"{residue}{s}"
    return f"{first}" if first else f"{ftype} {s}"


def csv_rows(text):
    """CSV text -> rows over COLUMNS. A leading BOM is dropped, as utf-8-sig does for files."""
    reader = csv.DictReader(io.StringIO(text.removeprefix("\ufeff"), newline=""))
    return [{c: r.get(c, "") or "" for c in COLUMNS} for r in reader]


def read_csv(path):
    # newline="" keeps CRLF inside quoted fields, as csv expects
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return csv_rows(fh.read())


def csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_csv(rows, path):
    Path(path).write_text(csv_text(rows), encoding="utf-8", newline="")
