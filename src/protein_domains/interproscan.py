"""InterProScan 5/6 JSON -> feature rows."""

from .features import row, site_label


# InterProScan: member database -> (shape, shown by default)
IPRSCAN_SOURCE = {
    "Pfam": ("box", 1),
    "MobiDB-lite": ("bar", 1),
    "Coils": ("bar", 1),
    "SignalP_EUK": ("box", 1),
    "SignalP_GRAM_POSITIVE": ("box", 1),
    "SignalP_GRAM_NEGATIVE": ("box", 1),
    "SignalP": ("box", 1),
    "TMHMM": ("box", 1),
    "DeepTMHMM": ("box", 1),
    "Phobius": ("bar", 0),
    # everything else (SMART, CDD, Gene3D, SUPERFAMILY, PANTHER, PRINTS,
    # PROSITE, NCBIfam, HAMAP, PIRSF, PIRSR regions, InterPro-N ...) -> box, off
}
SITE_PREFIX = {  # PIRSR / CDD site descriptions
    "ACT_SITE": "Active site",
    "BINDING": "Binding site",
    "NP_BIND": "Binding site",
    "METAL": "Binding site",
    "SITE": "Site",
    "MOD_RES": "Modified residue",
    "DISULFID": "Disulfide bond",
}


def parse_iprscan(j):
    rows = []
    for i, res in enumerate(j["results"]):
        seq = res.get("sequence", "")
        xref = (res.get("xref") or [{}])[0]
        pid = xref.get("id") or xref.get("name") or f"seq{i + 1}"
        rows.append(
            row(
                protein=pid,
                source="InterProScan",
                type="Protein",
                start=1,
                end=len(seq),
                label=xref.get("name") or pid,
                show=1,
            )
        )
        gcount = 0
        for m in res.get("matches", []):
            sig = m["signature"]
            src = m.get("source") or sig["signatureLibraryRelease"]["library"]
            entry = sig.get("entry") or {}
            shape, show = IPRSCAN_SOURCE.get(src, ("box", 0))
            if src in ("Pfam", "SMART"):
                lab = sig.get("name") or sig.get("description") or sig["accession"]
            elif src == "MobiDB-lite":
                lab = "disordered"
            else:
                lab = (
                    sig.get("description")
                    or entry.get("description")
                    or sig.get("name")
                    or sig["accession"]
                )
            ftype = (
                "Disorder"
                if src == "MobiDB-lite"
                else "Coiled coil"
                if src == "Coils"
                else sig.get("type") or "Domain"
            )
            for loc in m.get("locations", []):
                frags = loc.get("location-fragments") or [
                    {"start": loc["start"], "end": loc["end"]}
                ]
                grp = ""
                if len(frags) > 1:
                    gcount += 1
                    grp = f"{src}:{sig['accession']}:{gcount}"
                for fr in frags:
                    rows.append(
                        row(
                            protein=pid,
                            source=src,
                            accession=sig["accession"]
                            + (
                                f" ({entry['accession']})"
                                if entry.get("accession")
                                else ""
                            ),
                            type=ftype,
                            start=fr["start"],
                            end=fr["end"],
                            label=lab,
                            shape=shape,
                            show=show,
                            group=grp,
                        )
                    )
                # residue-level predictions (PIRSR, CDD ...)
                for site in loc.get("sites") or []:
                    d = site.get("description", "")
                    pre, _, rest = d.partition(":")
                    stype = SITE_PREFIX.get(pre.strip(), "Site")
                    for sl in site.get("siteLocations", []):
                        s, e = sl["start"], sl["end"]
                        if s == e:
                            rows.append(
                                row(
                                    protein=pid,
                                    source=src,
                                    accession=sig["accession"],
                                    type=stype,
                                    start=s,
                                    end=e,
                                    label=site_label(
                                        stype, rest.strip(), s, e, sl.get("residue", "")
                                    ),
                                    shape="lollipop",
                                    show=1,
                                )
                            )
                        else:
                            rows.append(
                                row(
                                    protein=pid,
                                    source=src,
                                    accession=sig["accession"],
                                    type=stype,
                                    start=s,
                                    end=e,
                                    label=rest.strip() or d,
                                    shape="bar",
                                    show=1,
                                )
                            )
    return rows
