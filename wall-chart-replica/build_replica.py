"""Builds boys.html / girls.html -- plain HTML + CSS replicas of the two IAP wall
charts in ../Images, from numbers read off those images (see source/).

Run from the project root:  .venv/Scripts/python.exe wall-chart-replica/build_replica.py
"""
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import UnivariateSpline

HERE = Path(__file__).parent
CURVES = json.loads((HERE / "source" / "curves_from_images.json").read_text())
INSET = json.loads((HERE / "source" / "inset_raw_points.json").read_text())

# Pixel geometry measured on the original images (page size, plot box, etc.).
G = {
    "girls": dict(
        W=1156, H=1496, bg="#e79dec", ink="#280025", insetbg="#e79dec", ob="#a8444e", ow="#efdc72", ymax=175, plot=(92.5, 64.0, 912.5, 1285.0), ytick_fs=16.5,
        title=(64, 8, 917, 52), title_word="Girls", ylabel_x=20, xlabel_y=1361, foot=(88, 1396),
        mph=dict(x=975, y=345, w=157, head_y=380, head_h=36, row_h=20.25, bar_to=182, bar="#c573bb",
                 labels={159: "3rd", 163: "10th", 167: "25th", 171: "50th", 175: "75th", 179: "90th", 183: "97th"}),
        inset=dict(box=(92, 62, 420, 332), plot=(128.6, 89.75, 407.4, 291.25), hmax=170, xstep=5,
                   title="Girls BMI Quick Assessment Tool 8 - 18 Years",
                   tags=dict(OB=(390, 105), OW=(394, 131), UW=(398, 180))),
    ),
    "boys": dict(
        W=1048, H=1386, bg="#bacfec", ink="#111", insetbg="#dce5f4", ob="#c9302c", ow="#eec443", ymax=195, plot=(110.0, 65.5, 778.5, 1191.2), ytick_fs=12.5,
        title=(70, 8, 784, 50), title_word="Boys", ylabel_x=50, xlabel_y=1260, foot=(77, 1298),
        mph=dict(x=851, y=310, w=175, head_y=345, head_h=33, row_h=19.7, bar_to=186, bar="#9abdd3",
                 labels={158: "3rd", 163: "10th", 168: "25th", 173: "50th", 178: "75th", 182: "90th", 187: "97th"}),
        inset=dict(box=(109, 66, 420, 372), plot=(153.0, 89.9, 405.0, 325.2), hmax=180, xstep=2.5,
                   title="Boys BMI quick Assessment Tool 8-18 Years",
                   tags=dict(OB=(384, 97), OW=(385, 127), UW=(384, 193))),
    ),
}
CENT = ["3", "10", "25", "50", "75", "90", "97"]
FOOT = [
    "Modified from: 1. WHO MGRS (Multicentre Growth Reference Study) 2006.",
    "2. Revised IAP Growth Charts for Height, Weight and Body Mass Index for 5 to 18 year old Indian Children.",
    "V. Khadilkar et al, from Indian Academy of Pediatrics, Growth Chart Committee, Indian Pediatrics, Jan 2015, Vol 52",
    "3. Khadilkar V, Lohiya N, Chiplonkar S, Khadilkar A. Body Mass Index Quick Screening Tool for IAP 2015 Growth Charts",
    "[published online ahead of print, 2020 Jun 12]. Indian Pediatr. 2020;S097475591600197.",
]


def px(v, total):
    return f"{v / total * 100:.4f}%"


def path(ages, vals, ymax):
    return "M" + " L".join(f"{a:g},{ymax - v:.2f}" for a, v in zip(ages, vals))


def inset_curve(pts, hmax):
    p = np.array(pts)
    x, y = p[:, 0], p[:, 1]
    spl = UnivariateSpline(x, y, k=3, s=len(x) * 0.15 ** 2)
    xs = np.arange(120, hmax + 0.001, 1.0)
    return xs, spl(xs)


