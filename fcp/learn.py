"""The self-refitting graph, its baselines, and scoring.

Implements exactly what PREREGISTRATION.md describes. Pure Python (no numpy)
so the arithmetic is identical on every machine and store.
"""

import json
import math
import os
import random

from fcp.fetch import ROOT
from fcp.parse import PROCESSED

# --- nodes and links ------------------------------------------------------

VAR_IDS = {"Crude": 1, "Gasoline": 2, "VMT": 3, "EVShare": 4, "FuelUse": 5, "CO2": 6}
VAR_SERIES = {
    "Crude": "us_crude_rac",
    "Gasoline": "us_gasoline_unleaded",
    "VMT": "us_vmt",
    "EVShare": "us_ev_share",
    "FuelUse": "us_motor_gasoline_use",
    "CO2": "us_transport_co2",
}
LINKS = [  # (link id, source, target)
    (101, "Crude", "Gasoline"),
    (102, "Gasoline", "FuelUse"),
    (103, "VMT", "FuelUse"),
    (104, "EVShare", "FuelUse"),
    (105, "FuelUse", "CO2"),
]
FIT_IDS = {"Gasoline": 201, "FuelUse": 202, "CO2": 203}
TARGETS = ["Gasoline", "FuelUse", "CO2"]
NOWCAST_INPUTS = ("Crude", "Gasoline", "VMT", "EVShare")  # known in near real time for year t
REQUIRED_INPUTS = ("Crude", "Gasoline", "VMT")  # a year is predicted only if these exist
ID_TO_VAR = {v: k for k, v in VAR_IDS.items()}

FIRST_YEAR = 1977
DESIGN_YEARS = list(range(1982, 2005))
HOLDOUT_YEARS = list(range(2005, 2025))
FREEZE_AFTER = 2004
DELTA = 1000.0
LAMBDA_GRID = [0.90, 0.95, 0.98, 1.00]
K_GRID = [3, 5, 7]
W_GRID = [10, 15, 20, None]  # None = all past years
BOOT_N = 10000
BOOT_SEED = 20261116


def link_state_id(link_id, year):
    return 1_000_000 + link_id * 10_000 + year


def prediction_id(target, year):
    return 2_000_000 + VAR_IDS[target] * 10_000 + year


# --- data -----------------------------------------------------------------

def load_series(path=PROCESSED):
    with open(path, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["series"]}


def changes(series):
    """Year-over-year changes per graph variable; flagged values count as missing."""
    out = {}
    for var, sid in VAR_SERIES.items():
        s = series[sid]
        flags = s["flags"]
        lv = {int(y): v for y, v in s["values"].items() if y not in flags}
        ch = {}
        for y in sorted(lv):
            if y - 1 in lv:
                if var == "EVShare":
                    ch[y] = lv[y] - lv[y - 1]
                elif lv[y] > 0 and lv[y - 1] > 0:
                    ch[y] = 100.0 * math.log(lv[y] / lv[y - 1])
        out[var] = ch
    return out


def last_year(ch):
    return max(max(v) for v in ch.values() if v)


# --- recursive least squares with forgetting, active-set form -------------

def rls_update(theta, P, x, y, lam, active):
    """Update theta (list) and P (list of lists) in place on the active indices only."""
    A = active
    xa = [x[i] for i in A]
    Px = [sum(P[i][j] * x[j] for j in A) for i in A]
    denom = lam + sum(xa[k] * Px[k] for k in range(len(A)))
    K = [p / denom for p in Px]
    err = y - sum(theta[i] * x[i] for i in A)
    for k, i in enumerate(A):
        theta[i] += K[k] * err
    newP = {}
    for a, i in enumerate(A):
        for b, j in enumerate(A):
            newP[(i, j)] = (P[i][j] - K[a] * Px[b]) / lam
    for (i, j), v in newP.items():
        P[i][j] = v
    return err


# --- the graph learner over a store ----------------------------------------

