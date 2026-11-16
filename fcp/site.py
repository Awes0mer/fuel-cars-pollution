"""Build the static site in site/ from the processed data and result files.

Every number on the pages is read from data/processed/series.json,
data/manifest.json or results/*.json at build time.

Usage: python -m fcp.site
"""

import json
import os

from fcp.charts import esc, line_chart
from fcp.cite import citations, edition, software_citation
from fcp.fetch import MANIFEST, ROOT
from fcp.learn import LINKS, load_series, results_path
from fcp.sources import NOT_COVERED, REJECTED, SOFTWARE, SOURCES
from fcp.stats import CORR_OUT, SUMMARY_OUT

SITE = os.path.join(ROOT, "site")
ROUNDTRIP = os.path.join(ROOT, "results", "hydradb_float_roundtrip.json")
SITE_URL = "https://awes0mer.github.io/fuel-cars-pollution"
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0b5cad"/>'
    '<path d="M14 20h14M30 22l12 10M30 44l12-10M44 32h8" stroke="#fff" stroke-width="4" fill="none"/>'
    '<circle cx="14" cy="20" r="6" fill="#fff"/><circle cx="14" cy="44" r="6" fill="#fff"/><circle cx="44" cy="32" r="7" fill="#f2b600"/>'
    '<circle cx="54" cy="32" r="4" fill="#fff"/></svg>'
)
REPO_URL = "https://github.com/Awes0mer/fuel-cars-pollution"

NAV = [
    ("index.html", "Results"),
    ("index.html#how", "How it works"),
    ("index.html#data", "The data"),
    ("walkthrough.html", "Walkthrough"),
    ("sources.html", "Sources & licences"),
    ("ai.html", "AI disclosure"),
    ("privacy.html", "Privacy"),
    ("terms.html", "Terms"),
]

