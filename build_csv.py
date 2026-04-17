"""Build Reform UK per-constituency win-likelihood CSV from the More in Common April 2026 MRP."""
import csv
import math
import openpyxl

SRC = "apr26-mrp-datatables.xlsx"
OUT = "reform_constituency_predictions.csv"

# σ on the margin between two parties in a typical MRP point estimate.
# MRP credible intervals per seat are usually ~±3-5pp per share;
# difference of two shares has σ ≈ 4pp. Used to map margin → P(win) via Φ.
SIGMA = 4.0

def phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def categorise(p):
    if p >= 0.85: return "Safe Reform"
    if p >= 0.60: return "Likely Reform"
    if p >= 0.40: return "Toss-up"
    if p >= 0.15: return "Lean Against"
    return "Safe Against"

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb["Results"]
rows = list(ws.iter_rows(values_only=True))
header = rows[0]
data = rows[1:]

party_cols = {p: header.index(p) for p in [
    "Conservative", "Labour", "Liberal Democrat", "Reform UK",
    "The Green Party", "Scottish National Party (SNP)", "Plaid Cymru", "Other",
]}
win_col = header.index("Winner")
const_col = header.index("Constituency")

out_rows = []
for r in data:
    if r[const_col] is None:
        continue
    name = r[const_col]
    shares = {p: (r[i] or 0.0) for p, i in party_cols.items()}
    winner = r[win_col]
    reform = shares["Reform UK"]
    others = {p: v for p, v in shares.items() if p != "Reform UK"}
    top_other_party = max(others, key=others.get)
    top_other_share = others[top_other_party]
    margin = reform - top_other_share  # positive => Reform leads
    p_win = phi(margin * 100.0 / SIGMA)  # shares are fractions; convert to pp
    out_rows.append({
        "constituency": name,
        "projected_winner": winner,
        "reform_share_pct": round(reform * 100, 2),
        "top_competitor": top_other_party,
        "top_competitor_share_pct": round(top_other_share * 100, 2),
        "margin_pp": round(margin * 100, 2),
        "reform_win_probability": round(p_win, 3),
        "likelihood_category": categorise(p_win),
        "con_pct": round(shares["Conservative"] * 100, 2),
        "lab_pct": round(shares["Labour"] * 100, 2),
        "libdem_pct": round(shares["Liberal Democrat"] * 100, 2),
        "green_pct": round(shares["The Green Party"] * 100, 2),
        "snp_pct": round(shares["Scottish National Party (SNP)"] * 100, 2),
        "plaid_pct": round(shares["Plaid Cymru"] * 100, 2),
        "other_pct": round(shares["Other"] * 100, 2),
    })

out_rows.sort(key=lambda x: -x["reform_win_probability"])

fields = list(out_rows[0].keys())
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

n = len(out_rows)
reform_wins = sum(1 for r in out_rows if r["projected_winner"] == "Reform UK")
safe = sum(1 for r in out_rows if r["likelihood_category"] == "Safe Reform")
likely = sum(1 for r in out_rows if r["likelihood_category"] == "Likely Reform")
tossup = sum(1 for r in out_rows if r["likelihood_category"] == "Toss-up")
print(f"Rows written: {n}")
print(f"Projected Reform wins (point estimate): {reform_wins}")
print(f"Safe Reform:   {safe}")
print(f"Likely Reform: {likely}")
print(f"Toss-up:       {tossup}")
print(f"Expected Reform seats (sum of P(win)): {sum(r['reform_win_probability'] for r in out_rows):.1f}")
