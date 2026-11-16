import math
import random

from fcp import learn as L
from fcp.stores import MemoryStore


def ols_2(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def test_rls_without_forgetting_matches_ols():
    rng = random.Random(1)
    xs = [rng.uniform(-10, 10) for _ in range(40)]
    ys = [1.5 - 0.7 * x + rng.gauss(0, 0.3) for x in xs]
    theta = [0.0, 0.0]
    P = [[1e8, 0.0], [0.0, 1e8]]
    for x, y in zip(xs, ys):
        L.rls_update(theta, P, [1.0, x], y, 1.0, [0, 1])
    a, b = ols_2(xs, ys)
    assert abs(theta[0] - a) < 1e-4 and abs(theta[1] - b) < 1e-5


def test_rls_inactive_index_untouched():
    theta = [0.0, 2.0, 0.0]
    P = [[10.0, 0, 0], [0, 10.0, 0], [0, 0, 10.0]]
    L.rls_update(theta, P, [1.0, 0.0, 3.0], 5.0, 0.9, [0, 2])
    assert theta[1] == 2.0 and P[1][1] == 10.0
    assert theta[0] != 0.0 and theta[2] != 0.0


def test_forgetting_tracks_a_shift():
    theta = [0.0, 0.0]
    P = [[1000.0, 0], [0, 1000.0]]
    for t in range(60):
        x = math.sin(t)
        y = (1.0 if t < 30 else -1.0) + 0.5 * x
        L.rls_update(theta, P, [1.0, x], y, 0.9, [0, 1])
    assert abs(theta[0] - (-1.0)) < 0.15  # old regime weight ~0.9**30


def synthetic_changes():
    rng = random.Random(7)
    ch = {v: {} for v in L.VAR_IDS}
    for y in range(1977, 2025):
        crude, vmt = rng.gauss(0, 20), rng.gauss(2, 2)
        gas = 0.5 * crude + rng.gauss(0, 3)
        ev = rng.gauss(0.5, 0.2) if y >= 2012 else None
        fuel = 0.9 * vmt - 0.05 * gas - (0.8 * ev if ev is not None else 0) + rng.gauss(0, 0.5)
        co2 = 0.8 * fuel + 0.3 + rng.gauss(0, 0.3)
        for k, v in (("Crude", crude), ("Gasoline", gas), ("VMT", vmt), ("EVShare", ev), ("FuelUse", fuel), ("CO2", co2)):
            if v is not None:
                ch[k][y] = v
    return ch


def test_graph_learns_synthetic_chain_and_beats_no_change():
    ch = synthetic_changes()
    preds, weights = L.run_graph(MemoryStore(), ch, 1.0)
    yrs = list(range(1995, 2025))
    g, n = L.mae(preds, ch, yrs)
    nc, _ = L.mae(L.run_no_change(ch), ch, yrs)
    assert n == 30 and g < 0.5 * nc
    w = weights[2024]
    assert abs(w["FuelUse"]["VMT->FuelUse"] - 0.9) < 0.15
    assert abs(w["CO2"]["FuelUse->CO2"] - 0.8) < 0.1


def test_memory_runs_are_deterministic():
    ch = synthetic_changes()
    a, _ = L.run_graph(MemoryStore(), ch, 0.95)
    b, _ = L.run_graph(MemoryStore(), ch, 0.95)
    assert a == b


def test_frozen_stops_updating():
    ch = synthetic_changes()
    p, w = L.run_graph(MemoryStore(), ch, 0.95, freeze_after=2004)
    assert w[2004] == w[2024]


def test_knn_uses_only_past_years():
    ch = synthetic_changes()
    p = L.run_knn(ch, 3, 10)
    for y, row in p.items():
        assert all(y - 10 <= n < y for n in row["neighbours"])


def test_changes_skip_flagged_and_missing():
    series = {
        sid: {"values": {"2000": 10.0, "2001": 11.0, "2003": 12.0, "2004": 13.0}, "flags": {"2004": "provisional"}}
        for sid in L.VAR_SERIES.values()
    }
    ch = L.changes(series)
    assert set(ch["CO2"]) == {2001}
    assert abs(ch["CO2"][2001] - 100 * math.log(1.1)) < 1e-12
    assert abs(ch["EVShare"][2001] - 1.0) < 1e-12
