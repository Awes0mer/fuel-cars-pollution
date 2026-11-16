"""Build the static site in site/ from the processed data and result files.

Every number on the pages is read from data/processed/series.json,
data/manifest.json or results/*.json at build time.

Usage: python -m fcp.site
"""

import json
import os

from fcp.charts import esc, fmt, line_chart
from fcp.fetch import MANIFEST, ROOT
from fcp.learn import LINKS, load_series, results_path
from fcp.sources import NOT_COVERED, REJECTED, SOURCES
from fcp.stats import CORR_OUT, SUMMARY_OUT

SITE = os.path.join(ROOT, "site")
ROUNDTRIP = os.path.join(ROOT, "results", "hydradb_float_roundtrip.json")
REPO_URL = "https://github.com/Awes0mer/fuel-cars-pollution"

NAV = [
    ("index.html", "Results"),
    ("index.html#how", "How it works"),
    ("index.html#data", "The data"),
    ("sources.html", "Sources & licences"),
    ("ai.html", "AI disclosure"),
    ("privacy.html", "Privacy"),
    ("terms.html", "Terms"),
]

CSS = """
:root{--fg:#16191d;--muted:#4b5560;--line:#d8dde3;--bg:#ffffff;--soft:#f4f6f8;--accent:#0b5cad;--bad:#a40e26;--good:#1a7f37;color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
a{color:var(--accent)}
a:focus-visible,summary:focus-visible,input:focus-visible{outline:3px solid #f2b600;outline-offset:2px}
header.site{border-bottom:1px solid var(--line);background:var(--soft)}
header.site .in,main,footer .in{max-width:980px;margin:0 auto;padding:0 16px}
header.site .in{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;padding-top:10px;padding-bottom:10px}
header.site .brand{font-weight:700;color:var(--fg);text-decoration:none;margin-right:auto}
header.site nav{display:flex;flex-wrap:wrap;gap:2px 14px}
header.site nav a{font-size:.95rem;white-space:nowrap}
h1{font-size:1.75rem;line-height:1.25;margin:1.2rem 0 .4rem}
h2{font-size:1.35rem;margin:2.2rem 0 .6rem;border-top:1px solid var(--line);padding-top:1.2rem}
h3{font-size:1.1rem;margin:1.6rem 0 .4rem}
.lede{font-size:1.08rem;color:var(--muted);margin-top:0}
.box{border:1px solid var(--line);border-left:5px solid var(--accent);background:var(--soft);padding:12px 14px;margin:14px 0;border-radius:4px}
.box.warn{border-left-color:var(--bad)}
.verdict{font-size:1.25rem;font-weight:700}
.pass{color:var(--good)} .fail{color:var(--bad)}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.92rem;margin:.4rem 0}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;vertical-align:top}
th:first-child,td:first-child{text-align:left}
caption{text-align:left;color:var(--muted);font-size:.85rem;padding:4px 0}
table.text td,table.text th{text-align:left}
figure{margin:18px 0 26px}
.ctitle{font-weight:650;margin-bottom:4px}
svg.chart{width:100%;height:auto;display:block;background:#fff}
svg.chart .grid{stroke:#e6e9ed;stroke-width:1}
svg.chart .zero{stroke:#8a939c;stroke-width:1.2}
svg.chart .tick{font-size:14px;fill:#3d4650}
svg.chart .axis{font-size:14px;fill:#3d4650}
.legend{list-style:none;padding:0;margin:4px 0;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:.88rem}
.legend li{display:flex;align-items:center;gap:6px}
.source,.note{font-size:.82rem;color:var(--muted);margin:.35rem 0}
.flag{color:var(--bad);font-size:.8rem}
details{margin:.3rem 0}
summary{cursor:pointer;color:var(--accent);font-size:.9rem}
code{background:var(--soft);padding:1px 4px;border-radius:3px;font-size:.9em;word-break:break-word}
.diagram{max-width:720px}
.whatif{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:10px 0}
.whatif label{display:block;font-size:.9rem;color:var(--muted)}
.whatif input{width:100%;font:inherit;padding:6px;border:1px solid #9aa3ad;border-radius:4px}
output{font-weight:700}
footer{border-top:1px solid var(--line);margin-top:40px;background:var(--soft)}
footer .in{padding-top:14px;padding-bottom:24px;font-size:.88rem;color:var(--muted)}
ul.plain{padding-left:1.2rem}
.src{border:1px solid var(--line);border-radius:6px;padding:4px 14px 10px;margin:12px 0}
.src h3{margin:.6rem 0 .3rem;font-size:1.02rem}
.src dl{margin:0;display:grid;grid-template-columns:max-content 1fr;gap:2px 12px;font-size:.92rem}
.src dt{color:var(--muted)} .src dd{margin:0;min-width:0;overflow-wrap:anywhere}
@media (max-width:520px){.src dl{grid-template-columns:1fr}.src dt{margin-top:6px}}
"""


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def page(fname, title, body, description):
    nav = "".join('<a href="%s">%s</a>' % (h, esc(t)) for h, t in NAV)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>%s</title><meta name="description" content="%s">'
        '<link rel="stylesheet" href="style.css"></head><body>'
        '<a href="#main" style="position:absolute;left:-999px" onfocus="this.style.left=\'8px\'">Skip to content</a>'
        '<header class="site"><div class="in"><a class="brand" href="index.html">Fuel, Cars &amp; Pollution</a><nav aria-label="Site">%s</nav></div></header>'
        '<main id="main">%s</main>'
        '<footer><div class="in">Built for the HydraDB Hackathon (Track 1). Data: U.S. EIA, FHWA and EPA (U.S. government works), '
        'World Bank (CC BY 4.0), Ember (CC BY 4.0). Graph engine: HydraDB v0.4.0, self-hosted (Elastic License 2.0). '
        'This page is a static snapshot of the results. <a href="sources.html">Sources &amp; licences</a> · '
        '<a href="ai.html">AI disclosure</a> · <a href="privacy.html">Privacy</a> · <a href="terms.html">Terms</a> · '
        '<a href="%s">Code</a></div></footer></body></html>'
    ) % (esc(title), esc(description), nav, body, REPO_URL)


