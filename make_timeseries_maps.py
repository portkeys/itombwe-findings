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

# ---- load .env so arraylake picks up the token ----
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ---- CTrees reader (same constants as build_notebook.py) ----
ITOMBWE_BBOX   = [28.16, -4.01, 28.98, -2.85]
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
    w, s, e, n = ITOMBWE_BBOX
    ix = np.where((_ct["x"] >= w) & (_ct["x"] <= e))[0]
    iy = np.where((_ct["y"] >= s) & (_ct["y"] <= n))[0]
    _ct["win"] = (int(iy.min()), int(iy.max())+1, int(ix.min()), int(ix.max())+1)

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
print(f"loaded stack {stack.shape} in {time.time()-t0:.0f}s")

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
loss_frac = 100 * np.nanmean(total_change < -2)   # share of area losing >2 Mg/ha
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

print("\nDONE. Sizes:")
for f in ("fig_agb_panels.png", "fig_agb_change.png", "fig_agb_animation.gif"):
    print(f"  {f:24} {os.path.getsize(f)/1e6:.2f} MB")
