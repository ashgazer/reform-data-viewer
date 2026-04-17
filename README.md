# Reform UK constituency win-likelihood — project summary

## Files produced

| File | Purpose |
| --- | --- |
| `apr26-mrp-datatables.xlsx` | Raw MRP data from More in Common — April 2026 (downloaded) |
| `ec_jan2026.xlsx` | Raw MRP data from Electoral Calculus — January 2026 (downloaded) |
| `ge2024_results.csv` | HoC Library 2024 GE results by constituency (downloaded) |
| `constituencies.geojson` | ONS 2024 Westminster constituency boundaries (BUC, all 650 seats) |
| `build_csv.py` | Joins all three sources, derives per-seat σ and win probability |
| `reform_constituency_predictions.csv` | 631 GB constituencies, all derived columns |
| `build_html.py` | Embeds the CSV as JSON into a self-contained dashboard |
| `reform_dashboard.html` | Interactive dashboard — open directly in a browser |
| `build_map.py` | Merges boundaries + predictions into a self-contained Leaflet map |
| `reform_map.html` | Choropleth map — open directly in a browser |

## Data sources

Four independent inputs are combined:

### 1. More in Common — April 2026 MRP (primary voting intention)

**What an MRP is.** A standard voting-intention poll of ~2,000 people can't say anything reliable about any single constituency — there might be only three respondents per seat. An MRP (Multilevel Regression and Post-stratification) solves this in two steps:

1. **Multilevel regression.** Fit a model of vote choice as a function of respondent demographics (age, education, ethnicity, housing tenure, past vote, region, etc.) across a much larger sample — typically 10,000–40,000 respondents.
2. **Post-stratification.** For every one of the 650 constituencies, use census / commercial microdata on its demographic makeup to apply the model and produce a seat-level vote-share estimate.

MRPs famously called Labour's 2017 underperformance and the Conservatives' 2019 majority more accurately than conventional poll aggregation.

**Why More in Common April 2026 specifically.**

- **Most recent GB-wide MRP** at time of writing (April 2026 fieldwork).
- **Per-seat downloadable data.** Publishes `apr26-mrp-datatables-final.xlsx` — the `Results` sheet has 631 rows × 10 columns: `Constituency`, 8 party vote shares (fractions 0–1), and `Winner`.
- **Reputable non-partisan pollster** — MRPs are referenced by BBC, FT, Guardian.
- No Northern Ireland (standard for GB pollsters; NI has a separate party system).

### 2. Electoral Calculus — January 2026 MRP (second opinion)

Added so that "uncertainty" can be **observed** rather than assumed. Electoral Calculus is a long-standing election modeller publishing a periodic MRP. File: `DataTables_VIDec2025.xlsx`.

- **Different methodology, same format.** EC uses their own MRP pipeline; a different point estimate per seat.
- **~3 months older** than the MiC data. The time gap means pollster-vs-pollster disagreement reflects both methodology differences and genuine polling movement. That's acceptable — both are signal for how wide real uncertainty is.
- **Header location:** the `Seats` sheet has headers on row 19, data from row 20. Columns used: `Seat Name` (B), `CON` `LAB` `LIB` `Reform` `Green` `YP` `SNP/Plaid` `Minor` `Indep/Other` (D–L), `Predicted Winner (with TV)` (N).

### 3. House of Commons Library — 2024 general election results (baseline)

Official 2024 GE results by constituency. File: `HoC-GE2024-results-by-constituency.csv`. Used to compute **Reform's 2024 baseline vote share per seat** and the **swing from 2024 → 2026 MRP mean**.

- Column `RUK` = Reform UK vote count; divided by `Valid votes` gives baseline share.
- `First party` gives the 2024 winner for context in tooltips.

### 4. ONS — 2024 Westminster constituency boundaries (map geometry)

The map uses official **ONS Westminster Parliamentary Constituencies (July 2024) — Boundaries UK BUC** (ultra-generalised, ~1.6 MB). Pulled from the ONS ArcGIS FeatureServer as GeoJSON.