class Ctx:
    def __init__(self):
        self.series = load_series()
        self.manifest = {e["id"]: e for e in load_json(MANIFEST)["files"]}
        self.src = {s["id"]: s for s in SOURCES}
        self.res = load_json(results_path())
        self.corr = load_json(CORR_OUT)
        self.summ = load_json(SUMMARY_OUT)
        self.rt = load_json(ROUNDTRIP) if os.path.exists(ROUNDTRIP) else None

    def source_line(self, source_ids):
        bits = []
        for sid in source_ids:
            s, m = self.src[sid], self.manifest[sid]
            bits.append('%s — %s (%s); retrieved %s UTC; SHA-256 <code>%s…</code>; <a href="%s">file</a>' % (
                esc(s["publisher"]), esc(s["title"]), esc(s["licence"]), esc(m["retrieved_at_utc"].replace("T", " ").replace("+00:00", "")),
                esc(m["sha256"][:16]), esc(s["url"])))
        return "Source: " + " · ".join(bits)

    def line(self, sid, label=None):
        s = self.series[sid]
        return {"label": label or s["label"], "values": s["values"], "flags": s["flags"]}

    def chart(self, cid, title, desc, sids, y_label, labels=None, **kw):
        lines = [self.line(sid, (labels or {}).get(sid)) for sid in sids]
        srcs = []
        for sid in sids:
            for x in self.series[sid]["sources"]:
                if x not in srcs:
                    srcs.append(x)
        return line_chart(cid, title, desc, lines, y_label, self.source_line(srcs), **kw)


def lw(ex, m):
    return "<b>loses to</b>" if ex["graph"] > ex[m] else "beats"


def pct(v):
    return "%.2f" % v