class GraphLearner:
    """Link strengths live in the store; every prediction reads them back."""

    def __init__(self, store, lam, delta=DELTA, freeze_after=None, write_history=True):
        self.s = store
        self.lam = lam
        self.delta = delta
        self.freeze_after = freeze_after
        self.write_history = write_history

    def init_graph(self):
        s = self.s
        s.put("Variable", [{"id": i, "name": n} for n, i in VAR_IDS.items()])
        s.put("Link", [{"id": lid, "name": "%s->%s" % (a, b), "src": VAR_IDS[a], "dst": VAR_IDS[b], "w": 0.0} for lid, a, b in LINKS])
        fit_rows = []
        for t, fid in FIT_IDS.items():
            dim = 1 + sum(1 for _, _, b in LINKS if b == t)
            row = {"id": fid, "name": "fit:" + t, "target": VAR_IDS[t], "bias": 0.0}
            for i in range(dim):
                for j in range(dim):
                    row["p_%d_%d" % (i, j)] = self.delta if i == j else 0.0
            fit_rows.append(row)
        s.put("Fit", fit_rows)
        s.edge("FEEDS", [(VAR_IDS[a], lid) for lid, a, _ in LINKS])
        s.edge("INTO", [(lid, VAR_IDS[b]) for lid, _, b in LINKS])
        s.edge("FITS", [(fid, VAR_IDS[t]) for t, fid in FIT_IDS.items()])

    # Reading the model for one target is a graph walk: target <-INTO- links.
    def _model(self, target):
        link_ids = self.s.incoming(VAR_IDS[target], "INTO")
        links = []
        for lid in link_ids:
            p = self.s.get(lid, ["src", "w"])
            links.append((lid, ID_TO_VAR[int(p["src"])], float(p["w"])))
        dim = 1 + len(links)
        props = ["bias"] + ["p_%d_%d" % (i, j) for i in range(dim) for j in range(dim)]
        f = self.s.get(FIT_IDS[target], props)
        P = [[float(f["p_%d_%d" % (i, j)]) for j in range(dim)] for i in range(dim)]
        return links, float(f["bias"]), P

    def _value(self, var, inputs, cache):
        if var in NOWCAST_INPUTS:
            return inputs.get(var)
        if var not in cache:
            cache[var] = self.predict_node(var, inputs, cache)
        return cache[var]

    def predict_node(self, target, inputs, cache=None):
        cache = {} if cache is None else cache
        links, bias, _ = self._model(target)
        total = bias
        for _, src, w in links:
            v = self._value(src, inputs, cache)
            if v is not None:
                total += w * v
        return total

    def predict(self, inputs):
        cache = {}
        fuel = self._value("FuelUse", inputs, cache)  # hop 1: inputs -> FuelUse
        co2 = self._value("CO2", inputs, cache)  # hop 2: predicted FuelUse -> CO2
        gas = self.predict_node("Gasoline", inputs, cache)  # secondary: Crude -> Gasoline
        return {"FuelUse": fuel, "CO2": co2, "Gasoline": gas}

    def update(self, year, observed):
        if self.freeze_after is not None and year > self.freeze_after:
            return
        history = []
        for target in TARGETS:
            y = observed.get(target)
            if y is None:
                continue
            links, bias, P = self._model(target)
            theta = [bias] + [w for _, _, w in links]
            x = [1.0] + [observed.get(src) or 0.0 for _, src, _ in links]
            active = [0] + [k + 1 for k, (_, src, _) in enumerate(links) if observed.get(src) is not None]
            rls_update(theta, P, x, y, self.lam, active)
            for k, (lid, _, _) in enumerate(links):
                self.s.set_props(lid, {"w": theta[k + 1]})
                history.append({"id": link_state_id(lid, year), "link": lid, "year": year, "w": theta[k + 1]})
            fit = {"bias": theta[0]}
            for i in range(len(P)):
                for j in range(len(P)):
                    fit["p_%d_%d" % (i, j)] = P[i][j]
            self.s.set_props(FIT_IDS[target], fit)
        if self.write_history and history:
            self.s.put("LinkState", history)
            self.s.edge("HISTORY", [(h["link"], h["id"]) for h in history])

    def record_predictions(self, year, preds):
        if not self.write_history:
            return
        rows = [{"id": prediction_id(t, year), "target": VAR_IDS[t], "year": year, "value": v} for t, v in preds.items()]
        self.s.put("Prediction", rows)
        self.s.edge("OF", [(prediction_id(t, year), VAR_IDS[t]) for t in preds])

    def weights(self):
        out = {}
        for t in TARGETS:
            links, bias, _ = self._model(t)
            out[t] = {"bias": bias, **{"%s->%s" % (src, t): w for _, src, w in links}}
        return out


def year_inputs(ch, year):
    return {v: ch[v].get(year) for v in NOWCAST_INPUTS}


