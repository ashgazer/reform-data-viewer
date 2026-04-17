# Reform UK constituency win-likelihood — project summary

## Files produced

| File | Purpose |
| --- | --- |
| `apr26-mrp-datatables.xlsx` | Raw MRP data from More in Common (downloaded) |
| `constituencies.geojson` | ONS 2024 Westminster constituency boundaries (BUC, all 650 seats) |
| `build_csv.py` | Reads the xlsx, derives win probability, writes the CSV |
| `reform_constituency_predictions.csv` | 631 GB constituencies with per-seat projections |
| `build_html.py` | Embeds the CSV as JSON into a self-contained dashboard |
| `reform_dashboard.html` | Interactive dashboard — open directly in a browser |
| `build_map.py` | Merges boundaries + predictions into a self-contained Leaflet map |
| `reform_map.html` | Choropleth map — open directly in a browser |

## Data sources

Two independent inputs are combined:

### 1. Voting intention — More in Common April 2026 MRP

The projections come from **More in Common's April 2026 Multilevel Regression and Post-stratification (MRP) model**.

**What an MRP is.** A standard voting-intention poll of ~2,000 people can't say anything reliable about any single constituency — there might be only three respondents per seat. An MRP solves this in two steps:

1. **Multilevel regression.** Fit a model of vote choice as a function of respondent demographics (age, education, ethnicity, housing tenure, past vote, region, etc.) across a much larger sample — typically 10,000–40,000 respondents.
2. **Post-stratification.** For every one of the 650 constituencies, use census / commercial microdata on its demographic makeup to apply the model and produce a seat-level vote-share estimate.

MRPs famously called Labour's 2017 underperformance and the Conservatives' 2019 majority more accurately than conventional poll aggregation.

**Why More in Common April 2026 specifically.**

- **Most recent GB-wide MRP.** Published April 2026. Earlier MRPs (Electoral Calculus Jan 2026, More in Common Jan 2026, Electoral Calculus Oct 2025) had meaningfully different Reform numbers — polling has plateaued, so stale data would overstate Reform's position.
- **Provides per-seat data.** Many polling outputs are national-only; More in Common publishes a downloadable `.xlsx` with vote share for each party in each of the 631 GB seats plus a projected winner — the exact granularity needed.
- **Reputable methodology.** More in Common is a mainstream non-partisan polling organisation whose MRPs are referenced by the BBC, FT and Guardian.

**What the raw file contains.** `apr26-mrp-datatables.xlsx` has two sheets:

- `Cover page` — methodology notes, ignored by the pipeline.
- `Results` — 631 rows × 10 columns: `Constituency`, `Conservative`, `Labour`, `Liberal Democrat`, `Reform UK`, `The Green Party`, `Scottish National Party (SNP)`, `Plaid Cymru`, `Other`, `Winner`. Vote shares are fractions (0–1); `Winner` is the party with the highest projected share.

**What's *not* in it.** No Northern Ireland seats (More in Common, like most GB pollsters, doesn't model NI — its party system is separate). No raw posterior draws or uncertainty intervals — just point estimates. This is the central data limitation and drives the methodology choice below.

### 2. Constituency boundaries — ONS 2024

The map uses official **Office for National Statistics Westminster Parliamentary Constituencies (July 2024) — Boundaries UK BUC** (Building Ultra-Generalised Clipped). Downloaded from the ONS ArcGIS FeatureServer as GeoJSON.

- All 650 constituencies as defined for the 2024 general election.
- "BUC" is the most-generalised / smallest variant — coastlines are simplified, file is ~1.6 MB. Sufficient for a web map; switch to BGC or BFC in `build_map.py` if you need higher-fidelity boundaries.
- Join key: `PCON24NM` (constituency name), normalised to lowercase-alphanumeric to match the MRP file. 631 clean matches; 19 un-joined (18 NI + Chorley/Speaker).

## Methodology — calculating the Reform win likelihood

The goal is a per-seat probability `P(Reform wins seat i)`, `i ∈ {1, …, 631}`.

### Why a proxy is necessary