def build(sex):
    g = G[sex]
    W, H, ymax = g["W"], g["H"], g["ymax"]
    x0, y0, x1, y1 = g["plot"]
    pw, ph = x1 - x0, y1 - y0
    ages = CURVES[sex]["ages"]

    paths, labels = [], []
    for meas in ("height", "weight"):
        for i, c in enumerate(CENT):
            vals = CURVES[sex][meas][i]
            red = meas == "height" and c == "3"
            paths.append(f'<path class="{"red" if red else ""}" d="{path(ages, vals, ymax)}"/>')
            txt = "3(Short below this line)" if red else c
            labels.append(f'<span class="{"red" if red else ""}" style="top:{(1 - vals[-1] / ymax) * 100:.3f}%">{txt}</span>')
    ytk = "".join(f'<span style="top:{(1 - v / ymax) * 100:.4f}%">{v}</span>' for v in range(0, ymax + 1, 5))
    xtk = "".join(f'<span style="left:{a / 18 * 100:.4f}%">{a}</span>' for a in range(0, 19))

    ins = g["inset"]
    bx0, by0, bx1, by1 = ins["box"]
    ix0, iy0, ix1, iy1 = ins["plot"]
    hmax = ins["hmax"]
    ipw, iph = ix1 - ix0, iy1 - iy0
    ipaths = []
    for key, cls in (("UW", "uw"), ("OW", "ow"), ("OB", "ob")):
        xs, ys = inset_curve(INSET[sex][key], hmax)
        ipaths.append(f'<path class="{cls}" d="M' + " L".join(f"{x:g},{90 - y:.2f}" for x, y in zip(xs, ys)) + '"/>')
    iyt = "".join(f'<span style="top:{(1 - v / 90) * 100:.3f}%">{v}</span>' for v in range(0, 91, 5))
    ixt = "".join(f'<span style="left:{(h - 120) / (hmax - 120) * 100:.3f}%">{h}</span>' for h in range(120, hmax + 1, 5))
    nx = int(round((hmax - 120) / ins["xstep"]))
    tags = "".join(f'<span class="tag" style="left:{px(x, W)};top:{px(y, H)}">{k}</span>' for k, (x, y) in ins["tags"].items())

    m = g["mph"]
    rows = "".join(
        f'<tr><td class="f">{f}</td><td class="c">{m["labels"].get(f, "")}</td><td class="m">{f - 13}</td></tr>'
        for f in range(150, 191)
    )
    bar_h = (m["bar_to"] - 150 + 1) * m["row_h"]
    foot = "".join(f"<div>{t}</div>" for t in FOOT)
    t = g["title"]

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WHO 2006 &amp; IAP 2015 combined {g['title_word']} Charts 0-18 Years (replica)</title>
<link rel="stylesheet" href="chart.css">
<style>
/* numbers for this page, all measured on the original image ({W} x {H} px) */
.page{{--bg:{g['bg']};--W:{W};--H:{H};--yfs:{g['ytick_fs']};--mphbar:{m['bar']};--ink:{g['ink']};--insetbg:{g['insetbg']};--ob:{g['ob']};--ow:{g['ow']}}}
</style></head>
<body>
<div class="page">

  <div class="title" style="left:{px(t[0], W)};top:{px(t[1], H)};width:{px(t[2] - t[0], W)};height:{px(t[3] - t[1], H)}">
    WHO 2006 &amp; IAP 2015 combined {g['title_word']} Charts 0-18 Years</div>

  <!-- grid paper: 72 x {ymax} minor boxes (every 0.25 y and 1 unit); bold lines every 1 y and 5 units -->
  <div class="plot" style="left:{px(x0, W)};top:{px(y0, H)};width:{px(pw, W)};height:{px(ph, H)};--nx:72;--ny:{ymax};--mx:18;--my:{ymax // 5}">
    <svg class="curves" viewBox="0 0 18 {ymax}" preserveAspectRatio="none">{''.join(paths)}</svg>
    <div class="yticks">{ytk}</div><div class="xticks">{xtk}</div>
    <div class="ends">{''.join(labels)}</div>
  </div>
  <div class="ylabel" style="left:{px(g['ylabel_x'], W)};top:{px((y0 + y1) / 2, H)}">Height in CM and Weight in KG</div>
  <div class="xlabel" style="left:{px((x0 + x1) / 2, W)};top:{px(g['xlabel_y'], H)}">Age in Years</div>

  <!-- BMI quick-assessment inset (weight vs height, 8-18 y) -->
  <div class="inset" style="left:{px(bx0, W)};top:{px(by0, H)};width:{px(bx1 - bx0, W)};height:{px(by1 - by0, H)}">
    <div class="inset-title">{ins['title']}</div>
  </div>
  <div class="iplot" style="left:{px(ix0, W)};top:{px(iy0, H)};width:{px(ipw, W)};height:{px(iph, H)};--inx:{nx};--iny:18">
    <svg viewBox="120 0 {hmax - 120} 90" preserveAspectRatio="none">{''.join(ipaths)}</svg>
    <div class="yt">{iyt}</div><div class="xt">{ixt}</div>
    <div class="legend"><div>OB- Obese</div><div>OW- Overweight</div><div>UW- Underweight</div></div>
  </div>
  <div class="iylabel" style="left:{px(ix0 - 30, W)};top:{px((iy0 + iy1) / 2, H)}">Weight in KG</div>
  <div class="ixlabel" style="left:{px((ix0 + ix1) / 2, W)};top:{px(iy1 + 30, H)}">Height in CM</div>
  {tags}

  <!-- MPH (mid-parental height) percentile calculator -->
  <div class="mph" style="left:{px(m['x'], W)};top:{px(m['y'], H)};width:{px(m['w'], W)};--rowh:{m['row_h']};--headh:{m['head_h']};--headgap:{m['head_y'] - m['y']};--barh:{bar_h:.2f}">
    <div class="mph-title">MPH Percentile<br>Calculator</div>
    <table><thead><tr><th>Father's<br>Height</th><th>MPH<br>Centile</th><th>Mother's<br>Height</th></tr></thead>
    <tbody>{rows}</tbody></table>
    <i class="bar"></i>
  </div>

  <div class="foot" style="left:{px(g['foot'][0], W)};top:{px(g['foot'][1], H)}">{foot}</div>
</div>
</body></html>
"""
    (HERE / f"{sex}.html").write_text(html, encoding="utf-8")
    print(sex, "built", len(html) // 1024, "KB")


for s in ("girls", "boys"):
    build(s)
