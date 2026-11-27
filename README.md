# Protein domain visualization

Draws [DOG](#reference)-style protein domain diagrams as editable SVG from a UniProt accession, a UniProt entry JSON, or an InterProScan JSON. Each render also writes a `<out>_features.csv` feature table, which you can edit (labels, colours, which features to show) and render again. The output uses named layers, sizes in pt, and real text elements, so it opens cleanly in Illustrator or Inkscape. A browser GUI (`protein-domains-gui`) does the same editing by clicking on the figure, can fetch a UniProt entry by ID, and can add your own features (domain, region, site, disulfide bracket, secondary structure) that end up in the downloaded CSV.

The GUI also runs entirely in the browser, with no install: https://jandronis.github.io/Protein-domain-visualization/. That page runs the same Python code in Pyodide and estimates text widths, so its layout can differ slightly from a CLI render with the `metrics` extra. `uv run python scripts/build_site.py -o site` builds it locally as one `site/index.html`, which also works opened from disk.

```bash
uv sync --extra metrics                                 # metrics: exact text widths via matplotlib
uv run protein-domains P12345 -o fig.svg                # also writes fig_features.csv
uv run protein-domains fig_features.csv -o fig.svg --numbers
```

## Reference

The figure style follows DOG:

Ren J, Wen L, Gao X, Jin C, Xue Y, Yao X. DOG 1.0: illustrator of protein domain structures. *Cell Research* 19, 271–273 (2009). https://doi.org/10.1038/cr.2009.6
