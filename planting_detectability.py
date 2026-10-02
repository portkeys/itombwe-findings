"""Can the satellite see the One-Million-Trees planting? Itombwe-specific evidence from our own stack.

Answers three questions with the CTrees ~100 m AGB series (2000-2025) + Hansen GFC loss, reserve-clipped:
  1. Noise floor: how much does CTrees AGB wobble year-to-year on pixels where nothing happened
     (no Hansen loss), binned by biomass level, and how much does averaging over blocks of
     pixels (1 -> 256 ha) shrink it?  -> minimum detectable biomass change.
  2. Empirical regrowth: on pixels cleared 2001-2008, how fast does CTrees AGB climb back
     in the years after clearing?  -> what the satellite "reports" for young woody regrowth here.
  3. Candidate land: how much low-biomass (<30 Mg/ha) land is inside the reserve / Burhinyi sector.

Writes planting_detectability.json.
Run: .venv/bin/python planting_detectability.py
"""
import os, json, time
import numpy as np
import itombwe_aoi as aoi
import recompute_numbers as rc
import hansen_activity_data as hd

LOW_AGB = 30.0                      # Mg/ha: below this a pixel is effectively non-forest/degraded
BINS = [0, 25, 50, 100, 200, 1e9]   # AGB bins (Mg/ha) for the noise table
BLOCKS = [1, 2, 4, 8, 16]           # block edge in pixels -> 1, 4, 16, 64, 256 ha


def hansen_on_ctrees_grid(xs, ys, win):
    """Per CTrees pixel: fraction of 30 m forest pixels lost, and earliest loss year (0 = none)."""
    w, s, e, n = aoi.bbox()
    loss, tf = hd.read_window("lossyear", (w, s, e, n))
    tc, _ = hd.read_window("treecover2000", (w, s, e, n))
    H, W = loss.shape
    lon = tf.c + (np.arange(W) + 0.5) * tf.a
    lat = tf.f + (np.arange(H) + 0.5) * tf.e
    y0, y1, x0, x1 = win
    cx, cy = xs[x0:x1], ys[y0:y1]
    p = aoi.CTREES_PIX_DEG
    ci = np.clip(np.round((lon - cx[0]) / p).astype(int), 0, len(cx) - 1)
    ri = np.clip(np.round((cy[0] - lat) / p).astype(int), 0, len(cy) - 1)
    R, C = np.meshgrid(ri, ci, indexing="ij")
    shape = (len(cy), len(cx))
    tot = np.zeros(shape); lost = np.zeros(shape)
    first = np.full(shape, 99, dtype=np.int16)
    np.add.at(tot, (R, C), 1)
    m = (loss > 0) & (tc >= hd.FOREST_THRESHOLD)
    np.add.at(lost, (R[m], C[m]), 1)
    np.minimum.at(first, (R[m], C[m]), loss[m].astype(np.int16))
    first[first == 99] = 0
    anyloss = np.zeros(shape); np.add.at(anyloss, (R[loss > 0], C[loss > 0]), 1)
    return lost / np.maximum(tot, 1), first, anyloss > 0


