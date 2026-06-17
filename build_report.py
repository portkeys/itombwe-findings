"""Generate a self-contained, shareable HTML summary of the Itombwe biomass exploration.
Tone: "I did my homework — here's my current understanding and our preliminary findings."
Humble and collaborative (we/our), not deferential. Figures are base64-embedded so the
.html is a single portable file."""
import base64, os

def img(path):
    if not os.path.exists(path):
        return ""
    mime = "image/gif" if path.lower().endswith(".gif") else "image/png"
    b = base64.b64encode(open(path, "rb").read()).decode()
    return f"data:{mime};base64,{b}"

MAP    = img("fig_agb_map.png")
TREND  = img("fig_agb_timeseries.png")
REV    = img("fig_revenue.png")
PANELS = img("fig_agb_panels.png")        # 2000 | 2015 | 2025 density maps
CHANGE = img("fig_agb_change.png")        # per-pixel change 2000->2025
ANIM   = img("fig_agb_animation.gif")     # looping 2000->2025 animation
SECTORS = img("fig_sectors.png")          # per-sector breakdown (map + bars)
GFW    = img("fig_gfw_compare.png")       # Hansen/GFW deforestation vs CTrees biomass

# --- recalculated numbers, clipped to the REAL reserve polygon (RN_Itombwe) -----
# All figures below come from recompute_numbers.py -> itombwe_numbers.json, computed
# over the official 573k-ha reserve boundary (not the old ~1.18M-ha bounding box).
import json
NUM = json.load(open("itombwe_numbers.json"))
_wr = NUM["whole_reserve"]["per_year"]
_first, _last = _wr[0], _wr[-1]

AREA_HA      = NUM["area_ha"]                       # ~577,111 ha inside the mask
STOCK_BIOMASS = _last["stock_Mg"]                   # t dry biomass, latest year
STOCK_CO2E   = _last["stock_CO2e"]                  # t CO₂e (above-ground), latest year
CARBON_T     = STOCK_BIOMASS * NUM["constants"]["C_FRACTION"]   # t C (above-ground)
ROOT_SHOOT   = 0.24                                 # belowground add-on
STOCK_AGBG   = STOCK_CO2E * (1 + ROOT_SHOOT)        # AGB + BGB CO₂e
DENS_2025    = _last["mean_density"]
DENS_2000    = _first["mean_density"]
DENS_2015    = next(r["mean_density"] for r in _wr if r["year"] == 2015)
TOTAL_PCT    = NUM["whole_reserve"]["change_pct_total"]    # ~-1.38 %
ANN_PCT      = NUM["whole_reserve"]["change_pct_annual"]   # ~-0.055 %/yr

# --- VM0048 / VMD0055 credit estimate: Activity Data × Emission Factor -----------
# Replaces the old (wrong) stock-decline shortcut. AD = Hansen/GFW forest loss (ha/yr);
# EF = CTrees biomass at the cleared pixels -> tCO2e/ha. INTERIM project-level proxy:
# Verra has not published a South Kivu jurisdictional allocation, so AD is our own
# measured rate and the credit-stack deductions are illustrative placeholders.
AD = json.load(open("hansen_ad.json"))
VM = json.load(open("vm0048_credits.json"))

AD_HA_YR   = VM["ad"]["recent10_ha_yr"]               # ~1,616 ha/yr (2015-2024)
TOTAL_LOSS = AD["total_loss_2001_2024_ha"]            # ha cleared 2001-2024
LOSS_PCT   = 100 * TOTAL_LOSS / AD["forest2000_area_ha"]
FOREST2000 = AD["forest2000_area_ha"]
DENS_LOSS  = VM["ef"]["dens_loss_weighted_Mg_ha"]     # ~79 Mg/ha at cleared pixels
EF         = VM["ef"]["EF_AGB_BGB_tCO2e_ha"]          # ~168 tCO2e/ha (incl. roots)
BASE_EM    = VM["baseline_tCO2e_yr"]["recent10"]      # ~272,000 tCO2e/yr
EFFECT     = VM["credit_stack"]["effectiveness"]      # 0.50
LEAKAGE    = VM["credit_stack"]["leakage"]            # 0.20
UNCERT     = VM["credit_stack"]["uncertainty"]        # 0.15
BUFFER     = VM["credit_stack"]["buffer"]             # 0.15
NET        = round(VM["credit_stack"]["net_credits_yr"])

