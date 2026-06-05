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

# --- credits, built transparently from the numbers shown in the report ------
# Baseline = the SAME decline we measured in the CTrees series (0.1%/yr), not an
# inflated counterfactual. Stock is the standing above-ground CO₂e ("CO₂ held").
STOCK_CO2E = 210_000_000   # t CO₂e held (above-ground), from the biomass→CO₂ chain
BASELINE   = 0.001         # 0.1%/yr — the measured annual decline, used as the baseline
PREVENTED  = 0.75          # share of that loss the project actually prevents
LEAKAGE    = 0.20          # −20% emissions displaced elsewhere
BUFFER     = 0.15          # −15% non-permanence buffer withheld by the registry

GROSS = STOCK_CO2E * BASELINE                               # t/yr at risk in the baseline
NET   = round(GROSS * PREVENTED * (1 - LEAKAGE) * (1 - BUFFER))   # ≈ 107,100 credits/yr

def usd(x):
    return f"${x/1e6:.2f}M" if x < 1e9 else f"${x/1e9:.2f}B"
rev_rows = "".join(
    f"<tr><td>${p} per tonne</td><td>{usd(NET*p)}</td><td>{usd(NET*p*10)}</td></tr>"
    for p in (4, 8, 12, 20))

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
      <figcaption>Biomass density across the area (greener = more biomass), from the CTrees data, 2025.
      <span class="coords">Bounding box used (WGS84 / EPSG:4326):<br>
      longitude&nbsp;28.16°E&nbsp;→&nbsp;28.98°E&nbsp;·&nbsp;latitude&nbsp;2.85°S&nbsp;→&nbsp;4.01°S<br>
      corners: NW (2.85°S, 28.16°E), SE (4.01°S, 28.98°E). A rectangle around the reserve, not the exact gazetted boundary.</span></figcaption>
    </figure>
    <div>
      <p><b>What stands out:</b> There's a dense, high-biomass core (the
      darker greens) that looks like intact rainforest, wrapped in lighter areas — likely degraded,
      farmed, or cleared land — concentrated toward the west.</p>
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
      <b>106 to 104 Mg/ha</b> — the ~0.1%/yr we see in the trend. Real, but small enough to miss on
      a map.</p>
      <p>So a snapshot hides the story. To see <i>where</i> the forest is actually under pressure, it
      helps to map the change itself rather than the biomass — that's the panel below.</p>
    </div>
  </div>
  <figure>
    <img src="{PANELS}" alt="Biomass density in 2000, 2015 and 2025 side by side">
    <figcaption>The same area in 2000, 2015 and 2025 on one color scale — means 106 → 104 → 104 Mg/ha.
    The eye can barely tell them apart.</figcaption>
  </figure>
  <div class="two" style="margin-top:6px">
    <figure>
      <img src="{CHANGE}" alt="Map of biomass change across Itombwe, 2000 to 2025">
      <figcaption>Per-pixel change over the period (red = loss, green = gain), from a trend fit across
      all 26 years.</figcaption>
    </figure>
    <div>
      <div class="callout"><b>Key Findings</b> About <b>a third of the area</b>
      shows a net biomass loss, concentrated along the western edge and the farmed/settled frontier —
      exactly where rangers, satellite alerts, and cookstove/livelihood programs would go first.</div>
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
  <p class="lead">computed over the reserve bounding box. </p>
  <div class="cards">
    <div class="card"><div class="n">~1.18M ha</div><div class="l">Area I looked at</div>
      <div class="s">A box around the reserve — a bit larger than the official boundary</div></div>
    <div class="card"><div class="n">~111 Mg/ha</div><div class="l">Typical biomass density</div>
      <div class="s">Half the forest is denser than this, half less</div></div>
    <div class="card"><div class="n">~210 M</div><div class="l">tonnes CO₂e held</div>
      <div class="s">Roughly how much CO₂ the standing forest is storing</div></div>
    <div class="card"><div class="n">≈ −0.1%/yr</div><div class="l">Biomass trend, 2003–25</div>
      <div class="s">A slight downward drift over the period</div></div>
    <div class="card"><div class="n">~{NET/1e3:.0f}k</div><div class="l">possible credits / yr</div>
      <div class="s">From the step-by-step calculation further down</div></div>
    <div class="card"><div class="n">{usd(NET*4)}–{usd(NET*20)}</div><div class="l">illustrative revenue / yr</div>
      <div class="s">If those credits sold at $4–$20 each</div></div>
  </div>
</section>