A proper MRP posterior would give this directly — sample the multilevel model many times, count the share of draws in which Reform has the highest projected vote in seat *i*, and report that fraction. **More in Common publishes point estimates only**, not posterior draws. So the pipeline has to *reconstruct* uncertainty from the point estimates alone.

### The approach: Normal approximation on the margin

For each seat, let

- `r_i` = projected Reform UK vote share
- `c_i` = projected share of the strongest non-Reform party (the "top competitor")
- `m_i = r_i − c_i` = Reform's margin over the top competitor, in percentage points (positive ⇒ Reform leads).

Model the uncertainty on `m_i` as Normal with standard deviation `σ`:

```
P(Reform wins seat i) ≈ Φ( m_i / σ )
```

where `Φ` is the standard Normal cumulative distribution function. Computed in Python via `math.erf`:

```python
def phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
```

### Why this form

1. **It's the two-party limit of a proper MRP probability.** In a race where the outcome is effectively Reform vs. one challenger (true for most seats here), whether Reform wins is fully determined by the sign of `m_i`. If the posterior on `m_i` is roughly Normal — which MRPs empirically are for large enough samples — then `P(m_i > 0) = Φ(m_i / σ)`.
2. **It's monotone in the margin.** A 10-point lead yields a higher probability than a 2-point lead, as it should.
3. **It's calibrated at the boundary.** At `m_i = 0` (tied race) the formula gives exactly 50%, matching intuition.

### Choice of σ

σ is the only free parameter. It represents the standard deviation of the *difference between two parties' projected vote shares* at the seat level.

- Published MRPs typically report ~±3–5 pp credible intervals on individual party shares per seat. The standard deviation of the difference of two such estimates (allowing for modest positive correlation between errors) lands around **4 pp**.
- σ = 4 is used throughout. It's an explicit assumption, set in one place at the top of `build_csv.py`.
- **Sensitivity**: with σ = 3, safe bands widen (more seats called confidently) and toss-ups shrink. With σ = 6, more seats slide into toss-up / lean — the map looks messier. The point-estimate winner is unaffected; only the confidence around it moves.

### Pipeline step-by-step (inside `build_csv.py`)

For each of the 631 seats:

1. **Load** all projected vote shares from the `Results` sheet (8 party columns) and the published `Winner`.
2. **Compute** `top_competitor` = `argmax` of the non-Reform shares, and `top_competitor_share`.
3. **Compute** `margin_pp = (r − c) × 100` (convert from fraction to percentage points so σ = 4 works in natural units).
4. **Compute** `reform_win_probability = Φ(margin_pp / σ)` with σ = 4.
5. **Categorise** using fixed bands (below).
6. **Emit** one CSV row with the projected winner, Reform share, competitor, margin, probability, category, and all other-party shares.

The row sort and `projected_winner` column come from the MRP itself; only the probability and category are derived.

### Category bands

| Category | Probability range | Intuition |
| --- | --- | --- |
| Safe Reform | ≥ 85% | Reform almost certain to win |
| Likely Reform | 60–85% | Reform favoured but not certain |
| Toss-up | 40–60% | Genuinely uncertain — could go either way |
| Lean Against | 15–40% | Reform in contention but behind |
| Safe Against | < 15% | Reform not competitive |

The 40–60% toss-up band is intentionally symmetric around 50%. The outer 15%/85% thresholds are the common "safe seat" convention used by e.g. Cook Political Report in the US.

### Validation

Two sanity checks:

- **Sum of per-seat probabilities vs. point-estimate seat count.** Σ `reform_win_probability` = **321.9**. Published MRP point-estimate seats for Reform = **324**. A gap of ≈2 seats is expected because the probability-based estimate penalises narrow 1-point leads (reduced to ~60% not 100%) and rewards narrow 1-point deficits (raised to ~40% not 0%) — these average out but not exactly.
- **Headline match.** More in Common's press release headline: "324 seats — one short of a majority." The pipeline's `Reform point-estimate wins` output also prints 324. Point-estimate computation is therefore faithful to the source.

### What this is *not*