- Covers all 650 seats. Join key: `PCON24NM` (constituency name).
- BUC = most-generalised variant. Swap for BGC or BFC in `build_map.py` if you want higher-fidelity boundaries (at the cost of a larger HTML payload).

### Name-matching — the non-trivial bit

Each source uses slightly different constituency names. Fixing this was the main glue code:

- **Direction ordering.** MiC uses "East Hampshire"; EC uses "Hampshire East". `name_variants()` tries swapping the leading or trailing direction on each " and "-separated clause. Directions recognised: north / south / east / west / mid / central / upper / lower.
- **Parentheticals.** EC has `Caerfyrddin (Carmarthen)` and `Ynys Mon (Anglesey)`. Stripped before matching.
- **Diacritics.** `Ynys Môn` is normalised to `ynysmon` via `unicodedata.normalize("NFKD")`.
- **Hand-coded aliases** for genuine edge cases that don't fit any rule:
  - `Kingston upon Hull East` ↔ `Hull East` (and two sister Hull seats)
  - `City of Durham` ↔ `Durham, City of`
  - `The Wrekin` ↔ `Wrekin, The`
  - `Mid and South Pembrokeshire` ↔ `Pembrokeshire Mid and South`

**Result:** 631 / 631 MiC seats matched to both EC and 2024 HoC — zero unmatched.

## Methodology — calculating the Reform win likelihood

The goal is a per-seat probability `P(Reform wins seat i)`, `i ∈ {1, …, 631}`.

### Why a proxy is necessary

A proper MRP posterior would give this directly — sample the multilevel model many times, count the share of draws in which Reform has the highest projected vote in seat *i*, and report that fraction. **Neither MiC nor EC publishes posterior draws** — just point estimates. So the pipeline reconstructs uncertainty from (a) a Normal approximation and (b) cross-pollster disagreement.

### The approach: Normal approximation on the mean margin

For each seat *i*, combining both MRPs:

- `r_mic_i`, `r_ec_i` — projected Reform vote shares (MiC and EC)
- `c_mic_i`, `c_ec_i` — share of the top non-Reform competitor in each MRP
- `m_mic_i = r_mic_i − c_mic_i`, `m_ec_i = r_ec_i − c_ec_i` — Reform margin per MRP
- `m̄_i = mean(m_mic_i, m_ec_i)` — **mean margin** (point estimate)
- `d_i = |m_mic_i − m_ec_i|` — **observed cross-pollster disagreement** (pp)

Then:

```
P(Reform wins seat i) = Φ( m̄_i × 100 / σ_i )
```

where `Φ` is the standard Normal CDF (computed via `math.erf`), and `σ_i` is a **per-seat** uncertainty derived from disagreement (next).

### The new bit: empirical, per-seat σ

**Old approach:** σ = 4 pp, assumed.

**New approach:** σ_i is computed from data.

Step 1 — the **floor**, from the whole-set RMS of pollster margin disagreement:

```
σ_floor = RMS({ d_i : i ∈ matched seats }) / √2
```

The `/ √2` comes from the fact that `|m_1 − m_2|` has SD ≈ `σ_margin × √2` when each margin estimate has SD `σ_margin`. Running this on the 631 matched seats gives:

- RMS disagreement: **9.04 pp**
- σ_floor: **6.39 pp**

Step 2 — add **per-seat** variance when the two MRPs disagree strongly on *this* seat:

```
σ_i = √(σ_floor² + (d_i / √2)²)
```

A seat where the two pollsters closely agree gets `σ_i ≈ σ_floor`. A seat where they differ wildly gets a larger σ_i, expanding the uncertainty band and pulling the probability toward 50%.

### Why σ jumped from 4 to ~6.4

The new σ_floor is higher than the 4 pp textbook figure because:

- **3 months of real polling movement** between EC (Jan 2026) and MiC (Apr 2026). Some share of the disagreement is genuine change in voter intention, not methodological noise.
- **Different MRP implementations** (different covariates, different post-stratification frames) genuinely produce different seat-level estimates even at the same fieldwork date.

