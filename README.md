# Itombwe Forest — Exploring AI Biomass Data

A self-contained HTML report exploring open satellite biomass data for the
Itombwe Forest (South Kivu, DRC): comparing two datasets, converting biomass
to a carbon stock, and illustrating a REDD+ credit/revenue estimate.

**Live page:** https://portkeys.github.io/itombwe-findings/

The report is a single self-contained file (`index.html`) with all figures
embedded — no external assets. It is generated from `build_report.py` in this
repo; edit the source and regenerate rather than editing `index.html` directly.

## Source / regenerating

- `build_report.py` — builds `index.html` from the figure files (run this last).
- `make_timeseries_maps.py` — regenerates the 2000–2025 panels, change map, and
  animation from the CTrees ~100 m AGB dataset (needs `ARRAYLAKE_TOKEN` in `.env`).
- `build_notebook.py` — builds the demo notebook; executing it produces
  `fig_agb_map.png`, `fig_agb_timeseries.png`, `fig_revenue.png`, `fig_validation.png`.
- `fig_*.png` / `fig_agb_animation.gif` — figure inputs embedded into the report.

```bash
.venv/bin/python build_report.py   # regenerate index.html
```

`index.html` is served at the site root by GitHub Pages (`.nojekyll` keeps Pages
from running Jekyll over the repo).
