"""Draw site/og.png (1200x630 share image) from results/learning_results.json.

Usage: python -m fcp.ogimage
"""

import json
import os

from PIL import Image, ImageDraw, ImageFont

from fcp.fetch import ROOT
from fcp.learn import results_path
from fcp.stats import SUMMARY_OUT

OUT = os.path.join(ROOT, "site", "og.png")


def font(size, bold=False):
    for name in (("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def main():
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    with open(SUMMARY_OUT, encoding="utf-8") as f:
        s = json.load(f)
    sc = r["scores_co2"]
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill="#0b5cad")
    d.text((60, 42), "Fuel, Cars & Pollution", font=font(56, True), fill="#16191d")
    d.text((60, 112), "A HydraDB graph that refits its own links every year", font=font(32), fill="#3d4650")
    d.text((60, 160), "crude oil > gasoline > fuel use > U.S. transport CO2  (+ miles driven, EV share)", font=font(26), fill="#4b5560")
    # chart: actual vs graph, all predicted years
    rows = [p for p in r["per_year"] if p["actual_co2"] is not None]
    x0, x1, y0, y1 = 60, 700, 228, 548
    ys = [p["actual_co2"] for p in rows] + [p["graph"] for p in rows]
    pad = (max(ys) - min(ys)) * 0.06
    lo, hi = min(ys) - pad, max(ys) + pad
    yr0, yr1 = rows[0]["year"], rows[-1]["year"]

    def X(y):
        return x0 + (x1 - x0) * (y - yr0) / (yr1 - yr0)

    def Y(v):
        return y1 - (y1 - y0) * (v - lo) / (hi - lo)

    hx = X(2005)
    d.rectangle([hx, y0, x1, y1], fill="#eef4fb")
    d.text((hx + 8, y0 + 4), "holdout", font=font(20), fill="#4b5560")
    d.line([x0, Y(0), x1, Y(0)], fill="#8a939c", width=2)
    for key, color, width in (("actual_co2", "#16191d", 4), ("graph", "#0b5cad", 4)):
        seg = []
        prev = None
        for p in rows:
            if prev is not None and p["year"] != prev + 1:
                if len(seg) > 1:
                    d.line(seg, fill=color, width=width)
                seg = []
            seg.append((X(p["year"]), Y(p[key])))
            prev = p["year"]
        if len(seg) > 1:
            d.line(seg, fill=color, width=width)
    d.text((x0, y1 + 12), "Yearly change in U.S. transport CO2, %: actual (black) vs graph (blue)", font=font(20), fill="#4b5560")
    # numbers
    tx = 750
    d.text((tx, 240), "Pre-registered verdict: %s" % r["verdict"], font=font(32, True), fill="#1a7f37" if r["verdict"] == "PASS" else "#a40e26")
    d.text((tx, 296), "Holdout MAE, pp (n=%d)" % sc["graph"]["holdout_n"], font=font(24), fill="#4b5560")
    lines = [("Graph", sc["graph"]["holdout_mae"]), ("No change", sc["no_change"]["holdout_mae"]),
             ("k-NN (vector store)", sc["knn"]["holdout_mae"]), ("Frozen graph", sc["frozen_graph"]["holdout_mae"])]
    for i, (k, v) in enumerate(lines):
        d.text((tx, 336 + i * 38), k, font=font(26), fill="#16191d")
        d.text((tx + 330, 336 + i * 38), "%.2f" % v, font=font(26, True), fill="#16191d")
    ex = s["excluding_2020_2021"]
    d.text((tx, 506), "Without 2020-21: graph %.2f vs" % ex["graph"], font=font(22), fill="#a40e26")
    d.text((tx, 536), "no change %.2f. Fragile; read the caveats." % ex["no_change"], font=font(22), fill="#a40e26")
    d.text((60, 596), "Official data: EIA, FHWA, EPA, World Bank, Ember. Every number traced to a file hash.", font=font(20), fill="#4b5560")
    im.save(OUT, optimize=True)
    print("wrote", os.path.relpath(OUT, ROOT), im.size)


if __name__ == "__main__":
    main()
