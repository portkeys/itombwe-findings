"""Generate time-series biomass figures for the Itombwe report from the real
CTrees ~100 m AGB dataset (2000-2025, via Arraylake/Icechunk):

  fig_agb_panels.png     — 2000 | 2015 | 2025 density maps, shared color scale
  fig_agb_change.png     — per-pixel biomass trend 2000->2025 (where loss concentrates)
  fig_agb_animation.gif  — looping 2000->2025 density animation

Reuses the exact CTrees access pattern from build_notebook.py. Run:
    .venv/bin/python make_timeseries_maps.py
"""
import os, io, math, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, TwoSlopeNorm
from PIL import Image, ImageDraw, ImageFont
import itombwe_aoi as aoi          # REAL reserve polygon (replaces the bounding box)

# ---- load .env so arraylake picks up the token ----
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ---- CTrees reader (same constants as build_notebook.py) ----
CTREES_REPO    = "portkeys/ctrees_data"
CTREES_PATH    = "aboveground_biomass"
CTREES_SCALE   = 10.0
CTREES_FILL    = -9999
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
    _ct["agb"]   = root["agb"]
    _ct["x"]     = root["x"][:]
    _ct["y"]     = root["y"][:]
    _ct["years"] = [int(str(t)[:4]) for t in root["time"][:]]
    _ct["win"] = aoi.window(_ct["x"], _ct["y"])
    # boolean mask of pixels inside the real reserve polygon, aligned to the window
    _ct["mask"] = aoi.rasterize(aoi.reserve_geom(), _ct["x"], _ct["y"], _ct["win"])

def density(year):
    ti = _ct["years"].index(year)
    y0, y1, x0, x1 = _ct["win"]
    raw = _ct["agb"][ti, y0:y1, x0:x1].astype("float64")
    return np.where(raw == CTREES_FILL, np.nan, raw / CTREES_SCALE)

t0 = time.time()
connect()
YEARS = _ct["years"]
print(f"connected | {YEARS[0]}-{YEARS[-1]} | {len(YEARS)} years")

# ---- load the full stack once (only the AOI window) ----
stack = np.empty((len(YEARS),) + density(YEARS[0]).shape, dtype="float32")
stack[0] = density(YEARS[0])
for i, yr in enumerate(YEARS[1:], start=1):
    stack[i] = density(yr)
# clip to the real reserve polygon: everything outside the boundary -> NaN, so the
# maps render the reserve's true shape (not a rectangle) and stats are reserve-only.
outside = ~_ct["mask"]
stack[:, outside] = np.nan
print(f"loaded stack {stack.shape} in {time.time()-t0:.0f}s | "
      f"{_ct['mask'].sum()} pixels inside reserve")

VMAX = float(np.nanpercentile(stack, 98))   # shared scale across all years
print(f"shared vmax (p98) = {VMAX:.0f} Mg/ha")

def yr_slice(year):
    return stack[YEARS.index(year)]

