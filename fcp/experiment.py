"""Run the pre-registered experiment and write results/learning_results.json.

Usage:
  python -m fcp.experiment                 # HydraDB must be running (scripts/run_hydradb.sh)
  python -m fcp.experiment --memory-only   # no HydraDB; parity part of the rule is then NOT met

Steps (PREREGISTRATION.md): tune on design years only, then one final
walk-forward per model, score the holdout, apply the rule.
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import time

from fcp import learn as L
from fcp.fetch import ROOT
from fcp.hydra import HydraClient, default_token_path
from fcp.stores import HydraStore, MemoryStore


def git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def owned_ids(ch):
    years = range(L.FIRST_YEAR, L.last_year(ch) + 1)
    ids = list(L.VAR_IDS.values()) + [lid for lid, _, _ in L.LINKS] + list(L.FIT_IDS.values())
    ids += [L.link_state_id(lid, y) for lid, _, _ in L.LINKS for y in years]
    ids += [L.prediction_id(t, y) for t in L.TARGETS for y in years]
    return ids


def reset_hydra(client, ch):
    """Clear this project's id range so the run starts from an empty graph."""
    rows = [{"id": i} for i in owned_ids(ch)]
    for i in range(0, len(rows), 1000):
        client.query("UNWIND $rows AS row MATCH (n {id: row.id}) DETACH DELETE n", {"rows": rows[i:i + 1000]})
    probe = list(L.VAR_IDS.values()) + [lid for lid, _, _ in L.LINKS] + list(L.FIT_IDS.values())
    for nid in probe:
        if client.query("MATCH (n {id: $id}) RETURN n.id AS id", {"id": nid}):
            raise RuntimeError("node %d still present after reset" % nid)


def pick(grid_scores, keyfn):
    """Lowest design MAE; ties broken by keyfn (larger wins)."""
    best = min(s for _, s in grid_scores)
    cands = [c for c, s in grid_scores if s == best]
    return max(cands, key=keyfn)


def tune(ch):
    scored = L.scored_years(ch, L.DESIGN_YEARS)
    graph_grid, direct_grid, knn_grid = [], [], []
    for lam in L.LAMBDA_GRID:
        p, _ = L.run_graph(MemoryStore(), ch, lam, write_history=False)
        graph_grid.append((lam, L.mae(p, ch, scored)[0]))
        d = L.run_direct(ch, lam)
        direct_grid.append((lam, L.mae(d, ch, scored)[0]))
    for k in L.K_GRID:
        for w in L.W_GRID:
            p = L.run_knn(ch, k, w)
            knn_grid.append(((k, w), L.mae(p, ch, scored)[0]))
    lam_g = pick(graph_grid, lambda lam: lam)
    lam_d = pick(direct_grid, lambda lam: lam)
    k, w = pick(knn_grid, lambda kw: (kw[0], 10_000 if kw[1] is None else kw[1]))
    return {
        "design_years": scored,
        "graph_lambda": lam_g,
        "direct_lambda": lam_d,
        "knn_k": k,
        "knn_window": w,
        "graph_grid_design_mae": [{"lambda": a, "mae": b} for a, b in graph_grid],
        "direct_grid_design_mae": [{"lambda": a, "mae": b} for a, b in direct_grid],
        "knn_grid_design_mae": [{"k": a[0], "window": a[1], "mae": b} for a, b in knn_grid],
    }


def parity(pa, pb):
    years = sorted(set(pa) | set(pb))
    worst, n, missing = 0.0, 0, 0
    for y in years:
        if y not in pa or y not in pb:
            missing += 1
            continue
        for t in pa[y]:
            worst = max(worst, abs(pa[y][t] - pb[y][t]))
            n += 1
    return {"max_abs_diff": worst, "compared_values": n, "years_missing_in_one_store": missing}