The higher σ is therefore a more honest reflection of real modelling + temporal uncertainty than the 4-pp placeholder.

### Why a Normal approximation on the margin

1. **Two-party limit of a proper MRP.** When the race is effectively Reform vs. one challenger, whether Reform wins is fully determined by the sign of the margin. A Normal posterior on the margin gives `P(margin > 0) = Φ(m / σ)`.
2. **Monotone in the margin** — a bigger lead gives a higher probability.
3. **Calibrated at the boundary** — tied race (m = 0) gives exactly 50%.

### Pipeline step-by-step (inside `build_csv.py`)

1. **Load MiC** `Results` sheet — per-seat vote shares + projected winner.
2. **Load EC** `Seats` sheet from row 20 — per-seat vote shares + projected winner.
3. **Load 2024 HoC results** — per-seat Reform vote share and actual winner.
4. **Name-match** across all three via normalised name + direction-swap + alias table. 631 / 631 matched.
5. **Compute σ_floor** from whole-set cross-pollster margin disagreement.
6. For each seat:
   - `top_competitor`, `top_competitor_share` = MiC argmax of non-Reform shares.
   - `margin_mic`, `margin_ec`, `m̄`.
   - `σ_i = √(σ_floor² + (d_i/√2)²)`.
   - `reform_win_probability = Φ(m̄ × 100 / σ_i)`.
   - `likelihood_category` via fixed bands.
   - `reform_swing_pp = (r̄ − r_2024) × 100`.
7. **Emit** one CSV row per seat with all of the above.

### Category bands

| Category | Probability range | Intuition |
| --- | --- | --- |
| Safe Reform | ≥ 85% | Reform almost certain to win |
| Likely Reform | 60–85% | Reform favoured but not certain |
| Toss-up | 40–60% | Genuinely uncertain — could go either way |
| Lean Against | 15–40% | Reform in contention but behind |
| Safe Against | < 15% | Reform not competitive |

40–60% is symmetric around 50%; the 15/85 thresholds follow the Cook Political Report "safe seat" convention.

### Validation

- **Sum of per-seat probabilities vs. point-estimate seat count.** Σ `reform_win_probability` = **327.7**. MiC point-estimate Reform seats = **324**; EC = **335**; average = **329.5**. The summed-probability is within ~2 seats of the pollster average — consistent.
- **Headline match (MiC).** MiC press-release headline: "324 seats — one short of a majority." Pipeline's MiC projected-winner count prints 324. Faithful to source.
- **Headline match (EC).** EC Jan 2026 headline: 335 Reform seats. Pipeline's EC projected-winner count prints 335. Also faithful.
- **Agreement.** Both MRPs agree on Reform winning in **275 seats**. Agreement on winner regardless of party: **522 seats** (pollsters disagree on 109).

### What this is *not*

- **Not the MRPs' own posterior.** A true MRP probability would be derived from multilevel-model draws. The Normal-margin proxy still overstates certainty for very safe seats.
- **Not a forecast.** It's two MRP snapshots averaged — a read of early-2026 voting intention, not a call on the next election.
- **Not a two-party model only.** The "top competitor" is whichever party is highest, so three- and four-way races are handled at the point-estimate level — but the Normal approximation is weakest in multi-party marginals where more than two parties could plausibly win.
- **Not independent across seats.** Each seat's probability is computed independently; a correlated national Reform over- or under-performance would move all seats together.

### Caveats, in short

- **σ has a meaningful floor (~6.4 pp).** Seats with very narrow leads look like toss-ups, not safe wins.
- **Time gap** between MiC (Apr 2026) and EC (Jan 2026) inflates σ — part of the disagreement is real movement, not noise. A fresher EC MRP would tighten uncertainty.
- **No Northern Ireland.** Add ~18 seats (DUP / Sinn Féin / SDLP / Alliance / UUP) for a full Commons picture.
- **No Chorley.** The Speaker's seat is uncontested by major parties and excluded from both MRPs.
- **Snapshot.** Reflects MRP fieldwork as of early April 2026 / January 2026.