def results_section(c):
    r, s = c.res, c.summ
    sc = r["scores_co2"]
    verdict = r["verdict"]
    names = {"graph": "HydraDB graph (refit every year)", "no_change": "No change", "knn": "Vector-store k-NN (k=%d, window %s years)" % (
        r["tuning"]["knn_k"], r["tuning"]["knn_window"] or "all"), "frozen_graph": "Frozen graph (weights fixed after 2004)",
        "direct_regression": "Direct regression (no graph)"}
    ex = s["excluding_2020_2021"]
    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
            esc(names[m]), pct(sc[m]["holdout_mae"]), sc[m]["holdout_n"], pct(ex[m]), pct(sc[m]["design_mae"]))
        for m in ("graph", "no_change", "knn", "frozen_graph", "direct_regression"))
    rule_rows = "".join(
        '<tr><td>%d. %s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>' % (
            p["part"], esc(p["name"]), esc(p["threshold"]),
            ("%.3g" % p["value"]) if p["part"] == 1 else pct(p["value"]),
            ("%.3g" % p["margin"]) if p["part"] == 1 else pct(p["margin"]),
            "pass" if p["pass"] else "fail", "PASS" if p["pass"] else "FAIL")
        for p in r["rule"])
    boot = r["bootstrap_95"]
    boot_rows = "".join("<tr><td>Graph minus %s</td><td>%s to %s</td></tr>" % (
        esc(k.replace("graph_minus_", "").replace("_", " ")), pct(v["low"]), pct(v["high"])) for k, v in boot.items())
    worst = ", ".join("%d (%.2f pp)" % (e["year"], e["abs_error"]) for e in s["largest_graph_errors"])
    wins = s["graph_wins_by_year"]
    hy = r["hydradb"]
    out = []
    out.append('<h1>A graph that refits its own links every year</h1>')
    out.append('<p class="lede">Crude oil → gasoline → fuel use → transport CO2, with miles driven and electric-car adoption feeding in. '
               'The strength of each link is stored in HydraDB and refit every year, so each year\'s correction changes the next prediction. '
               'Tested walk-forward against a plain vector-store lookup and a "no change" guess, on years not used to design it.</p>')
    out.append('<div class="box"><p class="verdict">Pre-registered verdict: <span class="%s">%s</span> (all four parts)</p>'
               '<p>Holdout 2005–2024, n = %d years. Holdout MAE of the U.S. transport-CO2 change: graph <b>%s</b> pp, no change %s, k-NN %s, frozen graph %s. '
               'The rule was <a href="%s/blob/main/PREREGISTRATION.md">committed before any run</a>.</p></div>' % (
                   "pass" if verdict == "PASS" else "fail", verdict, sc["graph"]["holdout_n"], pct(sc["graph"]["holdout_mae"]),
                   pct(sc["no_change"]["holdout_mae"]), pct(sc["knn"]["holdout_mae"]), pct(sc["frozen_graph"]["holdout_mae"]), REPO_URL))
    out.append('<div class="box warn"><p><b>Read this before the verdict.</b></p><ul class="plain">'
               '<li>Without 2020 and 2021 (n = %d) the graph\'s MAE is <b>%s</b> pp: it %s no change (%s), %s k-NN (%s) and %s its own frozen version (%s).</li>'
               '<li>%s 95%% bootstrap interval of the MAE difference includes zero (table below). With n = %d, the ranking is not statistically settled.</li>'
               '<li>Year by year, the graph beats no change in %d of %d years and k-NN in %d of %d.</li>'
               '<li>Its largest misses: %s. 2008 is a recession it did not see coming from prices and miles alone.</li>'
               '<li>On the design years 1982–2004, k-NN scored %s and the graph %s (lower is better).</li>'
               '<li>Inputs are today&rsquo;s revised figures, not the first-release values available at the time; real-time accuracy is unmeasured.</li>'
               '<li>2009 and 2010 are not scored: FHWA marks 2009 vehicle-miles as unavailable, so both changes are missing.</li></ul></div>' % (
                   ex["n"], pct(ex["graph"]), lw(ex, "no_change"), pct(ex["no_change"]), lw(ex, "knn"), pct(ex["knn"]), lw(ex, "frozen_graph"), pct(ex["frozen_graph"]),
                   "Every" if all(v["low"] <= 0 <= v["high"] for v in r["bootstrap_95"].values()) else "Not every", s["holdout_n"], wins["no_change"], s["holdout_n"], wins["knn"], s["holdout_n"], esc(worst),
                   pct(sc["knn"]["design_mae"]), pct(sc["graph"]["design_mae"])))
    out.append('<h3>Scores</h3><div class="tablewrap"><table><caption>MAE of the predicted yearly change in U.S. transport CO2, percentage points of 100·ln change. '
               'Lower is better. Design years 1982–2004 were used to pick settings; holdout years were not.</caption>'
               '<thead><tr><th scope="col">Model</th><th scope="col">Holdout MAE</th><th scope="col">n</th><th scope="col">Holdout MAE without 2020–21 (n=%d)</th><th scope="col">Design MAE (n=%d)</th></tr></thead><tbody>%s</tbody></table></div>' % (
                   ex["n"], sc["graph"]["design_n"], rows))
    out.append('<h3>The pre-registered rule</h3><div class="tablewrap"><table><thead><tr><th scope="col">Part</th><th scope="col">Threshold</th><th scope="col">Value</th><th scope="col">Margin</th><th scope="col">Result</th></tr></thead><tbody>%s</tbody></table></div>' % rule_rows)
    out.append('<h3>Uncertainty</h3><div class="tablewrap"><table><caption>Paired bootstrap 95%% interval of the holdout MAE difference (negative = graph better); %d resamples, seed %d.</caption><thead><tr><th scope="col">Comparison</th><th scope="col">95%% interval (pp)</th></tr></thead><tbody>%s</tbody></table></div>' % (
        r["config"]["bootstrap"]["n"], r["config"]["bootstrap"]["seed"], boot_rows))
    # per-year chart
    per = r["per_year"]
    lines = [
        {"label": "Actual (EIA)", "values": {str(p["year"]): p["actual_co2"] for p in per}, "flags": {}, "color": "#16191d", "dash": ""},
        {"label": "HydraDB graph", "values": {str(p["year"]): p["graph"] for p in per}, "flags": {}, "color": "#0b5cad", "dash": ""},
        {"label": "k-NN", "values": {str(p["year"]): p["knn"] for p in per}, "flags": {}, "color": "#b34d00", "dash": "6 4"},
        {"label": "No change", "values": {str(p["year"]): p["no_change"] for p in per}, "flags": {}, "color": "#5b6570", "dash": "2 3"},
        {"label": "Frozen graph", "values": {str(p["year"]): p["frozen_graph"] for p in per}, "flags": {}, "color": "#7a3fb8", "dash": "10 3 2 3"},
    ]
    out.append(line_chart("pred", "Predicted vs actual yearly change in U.S. transport CO2",
                          "Walk-forward predictions 1977 to 2024. Design years 1982-2004, holdout 2005-2024; 2009 and 2010 missing because vehicle-miles for 2009 are unavailable.",
                          lines, "change, % (100·ln)", c.source_line(["eia_mer_t1105", "eia_mer_t0901", "eia_mer_t0904", "fhwa_vm203", "ember_ev_monthly"]) +
                          " · Predictions: results/learning_results.json", y_zero=True, unit_note="percentage points of 100·ln change; holdout starts 2005",
                          shade=(2005, 2024, "holdout")))
    out.append('<h3>HydraDB in this run</h3><ul class="plain">'
               '<li>Self-hosted <code>graph-node</code> v0.4.0, local mode, loopback only, new empty store, new random token, usage reporting off.</li>'
               '<li>The full walk-forward ran through HydraDB: %d HTTP queries in %s s. Graph after the run: %s.</li>'
               '<li>Parity with the in-memory store: %d predictions compared, largest difference <b>%.3g</b> pp (limit 1e-9). Not bit-identical: %s</li></ul>' % (
                   hy["http_requests"], hy["seconds"], esc(", ".join("%d %s" % (v, k) for k, v in hy["node_counts"].items())),
                   hy["parity"]["compared_values"], hy["parity"]["max_abs_diff"],
                   ("in a separate test HydraDB returned %d of %d floats one unit in the last place away from what was written; the tiny drift compounds over 48 refits." % (c.rt["mismatches"], c.rt["values_tested"])) if c.rt else "cause not measured."))
    return "".join(out)


