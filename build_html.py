"""Generate a self-contained HTML dashboard from reform_constituency_predictions.csv."""
import csv
import json
from pathlib import Path

CSV_PATH = Path("reform_constituency_predictions.csv")
OUT = Path("reform_dashboard.html")

rows = []
with CSV_PATH.open() as f:
    for r in csv.DictReader(f):
        for k in ("reform_share_pct", "top_competitor_share_pct", "margin_pp",
                  "reform_win_probability", "con_pct", "lab_pct", "libdem_pct",
                  "green_pct", "snp_pct", "plaid_pct", "other_pct"):
            r[k] = float(r[k])
        rows.append(r)

data_json = json.dumps(rows, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Reform UK — Constituency Win Likelihood</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1419; --panel: #1a1f26; --panel2: #0f141a; --border: #2a323d;
    --text: #e6e6e6; --muted: #8b95a1; --accent: #00c4c6; --accent-dim: #008d8f;
    --safe: #00a4a6; --likely: #008d8f; --tossup: #c89500;
    --lean: #6b7685; --safeag: #3b4350;
  }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0; background: var(--bg); color: var(--text); }
  header { padding: 1.5rem 2rem; background: var(--panel);
           border-bottom: 2px solid var(--accent); }
  h1 { margin: 0 0 0.25rem; font-size: 1.4rem; }
  .sub { color: var(--muted); font-size: 0.88rem; }
  .container { max-width: 1500px; margin: 0 auto; padding: 1.5rem 2rem; }
  .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
             gap: 0.75rem; margin-bottom: 1.25rem; }
  .card { background: var(--panel); border: 1px solid var(--border);
          border-radius: 8px; padding: 0.9rem 1rem; transition: all 0.15s; }
  .card.click { cursor: pointer; }
  .card.click:hover { border-color: var(--accent); }
  .card.active { border-color: var(--accent);
                 box-shadow: inset 0 0 0 1px var(--accent); }
  .card .label { color: var(--muted); font-size: 0.72rem;
                 text-transform: uppercase; letter-spacing: 0.06em; }
  .card .value { font-size: 1.7rem; font-weight: 600; margin-top: 0.25rem;
                 line-height: 1.1; }
  .card .suffix { color: var(--muted); font-size: 0.8rem; margin-left: 0.25rem; }

  .controls { display: flex; gap: 0.6rem; margin-bottom: 1rem;
              flex-wrap: wrap; align-items: center; }
  input, select, button { background: var(--panel); color: var(--text);
                          border: 1px solid var(--border); padding: 0.5rem 0.75rem;
                          border-radius: 6px; font: inherit; }
  input:focus, select:focus { outline: none; border-color: var(--accent); }
  button { cursor: pointer; }
  button:hover { border-color: var(--accent); color: var(--accent); }
  #search { flex: 1; min-width: 240px; }

  .tabs { display: flex; gap: 0.2rem; margin-bottom: 1rem;
          border-bottom: 1px solid var(--border); }
  .tab { background: none; border: none; padding: 0.65rem 1.1rem;
         color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent;
         border-radius: 0; font-size: 0.92rem; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  .view { display: none; }
  .view.active { display: block; }

  .table-wrap { max-height: 700px; overflow: auto; border-radius: 8px;
                border: 1px solid var(--border); background: var(--panel); }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th, td { padding: 0.55rem 0.75rem; text-align: left;
           border-bottom: 1px solid var(--border); white-space: nowrap; }
  th { background: var(--panel2); cursor: pointer; user-select: none;
       position: sticky; top: 0; z-index: 1; font-weight: 600; }
  th:hover { color: var(--accent); }
  th.sort-asc::after { content: " ▲"; color: var(--accent); }
  th.sort-desc::after { content: " ▼"; color: var(--accent); }
  th.num, td.num { text-align: right; }
  tr:hover td { background: #222a35; }

  .prob-bar { position: relative; width: 70px; height: 14px;
              background: #222a35; border-radius: 3px; display: inline-block;
              vertical-align: middle; overflow: hidden; }
  .prob-bar > span { position: absolute; left: 0; top: 0; bottom: 0;
                     background: linear-gradient(90deg, var(--accent-dim), var(--accent));
                     border-radius: 3px; }
  .prob-text { display: inline-block; width: 42px; text-align: right;
               margin-left: 6px; font-variant-numeric: tabular-nums; }

  .cat { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
         font-weight: 600; display: inline-block; }
  .cat-safe-reform    { background: var(--safe);   color: #fff; }
  .cat-likely-reform  { background: var(--likely); color: #fff; }
  .cat-toss-up        { background: var(--tossup); color: #fff; }
  .cat-lean-against   { background: var(--lean);   color: #fff; }
  .cat-safe-against   { background: var(--safeag); color: #ccc; }

  .winner-reform-uk        { color: var(--accent); font-weight: 600; }
  .winner-labour           { color: #ee6b6b; }
  .winner-conservative     { color: #4aa3ff; }
  .winner-liberal-democrat { color: #e6b800; }
  .winner-the-green-party  { color: #6bcc6b; }
  .winner-scottish-national-party-snp { color: #ffc247; }
  .winner-plaid-cymru      { color: #e377c2; }

  .chart-wrap { background: var(--panel); padding: 1rem; border-radius: 8px;
                border: 1px solid var(--border); }
  .chart-wrap canvas { max-height: 520px; }
  .chart-note { color: var(--muted); font-size: 0.82rem; margin-top: 0.75rem; }

  footer { padding: 1rem 2rem; color: var(--muted); font-size: 0.82rem;
           border-top: 1px solid var(--border); margin-top: 2rem; }
  footer a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>Reform UK — constituency win likelihood</h1>
  <div class="sub">Source: More in Common April 2026 MRP · 631 GB constituencies (Northern Ireland excluded) · Win probability is a margin-based proxy (σ = 4pp)</div>
</header>

<div class="container">

  <div class="summary" id="summary"></div>

  <div class="controls">
    <input id="search" type="search" placeholder="Search constituency…">
    <select id="catFilter"><option value="">All categories</option></select>
    <select id="winnerFilter"><option value="">All projected winners</option></select>
    <button id="clearBtn">Clear</button>
    <span id="countLabel" class="sub"></span>
  </div>

  <div class="tabs">
    <button class="tab active" data-view="table">Table</button>
    <button class="tab" data-view="category">Category breakdown</button>
    <button class="tab" data-view="histogram">Reform vote share distribution</button>
    <button class="tab" data-view="scatter">Margin vs Reform share</button>
    <button class="tab" data-view="topbottom">Safest / closest seats</button>
  </div>

  <div class="view active" id="view-table">
    <div class="table-wrap">
      <table id="dataTable">
        <thead><tr>
          <th data-sort="constituency">Constituency</th>
          <th data-sort="projected_winner">Projected winner</th>
          <th data-sort="reform_share_pct" class="num">Reform %</th>
          <th data-sort="top_competitor">Top competitor</th>
          <th data-sort="top_competitor_share_pct" class="num">Competitor %</th>
          <th data-sort="margin_pp" class="num">Margin (pp)</th>
          <th data-sort="reform_win_probability" class="num">P(Reform wins)</th>
          <th data-sort="likelihood_category">Category</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div class="view" id="view-category">
    <div class="chart-wrap">
      <canvas id="catChart"></canvas>
      <div class="chart-note">Bars reflect the currently filtered set.</div>
    </div>
  </div>

  <div class="view" id="view-histogram">
    <div class="chart-wrap">
      <canvas id="histChart"></canvas>
      <div class="chart-note">Histogram of Reform UK projected vote share, in 2pp bins.</div>
    </div>
  </div>

  <div class="view" id="view-scatter">
    <div class="chart-wrap">
      <canvas id="scatterChart"></canvas>
      <div class="chart-note">Each point is a constituency. X = Reform vote share, Y = margin over top competitor. Colour = projected winner. Hover for detail.</div>
    </div>
  </div>

  <div class="view" id="view-topbottom">
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
      <div class="chart-wrap">
        <h3 style="margin-top:0;">Top 20 safest Reform seats</h3>
        <table id="topTable" style="width:100%;"><thead><tr>
          <th>Constituency</th><th class="num">Reform %</th><th class="num">Margin</th>
        </tr></thead><tbody></tbody></table>
      </div>
      <div class="chart-wrap">
        <h3 style="margin-top:0;">Closest Reform-projected seats (by margin)</h3>
        <table id="closeTable" style="width:100%;"><thead><tr>
          <th>Constituency</th><th class="num">Reform %</th><th class="num">Margin</th>
        </tr></thead><tbody></tbody></table>
      </div>
    </div>
  </div>

</div>

<footer>
  Data: <a href="https://www.moreincommon.org.uk/latest-insights/more-in-common-s-april-2026-mrp/" target="_blank">More in Common April 2026 MRP</a>. Probabilities are a Normal-CDF proxy on the inter-party margin and should not be read as the MRP's own posterior.
</footer>

<script>
const DATA = __DATA__;

const CATS = ["Safe Reform","Likely Reform","Toss-up","Lean Against","Safe Against"];
const CAT_COLOURS = {
  "Safe Reform":   "#00a4a6",
  "Likely Reform": "#008d8f",
  "Toss-up":       "#c89500",
  "Lean Against":  "#6b7685",
  "Safe Against":  "#3b4350",
};
const WINNER_COLOURS = {
  "Reform UK": "#00c4c6",
  "Labour": "#ee6b6b",
  "Conservative": "#4aa3ff",
  "Liberal Democrat": "#e6b800",
  "The Green Party": "#6bcc6b",
  "Scottish National Party (SNP)": "#ffc247",
  "Plaid Cymru": "#e377c2",
};

function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }

// --- populate filter dropdowns ---
const catFilter = document.getElementById("catFilter");
CATS.forEach(c => {
  const o = document.createElement("option"); o.value = c; o.textContent = c;
  catFilter.appendChild(o);
});
const winnerFilter = document.getElementById("winnerFilter");
const winners = [...new Set(DATA.map(r => r.projected_winner))].sort();
winners.forEach(w => {
  const o = document.createElement("option"); o.value = w; o.textContent = w;
  winnerFilter.appendChild(o);
});

// --- state ---
const state = {
  search: "",
  category: "",
  winner: "",
  sortKey: "reform_win_probability",
  sortDir: "desc",
};

function filtered() {
  const q = state.search.trim().toLowerCase();
  return DATA.filter(r => {
    if (q && !r.constituency.toLowerCase().includes(q)) return false;
    if (state.category && r.likelihood_category !== state.category) return false;
    if (state.winner && r.projected_winner !== state.winner) return false;
    return true;
  });
}

function sorted(rows) {
  const k = state.sortKey, dir = state.sortDir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[k], bv = b[k];
    if (typeof av === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv)) * dir;
  });
}

// --- summary cards ---
function renderSummary() {
  const all = DATA;
  const cur = filtered();
  const byCat = Object.fromEntries(CATS.map(c => [c, 0]));
  let reformPoint = 0, expected = 0;
  cur.forEach(r => {
    byCat[r.likelihood_category]++;
    if (r.projected_winner === "Reform UK") reformPoint++;
    expected += r.reform_win_probability;
  });
  const html = [
    { label: "Seats (filtered)", value: cur.length, suffix: `of ${all.length}` },
    { label: "Reform point-estimate wins", value: reformPoint },
    { label: "Expected Reform seats (ΣP)", value: expected.toFixed(1) },
    { label: "Safe Reform", value: byCat["Safe Reform"], cat: "Safe Reform" },
    { label: "Likely Reform", value: byCat["Likely Reform"], cat: "Likely Reform" },
    { label: "Toss-up", value: byCat["Toss-up"], cat: "Toss-up" },
    { label: "Lean Against", value: byCat["Lean Against"], cat: "Lean Against" },
    { label: "Safe Against", value: byCat["Safe Against"], cat: "Safe Against" },
  ].map(c => `
    <div class="card ${c.cat ? "click" : ""} ${c.cat && state.category === c.cat ? "active" : ""}"
         ${c.cat ? `data-cat="${c.cat}"` : ""}>
      <div class="label">${c.label}</div>
      <div class="value">${c.value}${c.suffix ? `<span class="suffix">${c.suffix}</span>` : ""}</div>
    </div>
  `).join("");
  document.getElementById("summary").innerHTML = html;
  document.querySelectorAll(".card.click").forEach(el => {
    el.addEventListener("click", () => {
      const cat = el.dataset.cat;
      state.category = state.category === cat ? "" : cat;
      catFilter.value = state.category;
      renderAll();
    });
  });
}

// --- table ---
function renderTable() {
  const rows = sorted(filtered());
  const tbody = document.querySelector("#dataTable tbody");
  tbody.innerHTML = rows.map(r => {
    const pct = (r.reform_win_probability * 100).toFixed(0);
    const winnerCls = "winner-" + slug(r.projected_winner);
    const catCls = "cat-" + slug(r.likelihood_category);
    return `<tr>
      <td>${r.constituency}</td>
      <td class="${winnerCls}">${r.projected_winner}</td>
      <td class="num">${r.reform_share_pct.toFixed(1)}</td>
      <td>${r.top_competitor}</td>
      <td class="num">${r.top_competitor_share_pct.toFixed(1)}</td>
      <td class="num">${r.margin_pp >= 0 ? "+" : ""}${r.margin_pp.toFixed(1)}</td>
      <td class="num">
        <span class="prob-bar"><span style="width:${pct}%"></span></span>
        <span class="prob-text">${pct}%</span>
      </td>
      <td><span class="cat ${catCls}">${r.likelihood_category}</span></td>
    </tr>`;
  }).join("");

  document.querySelectorAll("#dataTable th").forEach(th => {
    th.classList.remove("sort-asc","sort-desc");
    if (th.dataset.sort === state.sortKey) {
      th.classList.add(state.sortDir === "asc" ? "sort-asc" : "sort-desc");
    }
  });

  document.getElementById("countLabel").textContent = `${rows.length} seat${rows.length === 1 ? "" : "s"} shown`;
}

document.querySelectorAll("#dataTable th").forEach(th => {
  th.addEventListener("click", () => {
    const k = th.dataset.sort;
    if (state.sortKey === k) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    else { state.sortKey = k; state.sortDir = typeof DATA[0][k] === "number" ? "desc" : "asc"; }
    renderTable();
  });
});

// --- charts ---
let catChart, histChart, scatterChart;

function renderCatChart() {
  const rows = filtered();
  const counts = CATS.map(c => rows.filter(r => r.likelihood_category === c).length);
  const cfg = {
    type: "bar",
    data: { labels: CATS, datasets: [{
      data: counts,
      backgroundColor: CATS.map(c => CAT_COLOURS[c]),
      borderRadius: 4,
    }]},
    options: {
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${ctx.parsed.y} seats` } }
      },
      scales: {
        x: { ticks: { color: "#e6e6e6" }, grid: { color: "#2a323d" } },
        y: { beginAtZero: true, ticks: { color: "#e6e6e6" }, grid: { color: "#2a323d" } }
      }
    }
  };
  if (catChart) catChart.destroy();
  catChart = new Chart(document.getElementById("catChart"), cfg);
}

function renderHist() {
  const rows = filtered();
  const binSize = 2;
  const bins = Array(Math.ceil(100 / binSize)).fill(0);
  rows.forEach(r => {
    const b = Math.min(bins.length - 1, Math.floor(r.reform_share_pct / binSize));
    bins[b]++;
  });
  const labels = bins.map((_, i) => `${i*binSize}–${(i+1)*binSize}`);
  const cfg = {
    type: "bar",
    data: { labels, datasets: [{
      label: "Reform vote share %",
      data: bins,
      backgroundColor: "#00a4a6",
      borderRadius: 2,
    }]},
    options: {
      plugins: { legend: { display: false },
        tooltip: { callbacks: { title: ctx => `${ctx[0].label}% Reform`,
                                label: ctx => `${ctx.parsed.y} seats` } } },
      scales: {
        x: { title: { display: true, text: "Reform vote share (%)", color: "#8b95a1" },
             ticks: { color: "#e6e6e6", maxRotation: 0, autoSkip: true, maxTicksLimit: 15 },
             grid: { color: "#2a323d" } },
        y: { title: { display: true, text: "Constituencies", color: "#8b95a1" },
             beginAtZero: true, ticks: { color: "#e6e6e6" }, grid: { color: "#2a323d" } }
      }
    }
  };
  if (histChart) histChart.destroy();
  histChart = new Chart(document.getElementById("histChart"), cfg);
}

function renderScatter() {
  const rows = filtered();
  const byWinner = {};
  rows.forEach(r => {
    (byWinner[r.projected_winner] ??= []).push({
      x: r.reform_share_pct, y: r.margin_pp, c: r.constituency
    });
  });
  const datasets = Object.entries(byWinner).map(([w, pts]) => ({
    label: w, data: pts,
    backgroundColor: WINNER_COLOURS[w] || "#888",
    pointRadius: 3, pointHoverRadius: 6,
  }));
  const cfg = {
    type: "scatter",
    data: { datasets },
    options: {
      plugins: {
        legend: { labels: { color: "#e6e6e6" } },
        tooltip: { callbacks: {
          label: ctx => `${ctx.raw.c}: Reform ${ctx.raw.x.toFixed(1)}%, margin ${ctx.raw.y >= 0 ? "+" : ""}${ctx.raw.y.toFixed(1)}pp`
        } }
      },
      scales: {
        x: { title: { display: true, text: "Reform vote share (%)", color: "#8b95a1" },
             ticks: { color: "#e6e6e6" }, grid: { color: "#2a323d" } },
        y: { title: { display: true, text: "Margin over top competitor (pp)", color: "#8b95a1" },
             ticks: { color: "#e6e6e6" }, grid: { color: "#2a323d" } }
      }
    }
  };
  if (scatterChart) scatterChart.destroy();
  scatterChart = new Chart(document.getElementById("scatterChart"), cfg);
}

function renderTopBottom() {
  const rows = filtered();
  const safest = [...rows].sort((a, b) => b.margin_pp - a.margin_pp).slice(0, 20);
  const reformWins = rows.filter(r => r.projected_winner === "Reform UK");
  const closest = [...reformWins].sort((a, b) => a.margin_pp - b.margin_pp).slice(0, 20);
  const rowHtml = r => `<tr>
    <td>${r.constituency}</td>
    <td class="num">${r.reform_share_pct.toFixed(1)}</td>
    <td class="num">${r.margin_pp >= 0 ? "+" : ""}${r.margin_pp.toFixed(1)}</td>
  </tr>`;
  document.querySelector("#topTable tbody").innerHTML = safest.map(rowHtml).join("");
  document.querySelector("#closeTable tbody").innerHTML = closest.map(rowHtml).join("");
}

// --- tab switching ---
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    const v = btn.dataset.view;
    document.getElementById("view-" + v).classList.add("active");
    if (v === "category")  renderCatChart();
    if (v === "histogram") renderHist();
    if (v === "scatter")   renderScatter();
    if (v === "topbottom") renderTopBottom();
  });
});

// --- control wiring ---
document.getElementById("search").addEventListener("input", e => {
  state.search = e.target.value; renderAll();
});
catFilter.addEventListener("change", e => {
  state.category = e.target.value; renderAll();
});
winnerFilter.addEventListener("change", e => {
  state.winner = e.target.value; renderAll();
});
document.getElementById("clearBtn").addEventListener("click", () => {
  state.search = ""; state.category = ""; state.winner = "";
  document.getElementById("search").value = "";
  catFilter.value = ""; winnerFilter.value = "";
  renderAll();
});

function renderAll() {
  renderSummary();
  renderTable();
  const active = document.querySelector(".tab.active").dataset.view;
  if (active === "category")  renderCatChart();
  if (active === "histogram") renderHist();
  if (active === "scatter")   renderScatter();
  if (active === "topbottom") renderTopBottom();
}

renderAll();
</script>
</body>
</html>
"""

OUT.write_text(HTML.replace("__DATA__", data_json))
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(rows)} constituencies embedded)")