## Headline numbers

- **MiC projected Reform wins:** 324
- **EC projected Reform wins:** 335
- **Both MRPs agree Reform wins:** 275
- **Pollsters disagree on winner:** 109 seats
- **Expected Reform seats (ΣP):** 327.7
- Safe Reform: 173 · Likely: 117 · Toss-up: 75 · Lean Against: 103 · Safe Against: 163
- **Cross-pollster margin RMS disagreement:** 9.04 pp → **σ_floor ≈ 6.4 pp**

## CSV schema (`reform_constituency_predictions.csv`)

| Column | Meaning |
| --- | --- |
| `constituency` | Westminster constituency name (MiC's spelling) |
| `projected_winner_mic` | MiC MRP projected winning party |
| `projected_winner_ec` | EC MRP projected winning party (uses EC's naming e.g. "Reform", "LAB") |
| `winners_agree` | `yes` / `no` — do both MRPs agree on the winning party? |
| `reform_share_mean_pct` | Mean of MiC + EC Reform projected share |
| `reform_share_mic_pct` | MiC Reform projected share |
| `reform_share_ec_pct` | EC Reform projected share |
| `reform_share_2024_pct` | Actual Reform UK share in the 2024 GE |
| `reform_swing_pp` | Mean share − 2024 share (positive = Reform gained) |
| `top_competitor` | Highest-scoring non-Reform party in MiC |
| `top_competitor_share_pct` | That competitor's MiC share |
| `margin_mean_pp` | Mean of MiC + EC Reform margin over top competitor |
| `margin_mic_pp`, `margin_ec_pp` | Per-pollster margins |
| `sigma_pp` | Per-seat σ = √(σ_floor² + (d/√2)²) |
| `reform_win_probability` | Φ(margin_mean × 100 / σ), 0–1 |
| `likelihood_category` | Safe / Likely / Toss-up / Lean Against / Safe Against |
| `con_pct`, `lab_pct`, `libdem_pct`, `green_pct`, `snp_pct`, `plaid_pct`, `other_pct` | Other-party shares (MiC) |
| `winner_2024` | Party that actually won the seat in 2024 |

## Dashboard (`reform_dashboard.html`)

Self-contained HTML — double-click to open, no server needed. Embeds the full CSV as JSON at build time.

- **11 summary cards** — seats filtered, MiC Reform wins, EC Reform wins, both-agree count, pollsters-disagree count, ΣP, five category counts. Clickable category cards act as filters.
- **Filters**: free-text search, category, MiC winner dropdown, MRP-agreement dropdown (agree / disagree / any).
- **Seven tabbed views**, all filter-aware:
  1. **Table** — sortable on any column, 12 columns including swing, σ, both pollster winners, agreement badge.
  2. **Category breakdown** — bar chart.
  3. **Reform vote share distribution** — histogram on mean share (2pp bins).
  4. **Margin vs share** — scatter, coloured by MiC winner.
  5. **MRP agreement** — scatter of MiC margin × EC margin, agree-quadrant vs disagree-quadrant split.
  6. **Swing from 2024** — histogram (red below zero, teal above zero).
  7. **Safest / closest seats** — top 20 safest Reform seats + 20 tightest Reform-projected seats.

## Map (`reform_map.html`)

Self-contained Leaflet choropleth of all 650 UK constituencies.

- **Boundaries**: ONS 2024 BUC GeoJSON embedded inline.
- **Five colour modes** (side panel):
  1. **Projected winner (MiC)** — categorical, each party's brand colour.
  2. **P(Reform wins)** — sequential gradient 0 → 1.
  3. **Reform vote share %** — sequential gradient 0 → 60%.
  4. **Swing from 2024** — diverging gradient (red = Reform lost ground, teal = Reform gained).
  5. **MRP agreement** — teal = both MRPs agree, red = pollsters disagree.
- **Legend** updates per mode (seat counts for categorical modes; gradient scale for continuous).
- **Hover panel** shows both pollster winners, agreement status, Reform share, 2024 baseline, swing, margin ± σ, P(win), category.
- **Click to zoom** on a seat; Leaflet pan/zoom otherwise.
- **No base tiles** — pure choropleth on a flat dark background. Add `L.tileLayer(...)` in `build_map.py` for a road/terrain basemap.

## Tech stack

### Data pipeline (Python, build-time)

| Tool | Role |
| --- | --- |
| **`openpyxl`** | Reads both MRP `.xlsx` files. Only non-stdlib dep. |
| **`csv`** (stdlib) | Parses the HoC Library 2024 results and writes the predictions CSV. |
| **`json`** (stdlib) | Serialises predictions + GeoJSON into the inline `<script>` payloads in the HTML files — no runtime fetches. |
| **`math.erf`** (stdlib) | Backs the Normal CDF used for the probability proxy. No SciPy dependency. |
| **`re`** (stdlib) | Normalises names and swaps directions in `name_variants()`. |
| **`unicodedata`** (stdlib) | Strips diacritics for Welsh names (`Môn` → `Mon`). |
| **`curl`** | Downloads the two xlsx files, the 2024 CSV, and the ONS GeoJSON. |

### Dashboard front end (`reform_dashboard.html`)

| Library | Role |
| --- | --- |
| **Chart.js 4.4** (CDN, UMD build) | Category bar chart, histograms (share & swing), two scatter plots (margin-vs-share and MRP agreement). Canvas-based, handles 631 points smoothly. |
| **Vanilla JS + DOM APIs** | State management (filters / sort / agreement filter), table rendering, summary cards, tab switching. No framework. |
| **Plain CSS with custom properties** | Dark theme, responsive summary-card grid, sticky table header, colour-coded category badges, swing/agree text colouring. |

### Map front end (`reform_map.html`)

| Library | Role |
| --- | --- |
| **Leaflet 1.9.4** (CDN) | Projection, pan/zoom, polygon rendering, hover/click events, tooltips. `preferCanvas: true` draws 650 polygons to one Canvas instead of 650 SVG nodes. |
| **`L.geoJSON`** | Ingests the embedded GeoJSON; `style` is re-computed on every mode change via `layer.setStyle(styleFor)`. |
| **Vanilla JS for everything else** | Mode switching, legend rebuild, hover info panel. |
| **Inline GeoJSON + predictions** | Both are JSON literals in the HTML. Output is ~1.85 MB — opens on `file://` with no server or CORS. |

### Why this architecture

- **Single-file HTML outputs** — double-click to open. No `python -m http.server`, no CORS, no build tool. Cost: heavier initial page weight (~400 KB dashboard, ~1.85 MB map), fine on any modern connection.
- **Python at build time, vanilla JS at runtime** — output pages are dependency-light and trivially hostable (S3, GitHub Pages, email attachment). Python scripts are the reproducible source of truth.
- **CDN libraries** (Chart.js, Leaflet) — two stable URLs. Swap to vendored copies if offline use matters.
- **σ as a single line in `build_csv.py`** — changing the uncertainty model is a one-place edit.

## Reproducing

```bash
python3 build_csv.py       # joins the 3 data sources, emits the CSV
python3 build_html.py      # regenerates the dashboard from the CSV
python3 build_map.py       # regenerates the map from the CSV + GeoJSON
open reform_dashboard.html # macOS — the dashboard
open reform_map.html       # macOS — the map
```

To refresh the underlying data:

- **New MiC MRP:** replace `apr26-mrp-datatables.xlsx` with the newer xlsx.
- **New EC MRP:** replace `ec_jan2026.xlsx` (update `EC_XLSX` in `build_csv.py` if renaming).
- **2024 baseline** rarely changes but the CSV is pinned in HoC Library's CBP-10009 briefing.

Then re-run the three scripts.
