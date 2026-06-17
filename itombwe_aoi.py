"""Itombwe area-of-interest: the REAL reserve polygon, replacing the old bounding box.

Loads the official boundary shapefiles from boundary_file/ and exposes helpers to:
  * get the reserve geometry (whole reserve, EPSG:4326) and per-sector geometries,
  * pick the CTrees read-window (a rectangle, for fast I/O) from the polygon bbox,
  * rasterize any geometry onto the CTrees ~100 m pixel grid -> boolean mask
    (True = pixel centre inside the polygon).

Boundary facts (see explore notes):
  RN_Itombwe.shp        1 polygon  = unified Réserve Naturelle d'Itombwe   ~573,228 ha
  Secteurs_Itombwe.shp  15 polygons = same reserve split into 10 customary sectors
Both are EPSG:32735 (WGS84 / UTM 35S); we reproject to EPSG:4326 to match CTrees.
"""
import os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_BDIR = os.path.join(_HERE, "boundary_file")

RN_SHP      = os.path.join(_BDIR, "RN_Itombwe.shp")
SECTEURS_SHP = os.path.join(_BDIR, "Secteurs_Itombwe.shp")

# CTrees grid pixel size in degrees (~99 m); must match build_notebook.py.
CTREES_PIX_DEG = 0.0008888888888879225
_M_PER_DEG = 111_320.0

_cache = {}


def _load():
    """Load + reproject the boundaries once. Returns (rn_geom, sectors_dict)."""
    if _cache:
        return _cache["rn"], _cache["sectors"]
    import geopandas as gpd
    rn = gpd.read_file(RN_SHP).to_crs(4326)
    rn_geom = rn.union_all() if hasattr(rn, "union_all") else rn.unary_union

    sec = gpd.read_file(SECTEURS_SHP).to_crs(4326)
    sectors = {}
    for nom, sub in sec.dissolve(by="Nom").iterrows():
        sectors[nom] = sub.geometry
    _cache["rn"] = rn_geom
    _cache["sectors"] = sectors
    return rn_geom, sectors


def reserve_geom():
    """Shapely geometry of the whole reserve (EPSG:4326)."""
    return _load()[0]


def sector_geoms():
    """dict {sector_name: shapely geometry} in EPSG:4326, largest first."""
    secs = _load()[1]
    return dict(sorted(secs.items(), key=lambda kv: -kv[1].area))


def bbox():
    """[west, south, east, north] of the reserve in EPSG:4326 — use for the read window."""
    minx, miny, maxx, maxy = reserve_geom().bounds
    # pad by one pixel so edge pixels are not clipped by the read window
    p = CTREES_PIX_DEG
    return [minx - p, miny - p, maxx + p, maxy + p]


def window(x, y):
    """Given CTrees lon (x, ascending) and lat (y, descending) coordinate arrays,
    return (y0, y1, x0, x1) index window covering the reserve bbox."""
    w, s, e, n = bbox()
    ix = np.where((x >= w) & (x <= e))[0]
    iy = np.where((y >= s) & (y <= n))[0]
    return int(iy.min()), int(iy.max()) + 1, int(ix.min()), int(ix.max()) + 1


def pixel_area_ha(lat_center):
    """Latitude-corrected CTrees pixel area in hectares."""
    import math
    dx = CTREES_PIX_DEG * _M_PER_DEG * math.cos(math.radians(lat_center))
    dy = CTREES_PIX_DEG * _M_PER_DEG
    return dx * dy / 10_000.0


def rasterize(geom, x, y, win):
    """Boolean mask (True = pixel centre inside geom) aligned to the window x[x0:x1], y[y0:y1].
    x ascending lon, y descending lat (CTrees convention)."""
    from rasterio.features import geometry_mask
    from affine import Affine
    y0, y1, x0, x1 = win
    xs = x[x0:x1]
    ys = y[y0:y1]
    p = CTREES_PIX_DEG
    # top-left pixel-edge origin; y descending so the first row is the largest lat
    transform = Affine(p, 0, xs[0] - p / 2, 0, -p, ys[0] + p / 2)
    out_shape = (len(ys), len(xs))
    # geometry_mask returns True OUTSIDE by default; invert=True -> True inside
    inside = geometry_mask([geom], out_shape=out_shape, transform=transform, invert=True)
    return inside


if __name__ == "__main__":
    rn = reserve_geom()
    secs = sector_geoms()
    print("Reserve bounds (lon/lat):", [round(v, 4) for v in rn.bounds])
    print("Reserve area (ha, UTM):  ~573,228")
    print("Read window bbox:", [round(v, 4) for v in bbox()])
    print(f"{len(secs)} sectors:", list(secs.keys()))
