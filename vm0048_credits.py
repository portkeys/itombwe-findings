"""VM0048 / VMD0055 baseline + credit estimate for Itombwe — the AD × EF method that
replaces the old stock-decline shortcut.

  Baseline emissions (tCO2e/yr) = AD × EF
     AD = forest area deforested per year      [ha/yr]   <- Hansen GFC (hansen_ad.json)
     EF = committed emission per ha cleared     [tCO2e/ha] <- CTrees AGB at loss locations

EF is built loss-weighted: we sample CTrees AGB density at the exact Hansen deforestation
pixels (the cleared forest is mostly accessible edge forest, lower-biomass than the reserve
mean), convert biomass -> CO2e, and add a below-ground (root) component.

IMPORTANT: this is an INTERIM, project-level proxy. A compliant VM0048 baseline uses the
jurisdictional allocated deforestation risk map, which Verra has NOT yet published for South
Kivu (only DRC Mai Ndombe is near completion). So AD here is our own measured rate, not the
registry-allocated figure. The credit-stack deductions are illustrative placeholders.

Run: .venv/bin/python vm0048_credits.py
"""
import os, json
import numpy as np
import itombwe_aoi as aoi
import hansen_activity_data as hz

# ---- load .env for arraylake ----
for line in open(os.path.join(os.path.dirname(__file__), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

C_FRACTION = 0.47
CO2_PER_C = 44.0 / 12.0
ROOT_SHOOT = 0.24          # below-ground:above-ground (IPCC tropical moist)
CTREES_FILL = -9999
CTREES_SCALE = 10.0


def ctrees_stack():
    """Full CTrees AGB density stack (Mg/ha) over the reserve window: (years, rows, cols).
    Returns stack, xs, ys (descending lat), years list, reserve mask."""
    from arraylake import Client
    import zarr, icechunk
    client = Client()
    try:
        cfg = icechunk.RepositoryConfig.default()
        cfg.caching = icechunk.CachingConfig(num_chunk_refs=10_000)
        repo = client.get_repo("portkeys/ctrees_data", config=cfg)
    except Exception:
        repo = client.get_repo("portkeys/ctrees_data")
    root = zarr.open_group(repo.readonly_session(branch="main").store,
                           zarr_format=3, path="aboveground_biomass", mode="r")
    x = root["x"][:]; y = root["y"][:]
    years = [int(str(t)[:4]) for t in root["time"][:]]
    win = aoi.window(x, y)
    y0, y1, x0, x1 = win
    raw = root["agb"][:, y0:y1, x0:x1].astype("float32")          # (years, rows, cols)
    dens = np.where(raw == CTREES_FILL, np.nan, raw / CTREES_SCALE)
    mask = aoi.rasterize(aoi.reserve_geom(), x, y, win)
    return dens, x[x0:x1], y[y0:y1], years, mask


def main():
    ad = json.load(open("hansen_ad.json"))
    print("AD source:", ad["source"])

    # ---- re-read Hansen loss window (fast) to locate deforestation pixels ----
    bounds = tuple(aoi.bbox())
    loss, transform = hz.read_window("lossyear", bounds)
    tc2000, _ = hz.read_window("treecover2000", bounds)
    from rasterio.features import geometry_mask
    inside = geometry_mask([aoi.reserve_geom()], out_shape=loss.shape,
                           transform=transform, invert=True)
    lossmask = (loss > 0) & (tc2000 >= hz.FOREST_THRESHOLD) & inside

    # per deforestation pixel: clearing-year code, lon/lat, lat-corrected area (ha)
    rr, cc = np.where(lossmask)
    code = loss[rr, cc].astype(int)                   # 1..24 -> cleared in year 2000+code
    px = abs(transform.a)
    lon = transform.c + (cc + 0.5) * px
    lat = transform.f - (rr + 0.5) * px
    px_ha = (px * hz.M_PER_DEG * np.cos(np.radians(lat))) * (px * hz.M_PER_DEG) / 1e4

    # ---- PER-COHORT EF: sample CTrees biomass the YEAR BEFORE each pixel was cleared ----
    # pre-clearing standing stock = the carbon actually released; avoids sampling an
    # already-cleared pixel and respects the time dimension, as VM0048 intends.
    stack, xs, ys, years, rmask = ctrees_stack()
    ix = np.clip(np.searchsorted(xs, lon), 0, len(xs) - 1)
    ys_asc = ys[::-1]
    iy_asc = np.clip(np.searchsorted(ys_asc, lat), 0, len(ys_asc) - 1)
    iy = len(ys) - 1 - iy_asc
    y0 = years[0]                                     # 2000 -> stack index 0
    ti_prior = np.clip((2000 + code - 1) - y0, 0, len(years) - 1)   # index for year-before-clearing
    dens_prior = stack[ti_prior, iy, ix]              # Mg/ha pre-clearing, per pixel

    good = np.isfinite(dens_prior)
    area_g, code_g = px_ha[good], code[good]
    co2e = area_g * dens_prior[good] * C_FRACTION * CO2_PER_C * (1 + ROOT_SHOOT)   # tCO2e/pixel

    # aggregate committed emissions by clearing year
    annual_em = {2000 + k: {"year": 2000 + k,
                            "area_ha": float(area_g[code_g == k].sum()),
                            "co2e": float(co2e[code_g == k].sum())}
                 for k in range(1, 25)}

    total_area = float(area_g.sum())
    total_co2e = float(co2e.sum())
    dens_loss = float(np.average(dens_prior[good], weights=area_g))   # area-wtd pre-clearing density
    dens_reserve = float(np.nanmean(np.where(rmask, stack[years.index(2001)], np.nan)))
    EF_TOT = total_co2e / total_area                  # effective tCO2e/ha (incl. BGB)
    EF_AGB = EF_TOT / (1 + ROOT_SHOOT)
    print(f"\nPER-COHORT (biomass in the year before clearing):")
    print(f"  AGB density (Mg/ha): reserve mean {dens_reserve:.0f} | "
          f"cleared sites (area-wtd) {dens_loss:.0f}  (n={int(good.sum()):,})")
    print(f"  effective EF: AGB {EF_AGB:.0f} | +BGB {EF_TOT:.0f} tCO2e/ha")

    # ---- baseline = mean per-cohort annual emissions over the reference period ----
    em_recent = [annual_em[y]["co2e"] for y in range(2015, 2025)]
    em_all = [annual_em[y]["co2e"] for y in range(2001, 2025)]
    base_recent = sum(em_recent) / len(em_recent)
    base_all = sum(em_all) / len(em_all)
    AD_recent = ad["mean_ad_2015_2024_ha_yr"]
    AD_all = ad["mean_ad_2001_2024_ha_yr"]
    print(f"\nBaseline emissions (per-cohort AD × pre-clearing EF, incl. BGB):")
    print(f"  2015-2024 mean: {base_recent:,.0f} tCO2e/yr")
    print(f"  2001-2024 mean: {base_all:,.0f} tCO2e/yr")

    # ---- credit stack (illustrative placeholders, VMD0055-shaped) ----
    EFFECTIVENESS = 0.50     # ex-ante: share of baseline deforestation the project averts
    LEAKAGE = 0.20           # emissions displaced elsewhere
    UNCERTAINTY = 0.15       # VMD0055 uncertainty deduction (shrinks with field plots)
    BUFFER = 0.15            # AFOLU non-permanence buffer (set by Verra risk tool)
    baseline = base_recent
    after_eff = baseline * EFFECTIVENESS
    after_leak = after_eff * (1 - LEAKAGE)
    after_unc = after_leak * (1 - UNCERTAINTY)
    net = after_unc * (1 - BUFFER)
    print(f"\nCredit stack (illustrative):")
    print(f"  baseline                 {baseline:,.0f} tCO2e/yr")
    print(f"  × {EFFECTIVENESS:.0%} effectiveness     {after_eff:,.0f}")
    print(f"  × (1-{LEAKAGE:.0%}) leakage      {after_leak:,.0f}")
    print(f"  × (1-{UNCERTAINTY:.0%}) uncertainty  {after_unc:,.0f}")
    print(f"  × (1-{BUFFER:.0%}) buffer       {net:,.0f}  <- net issuable credits/yr")

    out = {
        "method": "VM0048 + VMD0055 (AD × EF), per-cohort pre-clearing EF — interim project-level proxy",
        "ef_method": "biomass sampled the year before each pixel's clearing (CTrees), per loss cohort",
        "ad": {"recent10_ha_yr": AD_recent, "all_ha_yr": AD_all,
               "ref_period_recent": "2015-2024", "source": ad["source"]},
        "ef": {"dens_loss_weighted_Mg_ha": dens_loss, "dens_reserve_mean_Mg_ha": dens_reserve,
               "EF_AGB_tCO2e_ha": EF_AGB, "EF_AGB_BGB_tCO2e_ha": EF_TOT,
               "C_FRACTION": C_FRACTION, "ROOT_SHOOT": ROOT_SHOOT},
        "annual_emissions_tCO2e": [annual_em[y] for y in range(2001, 2025)],
        "baseline_tCO2e_yr": {"recent10": base_recent, "all": base_all},
        "credit_stack": {"effectiveness": EFFECTIVENESS, "leakage": LEAKAGE,
                         "uncertainty": UNCERTAINTY, "buffer": BUFFER,
                         "net_credits_yr": net},
        "caveat": ("Interim proxy: AD is our own Hansen-measured rate, NOT the Verra "
                   "jurisdictional allocation (no South Kivu risk map published yet). "
                   "Credit-stack deductions are illustrative placeholders."),
    }
    json.dump(out, open("vm0048_credits.json", "w"), indent=2)
    print("\nwrote vm0048_credits.json")


if __name__ == "__main__":
    main()
