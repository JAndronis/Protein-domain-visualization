"""Detect each input's format and turn it into feature rows."""

import json
import sys
from pathlib import Path

from .features import csv_rows
from .interproscan import parse_iprscan
from .uniprot import UNIPROT_ID, fetch_uniprot, parse_uniprot


def rows_from_text(name, text):
    """One document -> feature rows. The suffix of `name` picks CSV or JSON, the content picks the JSON kind."""
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        return csv_rows(text)
    if suffix != ".json":
        sys.exit(f"{name}: expected a .json or .csv file")
    try:
        j = json.loads(text)
    except ValueError as e:
        sys.exit(f"{name}: not valid JSON ({e})")
    if isinstance(j, dict):
        results = j.get("results")
        if isinstance(results, list) and results and "matches" in results[0]:
            return parse_iprscan(j)
        if "primaryAccession" in j:
            return parse_uniprot(j)
    sys.exit(f"{name}: not a recognised UniProt or InterProScan JSON")


def load_inputs(inputs, names):
    rows = []
    for item in inputs:
        p = Path(item)
        if p.suffix.lower() in (".csv", ".json"):
            with open(p, newline="", encoding="utf-8-sig") as fh:
                rows += rows_from_text(str(p), fh.read())
        elif UNIPROT_ID.fullmatch(item):
            print(f"fetching {item} from UniProt ...", file=sys.stderr)
            rows += parse_uniprot(fetch_uniprot(item))
        else:
            sys.exit(f"don't know what to do with input '{item}'")
    # --name overrides labels of Protein rows in order
    if names:
        prots = [r for r in rows if r["type"] == "Protein"]
        for r, n in zip(prots, names):
            r["label"] = n
    return rows
