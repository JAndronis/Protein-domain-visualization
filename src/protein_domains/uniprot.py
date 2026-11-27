"""UniProtKB entry JSON -> feature rows."""

import json
import re
import sys
import urllib.error
import urllib.request
from http import HTTPStatus

from .features import row, site_label


UNIPROT_ID = re.compile(r"[A-Za-z0-9_]{4,12}")

UNIPROT_SHAPE = {
    # boxes on the backbone
    "Domain": ("box", 1),
    "Repeat": ("box", 1),
    "Zinc finger": ("box", 1),
    "DNA binding": ("box", 1),
    "Transmembrane": ("box", 1),
    "Intramembrane": ("box", 1),
    "Signal": ("box", 1),
    "Transit peptide": ("box", 1),
    "Propeptide": ("box", 1),
    # thin bars in lanes underneath
    "Region": ("bar", 1),
    "Compositional bias": ("bar", 1),
    "Coiled coil": ("bar", 1),
    "Motif": ("bar", 1),
    # single residues -> lollipops above
    "Modified residue": ("lollipop", 1),
    "Glycosylation": ("lollipop", 1),
    "Lipidation": ("lollipop", 1),
    "Cross-link": ("lollipop", 1),
    "Active site": ("lollipop", 1),
    "Binding site": ("lollipop", 1),
    "Site": ("lollipop", 0),
    "Disulfide bond": ("bracket", 1),
    # secondary structure (off by default; lots of small elements)
    "Helix": ("ss", 0),
    "Beta strand": ("ss", 0),
    "Turn": ("ss", 0),
    "Natural variant": ("lollipop", 0),
    "Mutagenesis": ("lollipop", 0),
    "Topological domain": ("bar", 0),
    "Chain": ("bar", 0),
}


def parse_uniprot(j):
    acc = j.get("primaryAccession", "protein")
    if j.get("entryType") == "Inactive":
        why = j.get("inactiveReason") or {}
        detail = why.get("deletedReason") or ", ".join(why.get("mergeDemergeTo") or [])
        sys.exit(
            f"{acc}: inactive UniProt entry ({why.get('inactiveReasonType', 'unknown reason')}"
            + (f": {detail}" if detail else "")
            + ")"
        )
    gene = None
    if j.get("genes"):
        gene = (j["genes"][0].get("geneName") or {}).get("value")
    L = j["sequence"]["length"]
    seq = j["sequence"].get("value", "")
    rows = [
        row(
            protein=acc,
            source="UniProt",
            accession=acc,
            type="Protein",
            start=1,
            end=L,
            label=gene or acc,
            show=1,
        )
    ]
    for f in j.get("features", []):
        t = f["type"]
        s = (f["location"]["start"] or {}).get("value")
        e = (f["location"]["end"] or {}).get("value")
        if s is None or e is None:
            continue
        desc = f.get("description") or ""
        if not desc and f.get("ligand"):
            desc = f["ligand"].get("name", "")
        shape, show = UNIPROT_SHAPE.get(t, ("box", 0))
        if shape == "lollipop":
            res = seq[s - 1] if seq and s == e else ""
            lab = site_label(t, desc, s, e, res)
        elif t == "Disulfide bond":
            lab = f"C{s}-C{e}"
        else:
            lab = desc or t
        if shape == "lollipop" and s != e:  # ranged 'site' -> bar
            shape = "bar"
        rows.append(
            row(
                protein=acc,
                source="UniProt",
                type=t,
                start=s,
                end=e,
                label=lab,
                shape=shape,
                show=show,
            )
        )
    return rows


def uniprot_url(acc):
    return f"https://rest.uniprot.org/uniprotkb/{acc}.json"


def read_uniprot_response(acc, status, text):
    """What a UniProt GET returned -> the entry dict, or sys.exit with the message to show.

    status 0 means no response at all and `text` says why. The transport (urllib here, fetch()
    in the browser) is the caller's, so every message lives in this one place.
    """
    if status == 200:
        return json.loads(text)
    if status == 0:
        sys.exit(f"{acc}: could not reach UniProt ({text})")
    try:
        messages = json.loads(text)["messages"]
        if not (
            isinstance(messages, list) and all(isinstance(m, str) for m in messages)
        ):
            raise TypeError
        msg = "; ".join(messages)
    except (ValueError, KeyError, TypeError):
        msg = ""
    if not msg:
        try:
            msg = HTTPStatus(status).phrase
        except ValueError:
            msg = "HTTP error"
    sys.exit(f"{acc}: {msg} (HTTP {status})")


def fetch_uniprot(acc):
    try:
        with urllib.request.urlopen(uniprot_url(acc), timeout=30) as r:
            status, text = 200, r.read().decode()  # urlopen raises on non-2xx
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode(errors="replace")
    except OSError as e:
        status, text = 0, str(getattr(e, "reason", e))
    return read_uniprot_response(acc, status, text)