def weights_table(w):
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td>%.4f</td></tr>' % (esc(t), esc(k.replace("->", " → ")), v)
                   for t in ("Gasoline", "FuelUse", "CO2") for k, v in w[t].items())
    return ('<details><summary>Data table: learned link strengths after the last refit</summary><div class="tablewrap"><table>'
            '<caption>Final weights and intercepts per target node</caption><thead><tr><th scope="col">Target</th><th scope="col">Term</th>'
            '<th scope="col">Value</th></tr></thead><tbody>%s</tbody></table></div></details>' % rows)


def diagram(w):
    fw = w
    def lbl(t, k):
        return "%.2f" % fw[t][k]
    return (
        '<figure><figcaption class="ctitle">The graph and its learned link strengths after the last refit</figcaption>'
        '<svg class="diagram chart" viewBox="0 0 720 250" role="img" aria-labelledby="dg-t dg-d"><title id="dg-t">Graph of learned links</title>'
        '<desc id="dg-d">Crude oil price change feeds gasoline price change (weight %s). Gasoline price (weight %s), vehicle-miles (weight %s) and EV share (weight %s) feed motor gasoline use. Motor gasoline use feeds transport CO2 (weight %s).</desc>'
        '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="#4b5560"/></marker></defs>'
        '<g font-size="13" fill="#16191d">'
        '<rect x="10" y="20" width="120" height="40" rx="6" fill="#eef4fb" stroke="#0b5cad"/><text x="70" y="45" text-anchor="middle">Crude oil</text>'
        '<rect x="200" y="20" width="120" height="40" rx="6" fill="#eef4fb" stroke="#0b5cad"/><text x="260" y="45" text-anchor="middle">Gasoline</text>'
        '<rect x="200" y="105" width="120" height="40" rx="6" fill="#eef4fb" stroke="#0b5cad"/><text x="260" y="130" text-anchor="middle">Miles driven</text>'
        '<rect x="200" y="190" width="120" height="40" rx="6" fill="#eef4fb" stroke="#0b5cad"/><text x="260" y="215" text-anchor="middle">EV share</text>'
        '<rect x="420" y="105" width="130" height="40" rx="6" fill="#fff6e8" stroke="#b34d00"/><text x="485" y="130" text-anchor="middle">Fuel use</text>'
        '<rect x="600" y="105" width="110" height="40" rx="6" fill="#fdecee" stroke="#a40e26"/><text x="655" y="130" text-anchor="middle">CO2</text>'
        '</g><g stroke="#4b5560" stroke-width="2" fill="none" marker-end="url(#ar)">'
        '<path d="M130,40H198"/><path d="M320,45L418,115"/><path d="M320,125H418"/><path d="M320,205L418,138"/><path d="M550,125H598"/></g>'
        '<g font-size="12" fill="#0b5cad" font-weight="700"><text x="164" y="34" text-anchor="middle">%s</text><text x="372" y="72">%s</text>'
        '<text x="369" y="119" text-anchor="middle">%s</text><text x="372" y="188">%s</text><text x="574" y="119" text-anchor="middle">%s</text></g></svg>'
        '<p class="note">Weights are per percentage point of change (EV share: per point of share). Intercepts: gasoline %s, fuel use %s, CO2 %s.</p>'
        '<p class="source">Source: <code>results/learning_results.json</code> → <code>final_weights</code> (learned from the files on the sources page).</p>'
        + weights_table(fw) + '</figure>'
    ) % (lbl("Gasoline", "Crude->Gasoline"), lbl("FuelUse", "Gasoline->FuelUse"), lbl("FuelUse", "VMT->FuelUse"), lbl("FuelUse", "EVShare->FuelUse"), lbl("CO2", "FuelUse->CO2"),
         lbl("Gasoline", "Crude->Gasoline"), lbl("FuelUse", "Gasoline->FuelUse"), lbl("FuelUse", "VMT->FuelUse"), lbl("FuelUse", "EVShare->FuelUse"), lbl("CO2", "FuelUse->CO2"),
         lbl("Gasoline", "bias"), lbl("FuelUse", "bias"), lbl("CO2", "bias"))