def usd(x):
    return f"${x/1e6:.2f}M" if x < 1e9 else f"${x/1e9:.2f}B"
rev_rows = "".join(
    f"<tr><td>${p} per tonne</td><td>{usd(NET*p)}</td><td>{usd(NET*p*10)}</td></tr>"
    for p in (4, 8, 12, 20))

# --- per-sector table rows (largest stock first) -----
_sec_sorted = sorted(NUM["sectors"].items(),
                     key=lambda kv: -kv[1]["per_year"][-1]["stock_CO2e"])
def _sec_row(name, rec):
    last = rec["per_year"][-1]
    cls = "new" if rec["change_pct"] >= 0 else "old"
    return (f"<tr><td>{name}</td><td>{rec['area_ha']:,.0f}</td>"
            f"<td>{last['mean_density']:.0f}</td>"
            f"<td>{last['stock_CO2e']/1e6:.1f}</td>"
            f"<td class='{cls}'>{rec['change_pct']:+.1f}%</td></tr>")
sector_rows = "".join(_sec_row(n, r) for n, r in _sec_sorted)

HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Itombwe Forest — Exploring AI Biomass Data</title>
<style>
  :root {{
    --ink:#16241d; --forest:#1b5e3f; --forest2:#2e8b62; --moss:#6aa57f;
    --cream:#f6f4ee; --card:#ffffff; --line:#e5dfd2; --muted:#6c7a72;
    --amber:#d9a441;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--cream); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    line-height:1.6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:0 22px 80px; }}
  header.hero {{ background:linear-gradient(135deg,#14402c 0%,#1b5e3f 55%,#2e8b62 100%);
    color:#f3f7f3; padding:54px 0 48px; }}
  header.hero .wrap {{ padding-bottom:0; }}
  .pill {{ display:inline-block; font-size:12px; letter-spacing:.08em; text-transform:uppercase;
    background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3);
    padding:5px 12px; border-radius:999px; margin-bottom:18px; }}
  h1 {{ font-family:Georgia,"Times New Roman",serif; font-weight:700; font-size:36px;
    line-height:1.18; margin:0 0 12px; }}
  .sub {{ font-size:17px; color:#dceae1; max-width:700px; margin:0; }}
  .meta {{ margin-top:22px; font-size:13px; color:#bcd3c6; }}
  section {{ margin-top:44px; }}
  h2 {{ font-family:Georgia,serif; font-size:23px; color:var(--forest);
    margin:0 0 6px; border-bottom:2px solid var(--line); padding-bottom:8px; }}
  h2 .em {{ color:var(--muted); font-size:14px; font-weight:400; font-family:inherit; }}
  p.lead {{ font-size:16px; }}
  .terms {{ display:grid; grid-template-columns:1fr 1fr; gap:2px 30px; margin-top:10px;
    background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 22px; }}
  .terms div {{ font-size:14px; padding:9px 0; border-bottom:1px dotted var(--line); }}
  .terms b {{ color:var(--forest); }}
  .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:8px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:18px 18px 16px; box-shadow:0 1px 2px rgba(0,0,0,.03); }}
  .card .n {{ font-size:29px; font-weight:700; color:var(--forest); line-height:1.1; }}
  .card .l {{ font-size:13px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted);
    margin-top:6px; }}
  .card .s {{ font-size:13px; color:var(--ink); margin-top:6px; opacity:.8; }}
  table {{ width:100%; border-collapse:collapse; margin-top:14px; font-size:15px;
    background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th,td {{ text-align:left; padding:11px 14px; border-bottom:1px solid var(--line); }}
  th {{ background:#eef3ee; color:var(--forest); font-size:13px; letter-spacing:.03em; text-transform:uppercase; }}
  tr:last-child td {{ border-bottom:none; }}
  td.old {{ color:var(--muted); }}
  td.new {{ color:var(--forest); font-weight:600; }}
  figure {{ margin:18px 0 0; }}
  figure img {{ width:100%; border:1px solid var(--line); border-radius:12px; display:block; }}
  figcaption {{ font-size:13px; color:var(--muted); margin-top:8px; }}
  .coords {{ display:block; margin-top:7px; font-family:ui-monospace,Menlo,Consolas,monospace;
    font-size:12px; color:var(--muted); background:#f1efe7; border:1px solid var(--line);
    border-radius:8px; padding:9px 12px; line-height:1.5; }}
  .two {{ display:grid; grid-template-columns:1.15fr .85fr; gap:24px; align-items:start; }}
  .callout {{ border-left:4px solid var(--forest2); background:#eef6f0; padding:14px 18px;
    border-radius:0 10px 10px 0; margin-top:16px; font-size:15px; }}
  .callout b {{ color:var(--ink); }}
  .assume {{ background:#f1efe7; border:1px solid var(--line); border-radius:10px;
    padding:13px 17px; margin-top:14px; font-size:14px; }}
  .assume b {{ color:var(--forest); }}
  .explain {{ background:#eef6f0; border:1px solid #cfe4d6; border-radius:14px;
    padding:20px 22px; margin-top:18px; }}
  .explain h3 {{ margin:0 0 8px; font-size:18px; color:var(--forest); font-family:Georgia,serif; }}
  .explain ol {{ margin:10px 0 4px; padding-left:20px; }}
  .explain li {{ margin:6px 0; }}
  .flow {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:14px; }}
  .flow .step {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
    padding:10px 14px; font-size:14px; }}
  .flow .step b {{ display:block; font-size:18px; color:var(--forest); }}
  .flow .arr {{ color:var(--moss); font-size:20px; }}
  footer {{ margin-top:54px; padding-top:18px; border-top:1px solid var(--line);
    font-size:13px; color:var(--muted); }}
  a {{ color:var(--forest); }}
  @media (max-width:720px) {{ .cards{{grid-template-columns:1fr 1fr;}} .two{{grid-template-columns:1fr;}}
    .terms{{grid-template-columns:1fr;}} h1{{font-size:29px;}} }}
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <span class="pill">Exploratory data notes · open satellite biomass</span>
    <h1>Exploring Biomass Data<br>for the Itombwe Forest</h1>
    <p class="sub">open satellite biomass data for Itombwe —
    comparing two datasets and working out what they suggest about the forest's carbon.</p>
  </div>
</header>

<div class="wrap">

<section>
  <h2>Itombwe</h2>
  <p class="lead">From Ctree's 100m Above Ground Biomass (AGB) data (2000-2025).</p>
  <div class="two">
    <figure>
      <img src="{MAP}" alt="Aboveground biomass density map of Itombwe">
      <figcaption>Biomass density across the reserve (greener = more biomass), from the CTrees data, 2025.
      <span class="coords">Official reserve boundary (RN_Itombwe, WGS84 / EPSG:4326):<br>
      a {AREA_HA:,.0f}-ha polygon spanning longitude&nbsp;27.95°E&nbsp;→&nbsp;29.00°E&nbsp;·&nbsp;latitude&nbsp;2.94°S&nbsp;→&nbsp;3.87°S.<br>
      Now clipped to the exact gazetted boundary — not a bounding box.</span></figcaption>
    </figure>
    <div>
      <p><b>What stands out:</b> There's a dense, high-biomass core (the
      darker greens) that looks like intact rainforest — densest in the southwest (the Wamuzimu and
      Basile sectors) — wrapped in lighter areas, likely degraded, farmed, or cleared land, that thin
      out toward the eastern and northeastern edges (the Bafuliiru lowland reads lowest).</p>
      <p>That pattern points to where the forest seems healthy versus where the pressure is,
      straight from satellite + AI with no ground survey. Whether the pale zones are genuine
      degradation or just naturally lower vegetation is something we'd want to confirm on the ground.</p>
    </div>
  </div>
</section>

<section>
  <h2>Change over time (2000–2025)</h2>
  <p class="lead">CTrees covers 2000–2025, so we can watch the forest change rather than rely on a
  single snapshot.</p>
  <div class="two">
    <figure>
      <img src="{ANIM}" alt="Animated biomass density for Itombwe, 2000 to 2025">
      <figcaption>Biomass density for every year, 2000 → 2025 (loops automatically).</figcaption>
    </figure>
    <div>
      <p><b>Year to year, the maps look almost identical.</b> Average density drifts from about
      <b>{DENS_2000:.0f} to {DENS_2025:.0f} Mg/ha</b> — the {ANN_PCT:+.2f}%/yr we see in the trend
      ({TOTAL_PCT:+.1f}% over the full period). Real, but small enough to miss on a map.</p>
      <p>So a snapshot hides the story. To see <i>where</i> the forest is actually under pressure, it
      helps to map the change itself rather than the biomass — that's the panel below.</p>
    </div>
  </div>
  <figure>
    <img src="{PANELS}" alt="Biomass density in 2000, 2015 and 2025 side by side">
    <figcaption>The same reserve in 2000, 2015 and 2025 on one color scale — means
    {DENS_2000:.0f} → {DENS_2015:.0f} → {DENS_2025:.0f} Mg/ha. The eye can barely tell them apart.</figcaption>
  </figure>
  <div class="two" style="margin-top:6px">
    <figure>
      <img src="{CHANGE}" alt="Map of biomass change across Itombwe, 2000 to 2025">
      <figcaption>Per-pixel change over the period (red = loss, green = gain), from a trend fit across
      all 26 years.</figcaption>
    </figure>
    <div>
      <div class="callout"><b>Key Findings</b> About <b>27% of the reserve</b>
      shows a net biomass loss, concentrated along the eastern and northeastern edges and the
      farmed/settled frontier — exactly where rangers, satellite alerts, and cookstove/livelihood
      programs would go first.</div>
      <p style="font-size:14px;color:var(--muted);margin-top:12px">Note: at
      ~100 m, the change in any single pixel carries model noise, so read the <i>clusters</i> as the
      signal rather than individual pixels. The hotspots are worth confirming against GFW
      GLAD/RADD alerts and on the ground.</p>
    </div>
  </div>
</section>

<section>
  <h2>Helpful Glossary</h2>
  <div class="terms">
    <div><b>Biomass</b> — the living plant matter (trunks, branches, leaves). More biomass = more carbon stored.</div>
    <div><b>Mg/ha (tonnes per hectare)</b> — how dense the biomass is. A hectare is ~2.5 acres.</div>
    <div><b>Carbon stock</b> — how much carbon the forest is holding right now.</div>
    <div><b>CO₂e</b> — that carbon expressed as tonnes of CO₂; the unit carbon markets trade in.</div>
    <div><b>REDD+</b> — a framework where forests earn money for the emissions avoided by <i>not</i> being cleared.</div>
    <div><b>Carbon credit</b> — one tonne of CO₂ kept out of the air; buyers purchase these to offset their own emissions.</div>
  </div>
</section>

<section>
  <h2>Preliminary Results from CTree Data</h2>
  <p class="lead">computed over the official reserve boundary (RN_Itombwe). </p>
  <div class="cards">
    <div class="card"><div class="n">~{AREA_HA/1e3:.0f}k ha</div><div class="l">Reserve area</div>
      <div class="s">The official gazetted boundary — down from the ~1.18M-ha bounding box used earlier</div></div>
    <div class="card"><div class="n">~{DENS_2025:.0f} Mg/ha</div><div class="l">Mean biomass density</div>
      <div class="s">Averaged across the reserve in 2025</div></div>
    <div class="card"><div class="n">~{STOCK_CO2E/1e6:.0f} M</div><div class="l">tonnes CO₂e held</div>
      <div class="s">Above-ground; roughly how much CO₂ the standing forest is storing</div></div>
    <div class="card"><div class="n">{ANN_PCT:+.2f}%/yr</div><div class="l">Biomass trend, 2000–25</div>
      <div class="s">A slight downward drift ({TOTAL_PCT:+.1f}% over the full period)</div></div>
    <div class="card"><div class="n">~{NET/1e3:.0f}k</div><div class="l">possible credits / yr</div>
      <div class="s">VM0048 AD×EF (interim): GFW clearing × CTrees carbon</div></div>
    <div class="card"><div class="n">{usd(NET*4)}–{usd(NET*20)}</div><div class="l">illustrative revenue / yr</div>
      <div class="s">If those credits sold at $4–$20 each</div></div>
  </div>
</section>

<section>
  <h2>Where the carbon sits <span class="em">— by customary sector</span></h2>
  <p>The reserve is shared among ten customary sectors (<i>groupements</i>). Splitting the same
  CTrees data by sector shows where the standing carbon — and the loss — actually concentrates.</p>
  <figure>
    <img src="{SECTORS}" alt="Biomass density and carbon stock by sector">
    <figcaption>Left: mean 2025 biomass density per sector. Right: above-ground stock (Mt CO₂e) and
    2000→2025 change. Two sectors — Wamuzimu and Itombwe — hold most of the reserve's carbon.</figcaption>
  </figure>
  <table>
    <tr><th>Sector</th><th>Area (ha)</th><th>Mean Mg/ha</th><th>Stock (Mt CO₂e)</th><th>Change 2000→25</th></tr>
    {sector_rows}
  </table>
  <div class="callout"><b>Reading it:</b> <b>Wamuzimu</b> and <b>Itombwe</b> together hold roughly
  three-quarters of the reserve's above-ground carbon. The steepest proportional losses sit in the
  smaller, more accessible edge sectors — useful for targeting patrols and livelihood programs.</div>
</section>

<section>
  <h2>Biomass dataset comparison <span class="em">— CTrees vs. Chloris</span></h2>
  <p>There are several open satellite biomass products. I pulled two and compared them over Itombwe:
  <b>CTrees</b> (fine, ~100 m pixels) and <b>Chloris</b> (coarse, ~4.6 km pixels). They give
  noticeably different pictures.</p>
  <table>
    <tr><th>What I looked at</th><th>Chloris (~4.6 km)</th><th>CTrees (~100 m)</th></tr>
    <tr><td>Resolution over the reserve</td><td class="old">~270 pixels</td><td class="new">~590,000 pixels</td></tr>
    <tr><td>Mean biomass density</td><td class="old">~214 Mg/ha</td><td class="new">~{DENS_2025:.0f} Mg/ha</td></tr>
    <tr><td>Implied carbon stock</td><td class="old">~220 M tonnes CO₂e</td><td class="new">~{STOCK_CO2E/1e6:.0f} M tonnes CO₂e</td></tr>
    <tr><td>Trend, 2000–2025</td><td class="old">roughly flat</td><td class="new">a slight decline</td></tr>
  </table>
  <div class="callout"><b>Why they differ so much.</b> It's mostly resolution. Coarse pixels average
  small clearings and degraded edges together with healthy forest into one number; fine pixels keep
  them separate, so CTrees reads lower. Worth settling on which dataset fits Itombwe best.
  <br><span style="font-size:13px;color:var(--muted)">(CTrees numbers are now clipped to the exact
  reserve polygon; the Chloris figures are scaled from the earlier read and worth re-clipping too.)</span></div>
</section>

<section>
  <h2>Biomass over time</h2>
  <div class="two">
    <div>
      <p class="lead">Across 2000–2025 the reserve's carbon stock drifts gently downward — about
      <b>{TOTAL_PCT:+.1f}% over the period</b> ({ANN_PCT:+.2f}% a year).</p>
      <p>Small but steady, and in the direction you'd expect if slow logging and charcoal/fuelwood
      pressure are nibbling at the forest. The coarser dataset showed this same forest as basically
      flat.</p>
    </div>
    <figure>
      <img src="{TREND}" alt="Reserve carbon stock and mean density over time">
      <figcaption>Above-ground carbon stock (Mt CO₂e) and mean density over the reserve, 2000–2025 (CTrees).</figcaption>
    </figure>
  </div>
</section>

<section>
  <h2>Deforestation — the activity data <span class="em">— GFW / Hansen vs CTrees</span></h2>
  <p>Carbon credits aren't paid on biomass density — they're paid on <b>forest actually cleared</b>.
  For that we pulled the <b>Hansen Global Forest Change</b> tree-cover-loss layer (the UMD/Landsat
  ~30 m product that Global Forest Watch redistributes — "GFW loss" <i>is</i> Hansen) and clipped it
  to the reserve.</p>
  <figure>
    <img src="{GFW}" alt="Hansen/GFW forest loss vs CTrees biomass over Itombwe">
    <figcaption>Left: where the forest was cleared, 2001–2024 (red). Right: forest cleared per year
    (bars) against CTrees mean biomass density (line). The clearing rate has roughly tripled; the net
    biomass line barely moves.</figcaption>
  </figure>
  <div class="cards" style="grid-template-columns:repeat(3,1fr)">
    <div class="card"><div class="n">{TOTAL_LOSS:,.0f} ha</div><div class="l">Cleared 2001–2024</div>
      <div class="s">{LOSS_PCT:.1f}% of the reserve's 2000 forest</div></div>
    <div class="card"><div class="n">~{AD_HA_YR:,.0f} ha/yr</div><div class="l">Recent rate (2015–24)</div>
      <div class="s">Up from ~500 ha/yr in the 2000s — accelerating</div></div>
    <div class="card"><div class="n">~{DENS_LOSS:.0f} Mg/ha</div><div class="l">Biomass at cleared sites</div>
      <div class="s">Roughly half the reserve mean — clearing hits the accessible edges</div></div>
  </div>
  <div class="callout"><b>Why GFW and CTrees seem to disagree.</b> They measure different things and
  both are right. GFW counts <i>gross</i> canopy removal at 30 m; CTrees tracks <i>net</i> biomass at
  100 m, where regrowth and the coarser pixels offset much of the loss. So CTrees reads a gentle −1.4%
  while GFW shows 4.4% of the forest cleared and accelerating. For crediting, the <b>cleared area
  (GFW)</b> is the activity data Verra wants; CTrees supplies the carbon-per-hectare.</div>
</section>

<section>
  <h2>From biomass to a carbon number</h2>
  <p>Turning "tonnes of wood" into "tonnes of CO₂" is just a couple of standard conversions (the
  same factors the IPCC publishes), so it's reproducible from the same data:</p>
  <div class="flow">
    <div class="step">Biomass<b>~{STOCK_BIOMASS/1e6:.0f} Mt</b>of wood</div>
    <div class="arr">→</div>
    <div class="step">about half is carbon<b>~{CARBON_T/1e6:.0f} Mt</b>of carbon</div>
    <div class="arr">→</div>
    <div class="step">as CO₂<b>~{STOCK_CO2E/1e6:.0f} Mt</b>CO₂e</div>
    <div class="arr">→</div>
    <div class="step">+ roots<b>~{STOCK_AGBG/1e6:.0f} Mt</b>CO₂e total</div>
  </div>
</section>

<section>
  <h2>What it might be worth <span class="em">— Verra VM0048 / VMD0055</span></h2>
  <div class="explain">
    <h3>How a project earns credits — and the formula Verra actually uses</h3>
    <ol>
      <li>The forest is being <b>cleared</b> every year — for farmland, charcoal and fuelwood —
      releasing the carbon in those trees. A protection effort (<b>rangers and patrols</b>,
      <b>improved cookstoves</b> and <b>livelihoods</b>, <b>satellite alerts</b>) lowers that rate.
      Each tonne of CO₂ kept in the trees earns <b>one carbon credit</b>; buyers purchase them to
      offset emissions, and that money funds the protection.</li>
      <li>Verra's REDD methodology — <b>VM0048</b> with its unplanned-deforestation module
      <b>VMD0055</b> — does <i>not</i> credit an average biomass-decline rate. It uses
      <b>Activity&nbsp;Data × Emission&nbsp;Factor</b>: the <i>area of forest cleared per year</i> ×
      the <i>carbon released per hectare</i>. That's the calculation below — built from the GFW
      clearing rate (AD) and the CTrees biomass at each cleared site <i>in the year before it was
      cleared</i> (EF), summed per annual cohort.</li>
    </ol>
  </div>
  <div class="callout" style="border-left-color:var(--amber);background:#fbf4e4">
    <b>Interim estimate.</b> A fully compliant VM0048 baseline reads its deforestation rate from a
    Verra <b>jurisdictional risk map</b> — which is <b>not yet published for South Kivu</b> (only DR
    Congo's Mai Ndombe region is near completion). So we use our own GFW-measured clearing rate as a
    stand-in, and the effectiveness / leakage / uncertainty / buffer factors are illustrative
    placeholders a registry-approved method would set.</div>
  <p style="margin-top:18px">On this basis the estimate lands around <b>~{NET:,.0f} credits a year</b>.
  The chain is the VM0048 formula, one factor at a time:</p>
  <table style="max-width:760px">
    <tr><th>Step</th><th>What it does</th><th>Running total</th></tr>
    <tr><td>Activity data (AD)</td><td>forest cleared per year (GFW/Hansen, 2015–24 mean)</td>
      <td>{AD_HA_YR:,.0f} ha/yr</td></tr>
    <tr><td>× EF = {EF:,.0f} tCO₂e/ha</td><td>carbon per ha at the cleared sites, pre-clearing (CTrees {DENS_LOSS:.0f} Mg/ha + roots)</td>
      <td>{BASE_EM:,.0f} tCO₂e/yr baseline</td></tr>
    <tr><td>× {EFFECT:.0%} effectiveness</td><td>share of that clearing the project actually averts</td>
      <td>{BASE_EM*EFFECT:,.0f} t/yr</td></tr>
    <tr><td>× (1−{LEAKAGE:.0%}) leakage</td><td>emissions displaced elsewhere</td>
      <td>{BASE_EM*EFFECT*(1-LEAKAGE):,.0f} t/yr</td></tr>
    <tr><td>× (1−{UNCERT:.0%}) uncertainty</td><td>VMD0055 deduction (shrinks with field plots)</td>
      <td>{BASE_EM*EFFECT*(1-LEAKAGE)*(1-UNCERT):,.0f} t/yr</td></tr>
    <tr><td>× (1−{BUFFER:.0%}) buffer</td><td>non-permanence buffer withheld by the registry</td>
      <td class="new">≈ {NET:,.0f} credits/yr</td></tr>
  </table>
  <div class="assume"><b>In one line:</b> {AD_HA_YR:,.0f} ha/yr × {EF:,.0f} tCO₂e/ha ×
  {EFFECT:.0%} × {1-LEAKAGE:.0%} × {1-UNCERT:.0%} × {1-BUFFER:.0%} ≈ {NET:,.0f} credits/yr. The
  baseline ({BASE_EM:,.0f} tCO₂e/yr) is real — GFW clearing × CTrees carbon. Note the carbon at
  cleared sites (~{DENS_LOSS:.0f} Mg/ha) is about half the reserve mean: clearing eats the accessible
  edges first. Carbon prices below ($4–$20/tonne) span the voluntary market range.</div>
  <div class="two" style="margin-top:6px">
    <table>
      <tr><th>Carbon price</th><th>Revenue / yr</th><th>Over 10 yrs</th></tr>
      {rev_rows}
    </table>
    <figure>
      <img src="{REV}" alt="Revenue at different carbon prices">
      <figcaption>Revenue at different carbon prices and time horizons.</figcaption>
    </figure>
  </div>
</section>

</div>
</body>
</html>
"""

# The report is a single self-contained file (all figures base64-embedded). It is
# written as index.html so GitHub Pages serves it directly at the site root.
# (.nojekyll, committed alongside, keeps Pages from running Jekyll over the repo.)
REPORT = "index.html"
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"Wrote {REPORT}  ({len(HTML)/1000:.0f} KB markup; figures embedded)")
