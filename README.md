# Protein domain visualization

Draws DOG-style protein domain diagrams as editable SVG from a UniProt accession, a UniProt entry JSON, or an InterProScan JSON. Each render also writes a `<out>_features.csv` feature table, which you can edit (labels, colours, which features to show) and render again. The output uses named layers, sizes in pt, and real text elements, so it opens cleanly in Illustrator or Inkscape. A browser GUI (`protein-domains-gui`) does the same editing by clicking on the figure.

```bash
uv sync --extra metrics                                 # metrics: exact text widths via matplotlib
uv run protein-domains P12345 -o fig.svg                # also writes fig_features.csv
uv run protein-domains fig_features.csv -o fig.svg --numbers
```