- **Not the MRP's own posterior.** A true MRP probability would be derived from the multilevel model's draws, not reconstructed from the point estimate. The proxy overstates certainty at the tails (Safe Reform seats collapse to ~1.0; Safe Against to ~0.0) and understates the role of correlated errors across seats (a national Reform under-performance would lower *all* probabilities, not each independently).
- **Not a forecast.** It's the MRP's snapshot of current voting intention expressed as win likelihoods. Treat it as a read of April 2026 sentiment, not a call on the next election.
- **Not a two-party model only.** In multi-party seats (Scotland with SNP, Wales with Plaid, LD-facing Con seats) the "top competitor" is whichever party is highest, so three- and four-way races are handled correctly at the point-estimate level — but the Normal margin approximation is weakest here, because more than two parties can plausibly win.

### Caveats, in short

- **σ = 4 pp is an assumption** — real uncertainty is heteroscedastic.
- **Point estimate vs probability band can disagree** at the edges — e.g. Reform leading by 1 pp is projected to win but flagged "Likely" rather than "Safe".
- **No Northern Ireland.** Add ~18 seats (mostly DUP / Sinn Féin / SDLP / Alliance) for a full Commons picture.
- **No Chorley.** The Speaker's seat is uncontested by major parties by convention and excluded from the MRP.
- **Snapshot.** Reflects MRP fieldwork through early April 2026.

## Headline numbers

- Reform point-estimate wins: **324** (one short of a majority — matches the published MRP headline)
- Expected Reform seats (Σ of per-seat probabilities): **321.9**
- Safe Reform: 240 · Likely Reform: 63 · Toss-up: 49

## CSV schema (`reform_constituency_predictions.csv`)

| Column | Meaning |
| --- | --- |
| `constituency` | Westminster constituency name |
| `projected_winner` | MRP point-estimate winning party |
| `reform_share_pct` | Projected Reform UK vote share |
| `top_competitor` | Highest-scoring non-Reform party |
| `top_competitor_share_pct` | That competitor's projected share |
| `margin_pp` | Reform share − top competitor share (pp; positive = Reform leads) |
| `reform_win_probability` | Normal-CDF proxy, 0–1 |
| `likelihood_category` | Safe / Likely / Toss-up / Lean Against / Safe Against |
| `con_pct`, `lab_pct`, `libdem_pct`, `green_pct`, `snp_pct`, `plaid_pct`, `other_pct` | Projected vote share for each other party |

## Dashboard (`reform_dashboard.html`)

Self-contained HTML — no server needed, no build step, works offline except for the Chart.js CDN. Features:

- **8 summary cards** (click category cards to filter)
- **Filters**: free-text search, category, projected-winner dropdown
- **Views**:
  - Sortable table of all 631 seats with probability bars
  - Category breakdown bar chart
  - Reform vote share histogram (2pp bins)
  - Margin-vs-share scatter, coloured by projected winner
  - Top-20 safest Reform seats and closest Reform-projected seats

All views respect the active filters.

## Map (`reform_map.html`)

Self-contained Leaflet choropleth of all 650 UK constituencies.

