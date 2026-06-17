"""Activity Data (AD) for the Itombwe reserve from Hansen Global Forest Change (GFC-2024-v1.12).

VM0048/VMD0055 needs AD = forest area deforested per year. Hansen GFC is the UMD/Landsat
~30 m product that Global Forest Watch redistributes, so "GFW tree-cover loss" = this layer.

We read ONLY the reserve window from the public tile via /vsicurl (no full-tile download):
  * lossyear      (0 = no loss, 1..24 = loss in 2001..2024)
  * treecover2000 (% canopy in 2000)  -> forest = canopy >= FOREST_THRESHOLD
Then mask to the reserve polygon and count forest-loss hectares per year.

Outputs:
  hansen_ad.json         annual deforested ha/yr + forest-2000 area, reserve-clipped
  hansen_loss.npy        downsampled loss-year raster (for the comparison figure)
Run: .venv/bin/python hansen_activity_data.py
"""
import os, json
import numpy as np
import itombwe_aoi as aoi

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask

GFC_VER = "GFC-2024-v1.12"
TILE = "00N_020E"                      # 10x10° tile covering Itombwe (lon 20-30E, lat 0-10S)
BASE = f"https://storage.googleapis.com/earthenginepartners-hansen/{GFC_VER}"
FOREST_THRESHOLD = 30                  # % canopy in 2000 to count as "forest" (GFW default)
M_PER_DEG = 111_320.0


def _url(layer):
    return f"/vsicurl/{BASE}/Hansen_{GFC_VER}_{layer}_{TILE}.tif"


def read_window(layer, bounds):
    """Read the reserve-bbox window from a Hansen layer; return (array, transform)."""
    with rasterio.open(_url(layer)) as ds:
        win = from_bounds(*bounds, transform=ds.transform)
        arr = ds.read(1, window=win)
        transform = ds.window_transform(win)
    return arr, transform


def main():
    w, s, e, n = aoi.bbox()
    bounds = (w, s, e, n)
    print(f"reading Hansen {GFC_VER} window over reserve bbox ...")
    loss, transform = read_window("lossyear", bounds)
    tc2000, _ = read_window("treecover2000", bounds)
    print(f"window {loss.shape} @ ~30 m")

    # reserve polygon mask at the Hansen grid
    inside = geometry_mask([aoi.reserve_geom()], out_shape=loss.shape,
                           transform=transform, invert=True)

    # per-row latitude-corrected pixel area (ha) for this 30 m grid
    rows = loss.shape[0]
    px_deg = abs(transform.e)                       # 0.00025
    top_lat = transform.f                           # north edge
    row_lat = top_lat - (np.arange(rows) + 0.5) * px_deg
    dy = px_deg * M_PER_DEG
    px_ha_row = (px_deg * M_PER_DEG * np.cos(np.radians(row_lat))) * dy / 1e4
    area_grid = np.repeat(px_ha_row[:, None], loss.shape[1], axis=1)

    forest2000 = (tc2000 >= FOREST_THRESHOLD) & inside
    forest_area_ha = float(area_grid[forest2000].sum())
    reserve_area_ha = float(area_grid[inside].sum())
    print(f"reserve area (30 m): {reserve_area_ha:,.0f} ha | "
          f"forest>={FOREST_THRESHOLD}% in 2000: {forest_area_ha:,.0f} ha "
          f"({100*forest_area_ha/reserve_area_ha:.1f}%)")

    # forest-loss area per year (only where there was forest in 2000, inside reserve)
    annual = []
    floss = forest2000  # base forest mask
    for yr_code in range(1, 25):                    # 1..24 -> 2001..2024
        m = (loss == yr_code) & floss
        ha = float(area_grid[m].sum())
        annual.append({"year": 2000 + yr_code, "deforested_ha": ha})

    total_loss = sum(a["deforested_ha"] for a in annual)
    years = [a["year"] for a in annual]
    has = [a["deforested_ha"] for a in annual]
    print("\nForest loss (ha/yr) inside reserve:")
    for a in annual:
        bar = "#" * int(a["deforested_ha"] / max(has) * 40) if max(has) else ""
        print(f"  {a['year']}  {a['deforested_ha']:8.1f}  {bar}")
    print(f"\ntotal 2001-2024 forest loss: {total_loss:,.0f} ha "
          f"({100*total_loss/forest_area_ha:.2f}% of 2000 forest)")
    # historical baseline rate (VM0048 uses ~10-yr historical average, no upward trend)
    last10 = [a["deforested_ha"] for a in annual if a["year"] >= 2015]
    mean10 = sum(last10) / len(last10)
    mean_all = total_loss / len(annual)
    print(f"mean AD 2001-2024: {mean_all:,.1f} ha/yr | mean AD 2015-2024: {mean10:,.1f} ha/yr")

    out = {
        "source": f"Hansen {GFC_VER} (UMD/GLAD, Landsat ~30 m; = GFW tree-cover loss)",
        "tile": TILE, "forest_threshold_pct": FOREST_THRESHOLD,
        "reserve_area_ha": reserve_area_ha,
        "forest2000_area_ha": forest_area_ha,
        "annual": annual,
        "total_loss_2001_2024_ha": total_loss,
        "mean_ad_2001_2024_ha_yr": mean_all,
        "mean_ad_2015_2024_ha_yr": mean10,
    }
    with open("hansen_ad.json", "w") as f:
        json.dump(out, f, indent=2)

    # downsample loss-year raster for a comparison figure (factor ~5 -> ~150 m)
    f = 5
    H, W = loss.shape
    lr = loss[:H // f * f, :W // f * f].reshape(H // f, f, W // f, f)
    ins = inside[:H // f * f, :W // f * f].reshape(H // f, f, W // f, f)
    loss_any = ((lr > 0) & ins).any(axis=(1, 3)).astype("uint8")
    inside_ds = ins.any(axis=(1, 3)).astype("uint8")
    np.save("hansen_loss.npy", loss_any)
    np.save("hansen_inside.npy", inside_ds)
    print("\nwrote hansen_ad.json, hansen_loss.npy, hansen_inside.npy")


if __name__ == "__main__":
    main()