def main():
    t0 = time.time()
    rc.connect()
    years = rc._ct["years"]
    xs, ys, win = rc._ct["x"], rc._ct["y"], rc._ct["win"]
    stack = np.stack([rc.density(y) for y in years]).astype("float32")
    inside = aoi.rasterize(aoi.reserve_geom(), xs, ys, win) & np.isfinite(stack).all(axis=0)
    burh = aoi.rasterize(aoi.sector_geoms()["Burhinyi"], xs, ys, win) & inside
    print(f"stack {stack.shape} loaded in {time.time()-t0:.0f}s; reserve px {inside.sum()}")

    lossfrac, first, anyloss = hansen_on_ctrees_grid(xs, ys, win)
    stable = inside & ~anyloss
    # also exclude neighbours of loss so edge smear doesn't count as noise
    near = anyloss.copy()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            near |= np.roll(np.roll(anyloss, dr, 0), dc, 1)
    stable &= ~near
    print(f"stable px {stable.sum()} | Hansen ran in {time.time()-t0:.0f}s")

    # ---- 1. noise floor -------------------------------------------------------------
    last5 = stack[-6:]                          # 2020-2025
    d1 = np.diff(last5, axis=0)                 # year-on-year change, 5 diffs
    level = last5.mean(axis=0)
    # detrended residual about each pixel's own 2020-2025 linear trend
    t = np.arange(last5.shape[0]) - (last5.shape[0] - 1) / 2
    slope = (last5 * t[:, None, None]).sum(0) / (t ** 2).sum()
    resid = last5 - (level + slope * t[:, None, None])
    noise = []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = stable & (level >= lo) & (level < hi)
        if m.sum() < 50:
            continue
        noise.append({
            "agb_bin_Mg_ha": [lo, hi if hi < 1e8 else None],
            "n_px": int(m.sum()),
            "yoy_change_sd_Mg_ha": float(np.std(d1[:, m])),
            "resid_sd_Mg_ha": float(np.std(resid[:, m])),
            "trend_sd_Mg_ha_yr": float(np.std(slope[m])),
        })

    # block averaging on low-biomass stable land: does noise average down?
    blocks = []
    for b in BLOCKS:
        H, W = (stack.shape[1] // b) * b, (stack.shape[2] // b) * b
        r = resid[:, :H, :W].reshape(resid.shape[0], H // b, b, W // b, b)
        ok = stable[:H, :W].reshape(H // b, b, W // b, b).all(axis=(1, 3))
        lv = level[:H, :W].reshape(H // b, b, W // b, b).mean(axis=(1, 3))
        s_ = slope[:H, :W].reshape(H // b, b, W // b, b).mean(axis=(1, 3))
        rb = r.mean(axis=(2, 4))
        for name, sel in (("low_lt50", ok & (lv < 50)), ("all", ok)):
            if sel.sum() < 20:
                continue
            blocks.append({"block_px": b, "approx_ha": b * b, "subset": name, "n_blocks": int(sel.sum()),
                           "resid_sd_Mg_ha": float(np.std(rb[:, sel])),
                           "trend_sd_Mg_ha_yr": float(np.std(s_[sel]))})

    # ---- 2. empirical regrowth after clearing ---------------------------------------
    cleared = inside & (lossfrac >= 0.5) & (first >= 1) & (first <= 8)   # cleared 2001-2008
    traj = {}
    for k in range(-1, 18):
        vals = []
        for code in range(1, 9):
            yi = years.index(2000 + code) + k if (2000 + code + k) in years else None
            if yi is None:
                continue
            m = cleared & (first == code)
            vals.append(stack[yi][m])
        if vals:
            v = np.concatenate(vals)
            traj[k] = {"n": int(v.size), "p25": float(np.percentile(v, 25)),
                       "median": float(np.median(v)), "p75": float(np.percentile(v, 75)),
                       "p90": float(np.percentile(v, 90))}
    # regrowth rate: pixels whose post-clearing minimum was low, slope over the following decade
    rates = []
    for code in range(1, 9):
        m = cleared & (first == code)
        yi = years.index(2000 + code)
        seg = stack[yi + 1: yi + 11][:, m]          # 10 yrs after clearing
        if seg.shape[0] < 10:
            continue
        tt = np.arange(10) - 4.5
        sl = (seg * tt[:, None]).sum(0) / (tt ** 2).sum()
        rates.append(sl[seg[0] < LOW_AGB])
    rates = np.concatenate(rates)
    regrowth = {"n_px": int(rates.size),
                "slope_Mg_ha_yr": {q: float(np.percentile(rates, p))
                                   for q, p in (("p25", 25), ("median", 50), ("p75", 75), ("p90", 90))}}

    # sensitivity: on pixels Hansen says were >=80% cleared, how much of the pre-clearing AGB
    # does CTrees actually remove 2 yrs later? (a product that misses loss will miss gain too)
    resp = []
    for code in range(3, 23):
        m = inside & (lossfrac >= 0.8) & (first == code)
        if m.sum() < 10:
            continue
        yi = years.index(2000 + code)
        pre, post = stack[yi - 2][m], stack[min(yi + 2, len(years) - 1)][m]
        resp.append((pre, post))
    pre = np.concatenate([a for a, _ in resp]); post = np.concatenate([b for _, b in resp])
    ok = pre > 20
    frac = (pre[ok] - post[ok]) / pre[ok]
    sensitivity = {"n_px": int(ok.sum()), "pre_median_Mg_ha": float(np.median(pre[ok])),
                   "post_median_Mg_ha": float(np.median(post[ok])),
                   "fraction_removed_median": float(np.median(frac)),
                   "fraction_removed_p75": float(np.percentile(frac, 75))}

    # ---- 3. candidate low-biomass land ----------------------------------------------
    ha = np.repeat(np.array([aoi.pixel_area_ha(l) for l in ys[win[0]:win[1]]])[:, None],
                   win[3] - win[2], axis=1)
    low = stack[-1] < LOW_AGB
    land = {"threshold_Mg_ha": LOW_AGB, "year": years[-1],
            "reserve_low_ha": float(ha[inside & low].sum()),
            "reserve_ha": float(ha[inside].sum()),
            "burhinyi_low_ha": float(ha[burh & low].sum()),
            "burhinyi_ha": float(ha[burh].sum()),
            "burhinyi_mean_agb": float(stack[-1][burh].mean()),
            "reserve_mean_agb": float(stack[-1][inside].mean())}

    out = {"noise_by_agb": noise, "noise_by_block": blocks,
           "regrowth_trajectory_years_since_clearing": traj,
           "regrowth_slope_first_decade": regrowth, "loss_sensitivity": sensitivity,
           "low_biomass_land": land}
    json.dump(out, open("planting_detectability.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
