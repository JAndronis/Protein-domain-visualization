# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`protein-domains` is a CLI and small library that draws DOG-style protein domain diagrams as editable SVG
(named `<g>` layers, sizes in pt, real `<rect>`/`<text>`/`<path>` elements for Illustrator/Inkscape).
It is a uv project with src layout (`src/protein_domains/`) and no runtime dependencies. The optional
`metrics` extra (matplotlib) is only used for exact text widths.

Tests live in `tests/` (pytest), with sample inputs in `tests/data/` and expected outputs in
`tests/golden/`.

## Commands

```bash
uv sync --extra metrics          # drop --extra metrics to exercise the width-estimate path

# render from an InterProScan JSON (also writes <out>_features.csv next to the SVG, never overwriting it)
uv run protein-domains iprscan.json -o fig.svg --name "MyProtein"

# re-render from the edited feature table (the main editing loop)
uv run protein-domains fig_features.csv -o fig.svg --numbers

# other inputs: UniProt accession (fetched from rest.uniprot.org) or UniProt entry JSON; several can be stacked
uv run protein-domains P12345 entry.json -o fig.svg

# browser GUI on localhost: open a JSON/CSV or fetch a UniProt ID, set the CLI options, click elements to edit label/colour, add custom features
uv run protein-domains-gui            # --port N, --no-browser

# static page: gui.html + the package sources inlined, run by Pyodide (CDN) in the browser
uv run python scripts/build_site.py -o site/      # then: python3 -m http.server -d site, or open site/index.html

uv run --group dev pytest                         # unit tests; skips browser and network tests
uv run --group e2e pytest -m e2e                  # real Chromium: server mode, static mode, byte parity (needs the Pyodide CDN)
uv run --group e2e pytest -m network              # opens site/index.html from file://
uv run python scripts/capture_goldens.py          # regenerate tests/golden/ after an intended layout change

uvx ruff format src tests scripts
uvx ruff check src tests scripts
```

`python -m protein_domains` also works. Write scratch renders outside the project directory. Check
stderr after every render: it reports `text metrics: <font file|estimate>`, omitted boundary numbers, and
any remaining text overlaps. Layout differs between the matplotlib and estimate paths, so compare outputs
only within one path.

## Architecture

The pipeline is **inputs → row dicts (the CSV schema) → `render()` → SVG**. Every input format is
normalised to the same flat row schema (`features.COLUMNS`), which is also the user-editable CSV. Anything
new a parser extracts must fit that schema, and anything `render()` needs must be derivable from it.

Modules are organised by what they know, not by pipeline step:

- `features.py` owns the row schema, CSV read/write, and `site_label` (PTM abbreviations), which both
  parsers share.
- `uniprot.py` and `interproscan.py` each own one source format. They map source feature types to a
  default `shape` and `show` flag through `UNIPROT_SHAPE` and `IPRSCAN_SOURCE`. Unknown types default to
  `box`, hidden. Residue-level InterProScan sites (PIRSR/CDD) become `lollipop` rows, or `bar` rows when
  ranged. Discontinuous InterProScan domains get a shared `group` id, so `render()` colours the group once,
  labels only its largest fragment, and joins the fragments with dotted links.
- `inputs.py` detects each input's format and dispatches to a parser. `cli.py` is only argparse; its
  module docstring is the `--help` text.
- `render.py` holds the whole layout in one `layout()` function plus the colour palettes. `layout()` is
  pure: it returns a `Figure` (SVG text, overlaps, omitted boundary numbers, warnings, metrics source).
  `render()` writes that figure to a file and reports on stderr.
- `api.py` is the single registry of what the GUI page can ask Python (`ROUTES`) and owns the one error
  envelope: `handle(route, body)` never raises, `SystemExit` and other exceptions become `{"error"}`.
  `handle_json` is the string-in, string-out form both transports call. Inputs are `(name, text)`
  documents (`inputs.rows_from_text`), never paths. UniProt is split into `uniprot_url` and the pure
  `read_uniprot_response`; the page does the `fetch()` itself in both modes (`/api/fetch-plan`, then
  `/api/uniprot`) and urllib stays in the CLI's `fetch_uniprot`.
- `gui.py` serves `gui.html` with the stdlib `http.server`, forwards POSTs to `api.handle_json`, and has no
  state of its own. The page holds the
  row table and the `layout()` options, posts both to `/api/render` on every edit, and swaps in the
  returned SVG. Files are loaded through `rows_from_text()`, so the GUI accepts exactly what the CLI accepts.
- `scripts/build_site.py` (not in the wheel) writes `site/index.html`: `gui.html` plus every
  `src/protein_domains/*.py` as a JSON `<script id="py-sources">` and a pinned Pyodide `<script>`. The page
  picks its transport once from that tag: HTTP to `gui.py`, or `handle_json` inside Pyodide. Pyodide never
  loads matplotlib, so a static-page SVG equals the CLI run without the `metrics` extra, byte for byte.
  `gui.html` must keep exactly one inline `<script>`.
  Custom features are ordinary rows with `source` "Custom" that the page appends. Deleting a row shifts every
  later row index, so the page rebuilds the table and the name fields afterwards.
- `canvas.py` emits SVG fragments. `geometry.py` holds interval packing, label spreading and the
  collision tests. `metrics.py` measures text.

Rendering rules that span several of these modules:

- **Protein identity.** Each protein is defined by a `type == "Protein"` row (its `end` is the sequence
  length, its `label` the display name). Feature rows reference it through the `protein` column. Protein
  order in the figure follows the order of those rows.
- **Layout order.** `render()` lays out one protein at a time, top to bottom, with a running `y`/`cur`
  cursor. Within a protein: lollipop geometry first (it sets the height above the backbone) → name and
  backbone → domain boxes packed into lanes, with labels inside or on leader lines below → secondary
  structure → region bars (packed by bar *or* label width) → disulfide brackets → lollipops drawn. Then a
  shared residue axis and a wrapping legend.
- **Sizing.** Every spacing constant derives from `--font-size` (`fs`) and the per-kind text sizes in `S`.
  Absolute pt offsets break when the font size changes.
- **Overlap check.** `Canvas` records every text's rotated outline, every filled shape and every line
  segment with an `owner`. `Canvas.overlaps()` checks text against text, against shapes with a different
  owner, and against lines with a different owner. `render()` returns that list. A layout change should not add overlaps on
  the inputs in `tests/data/`.
- **Obstacles.** Inside a protein, the name and length label are registered as `obstacles`. Later
  placement (boundary numbers, outside labels, region lanes) avoids them through `blocked()`.
- **Boundary numbers** (`--numbers`) are never moved. A number without room is dropped and reported, so it
  can't be misread as another domain's boundary.
- **SVG ids.** `Canvas.uid()` counts ids per figure, so repeated renders in one process (the GUI renders
  on every edit) give identical ids.
- **Row tags.** `layout(tag_rows=True)` wraps each row's drawn parts in `<g data-row="i">`, where `i`
  indexes the `rows` list passed in. The GUI uses it to map a click back to its row. The CLI and the GUI's
  SVG download leave it off, so both produce the same bytes for the same rows and options. A new drawn
  element for a row must go through `tagged()` or it won't be clickable in the GUI.