CSS = """
:root{--ink:#1b2124;--muted:#4d575c;--line:#d9ddd9;--paper:#fcfcfa;--concrete:#eff1ee;
--sign:#0b6b4f;--lane:#f2b400;--blue:#0b5cad;--rust:#b34d00;--alarm:#a4161a;--asphalt:#1f2629;
--display:"Bahnschrift","DIN Alternate","DIN Condensed","Barlow Semi Condensed","Roboto Condensed","Arial Narrow",system-ui,sans-serif;
--body:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--fg:var(--ink);--bad:var(--alarm);--good:var(--sign);color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;background:var(--paper);color:var(--ink);font:16.5px/1.6 var(--body)}
a{color:var(--blue);text-underline-offset:2px}
:focus-visible{outline:3px solid var(--lane);outline-offset:2px}
.skip{position:absolute;left:8px;top:-60px;z-index:50;background:var(--ink);color:#fff;padding:8px 12px;border-radius:6px}
.skip:focus{top:8px}
header.site{position:sticky;top:0;z-index:20;background:var(--paper);border-bottom:1px solid var(--line)}
header.site .in,main,footer .in{max-width:1080px;margin:0 auto;padding:0 20px}
header.site .in{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;padding-top:9px;padding-bottom:9px}
header.site .brand{margin-right:auto;text-decoration:none;color:#fff;background:var(--sign);border:2px solid #fff;box-shadow:0 0 0 1.5px var(--sign);border-radius:6px;padding:3px 10px;font:700 .92rem/1.25 var(--display);letter-spacing:.05em;text-transform:uppercase;white-space:nowrap}
header.site nav{display:flex;flex-wrap:wrap;gap:0 16px}
header.site nav a{font-size:.9rem;white-space:nowrap;color:var(--ink);text-decoration:none;padding:3px 0;border-bottom:2px solid transparent}
header.site nav a:hover{border-bottom-color:var(--lane)}
h1,h2,h3{font-family:var(--display);color:var(--ink)}
h1{font-size:clamp(2.1rem,4.6vw,3.35rem);line-height:1.04;margin:0 0 .7rem;font-weight:700;letter-spacing:-.01em}
h2{font-size:clamp(1.45rem,2.7vw,1.95rem);line-height:1.15;margin:0 0 .6rem;font-weight:700}
h3{font-size:1.2rem;line-height:1.25;margin:1.8rem 0 .5rem;font-weight:650}
.eyebrow{font:700 .78rem/1.2 var(--display);letter-spacing:.14em;text-transform:uppercase;color:var(--sign);margin:0 0 .45rem}
.lede{font-size:1.1rem;color:var(--muted);margin:0 0 1.1rem;max-width:62ch}
.lane{height:6px;margin:56px 0 36px;background:repeating-linear-gradient(90deg,var(--lane) 0 34px,transparent 34px 60px);border-radius:3px}
.btn{display:inline-block;font:700 .98rem/1.2 var(--display);letter-spacing:.02em;padding:11px 18px;border-radius:8px;border:2px solid var(--ink);color:var(--ink);background:#fff;text-decoration:none;margin:0 8px 8px 0}
.btn.primary{background:var(--sign);border-color:var(--sign);color:#fff}
.btn:hover{transform:translateY(-1px)}
.hero{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:40px;align-items:center;padding:44px 0 18px}
.pylon{justify-self:end;width:100%;max-width:410px}
.pylon .board{background:var(--asphalt);border-radius:12px;padding:12px;box-shadow:0 10px 24px rgba(20,28,32,.18)}
.pylon .top{background:var(--sign);color:#fff;border:2px solid #fff;border-radius:7px;text-align:center;padding:6px 8px;font:700 .82rem/1.2 var(--display);letter-spacing:.14em;text-transform:uppercase}
.pylon .verdict{color:#fff;text-align:center;font:700 2.1rem/1.1 var(--display);letter-spacing:.06em;margin:10px 0 2px}
.pylon .verdict.pass{color:#8fe3b8}.pylon .verdict.fail{color:#ff9b9b}
.pylon .what{color:#c9d2d6;text-align:center;font-size:.8rem;line-height:1.35;margin:0 6px 10px}
.pylon table{width:100%;border-collapse:separate;border-spacing:0 5px;margin:0;font-size:1rem}
.pylon th,.pylon td{border:0;padding:0}
.pylon tbody tr:nth-child(even){background:none}
.pylon thead th{background:none;color:#9fb0b7;font:600 .72rem/1.2 var(--display);letter-spacing:.1em;text-transform:uppercase;text-align:right;padding:0 8px}
.pylon thead th:first-child{text-align:left;padding-left:10px}
.pylon tbody th{color:#fff;font:600 .95rem/1.2 var(--display);letter-spacing:.03em;text-align:left;background:#11171a;padding:8px 10px;border-radius:6px 0 0 6px}
.pylon tbody td{background:#11171a;color:#ffb81c;font:700 1.55rem/1 var(--display);font-variant-numeric:tabular-nums;text-align:right;padding:6px 10px;text-shadow:0 0 10px rgba(255,170,0,.45)}
.pylon tbody td:last-child{border-radius:0 6px 6px 0;color:#ffd77a}
.pylon tbody tr.me th{box-shadow:inset 4px 0 0 var(--lane)}
.pylon .foot{color:#e7eced;font-size:.84rem;line-height:1.4;margin:8px 4px 2px}
.pylon .foot b{color:#ffb4a8}
.pylon .foot a{color:#9cd2ff}
.pylon .pole{width:26px;height:26px;margin:0 auto;background:linear-gradient(90deg,#7c868a,#b9c1c4,#7c868a)}
.caveats{background:#fff;border:1px solid var(--line);border-left:6px solid var(--alarm);border-radius:12px;padding:18px 20px 8px;margin:26px 0}
.caveats .eyebrow{color:var(--alarm)}
.caveats ul{padding-left:1.1rem;margin:.4rem 0 .6rem}
.caveats li{margin:.35rem 0}
.bars{display:grid;gap:12px;margin:12px 0 6px}
.bar-row{display:grid;grid-template-columns:minmax(150px,240px) 1fr 104px;gap:12px;align-items:center}
.bar-name{font:600 .98rem/1.25 var(--display)}
.bar-row.me .bar-name{color:var(--blue)}
.bar-track{display:grid;gap:4px}
.bar-track span{display:block;height:14px;border-radius:0 7px 7px 0;background:#8d989d}
.bar-row.me .bar-track span{background:var(--blue)}
.bar-track span.ex{height:9px;background:repeating-linear-gradient(135deg,#8d989d 0 4px,#c7cfd2 4px 7px)}
.bar-row.me .bar-track span.ex{background:repeating-linear-gradient(135deg,var(--blue) 0 4px,#9fc3e8 4px 7px)}
.bar-val{font:700 1.15rem/1.15 var(--display);font-variant-numeric:tabular-nums;text-align:right}
.bar-val small{display:block;font:500 .8rem/1.2 var(--body);color:var(--muted)}
.bar-key{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:.85rem;color:var(--muted);margin:4px 0 0}
.bar-key i{display:inline-block;width:26px;height:10px;border-radius:0 5px 5px 0;background:#8d989d;margin-right:6px;vertical-align:middle}
.bar-key i.ex{background:repeating-linear-gradient(135deg,#8d989d 0 4px,#c7cfd2 4px 7px)}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h3{margin-top:.2rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}
.stat{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stat b{display:block;font:700 1.45rem/1.15 var(--display);font-variant-numeric:tabular-nums}
.stat span{font-size:.84rem;color:var(--muted)}
.pass{color:var(--good);font-weight:700} .fail{color:var(--bad);font-weight:700}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.92rem;margin:.4rem 0;font-variant-numeric:tabular-nums}
th,td{border-bottom:1px solid var(--line);padding:6px 9px;text-align:right;vertical-align:top}
thead th{background:var(--concrete);font:600 .8rem/1.25 var(--display);letter-spacing:.04em;text-transform:uppercase;color:#3b4448}
tbody tr:nth-child(even){background:#f8f9f7}
th:first-child,td:first-child{text-align:left}
caption{text-align:left;color:var(--muted);font-size:.85rem;padding:4px 0 6px}
table.text td,table.text th{text-align:left}
figure{margin:0;background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px 10px}
figure + figure{margin-top:18px}
.chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr));gap:18px;margin:12px 0 8px}
.chart-grid figure + figure{margin-top:0}
.wide{margin:18px 0}
.ctitle{font:650 1.04rem/1.3 var(--display);margin-bottom:4px}
svg.chart{width:100%;height:auto;display:block;background:#fff}
svg.chart .grid{stroke:#eceeec;stroke-width:1}
svg.chart .zero{stroke:#8a939c;stroke-width:1.2}
svg.chart .tick{font-size:15px;fill:#4d575c;font-family:var(--body)}
svg.chart .axis{font-size:15px;fill:#4d575c;font-family:var(--body)}
.legend{list-style:none;padding:0;margin:4px 0 6px;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:.86rem}
.legend li{display:flex;align-items:center;gap:6px}
.source,.note{font-size:.8rem;line-height:1.45;color:var(--muted);margin:.4rem 0}
.source{overflow-wrap:anywhere}
.flag{color:var(--bad);font-size:.8rem}
details{margin:.4rem 0}
summary{cursor:pointer;color:var(--blue);font-size:.88rem;font-weight:600}
code{background:var(--concrete);padding:1px 4px;border-radius:3px;font-size:.88em;overflow-wrap:anywhere}
output{font-weight:700}
.rbar{display:inline-block;height:10px;vertical-align:middle;border-radius:2px;margin-left:6px}
.rbar.pos{background:var(--rust)}.rbar.neg{background:var(--blue)}
footer{margin-top:56px;background:var(--concrete);border-top:6px solid var(--lane)}
footer .in{padding-top:18px;padding-bottom:28px;font-size:.86rem;color:var(--muted)}
ul.plain{padding-left:1.2rem}
main > h1:first-child{margin-top:1.8rem}
@media (max-width:820px){
.hero{grid-template-columns:1fr;gap:26px;padding-top:28px}
header.site{position:static}
html{scroll-padding-top:0}
.pylon{justify-self:stretch;max-width:none}
.bar-row{grid-template-columns:1fr 84px;gap:4px 10px}
.bar-name{grid-column:1/-1}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.btn:hover{transform:none}}
.flowcard{border:1px solid var(--line);border-radius:14px;background:#fff;padding:20px 20px 14px;margin:22px 0;box-shadow:0 2px 10px rgba(20,28,32,.05)}
.flow-h{border:0;padding:0;margin:.1rem 0 .4rem}
.flow-lede{margin:.2rem 0 .8rem;color:var(--muted)}
.k-up{color:#9a4100;font-weight:600}.k-down{color:#0a4f96;font-weight:600}
.presets{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px}
.presets button,.replay-controls button{font:600 .92rem/1.2 var(--display);letter-spacing:.02em;padding:8px 14px;border-radius:999px;border:1.5px solid var(--ink);background:#fff;color:var(--ink);cursor:pointer;min-height:40px}
.presets button:hover,.replay-controls button:hover{background:var(--ink);color:#fff}
#lr-play{background:var(--sign);border-color:var(--sign);color:#fff;min-width:84px}
.presets button:focus-visible,.replay-controls button:focus-visible,input[type=range]:focus-visible{outline:3px solid #f2b600;outline-offset:2px}
.flow-stage{position:relative;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-template-areas:"crude gas . ." ". vmt fuel co2" ". ev . .";column-gap:92px;row-gap:18px;align-items:center;padding:10px 4px 14px}
.flow-wires{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;pointer-events:none;z-index:0}
.fnode{position:relative;z-index:1;background:#fff;border:2px solid #c9d1da;border-radius:12px;padding:8px 10px;text-align:center;transition:border-color .35s,background-color .35s;min-width:0}
.fnode[data-node=Crude]{grid-area:crude}.fnode[data-node=Gasoline]{grid-area:gas}.fnode[data-node=VMT]{grid-area:vmt}
.fnode[data-node=EVShare]{grid-area:ev}.fnode[data-node=FuelUse]{grid-area:fuel}.fnode[data-node=CO2]{grid-area:co2}
.fnode .nm{font-size:.8rem;color:var(--muted);line-height:1.2}
.fnode .valrow{font-family:var(--display);font-size:1.4rem;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.fnode .arr{font-size:.8rem;vertical-align:2px}
.fnode .sub{font-size:.74rem;color:var(--muted);line-height:1.2;margin-top:2px;min-height:1.2em}
.fnode.up{border-color:#d9822b;background:#fff8f1}.fnode.up .valrow{color:#9a4100}
.fnode.down{border-color:#3d7fc4;background:#f2f7fd}.fnode.down .valrow{color:#0a4f96}
.fnode.flash{animation:flash .7s ease-out}
@keyframes flash{0%{box-shadow:0 0 0 0 rgba(242,182,0,.75);transform:scale(1.05)}100%{box-shadow:0 0 0 14px rgba(242,182,0,0);transform:scale(1)}}
.wire-bg{fill:none;stroke:#fff;stroke-width:14px;stroke-linecap:round}
.wire{fill:none;stroke-linecap:round;transition:stroke-width .6s ease,stroke .4s}
.wire.flat{stroke:#b9c1ca}.wire.up{stroke:#e8a465}.wire.down{stroke:#7aaadb}
.mk-flat{fill:#9aa3ad}.mk-up{fill:#c9661a}.mk-down{fill:#3d7fc4}
.dots.up circle{fill:#b34d00}.dots.down circle{fill:#0b5cad}
.wire-label{font-size:12.5px;font-weight:700;fill:#3d4650;paint-order:stroke;stroke:#fff;stroke-width:4px}
.flow-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px 18px;margin:8px 0}
.flow-controls label,.yr-slider{font-size:.9rem;color:var(--muted)}
.flow-controls output{font-weight:700;color:var(--fg);margin-left:4px}
input[type=range]{width:100%;accent-color:#0b5cad;min-height:28px}
.flow-summary{font-weight:600;min-height:3em;margin:.4rem 0}
.steps{list-style:none;padding:0;margin:4px 0 10px;display:flex;flex-wrap:wrap;gap:6px}
.step{padding:5px 12px;border-radius:999px;background:#e9edf1;color:#4b5560;font-size:.86rem;transition:background-color .3s,color .3s}
.step.on{background:var(--sign);color:#fff}
.replay-controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:6px 0}
.yr-slider{flex:1 1 220px;display:flex;align-items:center;gap:8px}
.lr-panel{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px 12px;margin:8px 0;padding:0}
.lr-panel div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.lr-panel dt{font-size:.78rem;color:var(--muted)}.lr-panel dd{margin:0;font-weight:700;font-variant-numeric:tabular-nums}
.err-strip .bar{fill:#0b5cad}.err-strip .bar.cur{fill:#f2b600}
.err-strip .clip{fill:#0b5cad}.err-strip .clip.nc{fill:#5b6570}
.err-strip .nc-dot{fill:#5b6570}.err-strip .band{fill:#e6eef8}.err-strip .band-label,.err-strip .yr{font-size:12px;fill:#4b5560}
figure.strip{margin:8px 0 4px}
@media (max-width:699px){
.flow-stage{grid-template-columns:repeat(3,minmax(0,1fr));grid-template-areas:"crude . ." "gas vmt ev" "fuel fuel fuel" "co2 co2 co2";column-gap:8px;row-gap:46px}
.fnode[data-node=FuelUse],.fnode[data-node=CO2]{justify-self:center;width:64%}
.fnode .valrow{font-size:1rem;white-space:normal;overflow-wrap:anywhere}
.fnode{padding:7px 5px}
.fnode .nm{font-size:.72rem}
.flowcard{padding:14px 12px 10px}
}
@media (prefers-reduced-motion:reduce){.wire,.fnode,.step{transition:none}.fnode.flash{animation:none}}
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
        '<link rel="icon" href="favicon.svg" type="image/svg+xml">'
        '<meta property="og:type" content="website"><meta property="og:title" content="%s"><meta property="og:description" content="%s">'
        '<meta property="og:image" content="%s/og.png"><meta property="og:url" content="%s/%s"><meta name="twitter:card" content="summary_large_image">'
        '<link rel="stylesheet" href="style.css"></head><body>'
        '<a class="skip" href="#main">Skip to content</a>'
        '<header class="site"><div class="in"><a class="brand" href="index.html">Fuel, Cars &amp; Pollution</a><nav aria-label="Site">%s</nav></div></header>'
        '<main id="main">%s</main>'
        '<footer><div class="in">Built for the HydraDB Hackathon (Track 1). Data: U.S. EIA, FHWA and EPA (U.S. government works), '
        'World Bank (CC BY 4.0), Ember (CC BY 4.0). Graph engine: HydraDB v0.4.0, self-hosted (Elastic License 2.0). '
        'Independent hackathon entry; not made or endorsed by HydraDB. This page is a static snapshot of the results. <a href="sources.html">Sources &amp; licences</a> · '
        '<a href="ai.html">AI disclosure</a> · <a href="privacy.html">Privacy</a> · <a href="terms.html">Terms</a> · '
        '<a href="%s">Code</a></div></footer></body></html>'
    ) % (esc(title), esc(description), esc(title), esc(description), SITE_URL, SITE_URL, fname, nav, body, REPO_URL)


class Ctx:
    def __init__(self):
        self.series = load_series()
        self.manifest = {e["id"]: e for e in load_json(MANIFEST)["files"]}
        self.src = {s["id"]: s for s in SOURCES}
        self.res = load_json(results_path())
        self.corr = load_json(CORR_OUT)
        self.summ = load_json(SUMMARY_OUT)
        self.rt = load_json(ROUNDTRIP) if os.path.exists(ROUNDTRIP) else None
        self.editions = {}

    def source_line(self, source_ids):
        bits = []
        for sid in source_ids:
            s, m = self.src[sid], self.manifest[sid]
            ed = self.editions.setdefault(sid, edition(sid))
            bits.append('%s — %s%s (%s); retrieved %s UTC; SHA-256 <code>%s…</code>; <a href="%s">file</a>' % (
                esc(s["publisher"]), esc(s["title"]), (", " + esc(ed)) if ed else "", esc(s["licence"]),
                esc(m["retrieved_at_utc"].replace("T", " ").replace("+00:00", "")), esc(m["sha256"][:16]), esc(s["url"])))
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


def strength(w):
    a = abs(w)
    return "strongly" if a >= 0.5 else "partly" if a >= 0.1 else "barely"


def note_2008(r):
    row = next((p for p in r["per_year"] if p["year"] == 2008), None)
    if not row or row["actual_co2"] is None or row["inputs"].get("VMT") is None:
        return ""
    return " In 2008 its inputs moved far less than CO2 did: miles driven %+.1f vs CO2 %+.1f (100·ln points)." % (row["inputs"]["VMT"], row["actual_co2"])


def design_line(sc):
    g, k = sc["graph"]["design_mae"], sc["knn"]["design_mae"]
    if k < g:
        return "On the design years 1982–2004, k-NN did better than the graph (%s vs %s)." % (pct(k), pct(g))
    return "On the design years 1982–2004, the graph did better than k-NN (%s vs %s)." % (pct(g), pct(k))


def vmt_line(s):
    v, e = s["vmt_check"], s["excluding_2011"]
    out = ("FHWA&rsquo;s VM-203 table (the pre-registered miles source) puts %d at %+.2f%% versus FHWA&rsquo;s own VM-1 table; the other %d years agree within %.2f%%." % (
        v["worst_year"], v["worst_gap_pct"], v["years_compared"] - 1, v["max_other_gap_pct"]))
    if "next_year" in v:
        out += (" That makes the %d miles change %+.2f instead of %+.2f. The official run keeps VM-203 as pre-registered; scored without %d (n = %d): "
                "graph %s, no change %s, k-NN %s, frozen %s." % (
                    v["next_year"], v["next_change_vm203"], v["next_change_vm1"], v["next_year"], e["n"],
                    pct(e["graph"]), pct(e["no_change"]), pct(e["knn"]), pct(e["frozen_graph"])))
    return out


def gap_note(c, first, last):
    span = str(first) if first == last else "%d–%d" % (first, last)
    from fcp.learn import REQUIRED_INPUTS, VAR_SERIES, changes

    ch = changes(c.series)
    missing = sorted({v for y in range(first, last + 1) for v in REQUIRED_INPUTS if ch[v].get(y) is None})
    names = {"Crude": "crude oil price", "Gasoline": "gasoline price", "VMT": "miles driven"}
    why = ", ".join(names[v] for v in missing) or "an input"
    return "%s skipped: no prediction, because the %s change is missing (%s)." % (span, why, ", ".join(c.series[VAR_SERIES[v]]["sources"][0] for v in missing))


def rerun_note(sc, r):
    path = os.path.join(ROOT, "results", "archive", "run3_learning_results.json")
    if not os.path.exists(path):
        return ""
    prev = load_json(path)
    return ('<p class="note">k-NN was rerun once: an independent review found that run 3 only used neighbour years with every other input present, which the '
            'pre-registration does not ask for. Run 3 tuned k = %d, window %s, holdout %s; this run follows the pre-registered wording and re-tunes on the design '
            'years only: k = %d, window %s, holdout %s. Nothing else changed. Run 3 is archived in <code>results/archive/</code>.</p>' % (
                prev["tuning"]["knn_k"], prev["tuning"]["knn_window"] or "all", pct(prev["scores_co2"]["knn"]["holdout_mae"]),
                r["tuning"]["knn_k"], r["tuning"]["knn_window"] or "all", pct(sc["knn"]["holdout_mae"])))


def pct(v):
    return "%.2f" % v


def hero(c):
    r, s = c.res, c.summ
    sc = r["scores_co2"]
    ex = s["excluding_2020_2021"]
    rows = [("graph", "HydraDB graph"), ("no_change", "No change"), ("knn", "Vector k-NN"), ("frozen_graph", "Frozen graph")]
    board = "".join('<tr%s><th scope="row">%s</th><td>%s</td><td>%s</td></tr>' % (
        ' class="me"' if k == "graph" else "", esc(n), pct(sc[k]["holdout_mae"]), pct(ex[k])) for k, n in rows)
    beaten_by = [n for k, n in rows[1:] if ex["graph"] > ex[k]]
    if len(beaten_by) == 3:
        foot = "Without 2020–21 the graph <b>loses to all three</b>."
    elif beaten_by:
        foot = "Without 2020–21 the graph <b>loses to %s</b>." % esc(", ".join(beaten_by))
    else:
        foot = "Without 2020–21 the graph still leads."
    first = r["per_year"][0]["year"]
    last = max(p["year"] for p in r["per_year"] if p["actual_co2"] is not None)
    return (
        '<section class="hero" aria-labelledby="hero-h"><div>'
        '<p class="eyebrow">HydraDB Hackathon · Track 1 · U.S. data %d–%d</p>'
        '<h1 id="hero-h">Oil to tailpipe: a graph that refits its own links every year</h1>'
        '<p class="lede">Crude oil prices, pump prices, miles driven and electric cars feed a small graph that predicts the yearly change in U.S. transport CO2. '
        'Each link\'s strength lives in HydraDB and is refit from official data every year, so every miss changes the next guess.</p>'
        '<p><a class="btn primary" href="#shock-flow">Push oil prices through the graph</a><a class="btn" href="walkthrough.html">Watch the walkthrough</a>'
        '<a class="btn" href="#caveats">Read the caveats first</a></p></div>'
        '<aside class="pylon" aria-label="Pre-registered test result"><div class="board"><div class="top">Pre-registered test</div>'
        '<div class="verdict %s">%s</div><p class="what">Average miss on the yearly CO2 change, in points. Lower is better. %d holdout years.</p>'
        '<table><thead><tr><th scope="col">Model</th><th scope="col">2005–24</th><th scope="col">w/o 2020–21</th></tr></thead><tbody>%s</tbody></table>'
        '<p class="foot">%s <a href="#caveats">Why that matters</a> · <a href="%s/blob/main/PREREGISTRATION.md">Rule, committed before the first run</a></p></div>'
        '<div class="pole" aria-hidden="true"></div></aside></section>'
    ) % (first, last, "pass" if r["verdict"] == "PASS" else "fail", esc(r["verdict"]), sc["graph"]["holdout_n"], board, foot, REPO_URL)


def score_bars(sc, ex, names):
    order = ["graph", "no_change", "knn", "frozen_graph", "direct_regression"]
    top = max(max(sc[m]["holdout_mae"], ex[m]) for m in order) * 1.04
    out = []
    for m in order:
        out.append('<div class="bar-row%s"><div class="bar-name">%s</div><div class="bar-track" aria-hidden="true">'
                   '<span style="width:%.1f%%"></span><span class="ex" style="width:%.1f%%"></span></div>'
                   '<div class="bar-val">%s<small>%s w/o 2020–21</small></div></div>' % (
                       " me" if m == "graph" else "", esc(names[m]), 100 * sc[m]["holdout_mae"] / top, 100 * ex[m] / top,
                       pct(sc[m]["holdout_mae"]), pct(ex[m])))
    return ('<div class="bars">%s</div><p class="bar-key"><span><i></i>all %d holdout years</span><span><i class="ex"></i>without 2020–21 (%d years)</span></p>' % (
        "".join(out), sc["graph"]["holdout_n"], ex["n"]))


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
    out.append(hero(c))
    out.append(shock_flow(c))
    lose_all = all(ex["graph"] > ex[m] for m in ("no_change", "knn", "frozen_graph"))
    out.append('<section class="caveats" id="caveats" aria-labelledby="cav-h"><p class="eyebrow">Before you trust the verdict</p>'
               '<h2 id="cav-h">%s</h2><ul>'
               '<li>Without 2020 and 2021 (n = %d) the graph\'s average miss is <b>%s</b> points: it %s no change (%s), %s k-NN (%s) and %s its own frozen version (%s).</li>'
               '<li>%s 95%% bootstrap interval of the difference includes zero. With n = %d years, the ranking is not statistically settled.</li>'
               '<li>Year by year, the graph beats no change in %d of %d years and k-NN in %d of %d.</li>'
               '<li>Its largest misses: %s.%s</li>'
               '<li>%s</li>'
               '<li>%s</li>'
               '<li>Inputs are today&rsquo;s revised figures, not the first-release values available at the time; real-time accuracy is unmeasured.</li>'
               '<li>2009 and 2010 are not scored: FHWA&rsquo;s VM-203 table, the pre-registered miles source, marks 2009 as unavailable.</li>'
               '<li>The k-NN baseline was rerun once to match the pre-registered wording exactly; see the scores below.</li></ul></section>' % (
                   ("The pass rests on two pandemic years" if r["verdict"] == "PASS" else "It failed, and here is by how much") if lose_all else "Read the limits first",
                   ex["n"], pct(ex["graph"]), lw(ex, "no_change"), pct(ex["no_change"]), lw(ex, "knn"), pct(ex["knn"]), lw(ex, "frozen_graph"), pct(ex["frozen_graph"]),
                   "Every" if all(v["low"] <= 0 <= v["high"] for v in r["bootstrap_95"].values()) else "Not every", s["holdout_n"],
                   wins["no_change"], s["holdout_n"], wins["knn"], s["holdout_n"], esc(worst), note_2008(r),
                   design_line(sc), vmt_line(s)))
    out.append(replay_flow(c))
    out.append('<section id="scores" aria-labelledby="scores-h"><div class="lane" aria-hidden="true"></div><p class="eyebrow">Scores</p>'
               '<h2 id="scores-h">Average miss on the yearly change in U.S. transport CO2</h2>'
               '<p class="lede">Percentage points of 100·ln change, holdout 2005–2024 (n = %d). Lower is better. Settings were picked on 1982–2004 only.</p>%s%s'
               '<details><summary>Table: holdout, without 2020–21, and design-period scores</summary><div class="tablewrap"><table><caption>MAE of the predicted yearly change in U.S. transport CO2</caption>'
               '<thead><tr><th scope="col">Model</th><th scope="col">Holdout MAE</th><th scope="col">n</th><th scope="col">Without 2020–21 (n=%d)</th><th scope="col">Design MAE (n=%d)</th></tr></thead><tbody>%s</tbody></table></div></details>'
               % (sc["graph"]["holdout_n"], score_bars(sc, ex, names), rerun_note(sc, r), ex["n"], sc["graph"]["design_n"], rows))
    out.append('<div class="card wide"><h3>The pre-registered rule</h3><p class="note">All four parts must pass. <a href="%s/blob/main/PREREGISTRATION.md">Rule text</a>, committed before the first run.</p>'
               '<div class="tablewrap"><table><thead><tr><th scope="col">Part</th><th scope="col">Threshold</th><th scope="col">Value</th><th scope="col">Margin</th><th scope="col">Result</th></tr></thead><tbody>%s</tbody></table></div></div>' % (REPO_URL, rule_rows))
    out.append('<div class="card wide"><h3>Uncertainty</h3><p class="note">Paired bootstrap 95%% interval of the holdout MAE difference (negative = graph better); %d resamples, seed %d.</p>'
               '<div class="tablewrap"><table><thead><tr><th scope="col">Comparison</th><th scope="col">95%% interval (pp)</th></tr></thead><tbody>%s</tbody></table></div></div>' % (
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
                          shade=(2005, 2024, "holdout"), width=760, height=380))
    nc = hy["node_counts"]
    out.append('<h3>HydraDB in this run</h3>'
               '<div class="stats"><div class="stat"><b>%s</b><span>HTTP queries for the full walk-forward</span></div>'
               '<div class="stat"><b>%s s</b><span>wall time, local graph-node</span></div>'
               '<div class="stat"><b>%s</b><span>link-history nodes (one per link per year)</span></div>'
               '<div class="stat"><b>%s</b><span>prediction nodes</span></div>'
               '<div class="stat"><b>%.3g</b><span>largest HydraDB vs in-memory gap, points (limit 1e-9)</span></div></div>'
               '<p class="note">Self-hosted <code>graph-node</code> v0.4.0 in local mode: loopback only, new empty store, new random token, usage reporting off. '
               'Parity is not bit-identical: %s</p>' % (
                   "{:,}".format(hy["http_requests"]), hy["seconds"], "{:,}".format(nc.get("LinkState", 0)), "{:,}".format(nc.get("Prediction", 0)),
                   hy["parity"]["max_abs_diff"],
                   ("in a separate test HydraDB returned %d of %d floats one unit in the last place away from what was written; this is a likely cause of the gap, not a proven one." % (c.rt["mismatches"], c.rt["values_tested"])) if c.rt else "cause not measured."))
    return "".join(out)


def weights_table(w):
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td>%.4f</td></tr>' % (esc(t), esc(k.replace("->", " → ")), v)
                   for t in ("Gasoline", "FuelUse", "CO2") for k, v in w[t].items())
    return ('<details><summary>Data table: learned link strengths after the last refit</summary><div class="tablewrap"><table>'
            '<caption>Final weights and intercepts per target node</caption><thead><tr><th scope="col">Target</th><th scope="col">Term</th>'
            '<th scope="col">Value</th></tr></thead><tbody>%s</tbody></table></div></details>' % rows)




def how_section(c):
    r = c.res
    wy = r["link_weights_by_year"]
    lines = []
    for lid, a, b in LINKS:
        key = "%s->%s" % (a, b)
        lines.append({"label": key.replace("->", " → ").replace("VMT", "Miles driven").replace("EVShare", "EV share").replace("FuelUse", "Fuel use"),
                      "values": {y: wy[y][b][key] for y in wy}, "flags": {}})
    out = ['<div class="lane" aria-hidden="true"></div><p class="eyebrow">Method</p><h2 id="how">How it works</h2>',
           '<p>Each year, at the moment the year closes, the graph is asked: by how much did U.S. transport CO2 change? It knows that year\'s crude oil price, gasoline price, '
           'vehicle-miles driven and electric share of new car sales. It does not yet know fuel use or CO2.</p>',
           '<ol><li><b>Predict.</b> HydraDB is queried for the links pointing into "Fuel use" (a graph walk from the target node), their weights are read, and fuel use is predicted. '
           'Then the links into "CO2" are read and the <i>predicted</i> fuel use is pushed one more hop to CO2.</li>'
           '<li><b>Correct.</b> When the real figures arrive, each target\'s weights are refit by recursive least squares with forgetting factor λ = %s (picked on 1982–2004 only), '
           'and written back to HydraDB. A per-year history node is written for every link, and every prediction is stored as a node too.</li>'
           '<li><b>Repeat</b> for the next year with the corrected weights.</li></ol>' % r["tuning"]["graph_lambda"],
           '<p>Links are modelled as <b>nodes</b>, not edges: HydraDB v0.4.0 deduplicates edges on (source, target, type), so a link with a changing weight and a history needs its own node. '
           'The same code runs on an in-memory store; the two runs must agree (parity).</p>',
           '<p class="note"><b>Weak link:</b> the EV share → fuel use weight is not pinned down. It is learned from %d years only and swung between %.2f and %.2f after 2012. '
           'Read it as "unknown", not as a measured effect of EVs.</p>' % (c.summ["ev_link_weight_range_2012_on"]["ev_years_used"],
                                                                            c.summ["ev_link_weight_range_2012_on"]["min"], c.summ["ev_link_weight_range_2012_on"]["max"]),
           line_chart("weights", "Learned link strengths, refit every year", "Each line is one link weight in HydraDB after each yearly refit, 1977 to the last year with data.",
                      lines, "weight", "Source: results/learning_results.json (link_weights_by_year), learned from the EIA, FHWA and Ember files listed on the sources page.",
                      y_zero=True, digits=3, width=760, height=360)]
    return "".join(out)


FLOW_NODES = [
    ("Crude", "Crude oil price"),
    ("Gasoline", "Gasoline price"),
    ("VMT", "Miles driven"),
    ("EVShare", "EV share of new cars"),
    ("FuelUse", "Gasoline burned"),
    ("CO2", "Transport CO2"),
]


def flow_stage(label, sub=False):
    nodes = "".join(
        '<div class="fnode flat" data-node="%s"><div class="nm">%s</div>'
        '<div class="valrow"><span class="arr" aria-hidden="true">●</span> <span class="val">—</span></div>%s</div>' % (
            k, esc(n), '<div class="sub"></div>' if sub else "")
        for k, n in FLOW_NODES)
    return '<div class="flow-stage" role="group" aria-label="%s"><svg class="flow-wires" aria-hidden="true"></svg>%s</div>' % (esc(label), nodes)


def flow_data(c):
    r = c.res
    years = []
    prev = None
    for p in r["per_year"]:
        note = ""
        if prev is not None and p["year"] != prev + 1:
            note = gap_note(c, prev + 1, p["year"] - 1)
        years.append({"year": p["year"], "period": p["period"], "inputs": p["inputs"], "pred": p["graph"], "pred_fuel": p["graph_fuel"],
                      "actual": p["actual_co2"], "actual_fuel": p["actual_fuel"], "knn": p["knn"], "note": note})
        prev = p["year"]
    data = {"weights": r["final_weights"], "history": r["link_weights_by_year"], "years": years,
            "holdout_start": min(r["config"]["holdout_years_scored"])}
    return json.dumps(data, separators=(",", ":")).replace("</", "<\\/")


def shock_flow(c):
    w = c.res["final_weights"]
    last = max(p["year"] for p in c.res["per_year"] if p["actual_co2"] is not None)
    return (
        '<section class="flowcard" id="shock-flow" aria-labelledby="shock-h">'
        '<h2 id="shock-h" class="flow-h">Follow a price change through the graph</h2>'
        '<p class="flow-lede">Push oil prices up or down and watch the effect travel link by link: crude oil → gasoline price → gasoline burned → transport CO2. '
        'Miles driven and electric cars feed in too. Wire thickness is the learned link strength; moving dots show which way each link pushes '
        '(<span class="k-up">orange ▲ pushes up</span>, <span class="k-down">blue ▼ pushes down</span>).</p>'
        '<div class="presets" role="group" aria-label="Scenarios">'
        '<button type="button" data-preset="50,0,0">Oil +50%%</button>'
        '<button type="button" data-preset="-50,0,0">Oil −50%%</button>'
        '<button type="button" data-preset="0,-10,0">Driving −10%%</button>'
        '<button type="button" data-preset="0,0,5">EV share +5 pts</button>'
        '<button type="button" data-preset="30,2,1">Oil +30%%, driving +2%%, EVs +1 pt</button>'
        '<button type="button" data-preset="0,0,0">Reset</button></div>'
        '%s'
        '<div class="flow-controls">'
        '<label>Crude oil price change <output id="fx-crude-v"></output><input id="fx-crude" type="range" min="-60" max="60" step="1" value="30"></label>'
        '<label>Miles driven change <output id="fx-vmt-v"></output><input id="fx-vmt" type="range" min="-15" max="15" step="0.5" value="0"></label>'
        '<label>EV share of new cars change <output id="fx-ev-v"></output><input id="fx-ev" type="range" min="-5" max="10" step="0.5" value="0"></label></div>'
        '<p class="flow-summary" aria-live="polite"></p>'
        '<p class="note">What the links say, in plain words: oil price changes pass %s into pump prices (×%.2f); pump price changes move gasoline burned %s (×%.2f); '
        'miles driven move it %s (×%.2f). Changes are entered and shown in percent; the model works in log points (100·ln) and converts. '
        'Effects only: the yearly trend terms are left out so you see what each change does. '
        'This is arithmetic on the weights learned through %d; it was not tested as a scenario model, and co-movement is not proof of cause.</p>'
        '<noscript><p class="note">The animation needs JavaScript. The learned weights are in the table below.</p></noscript>'
        '<p class="source">Source: learned link weights in <code>results/learning_results.json</code> (<code>final_weights</code>), fitted on EIA, FHWA and Ember files listed on the '
        '<a href="sources.html">sources page</a>.</p>%s</section>'
    ) % (flow_stage("Price-change flowchart: crude oil, gasoline price, miles driven and EV share feed gasoline burned, which feeds transport CO2"),
         strength(w["Gasoline"]["Crude->Gasoline"]), w["Gasoline"]["Crude->Gasoline"], strength(w["FuelUse"]["Gasoline->FuelUse"]), w["FuelUse"]["Gasoline->FuelUse"],
         strength(w["FuelUse"]["VMT->FuelUse"]), w["FuelUse"]["VMT->FuelUse"], last, weights_table(w))


def replay_flow(c):
    r = c.res
    return (
        '<section class="flowcard" id="learn-flow" aria-labelledby="learn-h">'
        '<h2 id="learn-h" class="flow-h">Watch it learn, year by year</h2>'
        '<p class="flow-lede">Each year the graph runs the same loop. Press play to replay %d–%d: the wires change thickness as HydraDB stores the refitted link strengths.</p>'
        '<ol class="steps" aria-label="The yearly loop"><li class="step">1 Predict with last year\'s links</li><li class="step">2 Compare with EIA\'s figure</li>'
        '<li class="step">3 Refit the links (λ = %s)</li><li class="step">4 Write links + prediction to HydraDB</li></ol>'
        '<div class="replay-controls"><button type="button" id="lr-prev" aria-label="Previous year">◀</button>'
        '<button type="button" id="lr-play" aria-pressed="false">Play</button><button type="button" id="lr-next" aria-label="Next year">▶</button>'
        '<label class="yr-slider">Year <input id="lr-year" type="range" min="0" max="0" step="1" value="0"></label></div>'
        '%s'
        '<dl class="lr-panel"><div><dt>Year</dt><dd data-f="year"></dd></div><div><dt>Period</dt><dd data-f="period"></dd></div>'
        '<div><dt>Predicted CO2 change</dt><dd data-f="pred"></dd></div><div><dt>Actual (EIA)</dt><dd data-f="actual"></dd></div>'
        '<div><dt>Graph miss</dt><dd data-f="err"></dd></div><div><dt>No-change miss</dt><dd data-f="nc"></dd></div><div><dt>k-NN miss</dt><dd data-f="knn"></dd></div></dl>'
        '<p class="note">Changes are shown in percent. Misses are in points of 100·ln change, the unit the test is scored in.</p>'
        '<p class="note" data-f="note" aria-live="polite"></p>'
        '<figure class="strip"><figcaption class="ctitle">Graph miss by year (bars) and no-change miss (dots), points of 100·ln CO2 change; ▲ marks a value above the top of the strip</figcaption>'
        '<svg class="err-strip chart" role="img" aria-label="Absolute error of the graph per year, with the no-change error as dots; the data table is under the Predicted vs actual chart."></svg>'
        '<p class="source">Source: <code>results/learning_results.json</code> (<code>per_year</code>, <code>link_weights_by_year</code>). Data tables: '
        '<a href="#pred">predicted vs actual</a> and <a href="#weights">learned link strengths</a>.</p></figure></section>'
    ) % (r["per_year"][0]["year"], r["per_year"][-1]["year"], r["tuning"]["graph_lambda"],
         flow_stage("Learning-replay flowchart showing one year's inputs, predictions and link strengths", sub=True))




def data_section(c):
    out = ['<div class="lane" aria-hidden="true"></div><p class="eyebrow">Official data</p><h2 id="data">The data behind the graph</h2>',
           '<p class="lede">U.S. and world series sit on separate charts. Sales, vehicles in use and miles driven are separate series. Lines are never joined across sources, '
           'and missing years leave gaps.</p>',
           '<h3>Fuel</h3><div class="chart-grid">',
           c.chart("crude", "U.S. crude oil price (refiner acquisition cost)", "Annual average U.S. refiner acquisition cost of crude oil, composite, 1968 onward.",
                   ["us_crude_rac"], "dollars per barrel", unit_note="dollars per barrel, nominal"),
           c.chart("brent", "Brent crude oil spot price (world benchmark)", "Annual average Brent spot price, 1987 onward.", ["world_brent"], "dollars per barrel", unit_note="dollars per barrel, nominal"),
           c.chart("gas", "U.S. retail gasoline price, two separate EIA series", "Leaded regular 1949-1990 and unleaded regular 1976 onward, shown as separate lines.",
                   ["us_gasoline_leaded", "us_gasoline_unleaded"], "dollars per gallon", labels={"us_gasoline_leaded": "Leaded regular", "us_gasoline_unleaded": "Unleaded regular"},
                   unit_note="dollars per gallon including taxes, nominal"),
           c.chart("fuel", "U.S. motor gasoline consumed by transportation", "Thousand barrels per day, 1949 onward.", ["us_motor_gasoline_use"], "thousand barrels/day"),
           '</div><h3>Cars and driving</h3><div class="chart-grid">',
           c.chart("vmt", "U.S. vehicle-miles traveled, all roads", "Millions of vehicle-miles per year, 1957 to 2024; 2009 unavailable.", ["us_vmt"], "million vehicle-miles"),
           c.chart("veh", "U.S. registered vehicles per 1,000 people", "FHWA registrations divided by World Bank population, 2000 to 2024.", ["us_vehicles_per_1000"], "vehicles per 1,000 people", digits=0),
           c.chart("newcars", "U.S. new car registrations (all drivetrains)", "Annual sum of monthly new car registrations from Ember, 2011 onward.", ["us_new_car_registrations"], "cars per year", digits=0),
           c.chart("wnewcars", "World new car registrations (all drivetrains)", "Ember global estimate, annual sum of monthly data, 2016 onward.", ["world_new_car_registrations"], "cars per year", digits=0),
           '</div><h3>Electric cars</h3><div class="chart-grid">',
           c.chart("usev", "U.S. electric share of new car registrations", "Battery-electric plus plug-in hybrid share, 2011 onward.", ["us_ev_share"], "percent"),
           c.chart("wev", "World electric share of new car registrations", "Battery-electric plus plug-in hybrid share, Ember global estimate, 2016 onward.", ["world_ev_share"], "percent"),
           '</div><h3>Pollution</h3><div class="chart-grid">',
           c.chart("co2", "U.S. transportation-sector CO2 emissions", "Million metric tons of CO2 per year, 1973 onward.", ["us_transport_co2"], "million metric tons CO2"),
           c.chart("co", "U.S. highway-vehicle carbon monoxide emissions", "Thousand short tons; 1970, 1975, 1980, 1985, then yearly from 1990.", ["us_highway_co"], "thousand short tons"),
           c.chart("nox", "U.S. highway-vehicle NOx, VOC and PM2.5 emissions", "Thousand short tons; PM2.5 starts 1990.", ["us_highway_nox", "us_highway_voc", "us_highway_pm25"], "thousand short tons",
                   labels={"us_highway_nox": "NOx", "us_highway_voc": "VOC", "us_highway_pm25": "PM2.5 (primary)"}),
           '</div><h3>People</h3><div class="chart-grid">',
           c.chart("wpop", "World population", "World Bank total population, 1960 onward.", ["world_population"], "people", digits=0),
           c.chart("uspop", "U.S. population", "World Bank total population, 1960 onward.", ["us_population"], "people", digits=0),
           '</div>']
    rows = []
    for k in c.corr:
        r_ = k.get("pearson_r")
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s–%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(k["x_label"]), esc(k["y_label"]), esc(k["region"]), k["n"], k["first_year"], k["last_year"],
            ('%.2f<span class="rbar %s" style="width:%dpx" aria-hidden="true"></span>' % (r_, "pos" if r_ >= 0 else "neg", round(abs(r_) * 60))) if r_ is not None and r_ == r_ else "n/a",
            "%.2f" % k["spearman_rho"] if k.get("spearman_rho") is not None else "n/a"))
    out.append('<h3>Do they move together?</h3><p>Correlations of <b>year-over-year changes</b> (100·ln change; EV share: change in points), same region, same years, flagged values left out. '
               'Two rising levels correlate by accident; changes are a stricter test. These numbers describe co-movement only. <b>They do not show cause.</b> Small n (EV rows) means very wide uncertainty.</p>')
    out.append('<div class="tablewrap"><table class="text"><thead><tr><th scope="col">X</th><th scope="col">Y</th><th scope="col">Region</th><th scope="col">n</th><th scope="col">Years</th>'
               '<th scope="col">Pearson r</th><th scope="col">Spearman ρ</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows))
    out.append('<p class="source">Source: results/correlations.json, computed from the files on the <a href="sources.html">sources page</a>.</p>')
    out.append('<div class="card wide"><h3>Not covered</h3><ul class="plain">%s</ul></div>' % "".join("<li><b>%s</b>: %s</li>" % (esc(n["item"]), esc(n["why"])) for n in NOT_COVERED))
    return "".join(out)


def sources_page(c):
    cites = {x["id"]: x for x in citations()}
    cards = []
    for s in SOURCES:
        m = c.manifest[s["id"]]
        ct = cites[s["id"]]
        cards.append(
            '<section class="src"><h3>%s</h3><dl>'
            '<dt>Cite as</dt><dd>%s</dd>'
            '<dt>Licence</dt><dd>%s (<a href="%s">licence page</a>): <i>"%s"</i></dd>'
            '<dt>Changes made</dt><dd>%s</dd>'
            '<dt>File</dt><dd><a href="%s">%s</a></dd>'
            '<dt>Retrieved</dt><dd>%s UTC, %s bytes</dd>'
            '<dt>SHA-256</dt><dd><code>%s</code>%s</dd></dl></section>' % (
                esc(s["title"]), esc(ct["text"]), esc(s["licence"]), esc(s["licence_url"]), esc(s["licence_evidence"]),
                esc(ct["changes"]), esc(s["url"]), esc(s["url"]), esc(m["retrieved_at_utc"]), "{:,}".format(m["bytes"]), esc(m["sha256"]),
                ('<br>Stored copy: author names removed from the file metadata; data unchanged. SHA-256 as downloaded: <code>%s</code>' % esc(m["sha256_as_downloaded"]))
                if m.get("sha256_as_downloaded") else ""))
    sw = "".join('<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>' % (esc(x["url"]), esc(x["name"]), esc(x["licence"]), esc(x["role"]))
                 for x in SOFTWARE)
    rej = "".join("<li><b>%s</b>: %s</li>" % (esc(x["name"]), esc(x["reason"])) for x in REJECTED)
    return (
        '<h1>Sources &amp; licences</h1>'
        '<p class="lede">Every number on this site is read from one of the files below. <code>fcp/fetch.py</code> downloaded each one and recorded its URL, '
        'retrieval time and SHA-256 in <code>data/manifest.json</code>; <code>tests/test_data.py</code> re-reads the raw files and checks both. '
        'Licences were read on the linked pages on the retrieval date. Release and update dates in the citations are read from the downloaded files; for the '
        'Monthly Energy Review tables, from EIA&rsquo;s Monthly Energy Review page downloaded the same day.</p>'
        '<h2>Data</h2>%s'
        '<h2>Software</h2><p>All software is open source except the HydraDB engine, which is source-available under the Elastic License 2.0 and was used under '
        'the hackathon&rsquo;s terms. No third-party JavaScript, stylesheet, font or image is loaded by the site: the flowchart script, '
        'favicon and share image were made for this project. Fonts are not bundled; the pages name fonts that a reader\'s device may already have. '
        'The share image&rsquo;s text is set in Aileron Regular by Sora Sagano (dot colon), released under CC0 1.0 and shipped inside Pillow.</p>'
        '<div class="tablewrap"><table class="text"><thead><tr><th scope="col">Software</th><th scope="col">Licence</th><th scope="col">Used for</th></tr></thead>'
        '<tbody>%s</tbody></table></div>'
        '<p>Cite the graph engine as: %s</p>'
        '<h2>This project</h2><ul class="plain"><li>Code: MIT License (<a href="%s/blob/main/LICENSE">LICENSE</a>).</li>'
        '<li>Downloaded data files in <code>data/raw</code> keep their publishers\' licences listed above. Derived numbers that come from CC BY 4.0 data '
        '(World Bank, Ember) are shared under the same attribution terms, with the changes stated above.</li></ul>'
        '<h2>Names and trademarks</h2><ul class="plain">'
        '<li>This is an independent entry to the HydraDB Hackathon. It is not made, sponsored or endorsed by HydraDB. The name HydraDB is used only to identify the engine and the hackathon.</li>'
        '<li>Data publishers are named only to cite their data. Naming them does not imply that they endorse this project.</li></ul>'
        '<h2>Considered and not used</h2><ul class="plain">%s</ul>'
    ) % ("".join(cards), sw, esc(software_citation()), REPO_URL, rej)



def walkthrough_page():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "walkthrough_captions.txt")
    with open(path, encoding="utf-8") as f:
        rows = [line.strip().split("|", 1) for line in f if "|" in line]
    caps = "".join("<tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (esc(t), esc(x)) for t, x in rows)
    return ('<h1>Walkthrough</h1><p class="lede">A short narrated, captioned tour of the site: the price-change flowchart, the yearly learning replay, '
            'the scores and their caveats, and the sources. The captions are also below as text.</p>'
            '<video controls preload="metadata" width="1600" height="1000" style="width:100%%;height:auto;border:1px solid var(--line);border-radius:12px;background:#fff" '
            'aria-describedby="captions">'
            '<source src="walkthrough.mp4" type="video/mp4">Your browser cannot play this video; the captions are below.</video>'
            '<div class="tablewrap" id="captions"><table class="text"><caption>Captions</caption><thead><tr><th scope="col">Time</th><th scope="col">Caption</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % caps)


PRIVACY = (
    '<h1>Privacy</h1><p class="lede">Short version: this site collects nothing about you.</p><ul class="plain">'
    '<li><b>No tracking.</b> No cookies, analytics, advertising, fingerprinting, forms or accounts. The pages load nothing from any other website; '
    'the project&rsquo;s test suite checks every page for this.</li>'
    '<li><b>The calculator stays in your browser.</b> The sliders and buttons run locally; nothing you choose is sent anywhere.</li>'
    '<li><b>Hosting.</b> The files are served by GitHub Pages. Like any web host, GitHub may record technical request data such as the visitor&rsquo;s IP address '
    'in its logs, under the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub General Privacy Statement</a>. '
    'This project does not receive or use those logs.</li>'
    '<li><b>Old address.</b> The earlier address on netlify.app only redirects here. Netlify may log that request under '
    '<a href="https://www.netlify.com/privacy/">Netlify&rsquo;s privacy policy</a>.</li>'
    '<li><b>Data on the site.</b> Only public statistics from government and open-data publishers. No personal or business data.</li>'
    '<li><b>Questions.</b> Open an issue on the <a href="%s">project repository</a>.</li></ul>'
) % REPO_URL

TERMS = (
    '<h1>Terms of use</h1><ul class="plain">'
    '<li><b>What this is.</b> An educational, non-commercial entry to the HydraDB Hackathon. It explains how fuel prices, driving, electric cars and transport CO2 '
    'have moved together, and tests a small learning model.</li>'
    '<li><b>Not advice.</b> Nothing here is financial, investment, policy, legal or engineering advice. The model was tested on few years and its result is fragile; '
    'see the caveats on the <a href="index.html#caveats">results page</a>.</li>'
    '<li><b>Correlation is not cause.</b> Correlations and learned link strengths describe how series moved together. They do not show that one causes another.</li>'
    '<li><b>Licences.</b> The code is MIT-licensed. Each data file keeps its publisher\'s licence, listed with a citation on <a href="sources.html">Sources &amp; licences</a>. '
    'If you reuse the data, follow those licences: credit the World Bank and Ember (CC BY 4.0), acknowledge EIA with the release date, and use EPA material for '
    'non-commercial, scientific or educational purposes as EPA\'s policy states.</li>'
    '<li><b>No warranty.</b> The site, code and derived numbers are provided "as is", without warranty of any kind. To the extent the law allows, the authors '
    'are not liable for any loss arising from their use.</li>'
    '<li><b>Names.</b> HydraDB and the data publishers are named only to identify the engine, the hackathon and the sources. None of them made, sponsored or endorsed this project.</li>'
    '<li><b>Changes.</b> These pages may change. Every change is recorded in the repository history.</li></ul>'
)

AI = (
    '<h1>AI disclosure</h1><ul class="plain">'
    '<li><b>Who built it.</b> The code, analysis, page design and text were produced by an AI coding assistant, Claude Opus 5.5 running in Claude Code (Anthropic), '
    'working under the direction of the project author. The author set the brief and the rules, and approved each outward step such as hosting and publishing.</li>'
    '<li><b>No AI at runtime.</b> No AI model runs on this site or inside the learning loop. The learning is recursive least squares; its link strengths are stored in HydraDB.</li>'
    '<li><b>No hand-typed numbers.</b> Every figure on the site is generated by code from the downloaded files and the result files in the repository; tests check that the '
    'pages match those files.</li>'
    '<li><b>Rule first.</b> The pass/fail rule was written and committed before the first run and was not changed after the result was known.</li>'
    '<li><b>Mistakes are possible.</b> AI-written code and text can be wrong. The tests, the data check and the open repository are there so anyone can verify the work.</li></ul>'
)


def build():
    c = Ctx()
    os.makedirs(SITE, exist_ok=True)
    pages = {
        "index.html": ("Fuel, Cars & Pollution — a self-refitting HydraDB graph", results_section(c) + how_section(c) + data_section(c) +
                       '<script type="application/json" id="flow-data">%s</script><script src="flow.js" defer></script>' % flow_data(c),
                       "A HydraDB graph links crude oil, gasoline, miles driven, EVs, fuel use and transport CO2, and refits its links every year. Pre-registered walk-forward test."),
        "sources.html": ("Sources & licences — Fuel, Cars & Pollution", sources_page(c), "Every data file used, with URL, retrieval time, SHA-256 and licence."),
        "privacy.html": ("Privacy — Fuel, Cars & Pollution", PRIVACY, "Privacy notice."),
        "terms.html": ("Terms of use — Fuel, Cars & Pollution", TERMS, "Terms of use."),
        "ai.html": ("AI disclosure — Fuel, Cars & Pollution", AI, "How AI was used to build this project."),
        "walkthrough.html": ("Walkthrough — Fuel, Cars & Pollution", walkthrough_page(), "A short narrated, captioned walkthrough of the project."),
    }
    for fname, (title, body, desc) in pages.items():
        with open(os.path.join(SITE, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(fname, title, body, desc))
    with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CSS.strip() + "\n")
    with open(os.path.join(SITE, "favicon.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(FAVICON + "\n")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "flow.js"), encoding="utf-8") as src, \
            open(os.path.join(SITE, "flow.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write(src.read())
    print("site built:", ", ".join(sorted(pages)))


if __name__ == "__main__":
    build()
