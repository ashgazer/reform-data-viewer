"""Generate a self-contained Leaflet choropleth map of constituency projections."""
import csv, json, re
from pathlib import Path

GEO = Path("constituencies.geojson")
CSV_PATH = Path("reform_constituency_predictions.csv")
OUT = Path("reform_map.html")

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

NUM_COLS = (
    "reform_share_mean_pct", "reform_share_mic_pct", "reform_share_ec_pct",
    "reform_share_2024_pct", "reform_swing_pp", "top_competitor_share_pct",
    "margin_mean_pp", "margin_mic_pp", "margin_ec_pp", "sigma_pp",
    "reform_win_probability",
)

predictions = {}
with CSV_PATH.open() as f:
    for r in csv.DictReader(f):
        for k in NUM_COLS:
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        predictions[norm(r["constituency"])] = r

g = json.load(GEO.open())
# strip heavy properties to shrink the payload
for feat in g["features"]:
    p = feat["properties"]
    name = p.get("PCON24NM", "")
    code = p.get("PCON24CD", "")
    feat["properties"] = {"name": name, "code": code}

data_keyed = {norm(k): v for k, v in predictions.items()}
geo_json = json.dumps(g, separators=(",", ":"))
pred_json = json.dumps(data_keyed, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>UK constituency map — Reform UK projections (April 2026 MRP)</title>
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
        crossorigin=""></script>
<style>
  :root {
    --bg: #0f1419; --panel: #1a1f26; --border: #2a323d;
    --text: #e6e6e6; --muted: #8b95a1; --accent: #00c4c6;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text);
               font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  header { padding: 0.9rem 1.5rem; background: var(--panel);
           border-bottom: 2px solid var(--accent); display: flex;
           justify-content: space-between; align-items: center; gap: 1rem;
           flex-wrap: wrap; }
  header h1 { margin: 0; font-size: 1.15rem; }
  header .sub { color: var(--muted); font-size: 0.82rem; }
  .layout { display: grid; grid-template-columns: 1fr 280px;
            height: calc(100vh - 60px); }
  @media (max-width: 900px) { .layout { grid-template-columns: 1fr; height: auto; }
                               #map { height: 70vh; } }
  #map { background: #0a0d11; }
  aside { background: var(--panel); border-left: 1px solid var(--border);
          padding: 1rem 1.1rem; overflow-y: auto; }
  aside h2 { font-size: 0.78rem; color: var(--muted);
             text-transform: uppercase; letter-spacing: 0.08em;
             margin: 0 0 0.5rem; font-weight: 600; }
  aside section { margin-bottom: 1.25rem; }
  .mode-btn { display: block; width: 100%; text-align: left;
              background: #0f141a; color: var(--text);
              border: 1px solid var(--border); padding: 0.55rem 0.75rem;
              border-radius: 6px; cursor: pointer; margin-bottom: 0.4rem;
              font: inherit; font-size: 0.88rem; }
  .mode-btn:hover { border-color: var(--accent); }
  .mode-btn.active { border-color: var(--accent); background: #00c4c622; }
  .legend-row { display: flex; align-items: center; gap: 0.6rem;
                font-size: 0.85rem; padding: 0.2rem 0; }
  .legend-swatch { width: 18px; height: 14px; border-radius: 3px;
                   border: 1px solid #00000022; flex-shrink: 0; }
  .legend-count { color: var(--muted); margin-left: auto;
                  font-variant-numeric: tabular-nums; }
  .gradient-legend { height: 14px; background: linear-gradient(
      to right, #3b4350, #6b7685, #c89500, #008d8f, #00a4a6);
      border-radius: 3px; margin: 0.4rem 0 0.25rem; }
  .gradient-labels { display: flex; justify-content: space-between;
                     color: var(--muted); font-size: 0.75rem; }

  #info { background: #0f141a; border-radius: 6px; padding: 0.75rem;
          font-size: 0.85rem; min-height: 110px; }
  #info .name { font-size: 1rem; font-weight: 600; margin-bottom: 0.35rem; }
  #info .row { display: flex; justify-content: space-between; padding: 0.12rem 0;
               color: var(--muted); }
  #info .row b { color: var(--text); font-weight: 500; }

  .leaflet-container { background: #0a0d11; }
  .leaflet-popup-content-wrapper { background: var(--panel); color: var(--text);
                                    border-radius: 6px; }
  .leaflet-popup-tip { background: var(--panel); }
  .leaflet-popup-content { margin: 0.6rem 0.8rem; font-size: 0.85rem; }
  .leaflet-bar a { background: var(--panel); color: var(--text);
                   border-bottom-color: var(--border) !important; }
  .leaflet-bar a:hover { background: #242d38; }
</style>
</head>
<body>
<header>
  <div>
    <h1>UK constituency map — Reform UK projections</h1>
    <div class="sub">MiC Apr 2026 MRP · EC Jan 2026 MRP · 2024 HoC results · 631 GB constituencies · NI &amp; Chorley greyed</div>
  </div>
</header>

<div class="layout">
  <div id="map"></div>
  <aside>
    <section>
      <h2>Colour mode</h2>
      <button class="mode-btn active" data-mode="winner">Projected winner (MiC)</button>
      <button class="mode-btn" data-mode="prob">P(Reform wins)</button>
      <button class="mode-btn" data-mode="share">Reform vote share %</button>
      <button class="mode-btn" data-mode="swing">Swing from 2024</button>
      <button class="mode-btn" data-mode="agreement">MRP agreement</button>
    </section>

    <section>
      <h2>Legend</h2>
      <div id="legend"></div>
    </section>

    <section>
      <h2>Hover a seat</h2>
      <div id="info">Move over a constituency to see its projection.</div>
    </section>
  </aside>
</div>

<script>
const GEO  = __GEO__;
const PRED = __PRED__;

const WINNER_COLOURS = {
  "Reform UK":                     "#00c4c6",
  "Labour":                        "#e4003b",
  "Conservative":                  "#0087dc",
  "Liberal Democrat":              "#faa61a",
  "The Green Party":               "#6bcc6b",
  "Scottish National Party (SNP)": "#fff95d",
  "Plaid Cymru":                   "#005b54",
};
const NO_DATA = "#3b4350";
const AGREE_COL    = "#00c4c6";
const DISAGREE_COL = "#e4003b";

function norm(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, ""); }

// sequential scale 0..1 (teal gradient)
function seqColour(v) {
  if (v == null) return NO_DATA;
  const stops = [
    [0.00, [59, 67, 80]],
    [0.25, [107, 118, 133]],
    [0.50, [200, 149, 0]],
    [0.75, [0, 141, 143]],
    [1.00, [0, 164, 166]],
  ];
  return interp(v, stops);
}
// diverging scale -1..+1 (red-grey-teal) for swing
function divColour(v) {
  if (v == null) return NO_DATA;
  const stops = [
    [-1.0, [228,   0,  59]], // #e4003b
    [-0.5, [180,  80,  80]],
    [ 0.0, [ 55,  66,  78]], // near bg
    [ 0.5, [  0, 141, 143]],
    [ 1.0, [  0, 196, 198]], // #00c4c6
  ];
  return interp(v, stops);
}
function interp(v, stops) {
  v = Math.max(stops[0][0], Math.min(stops.at(-1)[0], v));
  for (let i = 0; i < stops.length - 1; i++) {
    const [t0, c0] = stops[i], [t1, c1] = stops[i+1];
    if (v <= t1) {
      const t = (v - t0) / (t1 - t0);
      const rgb = c0.map((_, k) => Math.round(c0[k] + (c1[k] - c0[k]) * t));
      return `rgb(${rgb.join(",")})`;
    }
  }
  return `rgb(${stops.at(-1)[1].join(",")})`;
}

let mode = "winner";

function styleFor(feature) {
  const rec = PRED[norm(feature.properties.name)];
  if (!rec) return { fillColor: NO_DATA, fillOpacity: 0.6,
                     color: "#1a1f26", weight: 0.5 };
  let fc;
  if (mode === "winner")        fc = WINNER_COLOURS[rec.projected_winner_mic] || NO_DATA;
  else if (mode === "prob")     fc = seqColour(rec.reform_win_probability);
  else if (mode === "share")    fc = seqColour(Math.min(1, (rec.reform_share_mean_pct || 0) / 60));
  else if (mode === "swing")    fc = divColour(rec.reform_swing_pp == null ? null :
                                               Math.max(-1, Math.min(1, rec.reform_swing_pp / 30)));
  else if (mode === "agreement")fc = rec.winners_agree === "yes" ? AGREE_COL
                                   : rec.winners_agree === "no"  ? DISAGREE_COL
                                   : NO_DATA;
  return { fillColor: fc, fillOpacity: 0.85, color: "#0f1419", weight: 0.3 };
}

const map = L.map("map", { preferCanvas: true,
                           attributionControl: true }).setView([54.5, -3], 6);

// minimal dark attribution; no tiles — pure choropleth on dark background
L.control.attribution({ prefix: false })
  .addAttribution("Boundaries © ONS 2024 · Data: More in Common Apr 2026 MRP")
  .addTo(map);

const info = document.getElementById("info");
function fmt(v, d=1) { return v == null ? "—" : (+v).toFixed(d); }
function sign(v, d=1) { return v == null ? "—" : ((v>=0?"+":"") + (+v).toFixed(d)); }

function showInfo(rec, name) {
  if (!rec) {
    info.innerHTML = `<div class="name">${name}</div>
      <div class="row">No MRP data (NI or Speaker's seat)</div>`;
    return;
  }
  const agree = rec.winners_agree;
  const agreeColor = agree === "yes" ? AGREE_COL : agree === "no" ? DISAGREE_COL : "#aaa";
  info.innerHTML = `
    <div class="name">${rec.constituency}</div>
    <div class="row"><span>MiC winner</span>
      <b style="color:${WINNER_COLOURS[rec.projected_winner_mic] || "#fff"}">${rec.projected_winner_mic}</b></div>
    <div class="row"><span>EC winner</span><b>${rec.projected_winner_ec || "—"}</b></div>
    <div class="row"><span>Pollsters</span>
      <b style="color:${agreeColor}">${agree === "yes" ? "agree" : agree === "no" ? "DISAGREE" : "—"}</b></div>
    <div class="row"><span>Reform share</span><b>${fmt(rec.reform_share_mean_pct)}%</b></div>
    <div class="row"><span>Reform 2024</span><b>${fmt(rec.reform_share_2024_pct)}%</b></div>
    <div class="row"><span>Swing</span><b>${sign(rec.reform_swing_pp)} pp</b></div>
    <div class="row"><span>Top rival</span><b>${rec.top_competitor} (${fmt(rec.top_competitor_share_pct)}%)</b></div>
    <div class="row"><span>Margin</span><b>${sign(rec.margin_mean_pp)} pp (±${fmt(rec.sigma_pp)})</b></div>
    <div class="row"><span>P(Reform wins)</span><b>${((+rec.reform_win_probability)*100).toFixed(0)}%</b></div>
    <div class="row"><span>Category</span><b>${rec.likelihood_category}</b></div>
  `;
}

const layer = L.geoJSON(GEO, {
  style: styleFor,
  onEachFeature: (feature, lyr) => {
    const rec = PRED[norm(feature.properties.name)];
    lyr.on({
      mouseover: e => { e.target.setStyle({ weight: 2, color: "#fff" });
                        e.target.bringToFront();
                        showInfo(rec, feature.properties.name); },
      mouseout:  e => layer.resetStyle(e.target),
      click:     e => map.fitBounds(e.target.getBounds(), { maxZoom: 9 }),
    });
    const winner = rec ? rec.projected_winner_mic : "No data";
    lyr.bindTooltip(`${feature.properties.name} — ${winner}`,
                    { sticky: true, direction: "top" });
  },
}).addTo(map);

map.fitBounds(layer.getBounds());

// ---- legend ----
function buildLegend() {
  const el = document.getElementById("legend");
  if (mode === "winner") {
    const counts = {};
    Object.values(PRED).forEach(r => {
      counts[r.projected_winner_mic] = (counts[r.projected_winner_mic] || 0) + 1;
    });
    const rows = Object.entries(WINNER_COLOURS).map(([party, col]) => `
      <div class="legend-row">
        <div class="legend-swatch" style="background:${col}"></div>
        <div>${party}</div>
        <div class="legend-count">${counts[party] || 0}</div>
      </div>
    `).join("");
    el.innerHTML = rows + `
      <div class="legend-row">
        <div class="legend-swatch" style="background:${NO_DATA}"></div>
        <div>No data (NI / Speaker)</div>
        <div class="legend-count">19</div>
      </div>`;
  } else if (mode === "swing") {
    el.innerHTML = `
      <div class="legend-row"><b>Reform swing from 2024</b></div>
      <div class="gradient-legend" style="background:linear-gradient(
        to right, #e4003b, #b45050, #37424e, #008d8f, #00c4c6);"></div>
      <div class="gradient-labels"><span>−30 pp</span><span>0</span><span>+30 pp</span></div>
    `;
  } else if (mode === "agreement") {
    let agree = 0, disagree = 0, nodata = 0;
    Object.values(PRED).forEach(r => {
      if (r.winners_agree === "yes") agree++;
      else if (r.winners_agree === "no") disagree++;
      else nodata++;
    });
    el.innerHTML = `
      <div class="legend-row">
        <div class="legend-swatch" style="background:${AGREE_COL}"></div>
        <div>Both MRPs agree on winner</div>
        <div class="legend-count">${agree}</div>
      </div>
      <div class="legend-row">
        <div class="legend-swatch" style="background:${DISAGREE_COL}"></div>
        <div>Pollsters disagree</div>
        <div class="legend-count">${disagree}</div>
      </div>
      <div class="legend-row">
        <div class="legend-swatch" style="background:${NO_DATA}"></div>
        <div>No data (NI / Speaker)</div>
        <div class="legend-count">${nodata + 19}</div>
      </div>`;
  } else {
    const label = mode === "prob" ? "P(Reform wins)" : "Reform vote share";
    const hi = mode === "prob" ? "100%" : "60%+";
    el.innerHTML = `
      <div class="legend-row"><b>${label}</b></div>
      <div class="gradient-legend"></div>
      <div class="gradient-labels"><span>0%</span><span>${hi}</span></div>
    `;
  }
}

// ---- mode switch ----
document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
    layer.setStyle(styleFor);
    buildLegend();
  });
});

buildLegend();
</script>
</body>
</html>
"""

out = HTML.replace("__GEO__", geo_json).replace("__PRED__", pred_json)
OUT.write_text(out)
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