def hydra_counts(client):
    out = {}
    for label in ("Variable", "Link", "Fit", "LinkState", "Prediction"):
        rows = client.query("MATCH (n:%s) RETURN count(*) AS c" % label)
        out[label] = int(rows[0]["c"]) if rows else 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory-only", action="store_true")
    args = ap.parse_args()

    series = L.load_series()
    ch = L.changes(series)
    t0 = time.time()
    tuned = tune(ch)
    lam = tuned["graph_lambda"]

    # Final runs.
    mem_preds, mem_weights = L.run_graph(MemoryStore(), ch, lam)
    hydra = None
    if not args.memory_only:
        client = HydraClient.from_token_file(default_token_path())
        reset_hydra(client, ch)
        th = time.time()
        hy_preds, hy_weights = L.run_graph(HydraStore(client), ch, lam)
        hydra = {
            "seconds": round(time.time() - th, 2),
            "http_requests": client.requests,
            "node_counts": hydra_counts(client),
            "parity": parity(mem_preds, hy_preds),
            "endpoint": "http://127.0.0.1:8443 (local mode, loopback only)",
        }
    graph_preds, graph_weights = (hy_preds, hy_weights) if hydra else (mem_preds, mem_weights)
    frozen_preds, _ = L.run_graph(MemoryStore(), ch, lam, freeze_after=L.FREEZE_AFTER, write_history=False)
    knn_preds = L.run_knn(ch, tuned["knn_k"], tuned["knn_window"])
    nochange_preds = L.run_no_change(ch)
    direct_preds = L.run_direct(ch, tuned["direct_lambda"])

    models = {
        "graph": graph_preds,
        "no_change": nochange_preds,
        "knn": knn_preds,
        "frozen_graph": frozen_preds,
        "direct_regression": direct_preds,
    }
    hold = L.scored_years(ch, L.HOLDOUT_YEARS)
    for name, p in models.items():
        missing = [y for y in hold if y not in p]
        if missing:
            raise RuntimeError("%s has no prediction for holdout years %s" % (name, missing))
    scores = {}
    for name, p in models.items():
        m, n = L.mae(p, ch, hold)
        md, nd = L.mae(p, ch, tuned["design_years"])
        scores[name] = {"holdout_mae": m, "holdout_n": n, "design_mae": md, "design_n": nd}

    secondary = {}
    for target in ("FuelUse", "Gasoline"):
        yrs = L.scored_years(ch, L.HOLDOUT_YEARS, target)
        secondary[target] = {
            "graph_holdout_mae": L.mae(graph_preds, ch, yrs, target)[0],
            "no_change_holdout_mae": L.mae(nochange_preds, ch, yrs, target)[0],
            "n": len(yrs),
        }

    g = scores["graph"]["holdout_mae"]
    nc = scores["no_change"]["holdout_mae"]
    kn = scores["knn"]["holdout_mae"]
    fr = scores["frozen_graph"]["holdout_mae"]
    par = hydra["parity"]["max_abs_diff"] if hydra else None
    rule = [
        {"part": 1, "name": "Parity HydraDB vs in-memory", "threshold": "max abs diff <= 1e-9 pp",
         "value": par, "pass": bool(hydra) and par <= 1e-9 and hydra["parity"]["years_missing_in_one_store"] == 0,
         "margin": None if par is None else 1e-9 - par},
        {"part": 2, "name": "Graph beats no change by 10%", "threshold": "graph MAE <= 0.90 x no-change MAE",
         "value": g, "limit": 0.9 * nc, "pass": g <= 0.9 * nc, "margin": 0.9 * nc - g},
        {"part": 3, "name": "Graph beats k-NN by 10%", "threshold": "graph MAE <= 0.90 x k-NN MAE",
         "value": g, "limit": 0.9 * kn, "pass": g <= 0.9 * kn, "margin": 0.9 * kn - g},
        {"part": 4, "name": "Refitting beats frozen weights", "threshold": "graph MAE < frozen-graph MAE",
         "value": g, "limit": fr, "pass": g < fr, "margin": fr - g},
    ]
    verdict = "PASS" if all(r["pass"] for r in rule) else "FAIL"

    boot = {}
    for other in ("no_change", "knn", "frozen_graph", "direct_regression"):
        lo, hi = L.bootstrap_diff(graph_preds, models[other], ch, hold)
        boot["graph_minus_" + other] = {"low": lo, "high": hi}

    per_year = []
    for y in range(L.FIRST_YEAR, L.last_year(ch) + 1):
        if y not in graph_preds:
            continue
        period = "holdout" if y in L.HOLDOUT_YEARS else "design" if y in L.DESIGN_YEARS else "burn-in" if y < min(L.DESIGN_YEARS) else "after holdout"
        row = {"year": y, "period": period,
               "actual_co2": ch["CO2"].get(y)}
        for name, p in models.items():
            row[name] = p[y]["CO2"] if y in p else None
        row["graph_fuel"] = graph_preds[y]["FuelUse"]
        row["actual_fuel"] = ch["FuelUse"].get(y)
        row["graph_gasoline"] = graph_preds[y]["Gasoline"]
        row["actual_gasoline"] = ch["Gasoline"].get(y)
        row["inputs"] = L.year_inputs(ch, y)
        if y in knn_preds:
            row["knn_neighbours"] = knn_preds[y]["neighbours"]
        per_year.append(row)

    out = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "code_commit": git("rev-parse", "HEAD"),
        "preregistration_commit": git("log", "--diff-filter=A", "--format=%H %cI", "--", "PREREGISTRATION.md"),
        "hydradb": hydra,
        "hydradb_engine": "hydra-db/hydradb v0.4.0, self-hosted graph-node, local mode",
        "config": {"first_year": L.FIRST_YEAR, "holdout_years_scored": hold, "delta": L.DELTA,
                   "lambda_grid": L.LAMBDA_GRID, "k_grid": L.K_GRID, "w_grid": L.W_GRID,
                   "bootstrap": {"n": L.BOOT_N, "seed": L.BOOT_SEED}},
        "tuning": tuned,
        "scores_co2": scores,
        "secondary_targets": secondary,
        "rule": rule,
        "verdict": verdict,
        "bootstrap_95": boot,
        "per_year": per_year,
        "graph_predictions_from": "hydradb" if hydra else "memory",
        "link_weights_by_year": {str(y): w for y, w in graph_weights.items()},
        "final_weights": graph_weights[max(graph_weights)],
        "seconds_total": round(time.time() - t0, 2),
    }
    os.makedirs(os.path.dirname(L.results_path()), exist_ok=True)
    with open(L.results_path(), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("verdict:", verdict)
    for r in rule:
        print("  part %d %-34s pass=%s value=%s margin=%s" % (r["part"], r["name"], r["pass"], r["value"], r["margin"]))
    for name, s in scores.items():
        print("  %-18s holdout MAE %.3f (n=%d)  design MAE %.3f (n=%d)" % (name, s["holdout_mae"], s["holdout_n"], s["design_mae"], s["design_n"]))
    if hydra:
        print("  hydradb:", hydra)


if __name__ == "__main__":
    main()
