"""Recompute Itombwe biomass numbers clipped to the REAL reserve polygon (RN_Itombwe),
replacing the old bounding box. Reads the CTrees ~100 m AGB stack (2000-2025) once over
the reserve bbox window, applies the polygon mask, and reports:
  * mean AGB density and total above-ground stock (Mg & CO2e) per year, whole reserve,
  * 2000->2025 change,
  * per-sector latest-year stock and change.
Writes itombwe_numbers.json for the figure/report builders to consume.

Run: .venv/bin/python recompute_numbers.py
"""
import os, json, math, time
import numpy as np
import itombwe_aoi as aoi

# ---- load .env so arraylake picks up the token ----
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

CTREES_REPO = "portkeys/ctrees_data"
CTREES_PATH = "aboveground_biomass"
CTREES_SCALE = 10.0
CTREES_FILL = -9999
C_FRACTION = 0.47          # carbon fraction of dry biomass (IPCC default)
CO2_PER_C = 44.0 / 12.0    # CO2e per tonne C

_ct = {}


def connect():
    from arraylake import Client
    import zarr, icechunk
    try:
        client = Client()
    except Exception:
        client = Client(token=os.environ.get("ARRAYLAKE_TOKEN"))
    try:
        cfg = icechunk.RepositoryConfig.default()
        cfg.caching = icechunk.CachingConfig(num_chunk_refs=10_000)
        repo = client.get_repo(CTREES_REPO, config=cfg)
    except Exception:
        repo = client.get_repo(CTREES_REPO)
    root = zarr.open_group(repo.readonly_session(branch="main").store,
                           zarr_format=3, path=CTREES_PATH, mode="r")
    _ct["agb"] = root["agb"]
    _ct["x"] = root["x"][:]
    _ct["y"] = root["y"][:]
    _ct["years"] = [int(str(t)[:4]) for t in root["time"][:]]
    _ct["win"] = aoi.window(_ct["x"], _ct["y"])


def density(year):
    ti = _ct["years"].index(year)
    y0, y1, x0, x1 = _ct["win"]
    raw = _ct["agb"][ti, y0:y1, x0:x1].astype("float64")
    return np.where(raw == CTREES_FILL, np.nan, raw / CTREES_SCALE)


def main():
    t0 = time.time()
    connect()
    years = _ct["years"]
    win = _ct["win"]
    y0, y1, x0, x1 = win
    xs, ys = _ct["x"], _ct["y"]
    print(f"connected | {years[0]}-{years[-1]} | window rows/cols {y1-y0}x{x1-x0}")

    # masks aligned to the window
    rn_mask = aoi.rasterize(aoi.reserve_geom(), xs, ys, win)
    print(f"reserve mask: {rn_mask.sum()} pixels inside")

    # per-row pixel-area grid (latitude-corrected) in hectares
    row_lats = ys[y0:y1]
    px_ha_row = np.array([aoi.pixel_area_ha(lat) for lat in row_lats])  # (rows,)
    area_grid = np.repeat(px_ha_row[:, None], x1 - x0, axis=1)          # (rows, cols)

    # load full stack (window only)
    stack = np.empty((len(years),) + (y1 - y0, x1 - x0), dtype="float32")
    for i, yr in enumerate(years):
        stack[i] = density(yr)
    print(f"loaded stack {stack.shape} in {time.time()-t0:.0f}s")

    def stats(mask):
        """mean density, total Mg, total CO2e per year over a boolean mask."""
        m = mask & np.isfinite(stack).all(axis=0)  # require finite across all years
        area_in = area_grid[m].sum()                # ha
        per_year = []
        for i, yr in enumerate(years):
            d = stack[i][m]
            valid = np.isfinite(d)
            mean = float(np.nanmean(stack[i][mask]))      # mean over all in-poly (any-finite)
            mg = float(np.nansum(stack[i] * area_grid * mask))  # tonnes biomass
            per_year.append({"year": yr, "mean_density": mean,
                             "stock_Mg": mg,
                             "stock_CO2e": mg * C_FRACTION * CO2_PER_C})
        return area_in, per_year

    area_ha, per_year = stats(rn_mask)
    first, last = per_year[0], per_year[-1]
    print("\n=== WHOLE RESERVE (RN_Itombwe) ===")
    print(f"area inside mask: {area_ha:,.0f} ha")
    print(f"{'year':>6} {'mean Mg/ha':>11} {'stock Mt':>10} {'CO2e Mt':>10}")
    for r in per_year:
        print(f"{r['year']:>6} {r['mean_density']:>11.1f} {r['stock_Mg']/1e6:>10.2f} {r['stock_CO2e']/1e6:>10.2f}")
    d_pct = 100 * (last['stock_Mg'] - first['stock_Mg']) / first['stock_Mg']
    ann_pct = d_pct / (last['year'] - first['year'])
    print(f"\n2000->2025 stock change: {d_pct:+.2f}%  ({ann_pct:+.3f}%/yr)")
    print(f"headline {last['year']} stock: {last['stock_Mg']/1e6:.1f} Mt biomass "
          f"= {last['stock_CO2e']/1e6:.1f} Mt CO2e")

    # per-sector (latest year + change)
    print("\n=== PER SECTOR ===")
    sectors_out = {}
    print(f"{'sector':>12} {'area ha':>10} {'mean Mg/ha':>11} {'stock MtCO2e':>13} {'chg %':>8}")
    for name, geom in aoi.sector_geoms().items():
        smask = aoi.rasterize(geom, xs, ys, win)
        a, py = stats(smask)
        f0, l0 = py[0], py[-1]
        chg = 100 * (l0['stock_Mg'] - f0['stock_Mg']) / f0['stock_Mg'] if f0['stock_Mg'] else float('nan')
        sectors_out[name] = {"area_ha": a, "per_year": py, "change_pct": chg}
        print(f"{name:>12} {a:>10,.0f} {l0['mean_density']:>11.1f} "
              f"{l0['stock_CO2e']/1e6:>13.2f} {chg:>+8.2f}")

    out = {
        "boundary": "RN_Itombwe (whole reserve)",
        "area_ha": area_ha,
        "years": years,
        "whole_reserve": {"per_year": per_year,
                          "change_pct_total": d_pct,
                          "change_pct_annual": ann_pct},
        "sectors": sectors_out,
        "constants": {"C_FRACTION": C_FRACTION, "CO2_PER_C": CO2_PER_C,
                      "CTREES_SCALE": CTREES_SCALE},
    }
    with open("itombwe_numbers.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote itombwe_numbers.json | total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
