"""
protein-domains -- editable, DOG-style protein domain diagrams as SVG.

INPUT (auto-detected; several may be combined, proteins are stacked on one scale)
  P12345                UniProt accession  -> fetched from rest.uniprot.org
  entry.json            UniProt entry JSON (UniProt page > Download > JSON)
  iprscan.json          InterProScan 5/6 JSON (web server or command line)
  features.csv          the editable feature table this script writes. It may also hold
                        only extra rows for a protein given by another input: name the
                        protein by its accession in the 'protein' column, no Protein row

OUTPUT
  fig.svg               real <rect>/<text>/<path> elements, named groups (layers),
                        sizes in pt -> opens cleanly in Illustrator / Affinity / Inkscape
  fig_features.csv      one row per feature. Edit it, then re-render from it:
                          show   1/0  draw this row or not
                          shape  box | bar | lollipop | bracket | ss
                          label  text drawn on the feature
                          color  #RRGGBB (blank = automatic)
                          group  rows with the same group share a colour and are
                                 drawn as one discontinuous domain
                        Row order within a protein is irrelevant; protein order
                        follows the 'Protein' rows. Change the 'Protein' row label
                        to rename the sequence.

WORKFLOW
  protein-domains iprscan.json -o fig.svg --name "MyProtein"
  # edit fig_features.csv (switch rows on/off, rename labels, recolour)
  protein-domains fig_features.csv -o fig.svg
  protein-domains P12345 mine.csv -o fig.svg   # mine.csv: your own rows for P12345

TEXT SIZES
  --font-size sets everything at once. Override single kinds of text with
  --name-size, --domain-size, --outside-size, --site-size, --region-size,
  --number-size, --axis-size, --legend-size (all in pt).

LAYOUT
  All spacing derives from --font-size and the individual sizes. Text is
  measured with the real font (matplotlib, if installed; otherwise a
  conservative estimate). Labels that do
  not fit inside a domain go below it on a leader line; crowded site labels fan
  out; region bars are packed by label width; axis ticks thin out as text grows.
  After drawing, every text element is checked against all other text, shapes
  and lines (using its rotated outline) and any remaining collision is reported.

Standard library only; the optional "metrics" extra (matplotlib) gives exact text widths.
"""

import argparse
import sys
from pathlib import Path

from .features import write_csv
from .inputs import load_inputs
from .render import render


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "inputs",
        nargs="+",
        help="UniProt accession(s), UniProt/InterProScan JSON, or CSV",
    )
    ap.add_argument(
        "-o", "--out", default="domains.svg", help="output SVG (default domains.svg)"
    )
    ap.add_argument(
        "--name",
        action="append",
        help="display name per protein, in order (repeatable)",
    )
    ap.add_argument(
        "--width",
        type=float,
        default=400,
        help="width of the longest protein, pt (default 400)",
    )
    ap.add_argument("--font", default="Arial", help="font family (default Arial)")
    ap.add_argument(
        "--font-size",
        type=float,
        default=8,
        help="base font size in pt (default 8); all spacing scales with it",
    )
    ap.add_argument(
        "--numbers",
        action="store_true",
        help="print start/end residue under each domain",
    )
    ap.add_argument(
        "--label-angle",
        type=float,
        default=-90,
        help="site label rotation, -90 (vertical) to -20 (default -90)",
    )
    sz = ap.add_argument_group(
        "text sizes in pt (each defaults to a fraction of --font-size)"
    )
    sz.add_argument(
        "--name-size", type=float, help="protein names (default font-size + 1)"
    )
    sz.add_argument(
        "--domain-size",
        type=float,
        help="labels inside domain boxes (default font-size)",
    )
    sz.add_argument(
        "--outside-size",
        type=float,
        help="domain labels moved below their box (default 0.875 x domain size)",
    )
    sz.add_argument(
        "--site-size",
        type=float,
        help="lollipop / site labels (default 0.875 x font-size)",
    )
    sz.add_argument(
        "--region-size",
        type=float,
        help="labels under region bars (default 0.875 x font-size)",
    )
    sz.add_argument(
        "--number-size",
        type=float,
        help="domain boundary numbers and protein length (default 0.75 x font-size)",
    )
    sz.add_argument(
        "--axis-size", type=float, help="ruler numbers (default 0.875 x font-size)"
    )
    sz.add_argument(
        "--legend-size", type=float, help="legend text (default 0.875 x font-size)"
    )
    ap.add_argument(
        "--axis",
        choices=["full", "labels", "none"],
        default="full",
        help="residue ruler at the bottom: full (line, ticks, numbers), "
        "labels (numbers only) or none (default full)",
    )
    ap.add_argument(
        "--min-label-scale",
        type=float,
        default=0.7,
        help="domain labels may shrink to this fraction of the font size to fit "
        "inside their box before moving outside (1 = never shrink; default 0.7)",
    )
    a = ap.parse_args()

    rows = load_inputs(a.inputs, a.name)
    out = Path(a.out)
    if not all(Path(i).suffix.lower() == ".csv" for i in a.inputs):
        csv_out = out.with_name(out.stem + "_features.csv")
        if csv_out.exists():
            print(
                f"note: {csv_out} exists, not overwriting (delete it to regenerate)",
                file=sys.stderr,
            )
        else:
            write_csv(rows, csv_out)
            print(f"wrote {csv_out}", file=sys.stderr)
    render(
        rows,
        out,
        width=a.width,
        fs=a.font_size,
        font=a.font,
        numbers=a.numbers,
        label_angle=a.label_angle,
        min_label_scale=a.min_label_scale,
        axis=a.axis,
        sizes=dict(
            name=a.name_size,
            domain=a.domain_size,
            outside=a.outside_size,
            site=a.site_size,
            region=a.region_size,
            number=a.number_size,
            axis=a.axis_size,
            legend=a.legend_size,
        ),
    )
    print(f"wrote {out}", file=sys.stderr)
