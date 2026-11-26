"""UniProtKB entry JSON -> feature rows."""

import json
import urllib.request

from .features import row, site_label


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


def fetch_uniprot(acc):
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.json"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())
