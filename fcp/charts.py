"""Accessible SVG line charts with a data table behind each, built at build time.

No JavaScript is needed to read any chart. Missing years break the line.
Flagged values are drawn as hollow markers and named in the table.
"""

import html
import math

PALETTE = [
    ("#0b5cad", ""),  # blue, solid
    ("#b34d00", "6 4"),  # orange, dashed
    ("#5b6570", "2 3"),  # grey, dotted
    ("#7a3fb8", "10 3 2 3"),  # purple, dash-dot
    ("#1a7f37", "1 0"),  # green, solid
    ("#a40e26", "4 2"),  # red, dashed
]


def esc(s):
    return html.escape(str(s), quote=True)


def style_of(ln, i):
    color, dash = PALETTE[i % len(PALETTE)]
    return ln.get("color", color), ln.get("dash", dash)


def nice_ticks(lo, hi, n=5):
    if hi == lo:
        hi = lo + 1
    span = hi - lo
    step = 10 ** math.floor(math.log10(span / n))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= n:
            step *= m
            break
    start = math.floor(lo / step) * step
    ticks = []
    v = start
    while v <= hi + step * 0.5:
        ticks.append(round(v, 10))
        v += step
    return ticks


def fmt(v, digits=2):
    if v is None:
        return "missing"
    a = abs(v)
    if a >= 1e9:
        return "%.2f bn" % (v / 1e9)
    if a >= 1e6:
        return "%.2f m" % (v / 1e6)
    if a >= 1000:
        return "{:,.0f}".format(v)
    return ("%." + str(digits) + "f") % v


def line_chart(cid, title, desc, lines, y_label, source_line, y_zero=False, x_range=None, unit_note="", digits=2, shade=None, width=560, height=340):
    """lines: list of dicts {label, values: {year: v}, flags: {year: flag}}."""
    W, H = width, height
    L, R, T, B = 64, 16, 16, 44
    all_years = sorted({int(y) for ln in lines for y in ln["values"]})
    if x_range:
        all_years = [y for y in all_years if x_range[0] <= y <= x_range[1]]
    vals = [v for ln in lines for y, v in ln["values"].items() if int(y) in all_years and v is not None]
    if not all_years or not vals:
        return '<p class="note">No data for %s.</p>' % esc(title)
    x0, x1 = all_years[0], all_years[-1]
    lo, hi = min(vals), max(vals)
    if y_zero:
        lo = min(lo, 0.0)
        hi = max(hi, 0.0)
    pad = (hi - lo) * 0.06 or 1.0
    floor = lo - pad
    if lo >= 0 and floor < 0:
        floor = 0.0  # all-positive series: the axis starts at zero, not below it
    ticks = nice_ticks(floor, hi + pad)
    ylo, yhi = ticks[0], ticks[-1]

    def X(y):
        return L + (W - L - R) * ((y - x0) / ((x1 - x0) or 1))

    def Y(v):
        return T + (H - T - B) * (1 - (v - ylo) / ((yhi - ylo) or 1))

    parts = []
    if shade:
        sx0, sx1 = X(max(shade[0], x0)), X(min(shade[1], x1))
        parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="#eef4fb"/>' % (sx0, T, sx1 - sx0, H - T - B))
        parts.append('<text x="%.1f" y="%d" class="tick" text-anchor="start">%s</text>' % (sx0 + 4, T + 14, esc(shade[2])))
    for t in ticks:
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/>' % (L, W - R, Y(t), Y(t)))
        parts.append('<text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (L - 6, Y(t) + 4, esc(fmt(t, 0 if abs(yhi - ylo) > 20 else 1))))
    if ylo < 0 < yhi:
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="zero"/>' % (L, W - R, Y(0), Y(0)))
    span = x1 - x0
    step = 1 if span <= 12 else 2 if span <= 24 else 5 if span <= 60 else 10
    for y in range(x0, x1 + 1):
        if y % step == 0 or (y == x0 and span <= 12):
            parts.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%d</text>' % (X(y), H - B + 18, y))
    parts.append('<text x="14" y="%d" class="axis" transform="rotate(-90 14 %d)" text-anchor="middle">%s</text>' % ((H - B + T) // 2, (H - B + T) // 2, esc(y_label)))
    for i, ln in enumerate(lines):
        color, dash = style_of(ln, i)
        pts = {int(y): v for y, v in ln["values"].items() if v is not None and int(y) in all_years}
        flags = {int(y): f for y, f in ln.get("flags", {}).items()}
        seg, segs = [], []
        for y in all_years:
            if y in pts:
                seg.append(y)
            elif seg:
                segs.append(seg)
                seg = []
        if seg:
            segs.append(seg)
        for s in segs:
            d = " ".join(("M" if k == 0 else "L") + "%.1f,%.1f" % (X(y), Y(pts[y])) for k, y in enumerate(s))
            parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.2"%s/>' % (d, color, ' stroke-dasharray="%s"' % dash if dash and dash != "1 0" else ""))
            if len(s) == 1:
                parts.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (X(s[0]), Y(pts[s[0]]), color))
        for y, f in flags.items():
            if y in pts:
                parts.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="#fff" stroke="%s" stroke-width="2"><title>%d: %s (%s)</title></circle>' % (X(y), Y(pts[y]), color, y, esc(fmt(pts[y], digits)), esc(f)))
    legend = "".join(
        '<li><svg width="28" height="10" aria-hidden="true"><line x1="0" x2="28" y1="5" y2="5" stroke="%s" stroke-width="3"%s/></svg>%s</li>'
        % (style_of(ln, i)[0], (' stroke-dasharray="%s"' % style_of(ln, i)[1]) if style_of(ln, i)[1] not in ("", "1 0") else "", esc(ln["label"]))
        for i, ln in enumerate(lines)
    )
    has_flags = any(ln.get("flags") for ln in lines)
    svg = (
        '<svg viewBox="0 0 %d %d" role="img" aria-labelledby="%s-t %s-d" class="chart">'
        '<title id="%s-t">%s</title><desc id="%s-d">%s</desc>%s</svg>'
        % (W, H, cid, cid, cid, esc(title), cid, esc(desc), "".join(parts))
    )
    # data table
    head = "".join('<th scope="col">%s</th>' % esc(ln["label"]) for ln in lines)
    body = []
    for y in all_years:
        cells = []
        for ln in lines:
            v = ln["values"].get(str(y), ln["values"].get(y))
            f = ln.get("flags", {}).get(str(y), ln.get("flags", {}).get(y))
            cells.append("<td>%s%s</td>" % (esc(fmt(v, digits)), (' <span class="flag">(%s)</span>' % esc(f)) if f and v is not None else ""))
        body.append('<tr><th scope="row">%d</th>%s</tr>' % (y, "".join(cells)))
    table = (
        '<details><summary>Data table: %s</summary><div class="tablewrap"><table><caption>%s%s</caption>'
        '<thead><tr><th scope="col">Year</th>%s</tr></thead><tbody>%s</tbody></table></div></details>'
        % (esc(title), esc(title), (" — " + esc(unit_note)) if unit_note else "", head, "".join(body))
    )
    flag_note = '<p class="note">Hollow markers are flagged values (provisional, partial, estimated or carried forward); they are shown but left out of correlations and scoring.</p>' if has_flags else ""
    return (
        '<figure id="%s"><figcaption class="ctitle">%s</figcaption>%s%s%s'
        '<p class="source">%s</p>%s</figure>' % (cid, esc(title), ('<ul class="legend">%s</ul>' % legend) if len(lines) > 1 else "",
                                                 svg, flag_note, source_line, table)
    )