<section>
  <h2>Biomass dataset comparison <span class="em">— CTrees vs. Chloris</span></h2>
  <p>There are several open satellite biomass products. I pulled two and compared them over Itombwe:
  <b>CTrees</b> (fine, ~100 m pixels) and <b>Chloris</b> (coarse, ~4.6 km pixels). They give
  noticeably different pictures.</p>
  <table>
    <tr><th>What I looked at</th><th>Chloris (~4.6 km)</th><th>CTrees (~100 m)</th></tr>
    <tr><td>Resolution over the reserve</td><td class="old">~30 pixels</td><td class="new">~1.2 million pixels</td></tr>
    <tr><td>Typical biomass density</td><td class="old">~214 Mg/ha</td><td class="new">~111 Mg/ha</td></tr>
    <tr><td>Implied carbon stock</td><td class="old">~450 M tonnes CO₂e</td><td class="new">~210 M tonnes CO₂e</td></tr>
    <tr><td>Trend, 2003–2025</td><td class="old">roughly flat</td><td class="new">a slight decline</td></tr>
  </table>
  <div class="callout"><b>Why they differ so much.</b> It's mostly resolution. Coarse pixels average
  small clearings and degraded edges together with healthy forest into one number; fine pixels keep
  them separate, so CTrees reads lower. Worth settling on which dataset fits Itombwe best.</div>
</section>

<section>
  <h2>Biomass over time</h2>
  <div class="two">
    <div>
      <p class="lead">Across 2000–2025 the average biomass drifts gently downward — roughly
      <b>0.1% a year</b>.</p>
      <p>Small but steady, and in the direction you'd expect if slow logging and charcoal/fuelwood
      pressure are nibbling at the forest. The coarser dataset showed this same forest as basically
      flat.</p>
    </div>
    <figure>
      <img src="{TREND}" alt="Average biomass over time">
      <figcaption>Average biomass density over the area, 2003–2025 (CTrees).</figcaption>
    </figure>
  </div>
</section>

<section>
  <h2>From biomass to a carbon number</h2>
  <p>Turning "tonnes of wood" into "tonnes of CO₂" is just a couple of standard conversions (the
  same factors the IPCC publishes), so it's reproducible from the same data:</p>
  <div class="flow">
    <div class="step">Biomass<b>~122 Mt</b>of wood</div>
    <div class="arr">→</div>
    <div class="step">about half is carbon<b>~57 Mt</b>of carbon</div>
    <div class="arr">→</div>
    <div class="step">as CO₂<b>~210 Mt</b>CO₂e</div>
    <div class="arr">→</div>
    <div class="step">+ roots<b>~261 Mt</b>CO₂e total</div>
  </div>
</section>

<section>
  <h2>What it might be worth — and how that works</h2>
  <div class="explain">
    <h3>How can a forest that's slowly losing biomass still earn money?</h3>
    <ol>
      <li>The forest is cleared and degraded a little more every year — for farmland, timber,
      charcoal and fuelwood — releasing the carbon in those trees as CO₂. The credit isn't about
      reviving a tree that's already cut; it's about preventing <i>next year's</i> clearing that
      hasn't happened yet.</li>
      <li>A protection effort lowers that rate of loss — concretely: <b>rangers and patrols</b> that
      deter illegal logging, <b>improved cookstoves</b> and <b>alternative livelihoods</b> so
      communities need less fuelwood and new farmland, and <b>satellite alerts</b> that catch
      encroachment early. Each tonne of CO₂ that stays in the trees instead of being emitted earns
      <b>one carbon credit</b>.</li>
      <li>Companies buy those credits — at some price per tonne — to offset their own emissions.</li>
      <li>That money pays for the protection, which is what slows the loss in the first place.</li>
    </ol>
    
  </div>
  <p style="margin-top:18px">Running the numbers lands around <b>~{NET:,.0f} credits a year</b>. Here's
  the full chain — it starts from the CO₂ already shown above and applies one factor at a time:</p>
  <table style="max-width:720px">
    <tr><th>Step</th><th>What it does</th><th>Running total</th></tr>
    <tr><td>CO₂ held</td><td>standing above-ground stock (from the conversion above)</td>
      <td>{STOCK_CO2E:,.0f} t CO₂e</td></tr>
    <tr><td>× 0.1% / yr</td><td>the decline we actually measured = baseline loss</td>
      <td>{GROSS:,.0f} t/yr at risk</td></tr>
    <tr><td>× 75%</td><td>share of that loss the project prevents</td>
      <td>{GROSS*PREVENTED:,.0f} t/yr</td></tr>
    <tr><td>× 80%</td><td>after −20% leakage (emissions displaced elsewhere)</td>
      <td>{GROSS*PREVENTED*(1-LEAKAGE):,.0f} t/yr</td></tr>
    <tr><td>× 85%</td><td>after −15% buffer pool (held back for permanence)</td>
      <td class="new">≈ {NET:,.0f} credits/yr</td></tr>
  </table>
  <div class="assume"><b>In one line:</b> {STOCK_CO2E:,.0f} × 0.1% × 0.75 × 0.80 × 0.85 ≈
  {NET:,.0f} credits/yr. The <b>0.1%/yr</b> baseline is the decline measured in the CTrees series
  above — not an inflated counterfactual; the 75% / −20% / −15% factors are placeholders a
  registry-approved method would set. Carbon prices below ($4–$20/tonne) span the voluntary market
  range.</div>
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