- **Boundaries** are ONS 2024 Westminster constituencies (ultra-generalised "BUC" version, ~1.6 MB GeoJSON) fetched from the ONS ArcGIS FeatureServer.
- **Name join** against the CSV is on a normalised key (lowercase, alphanumerics only). 631 seats match cleanly; 19 are shown grey (18 Northern Ireland seats not covered by the MRP, plus Chorley — the Speaker's seat is traditionally excluded from MRP projections).
- **Three colour modes** (toggle in the side panel):
  1. **Projected winner** — categorical, using each party's brand colour (Reform teal, Labour red, Conservative blue, Lib Dem orange, SNP yellow, Green, Plaid).
  2. **P(Reform wins)** — sequential gradient 0 → 1.
  3. **Reform vote share %** — sequential gradient 0 → 60%.
- **Interaction**: hover for a detail panel on the right, click to zoom to the constituency, Leaflet's native pan/zoom otherwise.
- **No base tiles** — the choropleth is drawn on a flat dark background to keep the page offline-safe and fast. Swap in `L.tileLayer(...)` in `build_map.py` if you want a road/terrain basemap.

## Tech stack

### Data pipeline (Python, build-time)

| Tool | Role |
| --- | --- |
| **`openpyxl`** | Reads the MRP's `.xlsx` file into Python in `build_csv.py`. |
| **`csv`** (stdlib) | Writes the predictions CSV and reads it back in the HTML/map builders. |
| **`json`** (stdlib) | Serialises the predictions and GeoJSON into the inline `<script>` payloads in the HTML files, so the output pages have no runtime data fetches. |
| **`math.erf`** (stdlib) | Backs the Normal CDF used to convert vote-share margins into the win-probability proxy. No SciPy dependency. |
| **`re`** (stdlib) | Normalises constituency names for the CSV-to-GeoJSON join. |
| **`curl`** | Downloads the raw MRP Excel file and the ONS GeoJSON in one-shot commands. |

The pipeline is deliberately dependency-light — only `openpyxl` is non-stdlib — so the scripts re-run with no virtualenv setup.

### Dashboard front end (`reform_dashboard.html`)

| Library | Role |
| --- | --- |
| **Chart.js 4.4** (CDN, UMD build) | Renders the category bar chart, vote-share histogram, and margin-vs-share scatter plot. Canvas-based, so it handles 631 points smoothly without the DOM overhead of SVG. |
| **Vanilla JS + DOM APIs** | Everything else: state management (filters/sort), table rendering, summary cards, tab switching. No framework — the page is <250 KB of HTML/JS with Chart.js loaded from CDN. |
| **Plain CSS with custom properties** | Dark theme, responsive grid for the summary cards, sticky table header, colour-coded category badges. No Tailwind/Bootstrap. |

Data lives in a single `const DATA = [...]` array baked into the HTML at build time, so filters/sorts/chart rebuilds are pure in-memory operations — no network, no storage.

### Map front end (`reform_map.html`)

| Library | Role |
| --- | --- |
| **Leaflet 1.9.4** (CDN) | Renders the interactive map: projection, pan/zoom, polygon rendering, hover/click events, tooltips. Uses `preferCanvas: true` so the 650 polygons draw via a single Canvas layer rather than 650 SVG nodes — faster and lighter on memory. |
| **`L.geoJSON`** | Ingests the embedded GeoJSON and binds the `style` and `onEachFeature` callbacks. `style` is a function of the current colour mode, so swapping modes is just `layer.setStyle(styleFor)`. |
| **No base tile layer** | Deliberately omitted: the map works fully offline once loaded, and dropping the tile server removes a ~1 s latency hit and a third-party dependency. |
| **Vanilla JS for mode switching, legend, and hover panel** | No framework. The legend and the right-hand detail card are rebuilt from the same state as the polygon style. |
| **Inline GeoJSON + predictions** | Both the ONS boundaries and the MRP predictions are injected as JSON literals at build time. The resulting 1.7 MB HTML opens on `file://` without CORS or server setup. |

### Why this architecture

- **Single-file HTML outputs** — users can double-click either HTML file and it works; no `python -m http.server`, no CORS, no build tool. The cost is a heavier initial page weight (~240 KB dashboard, ~1.7 MB map), which is a one-time load and negligible on modern connections.
- **Python at build time, vanilla JS at runtime** — keeps the output pages dependency-light and easy to host anywhere (S3, GitHub Pages, email attachment). The Python scripts are the reproducible source of truth.
- **CDN-loaded libraries (Chart.js, Leaflet)** — two small, stable, widely-cached URLs. Swapping to vendored copies is a one-line change if offline use matters.

## Reproducing

```bash
python3 build_csv.py       # regenerates the CSV from the xlsx
python3 build_html.py      # regenerates the dashboard from the CSV
python3 build_map.py       # regenerates the map from the CSV + GeoJSON
open reform_dashboard.html # macOS — the dashboard
open reform_map.html       # macOS — the map
```

To refresh the underlying MRP, replace `apr26-mrp-datatables.xlsx` with a newer file of the same structure from More in Common and re-run the three scripts.