def year_observed(ch, year):
    return {v: ch[v].get(year) for v in VAR_IDS}


def can_predict(ch, year):
    return all(ch[v].get(year) is not None for v in REQUIRED_INPUTS)


def run_graph(store, ch, lam, freeze_after=None, write_history=True):
    g = GraphLearner(store, lam, freeze_after=freeze_after, write_history=write_history)
    g.init_graph()
    preds = {}
    weights_by_year = {}
    for year in range(FIRST_YEAR, last_year(ch) + 1):
        if can_predict(ch, year):
            p = g.predict(year_inputs(ch, year))
            preds[year] = p
            g.record_predictions(year, p)
        g.update(year, year_observed(ch, year))
        if write_history:
            weights_by_year[year] = g.weights()
    return preds, weights_by_year


# --- baselines ---------------------------------------------------------------

def run_no_change(ch):
    return {y: {"CO2": 0.0, "FuelUse": 0.0, "Gasoline": 0.0} for y in range(FIRST_YEAR, last_year(ch) + 1) if can_predict(ch, y)}


def run_direct(ch, lam):
    """One RLS from the four inputs straight to CO2 (no intermediate node)."""
    dim = 1 + len(NOWCAST_INPUTS)
    theta = [0.0] * dim
    P = [[DELTA if i == j else 0.0 for j in range(dim)] for i in range(dim)]
    preds = {}
    for year in range(FIRST_YEAR, last_year(ch) + 1):
        inp = year_inputs(ch, year)
        x = [1.0] + [inp[v] if inp[v] is not None else 0.0 for v in NOWCAST_INPUTS]
        if can_predict(ch, year):
            preds[year] = {"CO2": sum(theta[i] * x[i] for i in range(dim))}
        y = ch["CO2"].get(year)
        if y is not None:
            active = [0] + [k + 1 for k, v in enumerate(NOWCAST_INPUTS) if inp[v] is not None]
            rls_update(theta, P, x, y, lam, active)
    return preds


def run_knn(ch, k, window):
    preds = {}
    for year in range(FIRST_YEAR, last_year(ch) + 1):
        if not can_predict(ch, year):
            continue
        lo = FIRST_YEAR if window is None else year - window
        pool = [y for y in range(max(lo, FIRST_YEAR), year) if ch["CO2"].get(y) is not None and can_predict(ch, y)]
        if not pool:
            continue
        stats = {}
        for v in NOWCAST_INPUTS:
            vals = [ch[v][y] for y in pool if ch[v].get(y) is not None]
            if len(vals) >= 2:
                m = sum(vals) / len(vals)
                sd = math.sqrt(sum((a - m) ** 2 for a in vals) / (len(vals) - 1))
                stats[v] = (m, sd if sd > 0 else 1.0)
        q = year_inputs(ch, year)
        dists = []
        for y in pool:
            sq, n = 0.0, 0
            for v, (m, sd) in stats.items():
                a, b = q.get(v), ch[v].get(y)
                if a is None or b is None:
                    continue
                sq += ((a - m) / sd - (b - m) / sd) ** 2
                n += 1
            if n:
                dists.append((math.sqrt(sq / n), -y, y))  # ties: the more recent year first
        dists.sort()
        nn = [y for _, _, y in dists[:k]]
        if not nn:
            continue
        preds[year] = {"CO2": sum(ch["CO2"][y] for y in nn) / len(nn), "neighbours": nn}
    return preds


# --- scoring ---------------------------------------------------------------

def mae(preds, ch, years, target="CO2"):
    errs = [abs(preds[y][target] - ch[target][y]) for y in years if y in preds and ch[target].get(y) is not None]
    return (sum(errs) / len(errs) if errs else float("nan")), len(errs)


def scored_years(ch, years, target="CO2"):
    return [y for y in years if can_predict(ch, y) and ch[target].get(y) is not None]


def bootstrap_diff(pa, pb, ch, years, target="CO2", n=BOOT_N, seed=BOOT_SEED):
    """Paired bootstrap of MAE(a) - MAE(b): (low, high) 95% interval."""
    ea = [abs(pa[y][target] - ch[target][y]) for y in years]
    eb = [abs(pb[y][target] - ch[target][y]) for y in years]
    rng = random.Random(seed)
    m = len(years)
    diffs = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]
        diffs.append(sum(ea[i] - eb[i] for i in idx) / m)
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]


def results_path():
    return os.path.join(ROOT, "results", "learning_results.json")