def how_section(c):
    r = c.res
    w = r["final_weights"]
    wy = r["link_weights_by_year"]
    lines = []
    for lid, a, b in LINKS:
        key = "%s->%s" % (a, b)
        lines.append({"label": key.replace("->", " → ").replace("VMT", "Miles driven").replace("EVShare", "EV share").replace("FuelUse", "Fuel use"),
                      "values": {y: wy[y][b][key] for y in wy}, "flags": {}})
    out = ['<h2 id="how">How it works</h2>',
           '<p>Each year, at the moment the year closes, the graph is asked: by how much did U.S. transport CO2 change? It knows that year\'s crude oil price, gasoline price, '
           'vehicle-miles driven and electric share of new car sales. It does not yet know fuel use or CO2.</p>',
           '<ol><li><b>Predict.</b> HydraDB is queried for the links pointing into "Fuel use" (a graph walk from the target node), their weights are read, and fuel use is predicted. '
           'Then the links into "CO2" are read and the <i>predicted</i> fuel use is pushed one more hop to CO2.</li>'
           '<li><b>Correct.</b> When the real figures arrive, each target\'s weights are refit by recursive least squares with forgetting factor λ = %s (picked on 1982–2004 only), '
           'and written back to HydraDB. A per-year history node is written for every link, and every prediction is stored as a node too.</li>'
           '<li><b>Repeat</b> for the next year with the corrected weights.</li></ol>' % r["tuning"]["graph_lambda"],
           '<p>Links are modelled as <b>nodes</b>, not edges: HydraDB v0.4.0 deduplicates edges on (source, target, type), so a link with a changing weight and a history needs its own node. '
           'The same code runs on an in-memory store; the two runs must agree (parity).</p>',
           diagram(w),
           '<p class="note"><b>Weak link:</b> the EV share → fuel use weight is not pinned down. It is learned from %d years only and swung between %.2f and %.2f after 2012. '
           'Read it as "unknown", not as a measured effect of EVs.</p>' % (c.summ["ev_link_weight_range_2012_on"]["ev_years_used"],
                                                                            c.summ["ev_link_weight_range_2012_on"]["min"], c.summ["ev_link_weight_range_2012_on"]["max"]),
           line_chart("weights", "Learned link strengths, refit every year", "Each line is one link weight in HydraDB after each yearly refit, 1977 to the last year with data.",
                      lines, "weight", "Source: results/learning_results.json (link_weights_by_year), learned from the EIA, FHWA and Ember files listed on the sources page.",
                      y_zero=True, digits=3),
           whatif(w)]
    return "".join(out)