def save_png_quantized(fig, path, colors=256):
    """Save a matplotlib figure as a palette-quantized PNG — colormap maps have
    few distinct colors, so this cuts file size 3-5x with no visible loss."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="white")
    buf.seek(0)
    im = Image.open(buf).convert("RGB").quantize(colors=colors, method=Image.FASTOCTREE)
    im.save(path, optimize=True)

# ============================================================ 1) 3-PANEL
panel_years = [2000, 2015, 2025]
fig, axes = plt.subplots(1, 3, figsize=(13, 5.4))
im = None
for ax, yr in zip(axes, panel_years):
    im = ax.imshow(yr_slice(yr), cmap="YlGn", vmin=0, vmax=VMAX)
    mean = np.nanmean(yr_slice(yr))
    ax.set_title(f"{yr}", fontsize=15, fontweight="bold", color="#1b5e3f", pad=8)
    ax.text(0.5, -0.04, f"mean {mean:.0f} Mg/ha", transform=ax.transAxes,
            ha="center", va="top", fontsize=10, color="#6c7a72")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#e5dfd2")
fig.subplots_adjust(left=0.01, right=0.91, top=0.93, bottom=0.06, wspace=0.06)
cax = fig.add_axes([0.93, 0.10, 0.018, 0.78])
cb = fig.colorbar(im, cax=cax); cb.set_label("Mg dry biomass / ha", fontsize=10)
save_png_quantized(fig, "fig_agb_panels.png", colors=256)
plt.close(fig)
print("saved fig_agb_panels.png")

# ============================================================ 2) CHANGE / TREND MAP
# Per-pixel OLS slope (Mg/ha per year) over 2000-2025 -> robust change signal.
t = np.array(YEARS, dtype="float64"); t -= t.mean()
ybar = np.nanmean(stack, axis=0)
num = np.tensordot(t, (stack - ybar), axes=(0, 0))
slope = num / np.sum(t**2)                      # Mg/ha per year
total_change = slope * (YEARS[-1] - YEARS[0])   # Mg/ha over the full period

vlim = float(np.nanpercentile(np.abs(total_change), 98))
fig, ax = plt.subplots(figsize=(6.8, 7.6))
norm = TwoSlopeNorm(vmin=-vlim, vcenter=0.0, vmax=vlim)
im = ax.imshow(total_change, cmap="RdYlGn", norm=norm)
ax.set_title("Apparent biomass change, 2000 → 2025\n(red = loss, green = gain)",
             fontsize=11, color="#16241d")
ax.set_xticks([]); ax.set_yticks([])
cb = fig.colorbar(im, ax=ax, shrink=0.72); cb.set_label("Δ Mg/ha over 25 years")
# share of reserve pixels losing >2 Mg/ha (over valid in-reserve pixels only)
valid = np.isfinite(total_change)
loss_frac = 100 * np.sum((total_change < -2) & valid) / np.sum(valid)
ax.text(0.5, -0.02, f"{loss_frac:.0f}% of pixels show a net loss > 2 Mg/ha",
        transform=ax.transAxes, ha="center", va="top", fontsize=9.5, color="#6c7a72")
fig.tight_layout()
save_png_quantized(fig, "fig_agb_change.png", colors=256)
plt.close(fig)
print(f"saved fig_agb_change.png | {loss_frac:.0f}% pixels net loss >2 Mg/ha")

# ============================================================ 3) ANIMATED GIF
def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

cmap = cm.get_cmap("YlGn")
norm = Normalize(vmin=0, vmax=VMAX)
H, W = stack.shape[1:]
target_h = 400
scale = target_h / H
target_w = int(round(W * scale))
BAND_H = 56                                           # header strip above the map for the year
f = font(40)
frames = []
for i, yr in enumerate(YEARS):
    rgba = cmap(norm(stack[i]))                       # (H,W,4) float
    rgb = (rgba[..., :3] * 255).astype("uint8")
    rgb[outside] = (20, 64, 44)                        # outside reserve -> canvas green
    map_img = Image.fromarray(rgb).resize((target_w, target_h), Image.BILINEAR)
    # place the map under a solid header band so the year never overlaps the map
    canvas = Image.new("RGB", (target_w, target_h + BAND_H), (20, 64, 44))
    canvas.paste(map_img, (0, BAND_H))
    d = ImageDraw.Draw(canvas)
    label = str(yr)
    tb = d.textbbox((0, 0), label, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(((target_w - tw) / 2 - tb[0], (BAND_H - th) / 2 - tb[1]), label,
           fill=(243, 247, 243), font=f)                # centered in the header band
    frames.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=64))

durations = [220] * len(frames)
durations[-1] = 1400   # hold the final year
frames[0].save("fig_agb_animation.gif", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, optimize=True, disposal=2)
sz = os.path.getsize("fig_agb_animation.gif") / 1e6
print(f"saved fig_agb_animation.gif | {len(frames)} frames | {target_w}x{target_h} | {sz:.2f} MB")

# ============================================================ 4) HEADLINE DENSITY MAP
# Single large map of the latest year, reserve shape, for the report hero figure.
C_FRACTION, CO2_PER_C = 0.47, 44.0 / 12.0
y0, y1, x0, x1 = _ct["win"]
row_lats = _ct["y"][y0:y1]
px_ha_row = np.array([aoi.pixel_area_ha(lat) for lat in row_lats])
area_grid = np.repeat(px_ha_row[:, None], x1 - x0, axis=1) * _ct["mask"]   # 0 outside reserve
area_ha = float(area_grid.sum())

latest = yr_slice(YEARS[-1])
mean_latest = float(np.nanmean(latest))
stock_co2e = float(np.nansum(latest * area_grid)) * C_FRACTION * CO2_PER_C

fig, ax = plt.subplots(figsize=(6.5, 7.5))
im = ax.imshow(latest, cmap="YlGn", vmin=0, vmax=VMAX)
ax.set_title(f"Itombwe Nature Reserve — aboveground biomass {YEARS[-1]}\n"
             f"CTrees ~100 m · {area_ha:,.0f} ha · mean {mean_latest:.0f} Mg/ha",
             fontsize=10, color="#16241d")
ax.set_xticks([]); ax.set_yticks([])
cb = fig.colorbar(im, ax=ax, shrink=0.7); cb.set_label("Mg dry biomass / ha")
fig.tight_layout()
save_png_quantized(fig, "fig_agb_map.png", colors=256)
plt.close(fig)
print(f"saved fig_agb_map.png | {area_ha:,.0f} ha | {stock_co2e/1e6:.1f} Mt CO2e")

# ============================================================ 5) STOCK / DENSITY TREND
# Reserve-wide total above-ground CO2e stock and mean density across 2000-2025.
mean_series = np.array([np.nanmean(stack[i]) for i in range(len(YEARS))])
stock_series = np.array([np.nansum(stack[i] * area_grid) for i in range(len(YEARS))]) \
    * C_FRACTION * CO2_PER_C / 1e6                       # Mt CO2e
chg = 100 * (stock_series[-1] - stock_series[0]) / stock_series[0]

fig, ax1 = plt.subplots(figsize=(7.4, 4.2))
ax1.plot(YEARS, stock_series, "o-", color="#1b5e3f", lw=2, ms=4, label="stock")
ax1.set_ylabel("Above-ground stock (Mt CO₂e)", color="#1b5e3f")
ax1.tick_params(axis="y", labelcolor="#1b5e3f")
ax1.set_xlabel("Year"); ax1.grid(alpha=.25)
ax2 = ax1.twinx()
ax2.plot(YEARS, mean_series, "s--", color="#d9a441", lw=1.2, ms=3, alpha=.8)
ax2.set_ylabel("Mean density (Mg/ha)", color="#b9842f")
ax2.tick_params(axis="y", labelcolor="#b9842f")
ax1.set_title(f"Itombwe reserve — above-ground carbon stock, 2000–{YEARS[-1]}  "
              f"({chg:+.1f}% over period)", fontsize=10.5, color="#16241d")
fig.tight_layout()
save_png_quantized(fig, "fig_agb_timeseries.png", colors=256)
plt.close(fig)
print(f"saved fig_agb_timeseries.png | stock {stock_series[0]:.1f} -> {stock_series[-1]:.1f} Mt CO2e ({chg:+.1f}%)")

# ============================================================ 6) PER-SECTOR BREAKDOWN
import json, geopandas as gpd
with open("itombwe_numbers.json") as fh:
    NUM = json.load(fh)
sec_gdf = gpd.read_file(aoi.SECTEURS_SHP).to_crs(4326).dissolve(by="Nom")
rows = []
for name, rec in NUM["sectors"].items():
    rows.append({"Nom": name,
                 "mean": rec["per_year"][-1]["mean_density"],
                 "stock": rec["per_year"][-1]["stock_CO2e"] / 1e6,
                 "chg": rec["change_pct"]})
sdf = sec_gdf.join(__import__("pandas").DataFrame(rows).set_index("Nom"))

fig, (axm, axb) = plt.subplots(1, 2, figsize=(13, 6.2),
                               gridspec_kw={"width_ratios": [1.15, 1]})
sdf.plot(column="mean", cmap="YlGn", legend=True, ax=axm, edgecolor="white", lw=0.6,
         legend_kwds={"label": "mean Mg/ha", "shrink": 0.7})
for _, r in sdf.iterrows():
    c = r.geometry.representative_point()
    axm.annotate(r.name, (c.x, c.y), ha="center", va="center", fontsize=7,
                 color="#16241d", fontweight="bold")
axm.set_title(f"Biomass density by customary sector ({YEARS[-1]})", fontsize=10.5, color="#16241d")
axm.set_xticks([]); axm.set_yticks([])
for s in axm.spines.values():
    s.set_visible(False)

order = sdf.sort_values("stock")
ypos = np.arange(len(order))
axb.barh(ypos, order["stock"], color="#2e8b62")
axb.set_yticks(ypos); axb.set_yticklabels(order.index, fontsize=9)
for i, (st, ch) in enumerate(zip(order["stock"], order["chg"])):
    axb.text(st, i, f"  {st:.1f} Mt ({ch:+.1f}%)", va="center", fontsize=8, color="#16241d")
axb.set_xlabel("Above-ground stock (Mt CO₂e)")
axb.set_title("Stock & 2000→2025 change by sector", fontsize=10.5, color="#16241d")
axb.grid(axis="x", alpha=.25)
axb.set_xlim(0, order["stock"].max() * 1.35)
fig.tight_layout()
save_png_quantized(fig, "fig_sectors.png", colors=256)
plt.close(fig)
print("saved fig_sectors.png")

print("\nDONE. Sizes:")
for f in ("fig_agb_map.png", "fig_agb_timeseries.png", "fig_agb_panels.png",
          "fig_agb_change.png", "fig_sectors.png", "fig_agb_animation.gif"):
    print(f"  {f:24} {os.path.getsize(f)/1e6:.2f} MB")
