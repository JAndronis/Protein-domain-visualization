"""Detect each input's format and turn it into feature rows."""

import json
import sys
from pathlib import Path

from .features import read_csv
from .interproscan import parse_iprscan
from .uniprot import UNIPROT_ID, fetch_uniprot, parse_uniprot


def load_inputs(inputs, names):
    rows = []
    for item in inputs:
        p = Path(item)
        if p.suffix.lower() == ".csv":
            rows += read_csv(p)
        elif p.suffix.lower() == ".json":
            j = json.loads(p.read_text(encoding="utf-8"))
            if (
                isinstance(j.get("results"), list)
                and j["results"]
                and "matches" in j["results"][0]
            ):
                rows += parse_iprscan(j)
            elif "primaryAccession" in j:
                rows += parse_uniprot(j)
            else:
                sys.exit(f"{p}: not a recognised UniProt or InterProScan JSON")
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