def whatif(w):
    data = json.dumps(w)
    return (
        '<h3>What the learned links imply</h3>'
        '<p>Type a change and follow it through the stored link weights: crude → gasoline → fuel use → CO2. This is arithmetic on the final weights, '
        '<b>not a validated scenario model</b>; only the yearly nowcast above was tested.</p>'
        '<div class="whatif"><div><label for="wi-crude">Crude oil price change (%%)</label><input id="wi-crude" type="number" step="1" value="20"></div>'
        '<div><label for="wi-vmt">Vehicle-miles change (%%)</label><input id="wi-vmt" type="number" step="0.5" value="1"></div>'
        '<div><label for="wi-ev">EV share of new sales change (points)</label><input id="wi-ev" type="number" step="0.5" value="1"></div></div>'
        '<p aria-live="polite">Gasoline: <output id="wi-gas"></output> %% · Fuel use: <output id="wi-fuel"></output> %% · Transport CO2: <output id="wi-co2"></output> %%</p>'
        '<noscript><p class="note">The calculator needs JavaScript; the weights are in the diagram above.</p></noscript>'
        '<script>(function(){var W=%s;function v(id){var x=parseFloat(document.getElementById(id).value);return isFinite(x)?x:0}'
        'function f(x){return (x>=0?"+":"")+x.toFixed(2)}'
        'function run(){var g=W.Gasoline.bias+W.Gasoline["Crude->Gasoline"]*v("wi-crude");'
        'var u=W.FuelUse.bias+W.FuelUse["Gasoline->FuelUse"]*g+W.FuelUse["VMT->FuelUse"]*v("wi-vmt")+W.FuelUse["EVShare->FuelUse"]*v("wi-ev");'
        'var c=W.CO2.bias+W.CO2["FuelUse->CO2"]*u;document.getElementById("wi-gas").textContent=f(g);'
        'document.getElementById("wi-fuel").textContent=f(u);document.getElementById("wi-co2").textContent=f(c)}'
        '["wi-crude","wi-vmt","wi-ev"].forEach(function(i){document.getElementById(i).addEventListener("input",run)});run()})();</script>'
    ) % data


