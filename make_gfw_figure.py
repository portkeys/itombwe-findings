"""GFW (Hansen) vs CTrees comparison figure for the Itombwe report.

fig_gfw_compare.png — two panels:
  (left)  Hansen forest-loss locations 2001-2024 over the reserve (where clearing concentrates)
  (right) annual deforested ha/yr (the activity data) vs CTrees mean biomass density —
          GFW shows accelerating gross clearing while net biomass barely moves.
Run: .venv/bin/python make_gfw_figure.py
"""
import io, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from PIL import Image

ad = json.load(open("hansen_ad.json"))
num = json.load(open("itombwe_numbers.json"))
loss = np.load("hansen_loss.npy")
inside = np.load("hansen_inside.npy")

years = [a["year"] for a in ad["annual"]]
ha = [a["deforested_ha"] for a in ad["annual"]]
# CTrees mean density per year, aligned to Hansen years (2001-2024)
ct = {r["year"]: r["mean_density"] for r in num["whole_reserve"]["per_year"]}
ct_series = [ct.get(y, np.nan) for y in years]


def save_png_quantized(fig, path, colors=256):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    Image.open(buf).convert("RGB").quantize(colors=colors, method=Image.FASTOCTREE).save(path, optimize=True)


fig, (axm, axb) = plt.subplots(1, 2, figsize=(13, 5.8),
                               gridspec_kw={"width_ratios": [1, 1.15]})

# ---- left: loss hotspot map ----
# 0 = outside (white), 1 = forest kept (pale green), 2 = forest lost (red)
img = np.where(inside == 1, 1, 0)
img = np.where(loss == 1, 2, img).astype("uint8")
cmap = ListedColormap(["#ffffff", "#cfe6d4", "#d6443a"])
axm.imshow(img, cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
axm.set_title("Where the forest was cleared, 2001–2024\n(Hansen/GFW ~30 m · red = loss)",
              fontsize=10.5, color="#16241d")
axm.set_xticks([]); axm.set_yticks([])
for s in axm.spines.values():
    s.set_visible(False)
axm.text(0.5, -0.02, f"{ad['total_loss_2001_2024_ha']:,.0f} ha cleared "
         f"({100*ad['total_loss_2001_2024_ha']/ad['forest2000_area_ha']:.1f}% of 2000 forest)",
         transform=axm.transAxes, ha="center", va="top", fontsize=9.5, color="#6c7a72")

# ---- right: annual AD bars vs CTrees density ----
axb.bar(years, ha, color="#d6443a", alpha=0.85, label="Forest cleared (Hansen/GFW)")
m10 = ad["mean_ad_2015_2024_ha_yr"]
axb.axhline(m10, ls="--", lw=1.3, color="#8a2820")
axb.text(years[0], m10, f" 2015–24 mean {m10:,.0f} ha/yr", va="bottom", ha="left",
         fontsize=8.5, color="#8a2820")
axb.set_ylabel("Forest cleared (ha/yr)", color="#b5362c")
axb.tick_params(axis="y", labelcolor="#b5362c")
axb.set_xlabel("Year")
axb.set_title("GFW activity data vs CTrees biomass\nGross clearing accelerates; net biomass barely moves",
              fontsize=10.5, color="#16241d")

ax2 = axb.twinx()
ax2.plot(years, ct_series, "o-", color="#1b5e3f", lw=1.8, ms=3.5, label="CTrees mean density")
ax2.set_ylabel("CTrees mean density (Mg/ha)", color="#1b5e3f")
ax2.tick_params(axis="y", labelcolor="#1b5e3f")
ymin = np.nanmin(ct_series); ymax = np.nanmax(ct_series)
ax2.set_ylim(ymin - 8, ymax + 8)     # zoom so the near-flat line is visible but clearly flat

lines = [plt.Line2D([], [], color="#d6443a", lw=6, alpha=.85),
         plt.Line2D([], [], color="#1b5e3f", lw=2, marker="o", ms=4)]
axb.legend(lines, ["Forest cleared (Hansen/GFW)", "CTrees mean density"],
           loc="upper left", fontsize=8.5, framealpha=.9)
fig.tight_layout()
save_png_quantized(fig, "fig_gfw_compare.png")
plt.close(fig)
print("saved fig_gfw_compare.png")

# ---- revenue figure (VM0048 net credits × carbon price) ----
NET = json.load(open("vm0048_credits.json"))["credit_stack"]["net_credits_yr"]
prices = [4, 8, 12, 20]
horizon = [1, 5, 10]
fig, ax = plt.subplots(figsize=(7, 4))
for p in prices:
    ax.plot(horizon, [NET * p * h for h in horizon], "o-", label=f"${p}/tCO₂e")
ax.set_xlabel("Crediting years"); ax.set_ylabel("Cumulative revenue (USD)")
ax.set_title(f"Illustrative REDD+ revenue · VM0048 ≈ {NET:,.0f} credits/yr",
             fontsize=10.5, color="#16241d")
ax.legend(); ax.grid(alpha=.3)
ax.ticklabel_format(style="plain", axis="y")
fig.tight_layout()
save_png_quantized(fig, "fig_revenue.png")
plt.close(fig)
print("saved fig_revenue.png")
