"""Correlations of year-over-year changes, and derived summaries of the results.

Correlations use 100*ln(V_t/V_t-1) (or the difference, for shares), matching
region and years, flagged values excluded. They describe co-movement only.

Usage: python -m fcp.stats   (writes results/correlations.json and results/summary.json)
"""

import json
import math
import os

from fcp.fetch import ROOT
from fcp.learn import load_series, results_path

CORR_OUT = os.path.join(ROOT, "results", "correlations.json")
SUMMARY_OUT = os.path.join(ROOT, "results", "summary.json")

PAIRS = [
    ("us_crude_rac", "us_gasoline_unleaded", "US"),
    ("us_gasoline_unleaded", "us_motor_gasoline_use", "US"),
    ("us_gasoline_unleaded", "us_transport_co2", "US"),
    ("us_vmt", "us_transport_co2", "US"),
    ("us_motor_gasoline_use", "us_transport_co2", "US"),
    ("us_ev_share", "us_motor_gasoline_use", "US"),
    ("us_motor_gasoline_use", "us_highway_nox", "US"),
    ("us_gasoline_unleaded", "us_ev_share", "US"),
    ("world_brent", "world_ev_share", "World"),
]
SHARE_SERIES = {"us_ev_share", "world_ev_share"}


def yoy(series):
    flags = series["flags"]
    lv = {int(y): v for y, v in series["values"].items() if y not in flags}
    out = {}
    for y in sorted(lv):
        if y - 1 in lv:
            if series["id"] in SHARE_SERIES:
                out[y] = lv[y] - lv[y - 1]
            elif lv[y] > 0 and lv[y - 1] > 0:
                out[y] = 100.0 * math.log(lv[y] / lv[y - 1])
    return out


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def correlations(series):
    out = []
    for a, b, region in PAIRS:
        ca, cb = yoy(series[a]), yoy(series[b])
        years = sorted(set(ca) & set(cb))
        row = {"x": a, "y": b, "x_label": series[a]["label"], "y_label": series[b]["label"], "region": region,
               "n": len(years), "first_year": years[0] if years else None, "last_year": years[-1] if years else None,
               "method": "Pearson r and Spearman rho of year-over-year changes; flagged values excluded"}
        if len(years) >= 3:
            xs, ys = [ca[y] for y in years], [cb[y] for y in years]
            row["pearson_r"] = pearson(xs, ys)
            row["spearman_rho"] = pearson(ranks(xs), ranks(ys))
        out.append(row)
    return out


def vmt_check():
    """Compare the pre-registered VM-203 miles series with FHWA's own VM-1 table."""
    from fcp.parse import vm1_total_vmt, vm203_total_vmt

    a, _ = vm203_total_vmt()
    b = vm1_total_vmt()
    gaps = {y: 100.0 * (a[y] / b[y] - 1.0) for y in b if y in a}
    worst = max(gaps, key=lambda y: abs(gaps[y]))
    others = [abs(g) for y, g in gaps.items() if y != worst]
    out = {"years_compared": len(gaps), "worst_year": worst, "worst_gap_pct": gaps[worst], "max_other_gap_pct": max(others)}
    if worst + 1 in a and worst + 1 in b:
        out["next_year"] = worst + 1
        out["next_change_vm203"] = 100.0 * math.log(a[worst + 1] / a[worst])
        out["next_change_vm1"] = 100.0 * math.log(b[worst + 1] / b[worst])
    return out


def summary(results):
    """Derived, reported-only numbers. Computed from results/learning_results.json."""
    rows = [r for r in results["per_year"] if r["period"] == "holdout" and r["actual_co2"] is not None]
    models = ["graph", "no_change", "knn", "frozen_graph", "direct_regression"]

    def mae_of(rs, m):
        return sum(abs(r[m] - r["actual_co2"]) for r in rs) / len(rs)

    ex = [r for r in rows if r["year"] not in (2020, 2021)]
    no2011 = [r for r in rows if r["year"] != 2011]
    return {
        "holdout_n": len(rows),
        "excluding_2020_2021": {"n": len(ex), **{m: mae_of(ex, m) for m in models}},
        "excluding_2011": {"n": len(no2011), **{m: mae_of(no2011, m) for m in models}},
        "vmt_check": vmt_check(),
        "graph_wins_by_year": {m: sum(1 for r in rows if abs(r["graph"] - r["actual_co2"]) < abs(r[m] - r["actual_co2"])) for m in models if m != "graph"},
        "ev_link_weight_range_2012_on": {
            "min": min(w["FuelUse"]["EVShare->FuelUse"] for y, w in results["link_weights_by_year"].items() if int(y) >= 2012),
            "max": max(w["FuelUse"]["EVShare->FuelUse"] for y, w in results["link_weights_by_year"].items() if int(y) >= 2012),
            "ev_years_used": sum(1 for r in results["per_year"] if r["inputs"].get("EVShare") is not None),
        },
        "largest_graph_errors": sorted(({"year": r["year"], "abs_error": abs(r["graph"] - r["actual_co2"])} for r in rows), key=lambda d: -d["abs_error"])[:3],
    }


def main():
    series = load_series()
    corr = correlations(series)
    with open(CORR_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(corr, f, indent=1)
        f.write("\n")
    with open(results_path(), encoding="utf-8") as f:
        res = json.load(f)
    summ = summary(res)
    with open(SUMMARY_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summ, f, indent=1)
        f.write("\n")
    for c in corr:
        print("%-24s %-24s n=%2d r=%s" % (c["x"], c["y"], c["n"], round(c.get("pearson_r", float("nan")), 3)))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