def data_section(c):
    out = ['<h2 id="data">The data</h2>',
           '<p>U.S. and world series are kept on separate charts. Sales, vehicles in use and miles driven are separate series. Lines are never joined across sources; '
           'missing years leave gaps.</p>',
           '<h3>Fuel</h3>',
           c.chart("crude", "U.S. crude oil price (refiner acquisition cost)", "Annual average U.S. refiner acquisition cost of crude oil, composite, 1968 onward.",
                   ["us_crude_rac"], "dollars per barrel", unit_note="dollars per barrel, nominal"),
           c.chart("brent", "Brent crude oil spot price (world benchmark)", "Annual average Brent spot price, 1987 onward.", ["world_brent"], "dollars per barrel", unit_note="dollars per barrel, nominal"),
           c.chart("gas", "U.S. retail gasoline price, two separate EIA series", "Leaded regular 1949-1990 and unleaded regular 1976 onward, shown as separate lines.",
                   ["us_gasoline_leaded", "us_gasoline_unleaded"], "dollars per gallon", labels={"us_gasoline_leaded": "Leaded regular", "us_gasoline_unleaded": "Unleaded regular"},
                   unit_note="dollars per gallon including taxes, nominal"),
           c.chart("fuel", "U.S. motor gasoline consumed by transportation", "Thousand barrels per day, 1949 onward.", ["us_motor_gasoline_use"], "thousand barrels/day"),
           '<h3>Cars and driving</h3>',
           c.chart("vmt", "U.S. vehicle-miles traveled, all roads", "Millions of vehicle-miles per year, 1957 to 2024; 2009 unavailable.", ["us_vmt"], "million vehicle-miles"),
           c.chart("veh", "U.S. registered vehicles per 1,000 people", "FHWA registrations divided by World Bank population, 2000 to 2024.", ["us_vehicles_per_1000"], "vehicles per 1,000 people", digits=0),
           c.chart("newcars", "U.S. new car registrations (all drivetrains)", "Annual sum of monthly new car registrations from Ember, 2011 onward.", ["us_new_car_registrations"], "cars per year", digits=0),
           c.chart("wnewcars", "World new car registrations (all drivetrains)", "Ember global estimate, annual sum of monthly data, 2016 onward.", ["world_new_car_registrations"], "cars per year", digits=0),
           '<h3>Electric cars</h3>',
           c.chart("usev", "U.S. electric share of new car registrations", "Battery-electric plus plug-in hybrid share, 2011 onward.", ["us_ev_share"], "percent"),
           c.chart("wev", "World electric share of new car registrations", "Battery-electric plus plug-in hybrid share, Ember global estimate, 2016 onward.", ["world_ev_share"], "percent"),
           '<h3>Pollution</h3>',
           c.chart("co2", "U.S. transportation-sector CO2 emissions", "Million metric tons of CO2 per year, 1973 onward.", ["us_transport_co2"], "million metric tons CO2"),
           c.chart("co", "U.S. highway-vehicle carbon monoxide emissions", "Thousand short tons; 1970, 1975, 1980, 1985, then yearly from 1990.", ["us_highway_co"], "thousand short tons"),
           c.chart("nox", "U.S. highway-vehicle NOx, VOC and PM2.5 emissions", "Thousand short tons; PM2.5 starts 1990.", ["us_highway_nox", "us_highway_voc", "us_highway_pm25"], "thousand short tons",
                   labels={"us_highway_nox": "NOx", "us_highway_voc": "VOC", "us_highway_pm25": "PM2.5 (primary)"}),
           '<h3>People</h3>',
           c.chart("wpop", "World population", "World Bank total population, 1960 onward.", ["world_population"], "people", digits=0),
           ]
    rows = []
    for k in c.corr:
        r_ = k.get("pearson_r")
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s–%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(k["x_label"]), esc(k["y_label"]), esc(k["region"]), k["n"], k["first_year"], k["last_year"],
            "%.2f" % r_ if r_ is not None else "n/a", "%.2f" % k["spearman_rho"] if k.get("spearman_rho") is not None else "n/a"))
    out.append('<h3>Do they move together?</h3><p>Correlations of <b>year-over-year changes</b> (100·ln change; EV share: change in points), same region, same years, flagged values left out. '
               'Two rising levels correlate by accident; changes are a stricter test. These numbers describe co-movement only. <b>They do not show cause.</b> Small n (EV rows) means very wide uncertainty.</p>')
    out.append('<div class="tablewrap"><table class="text"><thead><tr><th scope="col">X</th><th scope="col">Y</th><th scope="col">Region</th><th scope="col">n</th><th scope="col">Years</th>'
               '<th scope="col">Pearson r</th><th scope="col">Spearman ρ</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows))
    out.append('<p class="source">Source: results/correlations.json, computed from the files on the <a href="sources.html">sources page</a>.</p>')
    out.append('<h3>Not covered</h3><ul class="plain">%s</ul>' % "".join("<li><b>%s</b>: %s</li>" % (esc(n["item"]), esc(n["why"])) for n in NOT_COVERED))
    return "".join(out)


def sources_page(c):
    rows = []
    for s in SOURCES:
        m = c.manifest[s["id"]]
        rows.append('<section class="src"><h3>%s</h3><dl><dt>Publisher</dt><dd>%s</dd><dt>File URL</dt><dd><a href="%s">%s</a></dd>'
                    '<dt>Licence</dt><dd>%s (<a href="%s">licence page</a>): <i>"%s"</i></dd><dt>Retrieved</dt><dd>%s UTC, %s bytes</dd>'
                    '<dt>SHA-256</dt><dd><code>%s</code></dd></dl></section>' % (
            esc(s["title"]), esc(s["publisher"]), esc(s["url"]), esc(s["url"]), esc(s["licence"]), esc(s["licence_url"]), esc(s["licence_evidence"]),
            esc(m["retrieved_at_utc"]), "{:,}".format(m["bytes"]), esc(m["sha256"])))
    rej = "".join("<li><b>%s</b>: %s</li>" % (esc(x["name"]), esc(x["reason"])) for x in REJECTED)
    body = ('<h1>Sources &amp; licences</h1><p>Every number on this site is read from one of these files. Each was downloaded by <code>fcp/fetch.py</code>; '
            'the URL, retrieval time and SHA-256 are in <code>data/manifest.json</code>, and <code>tests/test_data.py</code> re-reads the raw files and checks both. '
            'Licences were checked on the pages linked below on the retrieval date.</p>'
            '%s'
            '<h2>Considered and not used</h2><ul class="plain">%s</ul>'
            '<h2>Credits and attribution</h2><ul class="plain">'
            '<li>Electric car registrations: Ember, Monthly EV Sales Data, CC BY 4.0. Values aggregated to calendar years and shares here.</li>'
            '<li>Population: World Bank, World Development Indicators (SP.POP.TOTL), CC BY 4.0.</li>'
            '<li>Prices, fuel use, CO2: U.S. Energy Information Administration, Monthly Energy Review (public domain).</li>'
            '<li>Vehicle-miles and registrations: U.S. Federal Highway Administration, Highway Statistics (U.S. government work).</li>'
            '<li>Highway-vehicle pollutants: U.S. EPA, Air Pollutant Emissions Trends Data (non-commercial, educational use).</li>'
            '<li>Graph engine: <a href="https://github.com/hydra-db/hydradb">HydraDB</a> v0.4.0, Elastic License 2.0, used self-hosted for this hackathon only. '
            'It is not copied into this repository and not offered as a service; this site is a static snapshot of results computed with it.</li>'
            '<li>Project code: see the repository licence.</li></ul>') % ("".join(rows), rej)
    return body


PRIVACY = ('<h1>Privacy</h1><ul class="plain"><li>This is a static site. It sets no cookies, runs no analytics, loads no third-party scripts or fonts, and has no forms or accounts.</li>'
           '<li>The only script on the site runs the calculator in your browser; nothing you type leaves the page.</li>'
           '<li>The company that hosts the files may keep standard server logs (such as IP address and time of request) under its own policy. This project does not receive or use them.</li>'
           '<li>The project uses public data only. It contains no personal or business data.</li></ul>')
TERMS = ('<h1>Terms</h1><ul class="plain"><li>This site is an educational hackathon project. It is provided as is, without warranty of any kind.</li>'
         '<li>Nothing here is financial, investment, policy or engineering advice. The models are small and were tested on few years; see the limits on the results page.</li>'
         '<li>Data stays under its own licence (see <a href="sources.html">Sources &amp; licences</a>). EPA material is used for non-commercial, educational purposes.</li>'
         '<li>Correlations shown here describe co-movement. They do not establish cause.</li></ul>')
AI = ('<h1>AI disclosure</h1><ul class="plain"><li>The code, analysis and text of this project were written with an AI coding assistant (Claude, by Anthropic), directed by the project author.</li>'
      '<li>No AI model runs on this site or in the learning loop. The learning is plain recursive least squares; its weights are stored in HydraDB.</li>'
      '<li>No number on this site was written by hand or by the AI: every figure is generated by code from the downloaded files and the result files in the repository.</li>'
      '<li>The pass/fail rule was written and committed before the first run, and was not changed after the result was known.</li></ul>')


def build():
    c = Ctx()
    os.makedirs(SITE, exist_ok=True)
    pages = {
        "index.html": ("Fuel, Cars & Pollution — a self-refitting HydraDB graph", results_section(c) + how_section(c) + data_section(c),
                       "A HydraDB graph links crude oil, gasoline, miles driven, EVs, fuel use and transport CO2, and refits its links every year. Pre-registered walk-forward test."),
        "sources.html": ("Sources & licences — Fuel, Cars & Pollution", sources_page(c), "Every data file used, with URL, retrieval time, SHA-256 and licence."),
        "privacy.html": ("Privacy — Fuel, Cars & Pollution", PRIVACY, "Privacy notice."),
        "terms.html": ("Terms — Fuel, Cars & Pollution", TERMS, "Terms of use."),
        "ai.html": ("AI disclosure — Fuel, Cars & Pollution", AI, "How AI was used to build this project."),
    }
    for fname, (title, body, desc) in pages.items():
        with open(os.path.join(SITE, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(fname, title, body, desc))
    with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CSS.strip() + "\n")
    print("site built:", ", ".join(sorted(pages)))


if __name__ == "__main__":
    build()
