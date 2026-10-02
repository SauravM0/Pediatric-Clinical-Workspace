/* GENERATED FILE -- do not edit.
 * Built from frontend/src/ by build.mjs (M6). Edit the source there and run
 * `npm run build`. tests/frontend/test_build_artefact.py fails if this file
 * and frontend/src/ have drifted, so an edit here would be reverted anyway.
 */
(() => {
  // frontend/src/domain.js
  var TW3_CONFIG = {
    pctAdultHeight: { boys: [], girls: [] }
  };
  var REPORT_RUS = [
    ["radius", "Radius"],
    ["ulna", "Ulna"],
    ["mc1", "First metacarpal"],
    ["mc3", "Third metacarpal"],
    ["mc5", "Fifth metacarpal"],
    ["pp1", "Proximal Phalanx Thumb"],
    ["pp3", "Proximal Phalanx III"],
    ["pp5", "Proximal Phalanx V"],
    ["mp3", "Middle Phalanx III"],
    ["mp5", "Middle Phalanx V"],
    ["dp1", "Distal Phalanx Thumb"],
    ["dp3", "Distal Phalanx III"],
    ["dp5", "Distal Phalanx V"]
  ];
  var REPORT_CARPALS = ["Capitate", "Hamate", "Triquetral", "Lunate", "Scaphoid", "Trapezium", "Trapezoid"];
  var LETTER_STAGES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"];
  var carpalCode2 = (name) => name.toLowerCase();
  var IMAGE_DOMAINS = [
    ["digital_diagnostic", "Digital \xB7 DICOM / PACS / direct"],
    ["compressed", "Compressed \xB7 WhatsApp / screenshot"],
    ["film_photo", "Photo of film \xB7 phone camera"],
    ["unknown", "Unknown"]
  ];
  var LOW_TRUST_DOMAINS = ["compressed", "film_photo"];
  function interpAnchors(anchors, x) {
    if (!anchors || anchors.length < 2) return null;
    if (x <= anchors[0][0]) return anchors[0][1];
    if (x >= anchors[anchors.length - 1][0]) return anchors[anchors.length - 1][1];
    for (let i = 0; i < anchors.length - 1; i++) {
      const [x0, y0] = anchors[i], [x1, y1] = anchors[i + 1];
      if (x >= x0 && x <= x1) {
        const w = (x - x0) / (x1 - x0);
        return y0 + w * (y1 - y0);
      }
    }
    return anchors[anchors.length - 1][1];
  }
  function pctAdultHeightAt(boneAge, sex) {
    return interpAnchors(TW3_CONFIG.pctAdultHeight && TW3_CONFIG.pctAdultHeight[sex], boneAge);
  }
  function maturationCategory(boneAge, chronoAge) {
    const diff = boneAge - chronoAge;
    if (diff > 1) return "accelerated";
    if (diff < -1) return "retarded";
    return "average";
  }

  // frontend/src/growthMath.js
  var IQR_TO_SD = 1.3489795;
  var CENTILE_Z = [[3, -1.8807936], [10, -1.2815516], [25, -0.6744898], [50, 0], [75, 0.6744898], [90, 1.2815516], [97, 1.8807936]];
  function zForValueFromCentileStats(stats, value) {
    if (!stats || !stats.available || !(value > 0)) return null;
    const pts = CENTILE_Z.map(([c, z]) => [stats["p" + c], z]).filter((p) => typeof p[0] === "number");
    if (pts.length < 2) return null;
    pts.sort((a, b) => a[0] - b[0]);
    const lerp = (x0, z0, x1, z1) => x1 === x0 ? z0 : z0 + (value - x0) / (x1 - x0) * (z1 - z0);
    const n = pts.length;
    if (value <= pts[0][0]) return lerp(pts[0][0], pts[0][1], pts[1][0], pts[1][1]);
    if (value >= pts[n - 1][0]) return lerp(pts[n - 2][0], pts[n - 2][1], pts[n - 1][0], pts[n - 1][1]);
    for (let i = 0; i < n - 1; i++) {
      if (value >= pts[i][0] && value <= pts[i + 1][0]) return lerp(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
    }
    return null;
  }
  function ageForMedianFromSeries(seriesForMeasure, value) {
    if (!seriesForMeasure || !(value > 0)) return { decimal: null, label: "N/A" };
    const p50 = seriesForMeasure.centiles && seriesForMeasure.centiles["50"];
    if (!p50 || p50.length < 2) return { decimal: null, label: "N/A" };
    const first = p50[0][1], last = p50[p50.length - 1][1];
    if (value < first) return { decimal: null, label: `Below ${p50[0][0].toFixed(1)} yr median` };
    if (value > last) return { decimal: null, label: `Above ${p50[p50.length - 1][0].toFixed(1)} yr median` };
    for (let i = 0; i < p50.length - 1; i++) {
      const [ageCur, cur] = p50[i], [ageNxt, nxt] = p50[i + 1];
      if (value >= cur && value <= nxt || value <= cur && value >= nxt) {
        const frac = nxt === cur ? 0 : (value - cur) / (nxt - cur);
        const dec = ageCur + frac * (ageNxt - ageCur);
        return { decimal: dec, label: `${dec.toFixed(1)} yrs` };
      }
    }
    return { decimal: null, label: "N/A" };
  }
  function spreadFromSeries(seriesForMeasure, ageYears) {
    const c = seriesForMeasure && seriesForMeasure.centiles;
    if (!c || !c["75"] || !c["25"]) return null;
    const nearestIdx = (arr) => {
      let best = 0, bestDiff = Infinity;
      for (let i = 0; i < arr.length; i++) {
        const diff = Math.abs(arr[i][0] - ageYears);
        if (diff < bestDiff) {
          bestDiff = diff;
          best = i;
        }
      }
      return best;
    };
    const i75 = nearestIdx(c["75"]), i25 = nearestIdx(c["25"]);
    return (c["75"][i75][1] - c["25"][i25][1]) / IQR_TO_SD;
  }
  function sdsToPercent(z) {
    return Math.min(Math.max((z + 4) / 8 * 100, 2), 98);
  }
  function probToPercent(p, max) {
    return Math.min(Math.max(p / max * 100, 1), 99);
  }
  function normalCDF(z) {
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const d = 0.39894228 * Math.exp(-z * z / 2);
    const p = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z >= 0 ? 1 - p : p;
  }

  // frontend/src/serverCalc.js
  var { useState, useEffect } = React;
  var DEBOUNCE_MS = 200;
  function useServerCalc(request) {
    const key = request ? request.url + "|" + (request.body ? JSON.stringify(request.body) : "") : null;
    const [state, setState] = useState({ key: null, data: null, error: null });
    useEffect(() => {
      if (!key) return void 0;
      const ctrl = new AbortController();
      const timer = setTimeout(() => {
        const init = request.body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request.body) } : { method: "GET" };
        fetch(request.url, { ...init, signal: ctrl.signal }).then(async (r) => {
          const d = await r.json().catch(() => null);
          if (!r.ok) {
            const detail = d && d.detail;
            throw new Error(typeof detail === "string" ? detail : `request failed (HTTP ${r.status})`);
          }
          return d;
        }).then((d) => setState({ key, data: d, error: null })).catch((e) => {
          if (e.name !== "AbortError") setState({ key, data: null, error: String(e.message || e) });
        });
      }, DEBOUNCE_MS);
      return () => {
        clearTimeout(timer);
        ctrl.abort();
      };
    }, [key]);
    const current = key !== null && state.key === key;
    return {
      data: current ? state.data : null,
      error: current ? state.error : null,
      loading: key !== null && !current
    };
  }
  function withQuery(path, params) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== void 0 && v !== "") q.append(k, String(v));
    });
    return `${path}?${q.toString()}`;
  }

  // frontend/src/charts.jsx
  function SDSBar({ z }) {
    const left = sdsToPercent(z);
    return /* @__PURE__ */ React.createElement("div", { style: { paddingTop: "8px", paddingBottom: "4px" } }, /* @__PURE__ */ React.createElement("div", { className: "sds-track" }, /* @__PURE__ */ React.createElement("div", { className: "sds-marker", style: { left: `${left}%` } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "9px", fontWeight: "700", color: "#94a3b8", letterSpacing: "0.05em", textTransform: "uppercase" } }, /* @__PURE__ */ React.createElement("span", null, "\u22124"), /* @__PURE__ */ React.createElement("span", null, "\u22122"), /* @__PURE__ */ React.createElement("span", null, "0"), /* @__PURE__ */ React.createElement("span", null, "+2"), /* @__PURE__ */ React.createElement("span", null, "+4")));
  }
  var MEASURE_META = {
    height: { label: "Height-for-age", short: "Height", unit: "cm" },
    weight: { label: "Weight-for-age", short: "Weight", unit: "kg" },
    bmi: { label: "BMI-for-age", short: "BMI", unit: "kg/m2" }
  };
  var GENDER_THEME = {
    boys: { name: "Boys", header: "#2f5bb7", point: "#1d4ed8", page: "#bcd4ef" },
    girls: { name: "Girls", header: "#c74a86", point: "#be185d", page: "#e3a6df" }
  };
  var IAP_INK = "#1f2937";
  var IAP_RED = "#dc2626";
  var IAP_GRID_MAJOR = "#c9b98c";
  var IAP_GRID_MINOR = "#e4dcc2";
  var IAP_PAPER = "#fbf7ea";
  var COMBINED_CHART_YMAX = { boys: 195, girls: 175 };
  var CHART_VALIDATION_18Y = {
    // Bounds follow the wall chart's traced height lines at 18 y (boys
    // P3 160.3 / P97 187.0; girls P3 147.1 / P97 169.6), which differ from the
    // published table by up to ~2 cm at P3 and ~1 cm at P97.
    boys: { p3: [159, 161.5], p97: [186, 188] },
    girls: { p3: [146, 148], p97: [169, 171] }
  };
  function centileValueAtAge(centileSeries, targetAge) {
    if (!Array.isArray(centileSeries) || !centileSeries.length) return null;
    let best = null, bestDist = Infinity;
    for (const [a, v] of centileSeries) {
      const d = Math.abs(a - targetAge);
      if (d < bestDist) {
        bestDist = d;
        best = v;
      }
    }
    return bestDist <= 0.15 ? best : null;
  }
  function validateHeightReferenceSanity(heightData, sex) {
    const bounds = CHART_VALIDATION_18Y[sex];
    if (!bounds || !heightData || !heightData.centiles) {
      return { ok: false, reason: "missing height data or unrecognized sex", p3At18: null, p97At18: null, expected: bounds || null };
    }
    const p3At18 = centileValueAtAge(heightData.centiles["3"], 18);
    const p97At18 = centileValueAtAge(heightData.centiles["97"], 18);
    const inRange2 = (v, [lo, hi]) => v !== null && v >= lo && v <= hi;
    const ok = inRange2(p3At18, bounds.p3) && inRange2(p97At18, bounds.p97);
    return { ok, reason: ok ? null : "height P3/P97 at 18y outside expected reference range", p3At18, p97At18, expected: bounds };
  }
  var GRID_SUBDIVS = 5;
  function computeSquareGrid(plotWidth, xRange, xMajorStep, yRange, yMajorStep) {
    const xMinorStep = xMajorStep / GRID_SUBDIVS;
    const yMinorStep = yMajorStep / GRID_SUBDIVS;
    const cellPx = plotWidth * xMinorStep / xRange;
    const plotHeight = cellPx * yRange / yMinorStep;
    return { xMinorStep, yMinorStep, cellPx, plotHeight };
  }
  function GrowthChart({ measure, sex, ageYears, value, series = [], chartData, width = 780 }) {
    const meta = MEASURE_META[measure];
    const theme = GENDER_THEME[sex] || GENDER_THEME.boys;
    if (!chartData || !chartData.centiles) {
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "20px" } }, "Loading reference data\u2026");
    }
    if (chartData.sex !== sex || chartData.measure !== measure) {
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b91c1c", padding: "20px" } }, "Growth chart data does not match the selected sex/measure \u2014 refusing to render. Please retry.");
    }
    const centileKeys = Object.keys(chartData.centiles).map(Number).sort((a, b) => a - b);
    const a0 = chartData.age_min, a1 = chartData.age_max;
    const m = { l: 58, r: 50, t: 46, b: 52 };
    const curves = centileKeys.map((c) => {
      const pts = chartData.centiles[c].map(([a, v]) => ({ a, v }));
      return { c, pts, last: pts[pts.length - 1] || null };
    });
    let ymin = Infinity, ymax = -Infinity;
    curves.forEach((cu) => cu.pts.forEach((p) => {
      ymin = Math.min(ymin, p.v);
      ymax = Math.max(ymax, p.v);
    }));
    if (value > 0) {
      ymin = Math.min(ymin, value);
      ymax = Math.max(ymax, value);
    }
    const pad = (ymax - ymin) * 0.05 || 1;
    ymin -= pad;
    ymax += pad;
    const yStep = ymax - ymin > 60 ? 20 : ymax - ymin > 25 ? 10 : 5;
    const plotWidth = width - m.l - m.r;
    const plan = computeSquareGrid(plotWidth, a1 - a0, 1, ymax - ymin, yStep);
    const height = m.t + plan.plotHeight + m.b;
    const sx = (a) => m.l + (a - a0) / (a1 - a0) * plotWidth;
    const sy = (v) => height - m.b - (v - ymin) / (ymax - ymin) * plan.plotHeight;
    const linePath = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${sx(p.a).toFixed(1)},${sy(p.v).toFixed(1)}`).join(" ");
    const plotR = width - m.r, plotB = height - m.b;
    const xticks = [];
    for (let a = Math.ceil(a0); a <= Math.floor(a1); a++) xticks.push(a);
    const xMinorStart = Math.floor(a0 / 1) * 1;
    const xminors = [];
    for (let a = xMinorStart; a <= a1 + 1e-6; a += plan.xMinorStep) if (a >= a0 - 1e-6) xminors.push(a);
    const yMinorStart = Math.floor(ymin / yStep) * yStep;
    const yticks = [];
    for (let v = Math.ceil(ymin / yStep) * yStep; v <= ymax; v += yStep) yticks.push(v);
    const yminors = [];
    for (let v = yMinorStart; v <= ymax + 1e-6; v += plan.yMinorStep) if (v >= ymin - 1e-6) yminors.push(v);
    const serialPts = [...series].filter((s) => s.value > 0 && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);
    return /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", style: { maxWidth: `${width}px`, display: "block" }, xmlns: "http://www.w3.org/2000/svg" }, /* @__PURE__ */ React.createElement("rect", { x: "0", y: "0", width, height, fill: "#ffffff" }), /* @__PURE__ */ React.createElement("rect", { x: "0", y: "0", width, height: "34", fill: theme.header }), /* @__PURE__ */ React.createElement("text", { x: m.l, y: "15", fontSize: "12.5", fontWeight: "800", fill: "#ffffff" }, "IAP-style ", meta.label, " \xB7 ", theme.name), /* @__PURE__ */ React.createElement("text", { x: m.l, y: "28", fontSize: "8.5", fill: "#ffffff", opacity: "0.9" }, chartData.reference, " \xB7 LMS \xB7 percentiles 3\u201397 \xB7 ages ", Math.round(a0), "\u2013", Math.round(a1), " yr"), /* @__PURE__ */ React.createElement("rect", { x: m.l, y: m.t, width: plotR - m.l, height: plotB - m.t, fill: IAP_PAPER, stroke: IAP_GRID_MAJOR, strokeWidth: "1.2" }), yminors.map((v, i) => /* @__PURE__ */ React.createElement("line", { key: "ym" + i, x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), xminors.map((a, i) => /* @__PURE__ */ React.createElement("line", { key: "xmi" + i, x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), yticks.map((v) => /* @__PURE__ */ React.createElement("g", { key: "y" + v }, /* @__PURE__ */ React.createElement("line", { x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MAJOR, strokeWidth: "0.9" }), /* @__PURE__ */ React.createElement("text", { x: m.l - 6, y: sy(v) + 3, textAnchor: "end", fontSize: "9", fill: "#6b7280" }, v))), xticks.map((a) => /* @__PURE__ */ React.createElement("g", { key: "x" + a }, /* @__PURE__ */ React.createElement("line", { x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MAJOR, strokeWidth: "0.9" }), /* @__PURE__ */ React.createElement("text", { x: sx(a), y: plotB + 14, textAnchor: "middle", fontSize: "9", fill: "#6b7280" }, a))), /* @__PURE__ */ React.createElement("text", { x: (m.l + plotR) / 2, y: height - 5, textAnchor: "middle", fontSize: "10", fontWeight: "700", fill: "#475569" }, "Age (years)"), /* @__PURE__ */ React.createElement("text", { x: 15, y: (m.t + plotB) / 2, textAnchor: "middle", fontSize: "10", fontWeight: "700", fill: "#475569", transform: `rotate(-90 15 ${(m.t + plotB) / 2})` }, meta.short, " (", meta.unit, ")"), curves.map((cu) => {
      const isMed = cu.c === 50, isLow = cu.c === 3;
      const col = isLow ? IAP_RED : IAP_INK;
      const last = cu.last;
      return /* @__PURE__ */ React.createElement("g", { key: cu.c }, /* @__PURE__ */ React.createElement("path", { d: linePath(cu.pts), fill: "none", stroke: col, strokeWidth: isMed ? 2 : isLow ? 1.7 : 1.1 }), last && /* @__PURE__ */ React.createElement("text", { x: sx(last.a) + 3, y: sy(last.v) + 3, fontSize: "8.5", fontWeight: isMed || isLow ? "800" : "600", fill: col }, cu.c, isLow && measure === "height" ? "  (short below)" : isLow && measure !== "bmi" ? "  (low below)" : ""));
    }), serialPts.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: theme.point, strokeWidth: "1.6", strokeDasharray: "5,3", points: serialPts.map((p) => `${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ") }), serialPts.map((p, i) => /* @__PURE__ */ React.createElement("circle", { key: "s" + i, cx: sx(p.age), cy: sy(p.value), r: "3", fill: "#ffffff", stroke: theme.point, strokeWidth: "1.5" })), value > 0 && ageYears >= a0 && ageYears <= a1 && /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement("line", { x1: sx(ageYears), y1: m.t, x2: sx(ageYears), y2: plotB, stroke: theme.point, strokeWidth: "0.9", strokeDasharray: "2,3", opacity: "0.6" }), /* @__PURE__ */ React.createElement("circle", { cx: sx(ageYears), cy: sy(value), r: "5.5", fill: theme.point, stroke: "#ffffff", strokeWidth: "2.5" }), /* @__PURE__ */ React.createElement("rect", { x: sx(ageYears) > plotR - 92 ? sx(ageYears) - 94 : sx(ageYears) + 9, y: sy(value) - 21, width: "86", height: "17", rx: "4", fill: theme.point }), /* @__PURE__ */ React.createElement("text", { x: sx(ageYears) > plotR - 92 ? sx(ageYears) - 51 : sx(ageYears) + 52, y: sy(value) - 9, textAnchor: "middle", fontSize: "9.5", fontWeight: "800", fill: "#ffffff" }, Number(value).toFixed(1), " ", meta.unit, " @ ", ageYears.toFixed(1), " y")));
  }
  function GrowthChartCombined({ sex, ageYears, heightValue, weightValue, heightData, weightData, heightSeries = [], weightSeries = [], width = 850 }) {
    const theme = GENDER_THEME[sex] || GENDER_THEME.boys;
    if (!heightData || !heightData.centiles || !weightData || !weightData.centiles) {
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "20px" } }, "Loading reference data\u2026");
    }
    if (heightData.sex !== sex || weightData.sex !== sex) {
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b91c1c", padding: "20px" } }, "Growth chart data does not match the selected sex \u2014 refusing to render. Please retry.");
    }
    if (heightData.measure !== "height" || weightData.measure !== "weight") {
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b91c1c", padding: "20px" } }, "Growth chart data does not match the expected measure \u2014 refusing to render. Please retry.");
    }
    const heightSanity = validateHeightReferenceSanity(heightData, sex);
    if (!heightSanity.ok) {
      console.error("GrowthChartCombined: height reference data failed sanity validation -- refusing to render/export", { sex, ...heightSanity });
      return /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b91c1c", padding: "20px" } }, "Growth chart reference data failed a sanity check for ", theme.name.toLowerCase(), " height (P3/P97 at 18y out of expected range) \u2014 refusing to render. Please retry.");
    }
    const centileKeys = Object.keys(heightData.centiles).map(Number).sort((a, b) => a - b);
    const a0 = 0, a1 = Math.max(18, heightData.age_max);
    const m = { l: 70, r: 160, t: 70, b: 110 };
    const plotR = width - m.r;
    const heightCurves = centileKeys.map((c) => ({ c, pts: heightData.centiles[c].map(([a, v]) => ({ a, v })) }));
    const weightCurves = centileKeys.map((c) => ({ c, pts: weightData.centiles[c].map(([a, v]) => ({ a, v })) }));
    let dataMax = 0;
    [...heightCurves, ...weightCurves].forEach((cu) => cu.pts.forEach((p) => {
      dataMax = Math.max(dataMax, p.v);
    }));
    if (heightValue > 0) dataMax = Math.max(dataMax, heightValue);
    if (weightValue > 0) dataMax = Math.max(dataMax, weightValue);
    const fixedYmax = COMBINED_CHART_YMAX[sex];
    const ymax = fixedYmax || Math.ceil(dataMax * 1.03 / 5) * 5;
    const ymin = 0;
    const heightOutOfRange = heightValue > 0 && heightValue > ymax;
    const weightOutOfRange = weightValue > 0 && weightValue > ymax;
    const outOfRange = heightOutOfRange || weightOutOfRange;
    const yMajor = 5;
    const plotWidth = plotR - m.l;
    const squarePlan = computeSquareGrid(plotWidth, a1 - a0, 1, ymax - ymin, yMajor);
    const plan = { ...squarePlan, xMinorStep: 0.25, plotHeight: Math.min(squarePlan.plotHeight, plotWidth * 1.5) };
    const height = m.t + plan.plotHeight + m.b;
    const plotB = height - m.b;
    const sx = (a) => m.l + (a - a0) / (a1 - a0) * plotWidth;
    const sy = (v) => plotB - (v - ymin) / (ymax - ymin) * plan.plotHeight;
    const linePath = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${sx(p.a).toFixed(1)},${sy(p.v).toFixed(1)}`).join(" ");
    const yticks = [];
    for (let v = 0; v <= ymax; v += yMajor) yticks.push(v);
    const yminors = [];
    for (let v = 0; v <= ymax + 1e-6; v += plan.yMinorStep) yminors.push(v);
    const xticks = [];
    for (let a = Math.ceil(a0); a <= Math.floor(a1); a += 1) xticks.push(a);
    const xminors = [];
    for (let a = a0; a <= a1 + 1e-6; a += plan.xMinorStep) xminors.push(Math.round(a * 1e4) / 1e4);
    const heightSerial = [...heightSeries].filter((s) => s.value > 0 && s.value <= ymax && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);
    const weightSerial = [...weightSeries].filter((s) => s.value > 0 && s.value <= ymax && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);
    const renderCurveGroup = (curves, quantity) => curves.map((cu) => {
      const isMed = cu.c === 50, isLow = cu.c === 3, isHeight = quantity === "height";
      const col = isLow && isHeight ? IAP_RED : IAP_INK;
      const last = cu.pts[cu.pts.length - 1];
      return /* @__PURE__ */ React.createElement("g", { key: quantity + cu.c }, /* @__PURE__ */ React.createElement("path", { d: linePath(cu.pts), fill: "none", stroke: col, strokeWidth: isMed ? 2.2 : isLow && isHeight ? 1.8 : 1.1 }), last && /* @__PURE__ */ React.createElement("text", { x: sx(last.a) + 4, y: sy(last.v) + 3, fontSize: "9.5", fontWeight: isMed || isLow && isHeight ? "800" : "600", fill: col }, cu.c, isLow && isHeight ? " (Short below this line)" : ""));
    });
    const labelBadge = (v, atAge, unit) => {
      const cx = sx(atAge), cy = sy(v);
      const flip = cx > plotR - 112;
      return /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "5.5", fill: theme.point, stroke: "#ffffff", strokeWidth: "2.5" }), /* @__PURE__ */ React.createElement("rect", { x: flip ? cx - 112 : cx + 9, y: cy - 21, width: "102", height: "17", rx: "4", fill: theme.point }), /* @__PURE__ */ React.createElement("text", { x: flip ? cx - 61 : cx + 60, y: cy - 9, textAnchor: "middle", fontSize: "9.5", fontWeight: "800", fill: "#ffffff" }, Number(v).toFixed(1), " ", unit, " @ ", ageYears.toFixed(1), " y"));
    };
    return /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", style: { maxWidth: `${width}px`, display: "block" }, xmlns: "http://www.w3.org/2000/svg" }, /* @__PURE__ */ React.createElement("rect", { x: "0", y: "0", width, height, fill: theme.page }), /* @__PURE__ */ React.createElement("rect", { x: "14", y: "14", width: width - 28, height: "40", fill: "#ffffff", rx: "4" }), /* @__PURE__ */ React.createElement("text", { x: width / 2, y: "40", textAnchor: "middle", fontSize: "16.5", fontWeight: "800", fill: "#1e293b" }, "WHO 2006 & IAP 2015 combined ", theme.name, " Chart \u2014 Height & Weight, 0\u201318 Years"), /* @__PURE__ */ React.createElement("rect", { x: m.l, y: m.t, width: plotR - m.l, height: plotB - m.t, fill: IAP_PAPER, stroke: IAP_GRID_MAJOR, strokeWidth: "1.2" }), yminors.map((v, i) => /* @__PURE__ */ React.createElement("line", { key: "ym" + i, x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), xminors.map((a, i) => /* @__PURE__ */ React.createElement("line", { key: "xmi" + i, x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), yticks.map((v) => /* @__PURE__ */ React.createElement("g", { key: "y" + v }, /* @__PURE__ */ React.createElement("line", { x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MAJOR, strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { x: m.l - 8, y: sy(v) + 3, textAnchor: "end", fontSize: "10", fill: "#57534e" }, v))), xticks.map((a) => /* @__PURE__ */ React.createElement("g", { key: "x" + a }, /* @__PURE__ */ React.createElement("line", { x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MAJOR, strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { x: sx(a), y: plotB + 16, textAnchor: "middle", fontSize: "10", fill: "#57534e" }, a))), /* @__PURE__ */ React.createElement("text", { x: (m.l + plotR) / 2, y: height - 46, textAnchor: "middle", fontSize: "12", fontWeight: "700", fill: "#334155" }, "Age in Years"), /* @__PURE__ */ React.createElement("text", { x: 24, y: (m.t + plotB) / 2, textAnchor: "middle", fontSize: "12", fontWeight: "700", fill: "#334155", transform: `rotate(-90 24 ${(m.t + plotB) / 2})` }, "Height in CM and Weight in KG"), renderCurveGroup(heightCurves, "height"), renderCurveGroup(weightCurves, "weight"), weightSerial.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: theme.point, strokeWidth: "1.6", strokeDasharray: "5,3", points: weightSerial.map((p) => `${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ") }), weightSerial.map((p, i) => /* @__PURE__ */ React.createElement("circle", { key: "ws" + i, cx: sx(p.age), cy: sy(p.value), r: "3", fill: "#ffffff", stroke: theme.point, strokeWidth: "1.5" })), heightSerial.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: theme.point, strokeWidth: "1.6", strokeDasharray: "5,3", points: heightSerial.map((p) => `${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ") }), heightSerial.map((p, i) => /* @__PURE__ */ React.createElement("circle", { key: "hs" + i, cx: sx(p.age), cy: sy(p.value), r: "3", fill: "#ffffff", stroke: theme.point, strokeWidth: "1.5" })), ageYears >= a0 && ageYears <= a1 && (heightValue > 0 || weightValue > 0) && /* @__PURE__ */ React.createElement("line", { x1: sx(ageYears), y1: m.t, x2: sx(ageYears), y2: plotB, stroke: theme.point, strokeWidth: "1", strokeDasharray: "2,3", opacity: "0.55" }), heightValue > 0 && !heightOutOfRange && ageYears >= a0 && ageYears <= a1 && labelBadge(heightValue, ageYears, "cm"), weightValue > 0 && !weightOutOfRange && ageYears >= a0 && ageYears <= a1 && labelBadge(weightValue, ageYears, "kg"), outOfRange && /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement("rect", { x: "14", y: "58", width: width - 28, height: "24", fill: "#fef2f2", stroke: "#fecaca", strokeWidth: "1", rx: "4" }), /* @__PURE__ */ React.createElement("text", { x: width / 2, y: "74", textAnchor: "middle", fontSize: "11", fontWeight: "800", fill: "#b91c1c" }, "\u26A0 Patient value is outside standard chart range.", heightOutOfRange ? ` Height ${heightValue}cm` : "", heightOutOfRange && weightOutOfRange ? " and" : "", weightOutOfRange ? ` Weight ${weightValue}kg` : "", " ", "not plotted \u2014 axis is fixed to the standard 0\u2013", ymax, " reference range.")), /* @__PURE__ */ React.createElement("text", { x: m.l, y: height - 26, fontSize: "8.5", fill: "#6b7280" }, heightData.reference, (heightData.wall_chart_traced_centiles || []).length ? " \xB7 height & weight lines drawn from the IAP wall chart" : ""), /* @__PURE__ */ React.createElement("text", { x: m.l, y: height - 14, fontSize: "8.5", fill: "#6b7280" }, 'Decision support only \u2014 not diagnostic; a clinician must verify all results. Red line = 3rd height percentile ("short below this line").'));
  }

  // frontend/src/ui.jsx
  function ProbBar({ prob, maxProb, threshold, label }) {
    const left = probToPercent(prob, maxProb);
    const threshLeft = probToPercent(threshold, maxProb);
    return /* @__PURE__ */ React.createElement("div", { style: { paddingTop: "8px", paddingBottom: "4px" } }, /* @__PURE__ */ React.createElement("div", { className: "prob-track", style: { position: "relative" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: "-6px", left: `${threshLeft}%`, width: "2px", height: "20px", background: "#475569", borderRadius: "1px", transform: "translateX(-50%)" } }), /* @__PURE__ */ React.createElement("div", { className: "prob-marker", style: { left: `${left}%` } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "9px", fontWeight: "700", color: "#94a3b8", letterSpacing: "0.05em", textTransform: "uppercase" } }, /* @__PURE__ */ React.createElement("span", null, "0%"), /* @__PURE__ */ React.createElement("span", { style: { color: "#475569" } }, "Tx threshold: ", threshold, "%"), /* @__PURE__ */ React.createElement("span", null, maxProb, "%")));
  }
  function StatusBadge({ text, variant }) {
    const styles = {
      low: "risk-badge-low",
      mid: "risk-badge-mid",
      high: "risk-badge-high",
      info: "bg-indigo-50 text-indigo-700 border border-indigo-200",
      neutral: "bg-slate-100 text-slate-600 border border-slate-200"
    };
    const glyph = { low: "\u2713", mid: "!", high: "\u25B2" }[variant];
    return /* @__PURE__ */ React.createElement("span", { style: { display: "inline-flex", alignItems: "center", gap: "5px", padding: "3px 10px", borderRadius: "99px", fontSize: "11px", fontWeight: "700" }, className: styles[variant] || styles.neutral }, glyph && /* @__PURE__ */ React.createElement("span", { "aria-hidden": "true", style: { fontSize: "10px", lineHeight: 1 } }, glyph), text);
  }
  function MetricRow({ label, value, unit, sub, children, accent }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "6px", padding: "14px 0", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", paddingTop: "6px" } }, label), /* @__PURE__ */ React.createElement("div", { style: { textAlign: "right" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "32px", fontWeight: "900", color: accent || "#1e293b", lineHeight: 1 } }, value), unit && /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "500", color: "#94a3b8", marginLeft: "6px" } }, unit), sub && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "2px" } }, sub))), children);
  }
  function SectionHeader({ title, subtitle, badge, badgeVariant }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", paddingBottom: "14px", borderBottom: "1.5px solid #f1f5f9", marginBottom: "4px", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("h3", { style: { fontSize: "13px", fontWeight: "800", color: "#334155", letterSpacing: "0.01em" } }, title), subtitle && /* @__PURE__ */ React.createElement("p", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, subtitle)), badge && /* @__PURE__ */ React.createElement(StatusBadge, { text: badge, variant: badgeVariant || "info" }));
  }
  function YesNoToggleRow({ label, value, setter }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "600", color: "#475569" } }, label), /* @__PURE__ */ React.createElement("div", { className: "toggle-pill" }, /* @__PURE__ */ React.createElement("button", { className: `toggle-btn ${value === "yes" ? "toggle-on" : "toggle-off"}`, onClick: () => setter("yes") }, "Yes"), /* @__PURE__ */ React.createElement("button", { className: `toggle-btn ${value === "no" ? "toggle-on" : "toggle-off"}`, onClick: () => setter("no") }, "No")));
  }
  function InputWithUnit({ label, value, onChange, placeholder, step, unit, accent, problem }) {
    return /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, label), /* @__PURE__ */ React.createElement("div", { style: { position: "relative", display: "flex", alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        step: step || "any",
        placeholder: placeholder || "\u2014",
        value,
        onChange,
        className: "input-field",
        "aria-invalid": problem ? true : void 0,
        style: {
          ...problem ? { borderColor: "#f87171", background: "#fff7f7" } : {},
          paddingRight: unit ? "44px" : "12px",
          color: accent || "#1e293b",
          minWidth: 0,
          width: "100%"
        }
      }
    ), unit && /* @__PURE__ */ React.createElement("span", { style: { position: "absolute", right: "10px", fontSize: "10px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", pointerEvents: "none", whiteSpace: "nowrap" } }, unit)), problem && /* @__PURE__ */ React.createElement("div", { role: "alert", style: { fontSize: "10px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.4" } }, problem));
  }
  function EmptyState({ title, hint, tone }) {
    const c = tone === "violet" ? { bg: "#f5f3ff", stroke: "#a78bfa" } : { bg: "#f1f5f9", stroke: "#94a3b8" };
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: "12px", padding: "40px 0", textAlign: "center", minHeight: "220px" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "56px", height: "56px", borderRadius: "50%", background: c.bg, display: "flex", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "none", stroke: c.stroke, strokeWidth: "2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "8", x2: "12", y2: "12" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "16", x2: "12.01", y2: "16" }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "14px", fontWeight: "700", color: "#475569" } }, title), hint && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", maxWidth: "300px", lineHeight: "1.6" } }, hint));
  }
  function heroTone(variant) {
    if (variant === "high") return { background: "linear-gradient(135deg,#fff1f2,#fef2f2)", border: "1.5px solid #fecaca" };
    if (variant === "mid") return { background: "linear-gradient(135deg,#fffbeb,#fefce8)", border: "1.5px solid #fde68a" };
    if (variant === "low") return { background: "linear-gradient(135deg,#f0fdf4,#f7fee7)", border: "1.5px solid #bbf7d0" };
    return { background: "#f8fafc", border: "1.5px solid #e2e8f0" };
  }
  function variantToState(v) {
    return v === "high" ? "high" : v === "mid" ? "borderline" : v === "low" ? "normal" : "none";
  }
  function computeAgeParts(dobStr) {
    if (!dobStr) return null;
    const b = /* @__PURE__ */ new Date(dobStr + "T00:00:00");
    const now = /* @__PURE__ */ new Date();
    if (isNaN(b.getTime()) || b > now) return null;
    let years = now.getFullYear() - b.getFullYear();
    let months = now.getMonth() - b.getMonth();
    let days = now.getDate() - b.getDate();
    if (days < 0) {
      months -= 1;
      days += new Date(now.getFullYear(), now.getMonth(), 0).getDate();
    }
    if (months < 0) {
      years -= 1;
      months += 12;
    }
    const decimal = (now - b) / (365.25 * 24 * 3600 * 1e3);
    return { years, months, days, decimal };
  }

  // frontend/src/state.jsx
  var ClinicalStateContext = React.createContext(null);
  function ClinicalStateProvider({ value, children }) {
    return React.createElement(ClinicalStateContext.Provider, { value }, children);
  }
  function useClinicalState() {
    const ctx = React.useContext(ClinicalStateContext);
    if (!ctx) {
      throw new Error(
        "useClinicalState must be used inside <ClinicalStateProvider>. A panel was rendered outside the provider that supplies its data."
      );
    }
    return ctx;
  }
  function usePatient() {
    const s = useClinicalState();
    return {
      age: s.age,
      dob: s.dob,
      gender: s.gender,
      height: s.height,
      weight: s.weight,
      evalAge: s.evalAge,
      evalHeight: s.evalHeight,
      evalWeight: s.evalWeight,
      patientName: s.patientName,
      patientMrn: s.patientMrn,
      examDate: s.examDate
    };
  }
  function useLiver() {
    const s = useClinicalState();
    return { metrics: s.liverMetrics, hasManual: s.hasManualLiver };
  }
  function useRenal() {
    const s = useClinicalState();
    return { metrics: s.renalMetrics, hasManual: s.hasManualRenal };
  }
  function useFrax() {
    const s = useClinicalState();
    return {
      metrics: s.fraxMetrics,
      hasManual: s.hasManualFrax,
      fraxMofEntered: s.fraxMofEntered,
      setFraxMofEntered: s.setFraxMofEntered,
      fraxHfEntered: s.fraxHfEntered,
      setFraxHfEntered: s.setFraxHfEntered
    };
  }
  function useInputs() {
    const s = useClinicalState();
    return {
      age: s.age,
      handleAgeChange: s.handleAgeChange,
      dob: s.dob,
      handleDobChange: s.handleDobChange,
      ageParts: s.ageParts,
      gender: s.gender,
      setGender: s.setGender,
      height: s.height,
      setHeight: s.setHeight,
      weight: s.weight,
      setWeight: s.setWeight,
      // Which cards the active tab actually consumes -- the panel stays live and
      // editable, irrelevant sections are only de-emphasised.
      labsRelevant: s.labsRelevant,
      creatinine: s.creatinine,
      setCreatinine: s.setCreatinine,
      albuminuria: s.albuminuria,
      setAlbuminuria: s.setAlbuminuria,
      systolic: s.systolic,
      setSystolic: s.setSystolic,
      diastolic: s.diastolic,
      setDiastolic: s.setDiastolic,
      ast: s.ast,
      setAst: s.setAst,
      alt: s.alt,
      setAlt: s.setAlt,
      platelets: s.platelets,
      setPlatelets: s.setPlatelets
    };
  }
  function useShell() {
    const s = useClinicalState();
    return {
      resetAll: s.resetAll,
      exportFullReport: s.exportFullReport,
      patientName: s.patientName,
      setPatientName: s.setPatientName,
      patientMrn: s.patientMrn,
      setPatientMrn: s.setPatientMrn,
      examDate: s.examDate,
      setExamDate: s.setExamDate,
      age: s.age,
      gender: s.gender,
      TABS: s.TABS,
      activeTab: s.activeTab,
      setActiveTab: s.setActiveTab,
      moduleStatus: s.moduleStatus,
      timeline: s.timeline
    };
  }
  function useOverview() {
    const s = useClinicalState();
    return {
      moduleStatus: s.moduleStatus,
      setActiveTab: s.setActiveTab
    };
  }
  function useGrowth() {
    const s = useClinicalState();
    return {
      age: s.age,
      evalAge: s.evalAge,
      evalGender: s.evalGender,
      evalHeight: s.evalHeight,
      evalWeight: s.evalWeight,
      examDate: s.examDate,
      exportGrowthReportPdf: s.exportGrowthReportPdf,
      gender: s.gender,
      growthChartMeasure: s.growthChartMeasure,
      growthMetrics: s.growthMetrics,
      growthSeries: s.growthSeries,
      hasManualGrowth: s.hasManualGrowth,
      height: s.height,
      moduleStatus: s.moduleStatus,
      patientMrn: s.patientMrn,
      patientName: s.patientName,
      setGrowthChartMeasure: s.setGrowthChartMeasure,
      setShowChart: s.setShowChart,
      showChart: s.showChart,
      timeline: s.timeline,
      weight: s.weight
    };
  }
  function useQrisk() {
    const s = useClinicalState();
    return {
      cholRatio: s.cholRatio,
      diabetes: s.diabetes,
      ethnicity: s.ethnicity,
      evalGender: s.evalGender,
      qAF: s.qAF,
      qAtypAntipsy: s.qAtypAntipsy,
      qCKD: s.qCKD,
      qCortico: s.qCortico,
      qED: s.qED,
      qFhCvd: s.qFhCvd,
      qMigraine: s.qMigraine,
      qRA: s.qRA,
      qSLE: s.qSLE,
      qSMI: s.qSMI,
      qTreatedHtn: s.qTreatedHtn,
      qriskMetrics: s.qriskMetrics,
      sbpSD: s.sbpSD,
      setCholRatio: s.setCholRatio,
      setDiabetes: s.setDiabetes,
      setEthnicity: s.setEthnicity,
      setQAF: s.setQAF,
      setQAtypAntipsy: s.setQAtypAntipsy,
      setQCKD: s.setQCKD,
      setQCortico: s.setQCortico,
      setQED: s.setQED,
      setQFhCvd: s.setQFhCvd,
      setQMigraine: s.setQMigraine,
      setQRA: s.setQRA,
      setQSLE: s.setQSLE,
      setQSMI: s.setQSMI,
      setQTreatedHtn: s.setQTreatedHtn,
      setSbpSD: s.setSbpSD,
      setSmokeCat: s.setSmokeCat,
      smokeCat: s.smokeCat
    };
  }
  function useRecord() {
    const s = useClinicalState();
    return {
      patientMrn: s.patientMrn,
      patientName: s.patientName,
      examDate: s.examDate,
      sexEntered: s.sexEntered,
      dob: s.dob,
      height: s.height,
      weight: s.weight,
      systolic: s.systolic,
      diastolic: s.diastolic,
      heightOk: s.heightOk,
      weightOk: s.weightOk,
      bpOk: s.bpOk
    };
  }
  function useLedger() {
    const s = useClinicalState();
    return {
      age: s.age,
      albuminuria: s.albuminuria,
      assessment: s.assessment,
      canLogSnapshot: s.canLogSnapshot,
      chronicityStatus: s.chronicityStatus,
      creatinine: s.creatinine,
      height: s.height,
      logCurrentData: s.logCurrentData,
      setTimeline: s.setTimeline,
      timeline: s.timeline,
      weight: s.weight
    };
  }
  function useBoneAge() {
    return useClinicalState().boneAge;
  }

  // frontend/src/clinicalRanges.js
  var RANGES = {
    age: { min: 0, max: 120, unit: "yrs" },
    // Lower bounds admit extremely preterm infants (~22-24 weeks: ~0.4 kg, ~28 cm).
    height: { min: 20, max: 250, unit: "cm" },
    weight: { min: 0.3, max: 350, unit: "kg" },
    creatinine: { min: 0.05, max: 25, unit: "mg/dL" },
    systolic: { min: 40, max: 300, unit: "mmHg" },
    diastolic: { min: 20, max: 200, unit: "mmHg" },
    // Acute liver failure can exceed 10,000 U/L; extreme thrombocytosis 2,000.
    ast: { min: 1, max: 5e4, unit: "U/L" },
    alt: { min: 1, max: 5e4, unit: "U/L" },
    platelets: { min: 1, max: 5e3, unit: "\xD710\xB3/\xB5L" },
    // Parents are adults (100 cm admits skeletal dysplasias); outside this is a
    // typo, or inches rather than cm.
    parentHeight: { min: 100, max: 230, unit: "cm" },
    boneAge: { min: 0, max: 20, unit: "yrs" },
    // QRISK3 inputs entered on its own tab.
    cholRatio: { min: 1, max: 20, unit: "ratio" },
    sbpSD: { min: 0, max: 50, unit: "mmHg" },
    // A percentage read off the official FRAX calculator.
    fraxPct: { min: 0, max: 100, unit: "%" }
  };
  function inRange(field, value) {
    if (value === "" || value === null || value === void 0) return false;
    const n = typeof value === "number" ? value : parseFloat(value);
    const r = RANGES[field];
    return Number.isFinite(n) && n >= r.min && n <= r.max;
  }
  function rangeProblem(field, value) {
    if (value === "" || value === null || value === void 0) return null;
    if (inRange(field, value)) return null;
    const r = RANGES[field];
    return `Outside plausible range (${r.min}\u2013${r.max} ${r.unit}) \u2014 check the value and unit`;
  }

  // frontend/src/boneAgeHandlers.js
  function useBoneAgeHandlers(s) {
    const {
      adjReviewer,
      age,
      aiEstimate,
      assessment,
      boxes,
      sexEntered,
      ageEntered,
      boxesRef,
      carpalStages,
      coverage,
      declaredFlags,
      estimateDomain,
      fbAge,
      fbConfidence,
      fbMethod,
      fbNote,
      fbRater,
      height,
      lastFilm,
      locDrag,
      locImg,
      locRef,
      ltTables,
      monitoring,
      patientCode,
      radiograph,
      rusStages,
      setAdjBusy,
      setAdjItems,
      setAdjMsg,
      setAiBusy,
      setAiEstimate,
      setAssessment,
      setBoneAge,
      setBoneAgeSource,
      setBoxes,
      setCarpalStages,
      setCovBusy,
      setCoverage,
      setDeclaredFlags,
      setFbAge,
      setFbBusy,
      setFbMsg,
      setFbNote,
      setLastFilm,
      setLcBusy,
      setLcMsg,
      setLocBusy,
      setLocImg,
      setLocMsg,
      setLcohBusy,
      setLocalCohort,
      setLtBusy,
      setLtMsg,
      setLtStatus,
      setLtTables,
      setMonBusy,
      setMonitoring,
      setRadiograph,
      setRusStages,
      setSelBone,
      setShowAudit,
      showAudit
    } = s;
    const LC_API = "/api/bone-age/assessments";
    const lcLocked = assessment && (assessment.assessment_status === "approved" || assessment.assessment_status === "superseded");
    const saveDraft = async () => {
      if (!patientCode.trim()) {
        setLcMsg({ type: "err", text: "Enter a patient code to save." });
        return;
      }
      if (!sexEntered) {
        setLcMsg({ type: "err", text: "Set biological sex first." });
        return;
      }
      const carpalEntries = Object.entries(carpalStages).map(([n, g]) => [carpalCode(n), g]);
      if (Object.keys(rusStages).length === 0 && carpalEntries.length === 0) {
        setLcMsg({ type: "err", text: "Grade at least one bone." });
        return;
      }
      setLcBusy(true);
      setLcMsg(null);
      try {
        let a = assessment;
        if (!a || a.assessment_status === "approved" || a.assessment_status === "superseded") {
          const res = await fetch(LC_API, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              patient_code: patientCode.trim(),
              sex: sexEntered,
              chronological_age_years: ageEntered,
              stage_system: "tw3-letters"
            })
          });
          if (!res.ok) throw new Error((await res.json()).detail || "create failed");
          a = await res.json();
        }
        for (const [bone, grade] of [...Object.entries(rusStages), ...carpalEntries]) {
          const r = await fetch(`${LC_API}/${a.id}/bones/${bone}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage: grade })
          });
          if (r.ok) {
            a = await r.json();
          } else {
            throw new Error((await r.json()).detail || `could not save ${bone}`);
          }
        }
        setAssessment(a);
        setLcMsg({ type: "ok", text: `Saved annotation \xB7 #${a.id} rev ${a.revision} \xB7 ${a.rus_staged_count}/13 RUS + ${a.carpal_staged_count}/7 carpal` });
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const bonesIntoGrids = (bones) => {
      const rus = {}, carp = {}, bx = {};
      (bones || []).forEach((b) => {
        if (b.localisation_box) bx[b.bone_code] = b.localisation_box;
        if (!b.confirmed_stage) return;
        if (b.bone_group === "carpal") carp[carpalName(b.bone_code)] = b.confirmed_stage;
        else rus[b.bone_code] = b.confirmed_stage;
      });
      setRusStages(rus);
      setCarpalStages(carp);
      setBoxes(bx);
    };
    const unsavedStaging = (() => {
      if (!assessment) return false;
      const saved = {};
      (assessment.bones || []).forEach((b) => {
        if (b.confirmed_stage) saved[b.bone_code] = b.confirmed_stage;
      });
      const grid = { ...rusStages };
      Object.entries(carpalStages).forEach(([n, g]) => {
        grid[carpalCode(n)] = g;
      });
      for (const k of /* @__PURE__ */ new Set([...Object.keys(saved), ...Object.keys(grid)])) {
        if (saved[k] !== grid[k]) return true;
      }
      return false;
    })();
    const SAVE_FIRST = "Save the annotation first: the grades on screen differ from the saved record.";
    const calculateAssessment = async () => {
      if (!assessment) return;
      if (unsavedStaging) {
        setLcMsg({ type: "err", text: SAVE_FIRST });
        return;
      }
      setLcBusy(true);
      setLcMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/calculate`, { method: "POST" });
        const d = await res.json();
        if (!res.ok) {
          setLcMsg({ type: "err", text: d.detail || "calculate failed" });
        } else {
          setAssessment(d);
          const rus = d.total_rus_score != null ? `RUS ${d.total_rus_score} \u2192 ` : "";
          setLcMsg({ type: "ok", text: d.bone_age_years != null ? `Calculated \xB7 ${rus}${d.bone_age_years.toFixed(1)} yr \xB7 review it, then Approve` : "Calculated, but no bone age was produced" });
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const approveAssessment = async () => {
      if (!assessment) return;
      if (unsavedStaging) {
        setLcMsg({ type: "err", text: SAVE_FIRST });
        return;
      }
      if (assessment.assessment_status !== "ready_for_review" || assessment.bone_age_years == null) {
        setLcMsg({ type: "err", text: "Calculate first: only a calculated bone age can be approved." });
        return;
      }
      const ok = window.confirm(
        `Approve bone age ${assessment.bone_age_years.toFixed(1)} years for patient ${assessment.patient_code || patientCode.trim()} (record #${assessment.id}, rev ${assessment.revision})?

The record will be locked and this bone age will be used by the clinical rules. Corrections afterwards need "Open revision".`
      );
      if (!ok) return;
      setLcBusy(true);
      setLcMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        const d = await res.json();
        if (!res.ok) setLcMsg({ type: "err", text: d.detail || "approve failed" });
        else {
          setAssessment(d);
          if (d.bone_age_years != null) {
            setBoneAge(Number(d.bone_age_years.toFixed(1)));
            setBoneAgeSource("rus");
          }
          setLcMsg({ type: "ok", text: `Approved by ${d.approved_by} \xB7 bone age ${d.bone_age_years != null ? d.bone_age_years.toFixed(1) + " yr" : "\u2014"} now in use` });
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const reviseAssessment = async () => {
      if (!assessment) return;
      setLcBusy(true);
      setLcMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/revise`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "re-read" })
        });
        const d = await res.json();
        if (!res.ok) setLcMsg({ type: "err", text: d.detail || "revise failed" });
        else {
          bonesIntoGrids(d.bones);
          setAssessment(d);
          setShowAudit(false);
          setLcMsg({ type: "ok", text: `Opened revision ${d.revision} (draft)` });
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const toggleAudit = async () => {
      if (!assessment) return;
      const next = !showAudit;
      setShowAudit(next);
      if (next) {
        try {
          const r = await fetch(`${LC_API}/${assessment.id}?include_audit=true`);
          if (r.ok) setAssessment(await r.json());
        } catch {
        }
      }
    };
    const submitFeedback = async () => {
      const yrs = parseFloat(fbAge);
      if (!(yrs > 0)) {
        setFbMsg({ type: "err", text: "Enter the correct bone age in years." });
        return;
      }
      setFbBusy(true);
      setFbMsg(null);
      try {
        const body = {
          corrected_age_years: yrs,
          method: fbMethod,
          confidence: fbConfidence,
          rater_id: fbRater || null,
          sex: sexEntered,
          chronological_age_years: ageEntered,
          ai_estimate_years: aiEstimate && aiEstimate.bone_age_years != null ? aiEstimate.bone_age_years : null,
          ai_model_version: aiEstimate && aiEstimate.model_version || null,
          radiograph_id: radiograph && radiograph.id || null,
          assessment_id: assessment && assessment.id || null,
          image_domain: radiograph && radiograph.source_domain || estimateDomain || null,
          note: fbNote || null
        };
        const res = await fetch("/api/bone-age/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const d = await res.json();
        if (!res.ok) {
          setFbMsg({ type: "err", text: d.detail || "could not save" });
        } else {
          setFbMsg({ type: "ok", text: d.message || "Thanks \u2014 logged." });
          setFbAge("");
          setFbNote("");
        }
      } catch (e) {
        setFbMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setFbBusy(false);
      }
    };
    const runEstimate = async (fileObj, flags) => {
      if (!sexEntered) {
        setAiEstimate({ error: "Set biological sex in Demographics first." });
        return;
      }
      const useFlags = flags || declaredFlags;
      setLastFilm(fileObj);
      setAiBusy(true);
      setAiEstimate(null);
      try {
        const fd = new FormData();
        fd.append("file", fileObj);
        fd.append("sex", sexEntered);
        fd.append("image_domain", estimateDomain);
        fd.append("declared_flags", useFlags.join(","));
        const res = await fetch("/api/bone-age/estimate", { method: "POST", body: fd });
        const d = await res.json();
        if (!res.ok) setAiEstimate({ error: d.detail || "estimate failed" });
        else setAiEstimate(d);
      } catch (e) {
        setAiEstimate({ error: String(e.message || e) });
      } finally {
        setAiBusy(false);
      }
    };
    const toggleDeclaredFlag = (code) => {
      setDeclaredFlags((prev) => {
        const next = prev.includes(code) ? prev.filter((f) => f !== code) : [...prev, code];
        if (lastFilm) runEstimate(lastFilm, next);
        return next;
      });
    };
    const attachImage = async (fileObj) => {
      if (!assessment) {
        setLcMsg({ type: "err", text: "Save the draft first, then attach a film." });
        return;
      }
      if (lcLocked) {
        setLcMsg({ type: "err", text: "Assessment is locked; open a revision to change the image." });
        return;
      }
      setLcBusy(true);
      setLcMsg(null);
      try {
        const fd = new FormData();
        fd.append("file", fileObj);
        const res = await fetch(`${LC_API}/${assessment.id}/image`, { method: "POST", body: fd });
        const d = await res.json();
        if (!res.ok) {
          setLcMsg({ type: "err", text: d.detail || "upload failed" });
        } else {
          setRadiograph(d);
          setLcMsg({ type: "ok", text: `Film attached \xB7 ${d.source_format} \xB7 ${d.quality_status.replace(/_/g, " ")}` });
          runEstimate(fileObj);
          localizeBones();
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const loadCoverage = async () => {
      setCovBusy(true);
      try {
        const r = await fetch("/api/bone-age/coverage");
        if (r.ok) setCoverage(await r.json());
      } catch {
      } finally {
        setCovBusy(false);
      }
    };
    const loadMonitoring = async () => {
      setMonBusy(true);
      try {
        const r = await fetch("/api/bone-age/monitoring");
        if (r.ok) setMonitoring(await r.json());
      } catch {
      } finally {
        setMonBusy(false);
      }
    };
    const loadLocalCohort = async () => {
      setLcohBusy(true);
      try {
        const r = await fetch("/api/bone-age/local-cohort");
        if (r.ok) setLocalCohort(await r.json());
      } catch {
      } finally {
        setLcohBusy(false);
      }
    };
    const loadAdjudication = async () => {
      setAdjBusy(true);
      setAdjMsg(null);
      try {
        const r = await fetch("/api/bone-age/adjudication?status=open");
        if (r.ok) setAdjItems((await r.json()).items || []);
      } catch (e) {
        setAdjMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setAdjBusy(false);
      }
    };
    const resolveAdjudication = async (id, stage) => {
      if (!adjReviewer.trim()) {
        setAdjMsg({ type: "err", text: "Enter the reviewing clinician first." });
        return;
      }
      setAdjBusy(true);
      setAdjMsg(null);
      try {
        const r = await fetch(`/api/bone-age/adjudication/${id}/resolve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resolved_stage: stage, resolved_by: adjReviewer.trim() })
        });
        if (r.ok) {
          setAdjMsg({ type: "ok", text: `Resolved to stage ${stage}.` });
          await loadAdjudication();
        } else {
          const e = await r.json();
          setAdjMsg({ type: "err", text: e.detail || "Resolve failed." });
        }
      } catch (e) {
        setAdjMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setAdjBusy(false);
      }
    };
    const _emptyLt = () => ({
      method: "TW3-letters",
      version: "letters-clinic",
      rus_stage_to_score: { boys: {}, girls: {} },
      carpal_stage_to_score: { boys: {}, girls: {} },
      rus_score_to_age: { twii: { boys: [], girls: [] }, twiii: { boys: [], girls: [] } },
      carpal_score_to_age: { twii: { boys: [], girls: [] }, twiii: { boys: [], girls: [] } },
      tw20_stage_to_score: { boys: {}, girls: {} },
      tw20_score_to_age: { boys: [], girls: [] },
      reference_cases: []
    });
    const loadLetterTables = async () => {
      setLtBusy(true);
      setLtMsg(null);
      try {
        const d = await (await fetch("/api/bone-age/letters-tables")).json();
        const t = d.tables && d.tables.rus_stage_to_score ? d.tables : _emptyLt();
        t.rus_stage_to_score = t.rus_stage_to_score || { boys: {}, girls: {} };
        t.carpal_stage_to_score = t.carpal_stage_to_score || { boys: {}, girls: {} };
        t.rus_score_to_age = t.rus_score_to_age || { twii: { boys: [], girls: [] }, twiii: { boys: [], girls: [] } };
        t.carpal_score_to_age = t.carpal_score_to_age || { twii: { boys: [], girls: [] }, twiii: { boys: [], girls: [] } };
        t.tw20_stage_to_score = t.tw20_stage_to_score || { boys: {}, girls: {} };
        t.tw20_score_to_age = t.tw20_score_to_age || { boys: [], girls: [] };
        t.reference_cases = (t.reference_cases || []).filter((c) => c && !c._fill && !String(c.id || "").startsWith("example"));
        setLtTables(t);
        setLtStatus(d.status);
      } catch (e) {
        setLtMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLtBusy(false);
      }
    };
    const setLtPoint = (group, sex, bone, letter, val) => {
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        t[group][sex] = t[group][sex] || {};
        t[group][sex][bone] = t[group][sex][bone] || {};
        if (val === "" || val === null) delete t[group][sex][bone][letter];
        else t[group][sex][bone][letter] = Number(val);
        return t;
      });
    };
    const curveToText = (arr) => (arr || []).map((p) => p.join(", ")).join("\n");
    const parseCurve = (text) => text.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => l.split(/[\s,]+/).map(Number)).filter((p) => p.length === 2 && p.every((n) => !isNaN(n)));
    const setLtCurve = (group, curve, sex, text) => {
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        t[group][curve] = t[group][curve] || {};
        t[group][curve][sex] = parseCurve(text);
        return t;
      });
    };
    const setLtSexCurve = (group, sex, text) => {
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        t[group] = t[group] || {};
        t[group][sex] = parseCurve(text);
        return t;
      });
    };
    const useGridAsReference = () => {
      if (!sexEntered) {
        setLtMsg({ type: "err", text: "Set biological sex before capturing a reference case." });
        return;
      }
      const rus = { ...rusStages };
      const carp = {};
      Object.entries(carpalStages).forEach(([n, g]) => carp[carpalCode(n)] = g);
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        t.reference_cases = [{
          id: "clinic-ref-1",
          sex: sexEntered,
          rus_stages: rus,
          carpal_stages: carp,
          expected: t.reference_cases[0] && t.reference_cases[0].expected || { rus_score: null, twiii_rus_age_years: null },
          tolerance_years: 0.3
        }];
        return t;
      });
      setLtMsg({ type: "ok", text: "Reference stages captured from the grading grid. Now enter the reported score/age below." });
    };
    const setRefExpected = (field, val) => {
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        if (!t.reference_cases[0]) t.reference_cases[0] = { id: "clinic-ref-1", sex: "girls", rus_stages: {}, carpal_stages: {}, expected: {}, tolerance_years: 0.3 };
        t.reference_cases[0].expected = t.reference_cases[0].expected || {};
        t.reference_cases[0].expected[field] = val === "" ? null : Number(val);
        return t;
      });
    };
    const saveLetterTables = async () => {
      setLtBusy(true);
      setLtMsg(null);
      try {
        const r = await fetch("/api/bone-age/letters-tables", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tables: ltTables })
        });
        const d = await r.json();
        if (!r.ok) {
          setLtMsg({ type: "err", text: d.detail || "save failed" });
        } else {
          setLtStatus(d.status);
          if (d.status.scoring_ready) setLtMsg({ type: "ok", text: "Saved \u2014 TW3 scoring is ON (accuracy gate passed). The report now fills with real numbers." });
          else if (!d.status.reference_validation.all_passed && d.status.reference_validation.n_cases > 0)
            setLtMsg({ type: "err", text: "Saved, but scoring stays OFF: the reference case is not reproduced by these values \u2014 recheck the points/curve or the reported numbers." });
          else if (d.status.provenance_complete === false)
            setLtMsg({ type: "err", text: "Saved, but scoring stays OFF: document the licensed source in the Provenance tab (book, edition, owner, who entered/verified, date)." });
          else setLtMsg({ type: "err", text: "Saved, but scoring stays OFF: fill every bone\u2019s points, the score\u2192age curves, and a reference case." });
        }
      } catch (e) {
        setLtMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLtBusy(false);
      }
    };
    const setImageDomain = async (domain) => {
      if (!assessment) return;
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/image-domain`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ domain })
        });
        const d = await res.json();
        if (!res.ok) {
          setLcMsg({ type: "err", text: d.detail || "could not set domain" });
        } else {
          setRadiograph((r) => ({ ...r || {}, source_domain: d.source_domain }));
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      }
    };
    const analysisUrl = radiograph ? `/api/bone-age/radiographs/${radiograph.radiograph_id}/analysis` : null;
    const localizeBones = async () => {
      if (!assessment) {
        setLocMsg({ type: "err", text: "Save the annotation and attach a film first." });
        return;
      }
      setLocBusy(true);
      setLocMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/localize`, { method: "POST" });
        const d = await res.json();
        if (!res.ok) {
          setLocMsg({ type: "err", text: d.detail || "localize failed" });
          return;
        }
        if (d.image_width) setLocImg({ width: d.image_width, height: d.image_height });
        if (!d.available) {
          setLocMsg({ type: "err", text: d.message || "No localizer model installed." });
          return;
        }
        const nb = { ...boxes };
        (d.boxes || []).forEach((b) => {
          nb[b.bone_code] = b.box;
        });
        setBoxes(nb);
        setLocMsg({ type: "ok", text: `Auto-located ${(d.boxes || []).length} bones \u2014 drag to correct, then Save boxes.` });
      } catch (e) {
        setLocMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLocBusy(false);
      }
    };
    const addOrSelectBox = (bone) => {
      setSelBone(bone);
      setBoxes((prev) => {
        if (prev[bone] || !locImg) return prev;
        const s2 = Math.min(locImg.width, locImg.height) * 0.16;
        const cx = locImg.width / 2, cy = locImg.height / 2;
        return { ...prev, [bone]: [cx - s2 / 2, cy - s2 / 2, cx + s2 / 2, cy + s2 / 2] };
      });
    };
    const clearBox = (bone) => setBoxes((prev) => {
      const n = { ...prev };
      delete n[bone];
      return n;
    });
    const saveBoxes = async () => {
      if (!assessment) return;
      setLocBusy(true);
      setLocMsg(null);
      try {
        let a = assessment;
        const cur = boxesRef.current;
        const codes = new Set(Object.keys(cur));
        for (const [bone, box] of Object.entries(cur)) {
          const r = await fetch(`${LC_API}/${assessment.id}/bones/${bone}/box`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ box: box.map((v) => Math.round(v * 10) / 10) })
          });
          if (r.ok) a = await r.json();
          else throw new Error((await r.json()).detail || `save ${bone}`);
        }
        (a.bones || []).forEach(async (b) => {
          if (b.localisation_box && !codes.has(b.bone_code)) {
            await fetch(`${LC_API}/${assessment.id}/bones/${b.bone_code}/box`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ box: null })
            });
          }
        });
        setAssessment(a);
        setLocMsg({ type: "ok", text: `Saved ${codes.size} bone box${codes.size === 1 ? "" : "es"}.` });
      } catch (e) {
        setLocMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLocBusy(false);
      }
    };
    const startBoxDrag = (bone, mode, e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!locRef.current || !locImg) return;
      const rect = locRef.current.getBoundingClientRect();
      const scale = rect.width / locImg.width;
      locDrag.current = {
        bone,
        mode,
        mx: (e.clientX - rect.left) / scale,
        my: (e.clientY - rect.top) / scale,
        orig: [...boxesRef.current[bone] || [0, 0, 0, 0]]
      };
      setSelBone(bone);
    };
    const onLocMove = (e) => {
      const d = locDrag.current;
      if (!d || !locRef.current || !locImg) return;
      const rect = locRef.current.getBoundingClientRect();
      const scale = rect.width / locImg.width;
      const mx = (e.clientX - rect.left) / scale, my = (e.clientY - rect.top) / scale;
      const W = locImg.width, H = locImg.height, clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
      setBoxes((prev) => {
        let [x0, y0, x1, y1] = d.orig;
        if (d.mode === "move") {
          let dx = mx - d.mx, dy = my - d.my;
          dx = clamp(dx, -x0, W - x1);
          dy = clamp(dy, -y0, H - y1);
          return { ...prev, [d.bone]: [x0 + dx, y0 + dy, x1 + dx, y1 + dy] };
        }
        return { ...prev, [d.bone]: [x0, y0, clamp(mx, x0 + 8, W), clamp(my, y0 + 8, H)] };
      });
    };
    const endLocDrag = () => {
      locDrag.current = null;
    };
    const lcBtn = (bg, disabled) => ({
      padding: "7px 12px",
      background: disabled ? "#cbd5e1" : bg,
      color: "white",
      border: "none",
      borderRadius: "8px",
      fontSize: "11px",
      fontWeight: "700",
      cursor: disabled ? "not-allowed" : "pointer"
    });
    return {
      LC_API,
      lcLocked,
      unsavedStaging,
      saveDraft,
      bonesIntoGrids,
      calculateAssessment,
      approveAssessment,
      reviseAssessment,
      toggleAudit,
      submitFeedback,
      runEstimate,
      toggleDeclaredFlag,
      attachImage,
      loadCoverage,
      loadMonitoring,
      loadLocalCohort,
      loadAdjudication,
      resolveAdjudication,
      loadLetterTables,
      setLtPoint,
      curveToText,
      setLtCurve,
      setLtSexCurve,
      useGridAsReference,
      setRefExpected,
      saveLetterTables,
      setImageDomain,
      analysisUrl,
      localizeBones,
      addOrSelectBox,
      clearBox,
      saveBoxes,
      startBoxDrag,
      onLocMove,
      endLocDrag,
      lcBtn
    };
  }

  // frontend/src/boneAgeState.js
  var { useState: useState2, useRef, useEffect: useEffect2 } = React;
  var DECLARABLE_FLAGS = [
    ["FRACTURE", "Fracture"],
    ["CAST_OR_HARDWARE", "Cast / hardware"],
    ["WRONG_LATERALITY", "Wrong side"],
    ["CLIPPED_DIGITS", "Clipped anatomy"],
    ["SEVERE_DEFORMITY", "Deformity"],
    ["FOREIGN_OBJECT", "Foreign object"]
  ];
  function useBoneAgeState() {
    const [boneAge, setBoneAge] = useState2("");
    const [boneAgeSource, setBoneAgeSource] = useState2("manual");
    const [rusStages, setRusStages] = useState2({});
    const [carpalStages, setCarpalStages] = useState2({});
    const [tw3Config, setTw3Config] = useState2(null);
    const [letterResult, setLetterResult] = useState2(null);
    const [boneReport, setBoneReport] = useState2(null);
    const [patientCode, setPatientCode] = useState2("");
    const [assessment, setAssessment] = useState2(null);
    const [lcMsg, setLcMsg] = useState2(null);
    const [lcBusy, setLcBusy] = useState2(false);
    const [showAudit, setShowAudit] = useState2(false);
    const [radiograph, setRadiograph] = useState2(null);
    const [coverage, setCoverage] = useState2(null);
    const [covBusy, setCovBusy] = useState2(false);
    const [monitoring, setMonitoring] = useState2(null);
    const [monBusy, setMonBusy] = useState2(false);
    const [localCohort, setLocalCohort] = useState2(null);
    const [lcohBusy, setLcohBusy] = useState2(false);
    const [adjItems, setAdjItems] = useState2(null);
    const [adjBusy, setAdjBusy] = useState2(false);
    const [adjReviewer, setAdjReviewer] = useState2("");
    const [adjMsg, setAdjMsg] = useState2(null);
    const [ltTables, setLtTables] = useState2(null);
    const [ltStatus, setLtStatus] = useState2(null);
    const [ltSection, setLtSection] = useState2("rus");
    const [ltSex, setLtSex] = useState2("boys");
    const [ltMsg, setLtMsg] = useState2(null);
    const [ltBusy, setLtBusy] = useState2(false);
    const [boxes, setBoxes] = useState2({});
    const [locImg, setLocImg] = useState2(null);
    const [locBusy, setLocBusy] = useState2(false);
    const [locMsg, setLocMsg] = useState2(null);
    const [selBone, setSelBone] = useState2(null);
    const locDrag = useRef(null);
    const locRef = useRef(null);
    const boxesRef = useRef({});
    useEffect2(() => {
      boxesRef.current = boxes;
    }, [boxes]);
    const [aiEstimate, setAiEstimate] = useState2(null);
    const [estimateDomain, setEstimateDomain] = useState2("unknown");
    const [declaredFlags, setDeclaredFlags] = useState2([]);
    const [lastFilm, setLastFilm] = useState2(null);
    const [fbAge, setFbAge] = useState2("");
    const [fbMethod, setFbMethod] = useState2("tw3-rus");
    const [fbConfidence, setFbConfidence] = useState2("medium");
    const [fbRater, setFbRater] = useState2("");
    const [fbNote, setFbNote] = useState2("");
    const [fbMsg, setFbMsg] = useState2(null);
    const [fbBusy, setFbBusy] = useState2(false);
    const [aiBusy, setAiBusy] = useState2(false);
    const [fatherHeight, setFatherHeight] = useState2("");
    const [motherHeight, setMotherHeight] = useState2("");
    return {
      DECLARABLE_FLAGS,
      boneAge,
      setBoneAge,
      boneAgeSource,
      setBoneAgeSource,
      rusStages,
      setRusStages,
      carpalStages,
      setCarpalStages,
      tw3Config,
      setTw3Config,
      letterResult,
      setLetterResult,
      boneReport,
      setBoneReport,
      patientCode,
      setPatientCode,
      assessment,
      setAssessment,
      lcMsg,
      setLcMsg,
      lcBusy,
      setLcBusy,
      showAudit,
      setShowAudit,
      radiograph,
      setRadiograph,
      coverage,
      setCoverage,
      covBusy,
      setCovBusy,
      monitoring,
      setMonitoring,
      monBusy,
      setMonBusy,
      localCohort,
      setLocalCohort,
      lcohBusy,
      setLcohBusy,
      adjItems,
      setAdjItems,
      adjBusy,
      setAdjBusy,
      adjReviewer,
      setAdjReviewer,
      adjMsg,
      setAdjMsg,
      ltTables,
      setLtTables,
      ltStatus,
      setLtStatus,
      ltSection,
      setLtSection,
      ltSex,
      setLtSex,
      ltMsg,
      setLtMsg,
      ltBusy,
      setLtBusy,
      boxes,
      setBoxes,
      locImg,
      setLocImg,
      locBusy,
      setLocBusy,
      locMsg,
      setLocMsg,
      selBone,
      setSelBone,
      locDrag,
      locRef,
      boxesRef,
      aiEstimate,
      setAiEstimate,
      estimateDomain,
      setEstimateDomain,
      declaredFlags,
      setDeclaredFlags,
      lastFilm,
      setLastFilm,
      fbAge,
      setFbAge,
      fbMethod,
      setFbMethod,
      fbConfidence,
      setFbConfidence,
      fbRater,
      setFbRater,
      fbNote,
      setFbNote,
      fbMsg,
      setFbMsg,
      fbBusy,
      setFbBusy,
      aiBusy,
      setAiBusy,
      fatherHeight,
      setFatherHeight,
      motherHeight,
      setMotherHeight
    };
  }

  // frontend/src/shell.jsx
  function AppHeader() {
    const { resetAll } = useShell();
    return /* @__PURE__ */ React.createElement("header", { style: { background: "white", borderBottom: "1px solid #e8ecf0", position: "sticky", top: 0, zIndex: 50, boxShadow: "0 1px 4px rgba(0,0,0,0.05)" } }, /* @__PURE__ */ React.createElement("div", { className: "app-header-inner" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "36px", height: "36px", borderRadius: "10px", background: "linear-gradient(135deg,#4f46e5,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "white", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M22 12h-4l-3 9L9 3l-3 9H2" }))), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "app-title", style: { fontSize: "15px", fontWeight: "900", color: "#0f172a", lineHeight: 1.2 } }, "Pediatric Clinical Workspace"), /* @__PURE__ */ React.createElement("div", { className: "app-subtitle", style: { fontSize: "10px", fontWeight: "700", color: "#94a3b8", letterSpacing: "0.06em", textTransform: "uppercase" } }, "Growth \xB7 TW3 Bone Age \xB7 QRISK3 \xB7 Renal \xB7 FRAX \xB7 FIB-4"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: resetAll,
        className: "reset-button",
        style: { display: "flex", alignItems: "center", gap: "7px", padding: "8px 18px", background: "white", border: "1.5px solid #fca5a5", borderRadius: "9px", fontSize: "13px", fontWeight: "700", color: "#dc2626", cursor: "pointer", whiteSpace: "nowrap", transition: "all 0.15s", boxShadow: "0 1px 3px rgba(220,38,38,0.08)" },
        onMouseEnter: (e) => {
          e.currentTarget.style.background = "#fff1f2";
          e.currentTarget.style.borderColor = "#f87171";
        },
        onMouseLeave: (e) => {
          e.currentTarget.style.background = "white";
          e.currentTarget.style.borderColor = "#fca5a5";
        }
      },
      /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "1 4 1 10 7 10" }), /* @__PURE__ */ React.createElement("path", { d: "M3.51 15a9 9 0 1 0 .49-3.77" })),
      "Reset Patient"
    ))));
  }
  function PatientIdentityBar() {
    const {
      patientName,
      setPatientName,
      patientMrn,
      setPatientMrn,
      examDate,
      setExamDate,
      age,
      gender,
      exportFullReport
    } = useShell();
    return /* @__PURE__ */ React.createElement("div", { className: "patient-bar no-print" }, /* @__PURE__ */ React.createElement("div", { className: "patient-bar-inner" }, /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "2 1 200px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-name" }, "Patient name"), /* @__PURE__ */ React.createElement("input", { id: "pt-name", type: "text", value: patientName, onChange: (e) => setPatientName(e.target.value), placeholder: "Full name" })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 130px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-mrn" }, "MRN / ID"), /* @__PURE__ */ React.createElement("input", { id: "pt-mrn", type: "text", value: patientMrn, onChange: (e) => setPatientMrn(e.target.value), placeholder: "e.g. 004821" })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 140px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-date" }, "Exam date"), /* @__PURE__ */ React.createElement("input", { id: "pt-date", type: "date", value: examDate, onChange: (e) => setExamDate(e.target.value) })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 120px" } }, /* @__PURE__ */ React.createElement("label", null, "Age / Sex"), /* @__PURE__ */ React.createElement("div", { className: "patient-reflect" }, age !== "" ? `${age} yr` : "\u2014 yr", " \xB7 ", gender === "boys" ? "Male" : gender === "girls" ? "Female" : "\u2014")), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: exportFullReport,
        title: "Print a combined summary of every module",
        style: { marginLeft: "auto", alignSelf: "center", display: "flex", alignItems: "center", gap: "7px", padding: "8px 16px", background: "#4f46e5", color: "white", border: "none", borderRadius: "9px", fontSize: "13px", fontWeight: "700", cursor: "pointer", whiteSpace: "nowrap" }
      },
      /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "6 9 6 2 18 2 18 9" }), /* @__PURE__ */ React.createElement("path", { d: "M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" }), /* @__PURE__ */ React.createElement("rect", { x: "6", y: "14", width: "12", height: "8" })),
      "Export report"
    )));
  }
  function TabBar() {
    const { TABS, activeTab, setActiveTab, moduleStatus, timeline } = useShell();
    return /* @__PURE__ */ React.createElement("div", { className: "card tab-card", style: { padding: "6px" } }, /* @__PURE__ */ React.createElement("div", { className: "tab-scroll custom-scrollbar" }, TABS.map((tab) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: tab.id,
        onClick: () => setActiveTab(tab.id),
        className: `${activeTab === tab.id ? "tab-active" : "tab-inactive"} tab-button`
      },
      tab.label,
      moduleStatus[tab.id] && /* @__PURE__ */ React.createElement(
        "span",
        {
          className: `status-dot status-dot-${moduleStatus[tab.id].state}`,
          title: moduleStatus[tab.id].label
        }
      ),
      tab.id === "timeline" && timeline.length > 0 && /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "6px", background: "#4f46e5", color: "white", fontSize: "9px", fontWeight: "800", padding: "1px 6px", borderRadius: "99px" } }, timeline.length)
    ))));
  }

  // frontend/src/panels/InputColumn.jsx
  function InputColumn() {
    const {
      age,
      handleAgeChange,
      dob,
      handleDobChange,
      ageParts,
      gender,
      setGender,
      height,
      setHeight,
      weight,
      setWeight,
      labsRelevant,
      creatinine,
      setCreatinine,
      albuminuria,
      setAlbuminuria,
      systolic,
      setSystolic,
      diastolic,
      setDiastolic,
      ast,
      setAst,
      alt,
      setAlt,
      platelets,
      setPlatelets
    } = useInputs();
    const bpOrderProblem = systolic !== "" && diastolic !== "" && diastolic >= systolic ? "Diastolic must be lower than systolic" : null;
    return /* @__PURE__ */ React.createElement("div", { className: "input-column" }, /* @__PURE__ */ React.createElement("div", { className: "card", style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#4f46e5", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "Demographics"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontSize: "9px", fontWeight: "700", color: "#cbd5e1", textTransform: "uppercase", letterSpacing: "0.05em" } }, "Required")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "14px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Chronological Age",
        value: age,
        onChange: handleAgeChange,
        placeholder: "e.g. 9.5",
        step: "0.1",
        unit: "yrs",
        unitPosition: "right",
        accent: "#4f46e5",
        problem: rangeProblem("age", age)
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Date of Birth"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "date",
        value: dob,
        onChange: handleDobChange,
        max: (/* @__PURE__ */ new Date()).toISOString().split("T")[0],
        className: "input-field",
        style: { width: "100%", color: dob ? "#1e293b" : "#94a3b8" }
      }
    ))), ageParts ? /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", color: "#4338ca", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "8px", padding: "7px 10px", lineHeight: "1.5" } }, "Age ", /* @__PURE__ */ React.createElement("strong", null, ageParts.years, " yr ", ageParts.months, " mo ", ageParts.days, " d"), /* @__PURE__ */ React.createElement("span", { style: { color: "#818cf8" } }, " \xB7 used as ", ageParts.decimal.toFixed(1), " yr in calculations")) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.4" } }, "Enter an age directly, or a date of birth to compute it automatically.")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Biological Sex"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px" } }, /* @__PURE__ */ React.createElement("button", { className: `gender-btn ${gender === "boys" ? "gender-active" : "gender-inactive"}`, onClick: () => setGender("boys") }, "\u2642 Male"), /* @__PURE__ */ React.createElement("button", { className: `gender-btn ${gender === "girls" ? "gender-active" : "gender-inactive"}`, onClick: () => setGender("girls") }, "\u2640 Female"))), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Height", value: height, onChange: (e) => setHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm", unit: "cm", problem: rangeProblem("height", height) }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Weight", value: weight, onChange: (e) => setWeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "kg", unit: "kg", problem: rangeProblem("weight", weight) })))), /* @__PURE__ */ React.createElement("div", { className: `card${labsRelevant ? "" : " section-dim"}`, style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#0891b2", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "Clinical Labs & Parameters")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "14px" } }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Serum Creatinine",
        value: creatinine,
        onChange: (e) => setCreatinine(e.target.value === "" ? "" : parseFloat(e.target.value)),
        placeholder: "mg/dL",
        step: "0.01",
        unit: "mg/dL",
        accent: "#0891b2",
        problem: rangeProblem("creatinine", creatinine)
      }
    ), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Albuminuria / ACR Stage"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px" } }, [["A1", "< 30 mg/g"], ["A2", "30\u2013300 mg/g"], ["A3", "> 300 mg/g"]].map(([lv, desc]) => /* @__PURE__ */ React.createElement("button", { key: lv, className: `alb-btn ${albuminuria === lv ? "alb-active" : "alb-inactive"}`, onClick: () => setAlbuminuria(lv) }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: albuminuria === lv ? "#4338ca" : "#334155" } }, lv), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", color: "#94a3b8", marginTop: "2px" } }, desc))))), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Systolic BP", value: systolic, onChange: (e) => setSystolic(e.target.value === "" ? "" : parseInt(e.target.value)), placeholder: "mmHg", unit: "mmHg", problem: rangeProblem("systolic", systolic) }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Diastolic BP", value: diastolic, onChange: (e) => setDiastolic(e.target.value === "" ? "" : parseInt(e.target.value)), placeholder: "mmHg", unit: "mmHg", problem: rangeProblem("diastolic", diastolic) || bpOrderProblem })), /* @__PURE__ */ React.createElement("div", { style: { paddingTop: "12px", borderTop: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("label", { className: "field-label", style: { marginBottom: "10px" } }, "Hepatic Enzymes & Platelets"), /* @__PURE__ */ React.createElement("div", { className: "liver-grid" }, [
      ["AST", "SGOT \xB7 U/L", ast, (e) => setAst(e.target.value === "" ? "" : parseFloat(e.target.value)), "ast"],
      ["ALT", "SGPT \xB7 U/L", alt, (e) => setAlt(e.target.value === "" ? "" : parseFloat(e.target.value)), "alt"],
      ["PLT", "\xD710\xB3 / \xB5L", platelets, (e) => setPlatelets(e.target.value === "" ? "" : parseFloat(e.target.value)), "platelets"]
    ].map(([lbl, sub, val, fn, field]) => /* @__PURE__ */ React.createElement("div", { key: lbl, style: { display: "flex", flexDirection: "column", alignItems: "stretch" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "800", color: "#334155", textAlign: "center", display: "block", marginBottom: "2px" } }, lbl), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "9px", fontWeight: "600", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", textAlign: "center", display: "block", marginBottom: "6px" } }, sub), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        placeholder: "\u2014",
        value: val,
        onChange: fn,
        className: "input-field",
        "aria-invalid": rangeProblem(field, val) ? true : void 0,
        style: {
          textAlign: "center",
          padding: "9px 8px",
          width: "100%",
          boxSizing: "border-box",
          ...rangeProblem(field, val) ? { borderColor: "#f87171", background: "#fff7f7" } : {}
        }
      }
    ), rangeProblem(field, val) && /* @__PURE__ */ React.createElement("div", { role: "alert", style: { fontSize: "10px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.3", textAlign: "center" } }, rangeProblem(field, val)))))))));
  }

  // frontend/src/qriskState.js
  var { useState: useState3 } = React;
  function useQriskInputs() {
    const [ethnicity, setEthnicity] = useState3(2);
    const [smokeCat, setSmokeCat] = useState3(0);
    const [diabetes, setDiabetes] = useState3(0);
    const [cholRatio, setCholRatio] = useState3("");
    const [sbpSD, setSbpSD] = useState3("");
    const [qAF, setQAF] = useState3("no");
    const [qTreatedHtn, setQTreatedHtn] = useState3("no");
    const [qRA, setQRA] = useState3("no");
    const [qCKD, setQCKD] = useState3("no");
    const [qMigraine, setQMigraine] = useState3("no");
    const [qSLE, setQSLE] = useState3("no");
    const [qSMI, setQSMI] = useState3("no");
    const [qAtypAntipsy, setQAtypAntipsy] = useState3("no");
    const [qCortico, setQCortico] = useState3("no");
    const [qED, setQED] = useState3("no");
    const [qFhCvd, setQFhCvd] = useState3("no");
    return {
      ethnicity,
      setEthnicity,
      smokeCat,
      setSmokeCat,
      diabetes,
      setDiabetes,
      cholRatio,
      setCholRatio,
      sbpSD,
      setSbpSD,
      qAF,
      setQAF,
      qTreatedHtn,
      setQTreatedHtn,
      qRA,
      setQRA,
      qCKD,
      setQCKD,
      qMigraine,
      setQMigraine,
      qSLE,
      setQSLE,
      qSMI,
      setQSMI,
      qAtypAntipsy,
      setQAtypAntipsy,
      qCortico,
      setQCortico,
      qED,
      setQED,
      qFhCvd,
      setQFhCvd
    };
  }

  // frontend/src/panels/RenalPanel.jsx
  var G_CODES = [
    ["G1", "\u2265 90", "Normal/high"],
    ["G2", "60\u201389", "Mild \u2193"],
    ["G3a", "45\u201359", "Mild\u2013mod \u2193"],
    ["G3b", "30\u201344", "Mod\u2013severe \u2193"],
    ["G4", "15\u201329", "Severe \u2193"],
    ["G5", "< 15", "Failure"]
  ];
  var A_CODES = ["A1", "A2", "A3"];
  var HEAT = {
    G1: ["low", "moderate", "high"],
    G2: ["low", "moderate", "high"],
    G3a: ["moderate", "high", "very_high"],
    G3b: ["high", "very_high", "very_high"],
    G4: ["very_high", "very_high", "very_high"],
    G5: ["very_high", "very_high", "very_high"]
  };
  var HEAT_BG = { low: "#dcfce7", moderate: "#fef9c3", high: "#fed7aa", very_high: "#fecaca" };
  function RenalPanel() {
    const { metrics, hasManual } = useRenal();
    const m = metrics;
    const r = m.ready ? m.result : null;
    const g = r && r.gfr_category ? r.gfr_category.code : null;
    const a = r && r.albuminuria_category ? r.albuminuria_category.code : null;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Renal Workspace \xB7 eGFR & KDIGO",
        subtitle: r ? `${r.primary.equation} \xB7 ${r.paediatric ? "paediatric" : "adult"} equation` : "Age-appropriate creatinine equation, KDIGO G \xD7 A staging",
        badge: r && g ? `${g}${a || ""}` : null,
        badgeVariant: r ? m.stageVariant : "info"
      }
    ), !hasManual ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter age, sex, height & serum creatinine",
        hint: "All four are required (height for the paediatric equation). Add the urine albumin-to-creatinine stage for a KDIGO risk category."
      }
    ) : !m.ready ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: m.reason ? "Not calculated" : m.error ? "Calculation failed" : "Calculating\u2026",
        hint: m.reason || m.error || ""
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { ...heroTone(m.stageVariant), borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b", marginBottom: "8px" } }, "Estimated GFR"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: m.stageVariant === "high" ? "#b91c1c" : m.stageVariant === "mid" ? "#b45309" : "#1e293b", lineHeight: 1 } }, r.primary.value.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#6366f1", fontWeight: "600" } }, r.primary.unit)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#818cf8", marginTop: "4px" } }, r.primary.equation, " \xB7 ", r.primary.citation)), /* @__PURE__ */ React.createElement("div", { style: { textAlign: "right", maxWidth: "260px" } }, g && /* @__PURE__ */ React.createElement(StatusBadge, { text: `${g} \xB7 ${r.gfr_category.label}`, variant: m.stageVariant === "info" ? "neutral" : m.stageVariant }), r.kdigo_risk && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: r.kdigo_risk.label, variant: m.stageVariant })))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#334155", lineHeight: "1.6" } }, r.interpretation), g && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" } }, "KDIGO GFR category"), /* @__PURE__ */ React.createElement("div", { className: "ckd-stage" }, G_CODES.map(([code, range, desc]) => /* @__PURE__ */ React.createElement("div", { key: code, className: `ckd-chip ${g === code ? `ckd-active-${code.toLowerCase()}` : "ckd-inactive"}` }, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", fontSize: "11px" } }, code), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", marginTop: "2px", fontWeight: "600", opacity: 0.85 } }, range), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", marginTop: "1px", opacity: 0.7 } }, desc))))), g && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", overflowX: "auto" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" } }, "KDIGO prognosis (G \xD7 albuminuria)", !a && " \u2014 record ACR stage to place the patient"), /* @__PURE__ */ React.createElement("table", { style: { borderCollapse: "separate", borderSpacing: "3px", fontSize: "10px", width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null), A_CODES.map((x) => /* @__PURE__ */ React.createElement("th", { key: x, style: { color: "#64748b", fontWeight: 800 } }, x)))), /* @__PURE__ */ React.createElement("tbody", null, G_CODES.map(([code]) => /* @__PURE__ */ React.createElement("tr", { key: code }, /* @__PURE__ */ React.createElement("td", { style: { fontWeight: 800, color: "#64748b", paddingRight: "6px" } }, code), A_CODES.map((ac, i) => {
      const here = code === g && ac === a;
      return /* @__PURE__ */ React.createElement(
        "td",
        {
          key: ac,
          "aria-label": here ? "this patient" : void 0,
          style: {
            background: HEAT_BG[HEAT[code][i]],
            textAlign: "center",
            padding: "5px 2px",
            borderRadius: "4px",
            outline: here ? "3px solid #1e293b" : code === g && !a ? "1px dashed #64748b" : "none",
            fontWeight: here ? 900 : 500
          }
        },
        here ? "\u25CF" : ""
      );
    }))))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", color: "#94a3b8", marginTop: "4px" } }, "Green low \xB7 yellow moderately increased \xB7 orange high \xB7 red very high risk")), r.alternatives.length > 0 && /* @__PURE__ */ React.createElement("div", { className: "secondary-grid", style: { marginTop: "16px" } }, r.alternatives.map((alt) => /* @__PURE__ */ React.createElement("div", { key: alt.equation, style: { background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" } }, alt.equation), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "22px", fontWeight: "900", color: "#334155" } }, alt.value.toFixed(1)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, alt.unit)))), /* @__PURE__ */ React.createElement("ul", { style: { marginTop: "14px", paddingLeft: "18px", fontSize: "11px", color: "#64748b", lineHeight: "1.6" } }, r.caveats.map((c) => /* @__PURE__ */ React.createElement("li", { key: c }, c)))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "Bedside Schwartz under 18 \xB7 CKD-EPI 2021 (race-free) from 18 \xB7 CKiD U25 shown to 25 y \xB7 none under 1 y \xB7 KDIGO G categories from 2 y. CKD requires a marker persisting > 3 months."));
  }

  // frontend/src/panels/LiverPanel.jsx
  function LiverPanel() {
    const { metrics, hasManual } = useLiver();
    const m = metrics;
    const r = m.ready ? m.result : null;
    const scaleMax = 5;
    const pos = (v) => Math.min(Math.max(v / scaleMax * 100, 1), 99);
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Liver Fibrosis \xB7 FIB-4 Index",
        subtitle: "Non-invasive fibrosis risk \u2014 Age \xB7 AST \xB7 ALT \xB7 Platelets",
        badge: r ? m.interpretation : null,
        badgeVariant: r ? m.variant === "info" ? "neutral" : m.variant : "info"
      }
    ), !hasManual ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter age, AST, ALT & platelets",
        hint: "FIB-4 needs all four. No score is shown until they are entered."
      }
    ) : !m.ready ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: m.reason ? "Not calculated" : m.error ? "Calculation failed" : "Calculating\u2026",
        hint: m.reason || m.error || ""
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { ...heroTone(m.variant), borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b", marginBottom: "8px" } }, "FIB-4 Score"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: m.variant === "high" ? "#b91c1c" : m.variant === "mid" ? "#b45309" : m.variant === "low" ? "#15803d" : "#334155", lineHeight: 1 } }, r.fib4.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#64748b", fontWeight: "600" } }, "index")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, "(Age \xD7 AST) / (Platelets \xD7 \u221AALT) \xB7 ", r.citation)), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(StatusBadge, { text: r.category_label, variant: m.variant === "info" ? "neutral" : m.variant }))), r.category && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "20px", background: "#f8fafc", borderRadius: "12px", padding: "16px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "12px" } }, "Risk Scale"), /* @__PURE__ */ React.createElement("div", { style: {
      position: "relative",
      height: "10px",
      borderRadius: "99px",
      background: `linear-gradient(to right, #22c55e 0%, #22c55e ${pos(r.cutoffs.low_below)}%, #eab308 ${pos(r.cutoffs.low_below)}%, #eab308 ${pos(r.cutoffs.high_at_or_above)}%, #ef4444 ${pos(r.cutoffs.high_at_or_above)}%, #ef4444 100%)`
    } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: "-4px", left: `${pos(r.fib4)}%`, width: "18px", height: "18px", borderRadius: "50%", background: "white", border: "3px solid #334155", transform: "translateX(-50%)", boxShadow: "0 1px 4px rgba(0,0,0,0.2)" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", fontWeight: "700", color: "#94a3b8", flexWrap: "wrap", gap: "4px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "#16a34a" } }, "Low < ", r.cutoffs.low_below.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { color: "#d97706" } }, "Indeterminate ", r.cutoffs.low_below.toFixed(2), "\u2013", r.cutoffs.high_at_or_above.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { color: "#dc2626" } }, "High \u2265 ", r.cutoffs.high_at_or_above.toFixed(2)))), /* @__PURE__ */ React.createElement("ul", { style: { marginTop: "14px", paddingLeft: "18px", fontSize: "11px", color: "#92400e", lineHeight: "1.6" } }, r.caveats.map((c) => /* @__PURE__ */ React.createElement("li", { key: c }, c)))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "Cut-offs: low < 1.30 (< 2.0 from age 65), high \u2265 2.67 (AASLD 2023; McPherson 2017). No category under 18."));
  }

  // frontend/src/panels/FraxPanel.jsx
  var OFFICIAL_FRAX_URL = "https://frax.shef.ac.uk/FRAX/tool.aspx";
  function FraxPanel() {
    const {
      metrics,
      hasManual,
      fraxMofEntered,
      setFraxMofEntered,
      fraxHfEntered,
      setFraxHfEntered
    } = useFrax();
    const { age, evalAge } = usePatient();
    const fraxMetrics = metrics;
    const toNumberOrBlank = (e) => e.target.value === "" ? "" : parseFloat(e.target.value);
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "FRAX \xB7 10-Year Fracture Probability",
        subtitle: "Result from the official FRAX calculator (India model), entered by the clinician",
        badge: hasManual ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "Above US threshold" : "Below US threshold" : null,
        badgeVariant: hasManual ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "high" : "low" : "info"
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "14px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#3730a3", lineHeight: "1.7" } }, /* @__PURE__ */ React.createElement("strong", null, "This workspace does not calculate FRAX."), " Run the official calculator (University of Sheffield, ", /* @__PURE__ */ React.createElement("em", null, "Asia \u2192 India"), " model) at", " ", /* @__PURE__ */ React.createElement("a", { href: OFFICIAL_FRAX_URL, target: "_blank", rel: "noopener noreferrer", style: { color: "#4338ca", fontWeight: 700 } }, "frax.shef.ac.uk"), ", then enter the two probabilities it reports below."), age !== "" && (evalAge < 40 || evalAge > 90) && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#92400e", lineHeight: "1.6" } }, "\u26A0 FRAX is defined for ages 40\u201390. This patient is ", evalAge, " years; the official tool will not give a valid probability outside that range."), /* @__PURE__ */ React.createElement("div", { className: "form-grid", style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Major osteoporotic fracture",
        value: fraxMofEntered,
        onChange: (e) => setFraxMofEntered(toNumberOrBlank(e)),
        placeholder: "from FRAX",
        step: "0.1",
        unit: "%",
        problem: rangeProblem("fraxPct", fraxMofEntered)
      }
    ), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Hip fracture",
        value: fraxHfEntered,
        onChange: (e) => setFraxHfEntered(toNumberOrBlank(e)),
        placeholder: "from FRAX",
        step: "0.1",
        unit: "%",
        problem: rangeProblem("fraxPct", fraxHfEntered)
      }
    )), hasManual && fraxMetrics.hfProb > fraxMetrics.mofProb && /* @__PURE__ */ React.createElement("div", { role: "alert", style: { marginTop: "12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#991b1b", lineHeight: "1.6" } }, "\u26A0 Hip-fracture probability is higher than major-osteoporotic-fracture probability. FRAX never reports this (hip is one of the major fracture sites) \u2014 check whether the two values were entered in the wrong boxes."), !hasManual ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter both FRAX probabilities",
        hint: "Nothing is shown until both values from the official calculator are entered."
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(fraxMetrics.isHighMof ? "high" : "low"), borderRadius: "16px", padding: "22px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "Major Osteoporotic Fracture"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: fraxMetrics.isHighMof ? "#dc2626" : "#16a34a", lineHeight: 1 } }, fraxMetrics.mofProb.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "10-yr probability \u2014 spine, hip, forearm, shoulder (as entered)")), /* @__PURE__ */ React.createElement(StatusBadge, { text: fraxMetrics.isHighMof ? "At/above 20%" : "Below 20%", variant: fraxMetrics.isHighMof ? "high" : "low" })), /* @__PURE__ */ React.createElement(ProbBar, { prob: fraxMetrics.mofProb, maxProb: 40, threshold: 20 })), /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(fraxMetrics.isHighHf ? "high" : "low"), borderRadius: "16px", padding: "22px", marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "Hip Fracture"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: fraxMetrics.isHighHf ? "#dc2626" : "#16a34a", lineHeight: 1 } }, fraxMetrics.hfProb.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "10-yr probability of hip fracture (as entered)")), /* @__PURE__ */ React.createElement(StatusBadge, { text: fraxMetrics.isHighHf ? "At/above 3%" : "Below 3%", variant: fraxMetrics.isHighHf ? "high" : "low" })), /* @__PURE__ */ React.createElement(ProbBar, { prob: fraxMetrics.hfProb, maxProb: 15, threshold: 3 }))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "Thresholds shown are the US NOF/BHOF intervention thresholds (MOF \u2265 20% or hip \u2265 3%), which BHOF applies to postmenopausal women and men aged \u2265 50 with low bone mass (osteopenia). India has no nationally validated FRAX intervention threshold, and UK NOGG uses age-dependent thresholds \u2014 treatment decisions rest with the clinician."));
  }

  // frontend/src/panels/OverviewPanel.jsx
  var { useState: useState4, useEffect: useEffect3 } = React;
  function ReferenceDataStatus() {
    const [data, setData] = useState4(null);
    const [error, setError] = useState4(null);
    useEffect3(() => {
      fetch("/api/reference-data").then((r) => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))).then(setData).catch((e) => setError(String(e.message || e)));
    }, []);
    if (error) return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", fontSize: "11px", color: "#b91c1c" } }, "Reference-data status unavailable: ", error);
    if (!data) return null;
    return /* @__PURE__ */ React.createElement("details", { className: "clinical-notes", style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("summary", null, "Reference data behind these numbers \xB7 ", data.active_count, " of ", data.total, " installed"), /* @__PURE__ */ React.createElement("div", { className: "clinical-notes-body" }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#64748b", marginBottom: "8px", lineHeight: 1.6 } }, data.note), data.items.map((i) => /* @__PURE__ */ React.createElement("div", { key: i.key, style: { padding: "8px 0", borderTop: "1px solid #eef2f7" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px", alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: `status-dot status-dot-${i.active ? "normal" : "borderline"}`, style: { marginLeft: 0 } }), /* @__PURE__ */ React.createElement("strong", { style: { fontSize: "12px", color: "#1e293b" } }, i.title), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10.5px", color: i.active ? "#15803d" : "#b45309", fontWeight: 700 } }, i.active ? "installed" : "missing")), !i.active && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", margin: "3px 0 0 16px", lineHeight: 1.55 } }, i.effect_while_missing, " ", /* @__PURE__ */ React.createElement("span", { style: { color: "#64748b" } }, "To obtain: ", i.obtain, " \u2014 see ", /* @__PURE__ */ React.createElement("code", null, i.how_to), "."))))));
  }
  function OverviewPanel() {
    const { moduleStatus, setActiveTab } = useOverview();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Patient Overview",
        subtitle: "Every module's headline at a glance \u2014 click any card to open its full workspace."
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "overview-grid", style: { marginTop: "16px" } }, ["growth", "boneage", "renal", "liver", "frax", "qrisk"].map((key) => {
      const m = moduleStatus[key];
      const accent = m.state === "high" ? "#dc2626" : m.state === "borderline" ? "#d97706" : m.state === "normal" ? "#16a34a" : "#94a3b8";
      return /* @__PURE__ */ React.createElement("button", { key, className: "overview-card", onClick: () => setActiveTab(key) }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" } }, m.title), /* @__PURE__ */ React.createElement("span", { className: `status-dot status-dot-${m.state}`, style: { marginLeft: 0 } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "6px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "30px", fontWeight: "900", color: accent, lineHeight: 1 } }, m.value), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "600", color: "#94a3b8" } }, m.unit)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#64748b", marginTop: "6px", lineHeight: "1.5" } }, m.label));
    })), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#4338ca", lineHeight: "1.7" } }, "Enter patient data in the left panel \u2014 every module recalculates automatically. A grey dot means that module still needs input; green / amber / red reflect the result. Decision support only \u2014 a clinician must verify every value."), /* @__PURE__ */ React.createElement(ReferenceDataStatus, null));
  }

  // frontend/src/panels/GrowthPanel.jsx
  function GrowthPanel() {
    const { age, evalAge, evalGender, evalHeight, evalWeight, examDate, exportGrowthReportPdf, gender, growthChartMeasure, growthMetrics, growthSeries, hasManualGrowth, height, moduleStatus, patientMrn, patientName, setGrowthChartMeasure, setShowChart, showChart, timeline, weight } = useGrowth();
    const gm = growthMetrics;
    const heightSeries = timeline.map((t) => ({ age: t.age, value: t.height })).filter((p) => p.value > 0);
    const weightSeries = timeline.map((t) => ({ age: t.age, value: t.weight })).filter((p) => p.value > 0);
    const bmiSeries = timeline.map((t) => ({ age: t.age, value: t.height > 0 ? t.weight / Math.pow(t.height / 100, 2) : 0 })).filter((p) => p.value > 0);
    const pctTxt = (p) => p === null || p === void 0 ? "\u2014" : p.toFixed(1) + "th";
    const zTxt = (z) => z === null || z === void 0 ? "\u2014" : (z >= 0 ? "+" : "") + z.toFixed(2);
    const inRange2 = evalAge >= 0 && evalAge <= 19;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ React.createElement("div", { className: "report-only", style: { fontSize: "13px", fontWeight: "700", color: "#334155", borderBottom: "1px solid #e5e7eb", paddingBottom: "8px" } }, patientName || "Unnamed patient", " \xB7 MRN ", patientMrn || "\u2014", " \xB7 ", age !== "" ? `${age} yr` : "\u2014 yr", " \xB7 ", gender === "boys" ? "Male" : gender === "girls" ? "Female" : "\u2014", " \xB7 Exam ", examDate), /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Pediatric Growth Chart \xB7 WHO (<5y) + IAP 2015 India (5\u201318y)",
        subtitle: "Real L,M,S percentiles \xB7 height, weight & BMI \xB7 WHO under 5y, IAP 2015 India 5\u201318y (fit from the paper's published tables).",
        badge: moduleStatus.growth.state !== "none" ? moduleStatus.growth.label : null,
        badgeVariant: moduleStatus.growth.state === "high" ? "high" : moduleStatus.growth.state === "borderline" ? "mid" : "low"
      }
    ), !hasManualGrowth ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter patient measurements",
        hint: "Age, biological sex, height and weight are required to plot the growth chart. Values recalculate automatically as you type."
      }
    ) : !inRange2 ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Pediatric workspace inactive",
        hint: "The growth reference covers ages 0\u201319 years. Enter an age in that range to use the growth engine."
      }
    ) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "4px" } }, /* @__PURE__ */ React.createElement("div", { className: "no-print", style: { display: "flex", justifyContent: "flex-end", marginTop: "12px", marginBottom: "8px" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: exportGrowthReportPdf,
        style: { display: "flex", alignItems: "center", gap: "6px", padding: "8px 14px", background: "#4f46e5", color: "white", border: "none", borderRadius: "9px", fontSize: "12px", fontWeight: "700", cursor: "pointer" }
      },
      /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "6 9 6 2 18 2 18 9" }), /* @__PURE__ */ React.createElement("path", { d: "M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" }), /* @__PURE__ */ React.createElement("rect", { x: "6", y: "14", width: "12", height: "8" })),
      "Export PDF"
    )), /* @__PURE__ */ React.createElement("div", { className: "summary-grid", style: { marginBottom: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: gm.stuntingVariant === "low" ? "#f0fdf4" : gm.stuntingVariant === "mid" ? "#fffbeb" : "#fff1f2", borderRadius: "12px", padding: "14px 16px", border: `1px solid ${gm.stuntingVariant === "low" ? "#bbf7d0" : gm.stuntingVariant === "mid" ? "#fde68a" : "#fecaca"}` } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", color: "#94a3b8", marginBottom: "4px" } }, "Height Status"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "15px", fontWeight: "900", color: gm.stuntingVariant === "low" ? "#16a34a" : gm.stuntingVariant === "mid" ? "#d97706" : "#dc2626" } }, gm.stuntingClass), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "2px" } }, pctTxt(gm.heightPct), " percentile")), /* @__PURE__ */ React.createElement("div", { style: { background: gm.underweightVariant === "low" ? "#f0fdf4" : gm.underweightVariant === "mid" ? "#fffbeb" : "#fff1f2", borderRadius: "12px", padding: "14px 16px", border: `1px solid ${gm.underweightVariant === "low" ? "#bbf7d0" : gm.underweightVariant === "mid" ? "#fde68a" : "#fecaca"}` } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", color: "#94a3b8", marginBottom: "4px" } }, "Weight / BMI Status"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "15px", fontWeight: "900", color: gm.underweightVariant === "low" ? "#16a34a" : gm.underweightVariant === "mid" ? "#d97706" : "#dc2626" } }, gm.underweightClass), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "2px" } }, "BMI ", pctTxt(gm.bmiPct), " percentile"))), /* @__PURE__ */ React.createElement(MetricRow, { label: "Chronological Age", value: evalAge.toFixed(1), unit: "yrs" }), /* @__PURE__ */ React.createElement(MetricRow, { label: "BMI", value: gm.bmiVal.toFixed(1), unit: "kg/m\xB2", sub: `z ${zTxt(gm.bmiZ)} \xB7 ${pctTxt(gm.bmiPct)} pct` }), /* @__PURE__ */ React.createElement(MetricRow, { label: "Median Weight for Age", value: gm.ref.wtMean !== null ? gm.ref.wtMean.toFixed(1) : "N/A", unit: "kg", sub: `Actual: ${evalWeight} kg` }), /* @__PURE__ */ React.createElement(MetricRow, { label: "Median Height for Age", value: gm.ref.htMean !== null ? gm.ref.htMean.toFixed(1) : "N/A", unit: "cm", sub: `Actual: ${evalHeight} cm` }), /* @__PURE__ */ React.createElement(MetricRow, { label: "Height Age (HA)", value: gm.heightAge.decimal ? gm.heightAge.decimal.toFixed(1) : "N/A", unit: "yrs equiv." }), /* @__PURE__ */ React.createElement(MetricRow, { label: "Weight Age (WA)", value: gm.weightAge.decimal ? gm.weightAge.decimal.toFixed(1) : "N/A", unit: "yrs equiv." }), /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 0", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b" } }, "Height SDS (", evalAge * 12 >= 60 ? "IAP" : "WHO", ")"), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "32px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, zTxt(gm.heightZ)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", color: "#94a3b8", marginLeft: "6px" } }, "SD"))), gm.heightZ !== null ? /* @__PURE__ */ React.createElement(SDSBar, { z: gm.heightZ }) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8" } }, "Out of reference range.")), /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 0" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b" } }, "BMI SDS (WHO)"), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "32px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, zTxt(gm.bmiZ)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", color: "#94a3b8", marginLeft: "6px" } }, "SD"))), gm.bmiZ !== null ? /* @__PURE__ */ React.createElement(SDSBar, { z: gm.bmiZ }) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8" } }, "Out of reference range.")), /* @__PURE__ */ React.createElement("div", { className: "no-print", style: { marginTop: "18px", borderTop: "1px solid #f1f5f9", paddingTop: "14px" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setShowChart((s) => !s),
        style: { width: "100%", display: "flex", alignItems: "center", gap: "10px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "11px 14px", cursor: "pointer", textAlign: "left" }
      },
      /* @__PURE__ */ React.createElement("span", { style: { color: "#4f46e5", fontWeight: "800", fontSize: "13px", transform: showChart ? "rotate(90deg)" : "none", transition: "transform 0.15s", display: "inline-block" } }, "\u25B8"),
      /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", fontWeight: "800", color: "#334155" } }, showChart ? "Hide growth chart" : "Show growth chart"),
      /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontSize: "11px", color: "#94a3b8", fontWeight: "600" } }, "Optional visualisation \u2014 the numbers above are the primary read")
    )), /* @__PURE__ */ React.createElement("div", { style: { display: showChart ? "block" : "none", marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { className: "no-print", style: { display: "flex", gap: "4px", background: "#f1f5f9", padding: "4px", borderRadius: "10px", marginBottom: "10px", width: "fit-content" } }, [{ key: "combined", label: "Growth Chart (H+W)" }, { key: "bmi", label: "BMI" }].map(({ key: mkey, label }) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: mkey,
        onClick: () => setGrowthChartMeasure(mkey),
        className: "toggle-btn",
        style: { background: growthChartMeasure === mkey ? "white" : "transparent", color: growthChartMeasure === mkey ? "#1e293b" : "#64748b", boxShadow: growthChartMeasure === mkey ? "0 1px 3px rgba(0,0,0,0.12)" : "none" }
      },
      label
    ))), /* @__PURE__ */ React.createElement("div", { id: "growth-chart-print", style: { border: "1px solid #eef2f7", borderRadius: "12px", padding: "8px", marginBottom: "16px", background: "white", overflowX: "auto" } }, growthChartMeasure === "combined" ? /* @__PURE__ */ React.createElement(
      GrowthChartCombined,
      {
        sex: evalGender,
        ageYears: evalAge,
        heightValue: evalHeight,
        weightValue: evalWeight,
        heightData: growthSeries[evalGender].height,
        weightData: growthSeries[evalGender].weight,
        heightSeries,
        weightSeries
      }
    ) : /* @__PURE__ */ React.createElement(GrowthChart, { measure: "bmi", sex: evalGender, ageYears: evalAge, value: gm.bmiVal, series: bmiSeries, chartData: growthSeries[evalGender].bmi })), growthChartMeasure === "combined" && !gm.weightAvailable && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#d97706", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "8px 12px", marginBottom: "12px" } }, "Weight-for-age has no reference data at this age. Use BMI-for-age for weight status instead."))));
  }

  // frontend/src/panels/QriskPanel.jsx
  function QriskPanel() {
    const { cholRatio, diabetes, ethnicity, evalGender, qAF, qAtypAntipsy, qCKD, qCortico, qED, qFhCvd, qMigraine, qRA, qSLE, qSMI, qTreatedHtn, qriskMetrics, sbpSD, setCholRatio, setDiabetes, setEthnicity, setQAF, setQAtypAntipsy, setQCKD, setQCortico, setQED, setQFhCvd, setQMigraine, setQRA, setQSLE, setQSMI, setQTreatedHtn, setSbpSD, setSmokeCat, smokeCat } = useQrisk();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "QRISK3 \xB7 10-Year Cardiovascular Risk",
        subtitle: "Hippisley-Cox 2017 (ClinRisk open source) \xB7 South-Asian ethnicity aware",
        badge: qriskMetrics.risk !== null ? qriskMetrics.band : "Age 25\u201384",
        badgeVariant: qriskMetrics.risk !== null ? qriskMetrics.variant : "neutral"
      }
    ), !qriskMetrics.inAgeRange && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#92400e", lineHeight: "1.6" } }, "\u26A0 QRISK3 is validated for ages 25\u201384. Set the patient's age in that range (Demographics) to compute risk."), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Ethnicity"), /* @__PURE__ */ React.createElement("select", { value: ethnicity, onChange: (e) => setEthnicity(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 1 }, "White / not stated"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Indian"), /* @__PURE__ */ React.createElement("option", { value: 3 }, "Pakistani"), /* @__PURE__ */ React.createElement("option", { value: 4 }, "Bangladeshi"), /* @__PURE__ */ React.createElement("option", { value: 5 }, "Other Asian"), /* @__PURE__ */ React.createElement("option", { value: 6 }, "Black Caribbean"), /* @__PURE__ */ React.createElement("option", { value: 7 }, "Black African"), /* @__PURE__ */ React.createElement("option", { value: 8 }, "Chinese"), /* @__PURE__ */ React.createElement("option", { value: 9 }, "Other"))), /* @__PURE__ */ React.createElement("div", { className: "split-grid" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Smoking"), /* @__PURE__ */ React.createElement("select", { value: smokeCat, onChange: (e) => setSmokeCat(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 0 }, "Non-smoker"), /* @__PURE__ */ React.createElement("option", { value: 1 }, "Ex-smoker"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Light (< 10/day)"), /* @__PURE__ */ React.createElement("option", { value: 3 }, "Moderate (10\u201319/day)"), /* @__PURE__ */ React.createElement("option", { value: 4 }, "Heavy (20+/day)"))), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Diabetes"), /* @__PURE__ */ React.createElement("select", { value: diabetes, onChange: (e) => setDiabetes(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 0 }, "None"), /* @__PURE__ */ React.createElement("option", { value: 1 }, "Type 1"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Type 2")))), /* @__PURE__ */ React.createElement("div", { className: "split-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Total : HDL Cholesterol ratio", value: cholRatio, onChange: (e) => setCholRatio(e.target.value), placeholder: "e.g. 4.0", step: "0.1", unit: "ratio", problem: rangeProblem("cholRatio", cholRatio) }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "SBP variability (SD, optional)", value: sbpSD, onChange: (e) => setSbpSD(e.target.value), placeholder: "mmHg SD", step: "0.1", unit: "SD", problem: rangeProblem("sbpSD", sbpSD) })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Uses BMI (from height/weight) and systolic BP from the left panel. Blank cholesterol ratio / SBP-SD contribute neutrally (QRISK3 convention). Townsend deprivation is set to 0 (UK-only index)."), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "6px 14px" } }, /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Atrial fibrillation", value: qAF, setter: setQAF }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "On BP treatment", value: qTreatedHtn, setter: setQTreatedHtn }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "CKD stage 3\u20135", value: qCKD, setter: setQCKD }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Rheumatoid arthritis", value: qRA, setter: setQRA }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Migraine", value: qMigraine, setter: setQMigraine }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "SLE (lupus)", value: qSLE, setter: setQSLE }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Severe mental illness", value: qSMI, setter: setQSMI }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Atypical antipsychotics", value: qAtypAntipsy, setter: setQAtypAntipsy }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Regular corticosteroids", value: qCortico, setter: setQCortico }), evalGender === "boys" && /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Erectile dysfunction", value: qED, setter: setQED }), /* @__PURE__ */ React.createElement(YesNoToggleRow, { label: "Family history of CVD", value: qFhCvd, setter: setQFhCvd }))), qriskMetrics.risk !== null && /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(qriskMetrics.variant), borderRadius: "16px", padding: "22px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "10-Year CVD Risk"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: qriskMetrics.variant === "high" ? "#dc2626" : qriskMetrics.variant === "mid" ? "#d97706" : "#16a34a", lineHeight: 1 } }, qriskMetrics.risk.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), qriskMetrics.typical !== null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "Healthy baseline (same age/sex/ethnicity): ", qriskMetrics.typical.toFixed(1), "%")), /* @__PURE__ */ React.createElement(StatusBadge, { text: qriskMetrics.band, variant: qriskMetrics.variant })), /* @__PURE__ */ React.createElement(ProbBar, { prob: qriskMetrics.risk, maxProb: 40, threshold: 10 })), qriskMetrics.risk !== null && qriskMetrics.imputed.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10.5px", color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "7px 10px", lineHeight: "1.5" } }, "\u26A0 Estimated with defaulted inputs: ", /* @__PURE__ */ React.createElement("strong", null, qriskMetrics.imputed.join(", ")), ". Enter these for a patient-specific score."), qriskMetrics.risk !== null && qriskMetrics.bmiClamped && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10.5px", color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "7px 10px", lineHeight: "1.5" } }, "\u26A0 BMI is outside QRISK3's 20\u201340 kg/m\xB2 range; the model scores it as if at the nearest limit."), qriskMetrics.risk === null && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "12px", padding: "14px 16px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: "#991b1b" } }, qriskMetrics.inAgeRange && qriskMetrics.bodySizeOk && qriskMetrics.loading ? "Calculating\u2026" : "QRISK3 not applicable"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.5" } }, !qriskMetrics.inAgeRange ? "QRISK3 is validated only for adults aged 25\u201384 (age and sex must be entered). No score is shown." : !qriskMetrics.bodySizeOk ? "Enter height and weight (BMI) to compute the score." : qriskMetrics.error ? `Calculation failed: ${qriskMetrics.error}` : qriskMetrics.reason || "")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "10px", padding: "12px 14px", fontSize: "11px", color: "#4338ca", lineHeight: "1.7" } }, /* @__PURE__ */ React.createElement("strong", null, "India note:"), " QRISK3 is derived on a UK cohort. Its Indian/South-Asian ethnicity term raises risk relative to White, but studies suggest it may still under-estimate true risk in Indians. Treat \u2265 10% as the usual statin-consideration threshold, and interpret alongside the ", /* @__PURE__ */ React.createElement("strong", null, "Lipid Association of India"), " risk stratification and ICMR guidance. QRISK3 does not apply to established CVD, familial hypercholesterolaemia, or type-appropriate secondary prevention."), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "18px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "QRISK3-2017 \xB7 Hippisley-Cox J et al., BMJ 2017;357:j2099 \xB7 ClinRisk open-source coefficients (GNU LGPL), verified against the CRAN QRISK3 reference. Clinician must verify \u2014 decision support only, not a diagnostic device."));
  }

  // frontend/src/panels/LedgerPanel.jsx
  function LedgerPanel() {
    const { age, albuminuria, assessment, canLogSnapshot, chronicityStatus, creatinine, height, logCurrentData, setTimeline, timeline, weight } = useLedger();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column", gap: "16px" } }, /* @__PURE__ */ React.createElement("div", { className: "timeline-header" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("h3", { style: { fontSize: "13px", fontWeight: "800", color: "#334155" } }, "CKD Progression Ledger"), /* @__PURE__ */ React.createElement("p", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "Session snapshots \u2014 chronicity assessment over \u2265 90 days"), /* @__PURE__ */ React.createElement("p", { style: { fontSize: "10.5px", color: "#b45309", marginTop: "4px", fontWeight: 700 } }, "Not saved: snapshots are cleared when the page reloads. Use the Patient Record tab for saved measurements.")), /* @__PURE__ */ React.createElement("div", { className: "timeline-actions" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: logCurrentData,
        disabled: !canLogSnapshot,
        title: canLogSnapshot ? "Record the current values" : "Enter age, sex, height and serum creatinine (within plausible ranges) first",
        style: { padding: "7px 16px", background: canLogSnapshot ? "#4f46e5" : "#cbd5e1", color: "white", border: "none", borderRadius: "9px", fontSize: "12px", fontWeight: "700", cursor: canLogSnapshot ? "pointer" : "not-allowed", boxShadow: "0 1px 4px rgba(79,70,229,0.3)", transition: "background 0.15s" },
        onMouseEnter: (e) => {
          if (canLogSnapshot) e.target.style.background = "#4338ca";
        },
        onMouseLeave: (e) => {
          if (canLogSnapshot) e.target.style.background = "#4f46e5";
        }
      },
      "+ Log Snapshot"
    ), timeline.length > 0 && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          if (window.confirm("Clear all logged snapshots from the ledger?")) setTimeline([]);
        },
        style: { padding: "7px 14px", background: "white", color: "#64748b", border: "1.5px solid #e2e8f0", borderRadius: "9px", fontSize: "12px", fontWeight: "600", cursor: "pointer", transition: "all 0.15s" },
        onMouseEnter: (e) => e.target.style.background = "#f8fafc",
        onMouseLeave: (e) => e.target.style.background = "white"
      },
      "Reset"
    ))), /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 16px", borderRadius: "12px", fontSize: "12px", lineHeight: "1.6" }, className: chronicityStatus.bgClass }, /* @__PURE__ */ React.createElement("span", { style: { fontWeight: "800", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "3px" } }, "Chronicity Assessment"), chronicityStatus.status), timeline.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "16px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "10px" } }, "eGFR Timeline"), /* @__PURE__ */ React.createElement("svg", { width: "100%", height: "100", viewBox: "0 0 500 100", preserveAspectRatio: "none", style: { borderRadius: "8px", background: "white", border: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("line", { x1: "0", y1: "22", x2: "500", y2: "22", stroke: "#f1f5f9", strokeWidth: "1.5" }), /* @__PURE__ */ React.createElement("line", { x1: "0", y1: "50", x2: "500", y2: "50", stroke: "#f1f5f9", strokeWidth: "1.5" }), /* @__PURE__ */ React.createElement("line", { x1: "0", y1: "78", x2: "500", y2: "78", stroke: "#f1f5f9", strokeWidth: "1.5" }), (() => {
      const sorted = [...timeline].sort((a, b) => new Date(a.date) - new Date(b.date));
      const pts = sorted.map((e, i) => ({
        x: sorted.length > 1 ? i / (sorted.length - 1) * 440 + 30 : 250,
        y: 90 - Math.min(e.egfr, 150) / 150 * 70,
        e
      }));
      return /* @__PURE__ */ React.createElement("g", null, pts.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: "#4f46e5", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round", points: pts.map((p) => `${p.x},${p.y}`).join(" ") }), pts.map((p, i) => /* @__PURE__ */ React.createElement("g", { key: p.e.id }, /* @__PURE__ */ React.createElement("circle", { cx: p.x, cy: p.y, r: "4", fill: "#4f46e5" }), /* @__PURE__ */ React.createElement("text", { x: p.x, y: p.y - 9, textAnchor: "middle", fill: "#4338ca", fontSize: "9", fontWeight: "bold" }, p.e.egfr), /* @__PURE__ */ React.createElement("text", { x: p.x, y: "96", textAnchor: "middle", fill: "#94a3b8", fontSize: "8" }, p.e.date.slice(5)))));
    })())), timeline.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 0", gap: "12px", textAlign: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "52px", height: "52px", borderRadius: "50%", background: "#f1f5f9", display: "flex", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#94a3b8", strokeWidth: "2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M12 5v14M5 12l7 7 7-7" }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "700", color: "#64748b" } }, "No snapshots logged yet"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, 'Enter patient data and click "Log Snapshot" to begin tracking.')) : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto", borderRadius: "12px", border: "1px solid #e2e8f0" }, className: "custom-scrollbar" }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", minWidth: "580px", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { background: "#f8fafc", borderBottom: "1px solid #e2e8f0" } }, ["Date", "Age", "Ht / Wt", "SCr", "eGFR", "ACR", "FIB-4"].map((h) => /* @__PURE__ */ React.createElement("th", { key: h, style: { padding: "10px 12px", textAlign: "left", fontWeight: "800", color: "#64748b", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" } }, h)))), /* @__PURE__ */ React.createElement("tbody", null, timeline.map((item, idx) => /* @__PURE__ */ React.createElement("tr", { key: item.id, style: { borderBottom: "1px solid #f1f5f9", background: idx % 2 === 0 ? "white" : "#fafbfc" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#1e293b" } }, item.date), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", color: "#475569" } }, item.age.toFixed(1), " y"), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", color: "#64748b" } }, item.height, " / ", item.weight), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#475569" } }, item.creatinine), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "800", color: "#4f46e5" } }, item.egfr), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("span", { style: { padding: "2px 8px", borderRadius: "99px", fontSize: "10px", fontWeight: "700", background: "#eef2ff", color: "#4338ca", border: "1px solid #c7d2fe" } }, item.albuminuria || "not recorded")), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#059669" } }, item.fib4 !== null ? item.fib4 : "\u2014")))))));
  }

  // frontend/src/panels/BoneAgeAdvanced.jsx
  function BoneAgeAdvanced() {
    const {
      LC_API,
      addOrSelectBox,
      adjBusy,
      adjItems,
      adjMsg,
      adjReviewer,
      age,
      analysisUrl,
      assessment,
      attachImage,
      boneAge,
      boneAgeSource,
      boneMetrics,
      bonesIntoGrids,
      boxes,
      carpalStages,
      clearBox,
      covBusy,
      coverage,
      curveToText,
      endLocDrag,
      evalAge,
      evalGender,
      evalHeight,
      fatherHeight,
      height,
      lcBtn,
      lcBusy,
      lcLocked,
      lcMsg,
      loadAdjudication,
      loadCoverage,
      loadLetterTables,
      loadMonitoring,
      locBusy,
      locImg,
      locMsg,
      locRef,
      localizeBones,
      ltBusy,
      ltMsg,
      ltSection,
      ltSex,
      ltStatus,
      ltTables,
      monBusy,
      monitoring,
      motherHeight,
      onLocMove,
      patientCode,
      radiograph,
      resolveAdjudication,
      reviseAssessment,
      rusStages,
      saveBoxes,
      saveDraft,
      saveLetterTables,
      selBone,
      setAdjReviewer,
      setAssessment,
      setBoneAge,
      setBoneAgeSource,
      setCarpalStages,
      setFatherHeight,
      setImageDomain,
      setLcBusy,
      setLcMsg,
      setLocImg,
      setLtCurve,
      setLtPoint,
      setLtSection,
      setLtSex,
      setLtSexCurve,
      setLtTables,
      setMotherHeight,
      setPatientCode,
      setRefExpected,
      setRusStages,
      setShowAudit,
      showAudit,
      startBoxDrag,
      toggleAudit,
      calculateAssessment,
      approveAssessment,
      unsavedStaging,
      useGridAsReference
    } = useBoneAge();
    return /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("details", { style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", fontWeight: "800", fontSize: "12px", color: "#7c3aed", padding: "8px 0", listStyle: "none" } }, "\u2699 Advanced \xB7 manual grading, save & approve, adult-height"), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "800", color: "#6b21a8", textTransform: "uppercase", letterSpacing: "0.05em" } }, "Manual TW3 grading \xB7 left hand\u2013wrist \xB7 stages A\u2013I"), /* @__PURE__ */ React.createElement("button", { onClick: () => {
      setRusStages({});
      setCarpalStages({});
    }, style: { padding: "5px 12px", background: "white", color: "#7c3aed", border: "1.5px solid #ddd6fe", borderRadius: "8px", fontSize: "11px", fontWeight: "700", cursor: "pointer" } }, "Clear grades")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#7c3aed", marginBottom: "6px", textTransform: "uppercase", letterSpacing: ".04em" } }, "RUS bones (13)"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "8px" } }, REPORT_RUS.map(([code, label]) => /* @__PURE__ */ React.createElement("div", { key: code }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#7c3aed", display: "block", marginBottom: "3px" } }, label), /* @__PURE__ */ React.createElement("select", { value: rusStages[code] || "", onChange: (e) => setRusStages((s) => {
      const n = { ...s };
      if (e.target.value) n[code] = e.target.value;
      else delete n[code];
      return n;
    }), className: "input-field", style: { padding: "7px 8px", width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 stage \u2014"), LETTER_STAGES.map((st) => /* @__PURE__ */ React.createElement("option", { key: st, value: st }, st)))))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#7c3aed", margin: "14px 0 6px", textTransform: "uppercase", letterSpacing: ".04em" } }, "Carpal bones (7)"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "8px" } }, REPORT_CARPALS.map((name) => /* @__PURE__ */ React.createElement("div", { key: name }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#7c3aed", display: "block", marginBottom: "3px" } }, name), /* @__PURE__ */ React.createElement("select", { value: carpalStages[name] || "", onChange: (e) => setCarpalStages((s) => {
      const n = { ...s };
      if (e.target.value) n[name] = e.target.value;
      else delete n[name];
      return n;
    }), className: "input-field", style: { padding: "7px 8px", width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 stage \u2014"), LETTER_STAGES.map((st) => /* @__PURE__ */ React.createElement("option", { key: st, value: st }, st)))))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "These letter grades appear in the report above. The RUS/carpal scores and the TWII / TWIII / TWII'20 bone ages compute once the clinic's licensed TW3 tables are supplied \u2014 no values are guessed.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "4px" } }, "Annotation record"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginBottom: "10px", lineHeight: "1.5" } }, "Saves the doctor-confirmed 20-bone letter staging to the local database (for review and to build the training dataset). Sex and age come from Demographics."), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 180px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#64748b", display: "block", marginBottom: "3px" } }, "Patient code"), /* @__PURE__ */ React.createElement(
      "input",
      {
        value: patientCode,
        onChange: (e) => setPatientCode(e.target.value),
        placeholder: "e.g. CASE-001",
        className: "input-field",
        style: { padding: "7px 8px", width: "100%" },
        disabled: lcLocked
      }
    )), /* @__PURE__ */ React.createElement("button", { onClick: saveDraft, disabled: lcBusy, style: lcBtn("#7c3aed", lcBusy) }, lcBusy ? "Saving\u2026" : assessment && !lcLocked ? "Update annotation" : "Save annotation"), /* @__PURE__ */ React.createElement("button", { onClick: async () => {
      if (!patientCode.trim()) {
        setLcMsg({ type: "err", text: "Enter a patient code to load." });
        return;
      }
      setLcBusy(true);
      setLcMsg(null);
      try {
        const r = await fetch(`${LC_API}?patient_code=${encodeURIComponent(patientCode.trim())}`);
        const list = await r.json();
        if (!r.ok || !Array.isArray(list) || list.length === 0) {
          setLcMsg({ type: "err", text: "No saved annotation for that code." });
          return;
        }
        const d = list[0];
        bonesIntoGrids(d.bones);
        setAssessment(d);
        setShowAudit(false);
        setLcMsg({ type: "ok", text: `Loaded #${d.id} rev ${d.revision} \xB7 ${d.assessment_status}` });
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    }, disabled: lcBusy, style: lcBtn("#475569", lcBusy) }, "Load saved"), assessment && !lcLocked && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: calculateAssessment,
        disabled: lcBusy || unsavedStaging,
        title: unsavedStaging ? "Save the annotation first" : "Score the saved staging",
        style: lcBtn("#0f766e", lcBusy || unsavedStaging)
      },
      "Calculate"
    ), assessment && !lcLocked && (() => {
      const canApprove = assessment.assessment_status === "ready_for_review" && assessment.bone_age_years != null && !unsavedStaging;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          onClick: approveAssessment,
          disabled: lcBusy || !canApprove,
          title: canApprove ? "Approve this bone age for clinical use" : "Calculate a bone age first",
          style: lcBtn("#059669", lcBusy || !canApprove)
        },
        "Approve"
      );
    })(), assessment && lcLocked && /* @__PURE__ */ React.createElement("button", { onClick: reviseAssessment, disabled: lcBusy, style: lcBtn("#0891b2", lcBusy) }, "Open revision"), assessment && /* @__PURE__ */ React.createElement("button", { onClick: toggleAudit, disabled: lcBusy, style: lcBtn("#64748b", lcBusy) }, showAudit ? "Hide audit" : "Audit")), assessment && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "11px", color: "#475569" } }, "Record #", assessment.id, " \xB7 rev ", assessment.revision, " \xB7 ", /* @__PURE__ */ React.createElement("strong", { style: { textTransform: "uppercase" } }, assessment.assessment_status), " ", "\xB7 ", assessment.rus_staged_count, "/13 RUS + ", assessment.carpal_staged_count, "/7 carpal staged", assessment.bone_age_years != null && /* @__PURE__ */ React.createElement(React.Fragment, null, " \xB7 bone age ", /* @__PURE__ */ React.createElement("strong", null, assessment.bone_age_years.toFixed(1), " yr")), assessment.assessment_status === "approved" && assessment.approved_by && /* @__PURE__ */ React.createElement(React.Fragment, null, " \xB7 approved by ", assessment.approved_by), unsavedStaging && !lcLocked && /* @__PURE__ */ React.createElement("span", { style: { color: "#b45309", fontWeight: "700" } }, " \xB7 unsaved grade changes")), lcMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", fontWeight: "700", color: lcMsg.type === "ok" ? "#059669" : "#dc2626" } }, lcMsg.text), showAudit && assessment && assessment.audit && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", maxHeight: "160px", overflowY: "auto", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "8px", fontFamily: "ui-monospace, Menlo, Consolas, monospace", fontSize: "10px", color: "#475569" } }, assessment.audit.map((e, i) => /* @__PURE__ */ React.createElement("div", { key: i }, e.timestamp ? e.timestamp.slice(0, 19).replace("T", " ") : "", " \xB7 ", e.event_type, " \xB7 ", e.actor, e.reason ? " \xB7 " + e.reason : ""))), assessment && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("label", { style: { ...lcBtn("#0f766e", lcBusy || lcLocked), display: "inline-block" } }, radiograph ? "Replace film" : "Attach film", /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "file",
        accept: ".dcm,image/*",
        style: { display: "none" },
        disabled: lcBusy || lcLocked,
        onChange: (e) => {
          const f = e.target.files && e.target.files[0];
          if (f) attachImage(f);
          e.target.value = "";
        }
      }
    )), radiograph && /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 200px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#64748b", display: "block", marginBottom: "3px" } }, "Image source (confirm)"), /* @__PURE__ */ React.createElement(
      "select",
      {
        value: radiograph.source_domain || "unknown",
        onChange: (e) => setImageDomain(e.target.value),
        className: "input-field",
        style: { padding: "7px 8px", width: "100%" },
        disabled: lcLocked
      },
      IMAGE_DOMAINS.map(([v, label]) => /* @__PURE__ */ React.createElement("option", { key: v, value: v }, label))
    ))), radiograph && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", color: "#475569" } }, "Film #", radiograph.radiograph_id, " \xB7 ", radiograph.source_format, " \xB7 quality ", String(radiograph.quality_status || "").replace(/_/g, " "), radiograph.duplicate_of ? ` \xB7 duplicate of #${radiograph.duplicate_of}` : ""), radiograph && LOW_TRUST_DOMAINS.includes(radiograph.source_domain) && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "8px 10px", fontSize: "10.5px", color: "#92400e", lineHeight: "1.5" } }, "\u26A0 ", radiograph.source_domain === "film_photo" ? "Photograph of a film" : "Compressed image", ": reduced reliability. Any future AI suggestion must be treated with lower confidence and every bone confirmed manually \u2014 this domain is evaluated separately from digital images.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Scoring, bone-age calculation and doctor approval unlock automatically once the clinic's licensed TW3 point/age tables are installed. Until then this record captures verified staging only.")), radiograph && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em" } }, "Bone localization"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "Auto-box the bones (or draw them), drag to correct, save. Confirmed boxes become training crops.")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px" } }, /* @__PURE__ */ React.createElement("button", { onClick: localizeBones, disabled: locBusy || lcLocked, style: lcBtn("#0f766e", locBusy || lcLocked) }, locBusy ? "\u2026" : "Auto-locate"), /* @__PURE__ */ React.createElement("button", { onClick: saveBoxes, disabled: locBusy || lcLocked || Object.keys(boxes).length === 0, style: lcBtn("#7c3aed", locBusy || lcLocked || Object.keys(boxes).length === 0) }, "Save boxes"))), analysisUrl && /* @__PURE__ */ React.createElement(
      "div",
      {
        ref: locRef,
        onMouseMove: onLocMove,
        onMouseUp: endLocDrag,
        onMouseLeave: endLocDrag,
        style: { position: "relative", width: "100%", maxWidth: "420px", margin: "12px auto 0", userSelect: "none" }
      },
      /* @__PURE__ */ React.createElement(
        "img",
        {
          src: analysisUrl,
          alt: "radiograph",
          draggable: false,
          onLoad: (e) => {
            if (!locImg) setLocImg({ width: e.target.naturalWidth, height: e.target.naturalHeight });
          },
          style: { width: "100%", display: "block", borderRadius: "8px", border: "1px solid #e2e8f0" }
        }
      ),
      locImg && Object.entries(boxes).map(([bone, b]) => {
        const sel = selBone === bone;
        const st = {
          position: "absolute",
          left: `${b[0] / locImg.width * 100}%`,
          top: `${b[1] / locImg.height * 100}%`,
          width: `${(b[2] - b[0]) / locImg.width * 100}%`,
          height: `${(b[3] - b[1]) / locImg.height * 100}%`,
          border: `2px solid ${sel ? "#f59e0b" : "#0ea5e9"}`,
          background: sel ? "rgba(245,158,11,0.12)" : "rgba(14,165,233,0.08)",
          cursor: "move",
          boxSizing: "border-box"
        };
        return /* @__PURE__ */ React.createElement("div", { key: bone, onMouseDown: (e) => startBoxDrag(bone, "move", e), style: st }, /* @__PURE__ */ React.createElement("span", { style: { position: "absolute", top: "-14px", left: "-1px", fontSize: "8px", fontWeight: "700", color: sel ? "#b45309" : "#0369a1", background: "white", padding: "0 2px", borderRadius: "2px", whiteSpace: "nowrap" } }, bone), /* @__PURE__ */ React.createElement(
          "div",
          {
            onMouseDown: (e) => startBoxDrag(bone, "resize", e),
            style: { position: "absolute", right: "-5px", bottom: "-5px", width: "10px", height: "10px", background: "white", border: `2px solid ${sel ? "#f59e0b" : "#0ea5e9"}`, borderRadius: "2px", cursor: "nwse-resize" }
          }
        ));
      })
    ), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10px", fontWeight: "700", color: "#64748b" } }, "Bones \u2014 click to add/select a box (\xD7 to remove):"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" } }, [...REPORT_RUS.map(([c]) => c), ...REPORT_CARPALS.map(carpalCode2)].map((code) => {
      const has = !!boxes[code];
      const sel = selBone === code;
      return /* @__PURE__ */ React.createElement(
        "span",
        {
          key: code,
          style: {
            display: "inline-flex",
            alignItems: "center",
            gap: "2px",
            padding: "3px 6px",
            borderRadius: "6px",
            fontSize: "10px",
            fontWeight: "700",
            cursor: "pointer",
            border: `1px solid ${has ? "#0ea5e9" : "#e2e8f0"}`,
            background: sel ? "#fef3c7" : has ? "#e0f2fe" : "white",
            color: has ? "#0369a1" : "#94a3b8"
          },
          onClick: () => addOrSelectBox(code)
        },
        code,
        has && /* @__PURE__ */ React.createElement("span", { onClick: (e) => {
          e.stopPropagation();
          clearBox(code);
        }, style: { color: "#ef4444", fontWeight: "800" } }, "\xD7")
      );
    })), locMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", fontWeight: "700", color: locMsg.type === "ok" ? "#059669" : "#dc2626" } }, locMsg.text), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Auto-locate needs a trained localizer model (see backend/ai/LOCALIZE.md); until then you can draw boxes manually and they still save + export as crops.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em" } }, "Dataset coverage"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "Unique patients per bone \xD7 stage across all saved annotations. Drives when AI suggestions could be trained.")), /* @__PURE__ */ React.createElement("button", { onClick: loadCoverage, disabled: covBusy, style: lcBtn("#475569", covBusy) }, covBusy ? "Loading\u2026" : coverage ? "Refresh" : "Load coverage")), coverage && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", marginBottom: "8px" } }, coverage.n_patients, " patients \xB7 ", coverage.n_assessments, " assessments.", Object.entries(coverage.summary).map(([sys, s]) => /* @__PURE__ */ React.createElement("span", { key: sys, style: { marginLeft: "8px" } }, "\xB7 ", /* @__PURE__ */ React.createElement("strong", null, sys), ": ", s.unique_patients, " pt / ", s.cells_covered, " cells / ", s.annotations, " anno"))), coverage.cells.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8" } }, "No confirmed staging yet \u2014 save an annotation above.") : /* @__PURE__ */ React.createElement("div", { style: { maxHeight: "220px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "8px" } }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "11px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { background: "#f8fafc", color: "#64748b", textAlign: "left" } }, /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "Bone"), /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "Stage"), /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "\u2642"), /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "\u2640"), /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "w/img"), /* @__PURE__ */ React.createElement("th", { style: { padding: "5px 8px" } }, "Support"))), /* @__PURE__ */ React.createElement("tbody", null, [...coverage.cells].sort((a, b) => a.unique_total - b.unique_total).map((c, i) => {
      const col = { empty: "#dc2626", minimal: "#d97706", experimental: "#d97706", limited: "#2563eb", candidate: "#059669" }[c.support] || "#64748b";
      return /* @__PURE__ */ React.createElement("tr", { key: i, style: { borderTop: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", color: "#334155" } }, c.bone_code, /* @__PURE__ */ React.createElement("span", { style: { color: "#cbd5e1" } }, " \xB7 ", c.stage_system.replace("tw3", ""))), /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", fontWeight: "700" } }, c.stage), /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px" } }, c.unique_boys), /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px" } }, c.unique_girls), /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px" } }, c.n_with_image), /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", color: col, fontWeight: "700" } }, c.support));
    })))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Bands (unique patients): minimal 1\u20139 \xB7 experimental 10\u201324 \xB7 limited 25\u201349 \xB7 candidate \u226550. Engineering thresholds only \u2014 not proof of clinical validity."))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em" } }, "Monitoring & drift"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "AI-vs-clinician error over time, input-quality drift, and a soft external plausibility check. Watch-the-gap only \u2014 this never changes a model or a reported age.")), /* @__PURE__ */ React.createElement("button", { onClick: loadMonitoring, disabled: monBusy, style: lcBtn("#475569", monBusy) }, monBusy ? "Loading\u2026" : monitoring ? "Refresh" : "Load monitoring")), monitoring && (() => {
      const st = monitoring.stats || {};
      const tr = st.trend || {};
      const dr = monitoring.input_drift || {};
      const pl = monitoring.plausibility || {};
      const pct = (v) => v == null ? "\u2014" : `${Math.round(v * 100)}%`;
      const yr = (v) => v == null ? "\u2014" : `${v} yr`;
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 150px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b" } }, "AI vs clinician MAE"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "18px", fontWeight: "800", color: "#334155" } }, yr(st.ai_vs_human_mae_years)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8" } }, st.paired_with_ai || 0, " paired \xB7 ", st.total_feedback || 0, " total")), /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 150px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b" } }, "Trend (recent vs older)"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "18px", fontWeight: "800", color: tr.improving ? "#059669" : "#334155" } }, yr(tr.recent_mae_years), " ", tr.improving ? "\u2193" : ""), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8" } }, "was ", yr(tr.older_mae_years))), /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 150px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b" } }, "Low-trust input share"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "18px", fontWeight: "800", color: dr.worsening ? "#d97706" : "#334155" } }, pct(dr.recent_low_trust_share), " ", dr.worsening ? "\u2191" : ""), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8" } }, "was ", pct(dr.older_low_trust_share), " \xB7 compressed/photo"))), pl.vs_cpp && /* @__PURE__ */ React.createElement("div", { style: { background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#92400e" } }, "External plausibility (soft \xB7 non-gating)"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#334155", marginTop: "4px" } }, "Observed bone-age distribution vs published cohorts \u2014 TV distance: CPP ", pl.vs_cpp.tv_distance ?? "\u2014", " \xB7 control ", pl.vs_control?.tv_distance ?? "\u2014", "."), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#b45309", marginTop: "6px", lineHeight: "1.5" } }, "\u26A0 ", pl.vs_cpp.caveat)));
    })()), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em" } }, "Adjudication queue"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "Bones where independent reads disagree are queued for a senior read \u2014 resolved to one stage, never silently averaged.")), /* @__PURE__ */ React.createElement("button", { onClick: loadAdjudication, disabled: adjBusy, style: lcBtn("#475569", adjBusy) }, adjBusy ? "Loading\u2026" : adjItems ? "Refresh" : "Load queue")), adjItems && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "11px", color: "#475569" } }, "Reviewing clinician"), /* @__PURE__ */ React.createElement(
      "input",
      {
        value: adjReviewer,
        onChange: (e) => setAdjReviewer(e.target.value),
        placeholder: "e.g. Dr Rao",
        style: { fontSize: "11px", padding: "4px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }
      }
    )), adjItems.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8" } }, "No disputed bones open. Multi-reader disagreements appear here for resolution.") : /* @__PURE__ */ React.createElement("div", { style: { maxHeight: "240px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "8px" } }, adjItems.map((it) => /* @__PURE__ */ React.createElement("div", { key: it.id, style: { padding: "8px 10px", borderTop: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#334155" } }, /* @__PURE__ */ React.createElement("strong", null, it.bone_code), " ", /* @__PURE__ */ React.createElement("span", { style: { color: "#cbd5e1" } }, "\xB7 ", it.film_key), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b", marginTop: "2px" } }, it.n_readers, " readers \xB7 votes ", Object.entries(it.votes).map(([s, n]) => `${s}:${n}`).join("  "))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "4px", flexWrap: "wrap" } }, Object.keys(it.votes).sort().map((stage) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: stage,
        onClick: () => resolveAdjudication(it.id, stage),
        disabled: adjBusy,
        style: { fontSize: "11px", fontWeight: "700", padding: "3px 9px", border: "1px solid #cbd5e1", borderRadius: "6px", background: "#f8fafc", color: "#334155", cursor: adjBusy ? "default" : "pointer" }
      },
      stage
    )))))), adjMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", fontWeight: "700", color: adjMsg.type === "ok" ? "#059669" : "#dc2626" } }, adjMsg.text))), /* @__PURE__ */ React.createElement(
      "details",
      {
        style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" },
        onToggle: (e) => {
          if (e.target.open && !ltTables) loadLetterTables();
        }
      },
      /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", listStyle: "none" } }, "\u{1F522} Licensed TW3 tables \u2014 enter once to turn scoring ON"),
      /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", margin: "8px 0 12px", lineHeight: "1.5" } }, "Enter the point values and score\u2192age curves from your own licensed TW3 reference. Nothing is shipped or guessed. Scoring switches on only after a reference case from one of your reported films is reproduced (accuracy gate)."),
      ltStatus && /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "10px", fontSize: "11px", fontWeight: "700", color: ltStatus.scoring_ready ? "#059669" : "#b45309" } }, ltStatus.scoring_ready ? "\u2713 Scoring is ON \u2014 report fills with real numbers." : ltStatus.provenance_complete === false ? "\u25CB Scoring OFF \u2014 document the licensed source (Provenance tab)." : "\u25CB Scoring OFF \u2014 table incomplete or reference not reproduced."),
      !ltTables ? /* @__PURE__ */ React.createElement("button", { onClick: loadLetterTables, disabled: ltBusy, style: lcBtn("#7c3aed", ltBusy) }, ltBusy ? "Loading\u2026" : "Open table editor") : /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "10px" } }, [["rus", "RUS points"], ["carpal", "Carpal points"], ["tw20", "TWII'20 points"], ["curves", "Score\u2192age curves"], ["ref", "Reference case"], ["prov", "Provenance"]].map(([k, label]) => /* @__PURE__ */ React.createElement("button", { key: k, onClick: () => setLtSection(k), style: { padding: "5px 10px", borderRadius: "8px", fontSize: "11px", fontWeight: "700", cursor: "pointer", border: "1px solid #ddd6fe", background: ltSection === k ? "#7c3aed" : "white", color: ltSection === k ? "white" : "#7c3aed" } }, label)), ltSection !== "ref" && /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", display: "flex", gap: "4px" } }, ["boys", "girls"].map((s) => /* @__PURE__ */ React.createElement("button", { key: s, onClick: () => setLtSex(s), style: { padding: "5px 10px", borderRadius: "8px", fontSize: "11px", fontWeight: "700", cursor: "pointer", border: "1px solid #cbd5e1", background: ltSex === s ? "#334155" : "white", color: ltSex === s ? "white" : "#334155" } }, s === "boys" ? "Boys" : "Girls")))), (ltSection === "rus" || ltSection === "carpal" || ltSection === "tw20") && (() => {
        const group = ltSection === "rus" ? "rus_stage_to_score" : ltSection === "carpal" ? "carpal_stage_to_score" : "tw20_stage_to_score";
        const carpalRows = REPORT_CARPALS.map((n) => [carpalCode2(n), n]);
        const rows = ltSection === "carpal" ? carpalRows : ltSection === "tw20" ? [...REPORT_RUS, ...carpalRows] : REPORT_RUS;
        const cell = (bone, L) => ((ltTables[group][ltSex] || {})[bone] || {})[L];
        return /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { borderCollapse: "collapse", fontSize: "11px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { padding: "3px 6px", textAlign: "left", color: "#64748b" } }, ltSex, " \xB7 bone"), LETTER_STAGES.map((L) => /* @__PURE__ */ React.createElement("th", { key: L, style: { padding: "3px 4px", color: "#64748b" } }, L)))), /* @__PURE__ */ React.createElement("tbody", null, rows.map(([code, label]) => /* @__PURE__ */ React.createElement("tr", { key: code }, /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", whiteSpace: "nowrap", color: "#334155" } }, label), LETTER_STAGES.map((L) => /* @__PURE__ */ React.createElement("td", { key: L, style: { padding: "1px" } }, /* @__PURE__ */ React.createElement(
          "input",
          {
            type: "number",
            value: cell(code, L) ?? "",
            onChange: (e) => setLtPoint(group, ltSex, code, L, e.target.value),
            style: { width: "42px", padding: "3px 2px", fontSize: "11px", textAlign: "center", border: "1px solid #e2e8f0", borderRadius: "4px" }
          }
        ))))))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "6px" } }, "Leave a cell blank if that letter is not defined for that bone. Enter both Boys and Girls."));
      })(), ltSection === "curves" && /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gap: "12px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" } }, [["rus_score_to_age", "RUS"], ["carpal_score_to_age", "Carpal"]].flatMap(
        ([grp, gl]) => ["twii", "twiii"].map((cv) => /* @__PURE__ */ React.createElement("div", { key: grp + cv }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#7c3aed", display: "block", marginBottom: "3px" } }, gl, " \xB7 ", cv.toUpperCase(), " \xB7 ", ltSex), /* @__PURE__ */ React.createElement(
          "textarea",
          {
            value: curveToText((ltTables[grp][cv] || {})[ltSex]),
            onChange: (e) => setLtCurve(grp, cv, ltSex, e.target.value),
            placeholder: "score, age\n300, 8\n450, 10",
            rows: 4,
            style: { width: "100%", fontFamily: "ui-monospace, monospace", fontSize: "11px", padding: "6px", border: "1px solid #e2e8f0", borderRadius: "6px" }
          }
        )))
      ), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#7c3aed", display: "block", marginBottom: "3px" } }, "TWII'20 (20-bone) \xB7 ", ltSex), /* @__PURE__ */ React.createElement(
        "textarea",
        {
          value: curveToText((ltTables.tw20_score_to_age || {})[ltSex]),
          onChange: (e) => setLtSexCurve("tw20_score_to_age", ltSex, e.target.value),
          placeholder: "score, age\n300, 8\n450, 10",
          rows: 4,
          style: { width: "100%", fontFamily: "ui-monospace, monospace", fontSize: "11px", padding: "6px", border: "1px solid #e2e8f0", borderRadius: "6px" }
        }
      )), /* @__PURE__ */ React.createElement("div", { style: { gridColumn: "1/-1", fontSize: "10px", color: "#94a3b8" } }, `One "score, age" pair per line (ascending score). \u22652 points per curve. Carpal / TWII'20 curves optional if you only report RUS.`)), ltSection === "prov" && /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gap: "8px", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" } }, [["book_title", "Book title *"], ["edition", "Edition / year *"], ["isbn", "ISBN"], ["licensed_owner", "Licensed owner *"], ["pages", "Pages"], ["entered_by", "Entered by *"], ["verified_by", "Verified by *"], ["verification_date", "Verification date *"]].map(([k, label]) => /* @__PURE__ */ React.createElement("div", { key: k }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#64748b", display: "block", marginBottom: "2px" } }, label), /* @__PURE__ */ React.createElement(
        "input",
        {
          type: k === "verification_date" ? "date" : "text",
          value: (ltTables.provenance || {})[k] || "",
          onChange: (e) => setLtTables((t) => ({ ...t, provenance: { ...t.provenance || {}, [k]: e.target.value } })),
          style: { width: "100%", padding: "5px 7px", fontSize: "11px", border: "1px solid #e2e8f0", borderRadius: "6px" }
        }
      ))), /* @__PURE__ */ React.createElement("div", { style: { gridColumn: "1/-1", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "* required. Licensed TW3 values may not drive scoring without a documented, legally-owned source.", ltStatus && ltStatus.missing_provenance && ltStatus.missing_provenance.length > 0 ? ` Still missing: ${ltStatus.missing_provenance.join(", ")}.` : "")), ltSection === "ref" && (() => {
        const ref = ltTables.reference_cases && ltTables.reference_cases[0] || null;
        const nRus = ref ? Object.keys(ref.rus_stages || {}).length : 0;
        const nCar = ref ? Object.keys(ref.carpal_stages || {}).length : 0;
        return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", marginBottom: "8px", lineHeight: "1.5" } }, "Pick one of your own previously-reported films: grade its bones in the grid above, then capture them here and type the score/age you reported. Scoring turns on only when these values reproduce."), /* @__PURE__ */ React.createElement("button", { onClick: useGridAsReference, style: { ...lcBtn("#0891b2", false), marginBottom: "8px" } }, "Capture reference stages from grid"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", marginBottom: "8px" } }, "Captured: ", nRus, "/13 RUS + ", nCar, "/7 carpal \xB7 sex ", ref ? ref.sex : "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gap: "8px", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#64748b" } }, "Reported RUS score"), /* @__PURE__ */ React.createElement("input", { type: "number", value: (ref && ref.expected && ref.expected.rus_score) ?? "", onChange: (e) => setRefExpected("rus_score", e.target.value), className: "input-field", style: { padding: "6px 8px", width: "100%" } })), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "10px", fontWeight: "700", color: "#64748b" } }, "Reported TWIII-RUS age (yr)"), /* @__PURE__ */ React.createElement("input", { type: "number", step: "0.1", value: (ref && ref.expected && ref.expected.twiii_rus_age_years) ?? "", onChange: (e) => setRefExpected("twiii_rus_age_years", e.target.value), className: "input-field", style: { padding: "6px 8px", width: "100%" } }))));
      })(), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("button", { onClick: saveLetterTables, disabled: ltBusy, style: lcBtn("#7c3aed", ltBusy) }, ltBusy ? "Saving\u2026" : "Validate & save tables"), ltMsg && /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", color: ltMsg.type === "ok" ? "#059669" : "#dc2626" } }, ltMsg.text)))
    ), /* @__PURE__ */ React.createElement("div", { className: "split-grid", style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "TW3 Bone Age (used for prediction)",
        value: boneAge,
        onChange: (e) => {
          setBoneAge(e.target.value === "" ? "" : parseFloat(e.target.value));
          setBoneAgeSource("manual");
        },
        placeholder: "e.g. 10.5",
        step: "0.1",
        unit: "yrs",
        accent: "#7c3aed"
      }
    ), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Source"), /* @__PURE__ */ React.createElement("div", { style: { padding: "10px 12px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "9px", fontSize: "12px", fontWeight: "700", color: "#475569" } }, boneAge === "" ? "Not set" : boneAgeSource === "rus" ? "From RUS staging" : "Manual entry"))), /* @__PURE__ */ React.createElement("div", { className: "split-grid", style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Father's Height", value: fatherHeight, onChange: (e) => setFatherHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm (optional)", unit: "cm", problem: rangeProblem("parentHeight", fatherHeight) }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Mother's Height", value: motherHeight, onChange: (e) => setMotherHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm (optional)", unit: "cm", problem: rangeProblem("parentHeight", motherHeight) })), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "10px", padding: "12px 14px", fontSize: "11px", color: "#64748b", lineHeight: "1.6" } }, "The TW3 bone age is derived only from the 20 doctor-confirmed bone stages above (RUS + carpal) via the licensed TW3 tables \u2014 never from the whole-image AI, which is a rough screening triage only. Automatic per-bone staging from the X-ray is not yet available (it needs stage-labelled training data the clinic is now collecting)."), !boneMetrics ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: "12px", padding: "36px 0", textAlign: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "52px", height: "52px", borderRadius: "50%", background: "#f5f3ff", display: "flex", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#a78bfa", strokeWidth: "2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M18 8a6 6 0 0 0-9.33-5" }), /* @__PURE__ */ React.createElement("path", { d: "M6 16a6 6 0 0 0 9.33 5" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "2", x2: "12", y2: "22" }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "700", color: "#64748b" } }, "Set a TW3 bone age or both parents' heights"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", maxWidth: "320px", lineHeight: "1.6" } }, "Stage the left hand\u2013wrist film above (TW3 RUS), or enter a TW3 bone age manually. Add parents' heights for the genetic target. Current height is taken from Demographics.")) : /* @__PURE__ */ React.createElement("div", null, boneMetrics.mph !== null ? /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { background: "linear-gradient(135deg,#f5f3ff,#eef2ff)", border: "1.5px solid #ddd6fe", borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#7c3aed", marginBottom: "8px" } }, "Mid-Parental Target Height"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: "#5b21b6", lineHeight: 1 } }, boneMetrics.mph.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#7c3aed", fontWeight: "600" } }, "cm")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#8b5cf6", marginTop: "4px" } }, "\u2248 ", Math.floor(boneMetrics.mph / 30.48), "\u2032", Math.round(boneMetrics.mph / 2.54 % 12), "\u2033 \xB7 genetic target from parents (Tanner) \xB7 range ", boneMetrics.mphLow.toFixed(0), "\u2013", boneMetrics.mphHigh.toFixed(0), " cm")), /* @__PURE__ */ React.createElement("div", { style: { textAlign: "right" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: "Genetic target \u2014 not a prediction", variant: "info" }), boneMetrics.mphPct !== null && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "12px", color: "#7c3aed", fontWeight: "700" } }, boneMetrics.mphPct.toFixed(1), "th centile (Khadilkar)"))) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "12px", padding: "16px", fontSize: "13px", fontWeight: "700", color: "#7c3aed", lineHeight: "1.6" } }, "Add both parents' heights for the mid-parental (genetic target) height and its \xB18.5 cm range."), boneMetrics.mph !== null && (() => {
      const lo = boneMetrics.mphLow, hi = boneMetrics.mphHigh, span = hi - lo;
      const marker = boneMetrics.predictedPah !== null ? boneMetrics.predictedPah : boneMetrics.mph;
      const pos = Math.min(Math.max((marker - lo) / span * 100, 1), 99);
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "14px", background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "relative", height: "10px", borderRadius: "99px", background: "#e9d5ff" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: "-3px", left: `${pos}%`, width: "16px", height: "16px", borderRadius: "50%", background: "white", border: "3px solid #7c3aed", transform: "translateX(-50%)", boxShadow: "0 1px 4px rgba(0,0,0,0.2)" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", fontWeight: "700", color: "#94a3b8" } }, /* @__PURE__ */ React.createElement("span", null, lo.toFixed(0), " cm"), /* @__PURE__ */ React.createElement("span", { style: { color: "#7c3aed" } }, "target range \xB18.5 cm", boneMetrics.predictedPah !== null ? " \xB7 marker = skeletal prediction" : ""), /* @__PURE__ */ React.createElement("span", null, hi.toFixed(0), " cm")));
    })(), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? "#f8fafc" : "#fffbeb", border: boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? "1px solid #e2e8f0" : "1px solid #fde68a", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b" } }, "Predicted Adult Height \xB7 TW3 skeletal"), boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "24px", fontWeight: "900", color: "#1e293b" } }, boneMetrics.predictedPah.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", color: "#94a3b8", marginLeft: "5px" } }, "cm"))), boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.predPct !== null ? `${boneMetrics.predPct.toFixed(1)}th centile \xB7 ` : "", boneMetrics.pct.toFixed(1), "% of adult height attained at bone age ", boneMetrics.ba.toFixed(1), " yr", boneMetrics.remaining !== null ? ` \xB7 ${boneMetrics.remaining.toFixed(1)} cm left to grow` : ""), boneMetrics.predVsTarget !== null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "700", marginTop: "8px", color: boneMetrics.withinTarget ? "#059669" : "#d97706" } }, boneMetrics.predVsTarget >= 0 ? "+" : "", boneMetrics.predVsTarget.toFixed(1), " cm vs genetic target \xB7 ", boneMetrics.withinTarget ? "within" : "outside", " mid-parental channel")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#92400e", lineHeight: "1.7", marginTop: "4px" } }, /* @__PURE__ */ React.createElement("strong", null, "Calibration required \u2014 no value shown by design."), " A skeletal prediction needs the licensed TW3 \u201C% of adult height attained by bone age\u201D reference (or another validated method) in ", /* @__PURE__ */ React.createElement("code", null, "TW3_CONFIG.pctAdultHeight"), ". The mid-parental target above is a ", /* @__PURE__ */ React.createElement("em", null, "genetic target"), ", not a prediction, and is never substituted here.")), /* @__PURE__ */ React.createElement("div", { className: "secondary-grid", style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Bone Age vs Chronological"), boneMetrics.hasBone ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "26px", fontWeight: "900", color: Math.abs(boneMetrics.diff) > 2 ? "#d97706" : "#1e293b", lineHeight: 1 } }, boneMetrics.diff >= 0 ? "+" : "", boneMetrics.diff.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "yr")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.diff > 1 ? "Advanced maturation" : boneMetrics.diff < -1 ? "Delayed maturation" : "Concordant with age")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, "No bone age set")), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Genetic Target on Khadilkar"), boneMetrics.mph !== null && boneMetrics.mphZ !== null ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "26px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, boneMetrics.mphZ >= 0 ? "+" : "", boneMetrics.mphZ.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "SDS")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.mphPct.toFixed(1), "th percentile \xB7 target vs ", evalGender === "boys" ? "male" : "female", " adult (", boneMetrics.adult[0], " cm)")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, "Add parents' heights for target SDS"))), /* @__PURE__ */ React.createElement(
      MetricRow,
      {
        label: "Current Height",
        value: height !== "" ? evalHeight.toFixed(1) : "\u2014",
        unit: "cm",
        sub: age !== "" ? `Chronological age ${evalAge.toFixed(1)} yr` : "Chronological age not entered"
      }
    )), /* @__PURE__ */ React.createElement("details", { className: "clinical-notes" }, /* @__PURE__ */ React.createElement("summary", null, "Clinical notes \xB7 TW3 workflow & Indian-population context"), /* @__PURE__ */ React.createElement("div", { className: "clinical-notes-body" }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#4338ca", lineHeight: "1.7", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("strong", null, "TW3 workflow:"), " use a ", /* @__PURE__ */ React.createElement("strong", null, "left"), " hand\u2013wrist PA radiograph. Stage all ", /* @__PURE__ */ React.createElement("strong", null, "20 bones"), " \u2014 13 RUS (radius, ulna, metacarpals 1\xB73\xB75, proximal/middle/distal phalanges 1\xB73\xB75) and 7 carpals \u2014 with the original TW3 letters A\u2192I. RUS and carpal maturity scores convert to ", /* @__PURE__ */ React.createElement("strong", null, "separate"), " bone ages (never averaged). Two independent reads within \xB10.5 yr is acceptable. Bayley\u2013Pinneau and Greulich\u2013Pyle are ", /* @__PURE__ */ React.createElement("strong", null, "not"), " used."), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#92400e", lineHeight: "1.7" } }, /* @__PURE__ */ React.createElement("strong", null, "Indian-population note:"), " No India-specific TW3 reference exists. In validation on Indian children, ", /* @__PURE__ */ React.createElement("strong", null, "TW3 was the most accurate"), " of the common methods (Shah et al., 2021, 851 children), which is why it is used here. However, skeletal maturation in Indian children differs from Western standards: boys run roughly ", /* @__PURE__ */ React.createElement("strong", null, "~6 months behind"), " and girls vary (delayed pre-puberty, sometimes advanced in early puberty) (Patel 2012; Khadilkar 2022). Scoring uses ", /* @__PURE__ */ React.createElement("strong", null, "TW3-C (Chinese)"), " tables as the closest freely-available reference \u2014 ", /* @__PURE__ */ React.createElement("strong", null, "no numeric correction is applied automatically"), ". Interpret borderline results, and ", /* @__PURE__ */ React.createElement("strong", null, "pubertal boys especially"), ", with clinical correlation."))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "18px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "TW3: Tanner, Healy, Goldstein & Cameron (2001) \u2014 licensed reference values required for scoring & skeletal height prediction. Mid-parental target: Tanner (open). Adult-height SDS/centile vs Khadilkar (WHO\u2013IAP) 18-yr reference. Clinician must verify \u2014 not a diagnostic device.")));
  }

  // frontend/src/panels/BoneAgePanel.jsx
  function BoneAgePanel() {
    const {
      DECLARABLE_FLAGS: DECLARABLE_FLAGS2,
      age,
      aiBusy,
      aiEstimate,
      assessment,
      boneAge,
      boneMetrics,
      boneReport,
      boxes,
      declaredFlags,
      estimateDomain,
      fbAge,
      fbBusy,
      fbConfidence,
      fbMethod,
      fbMsg,
      fbNote,
      fbRater,
      height,
      lcBtn,
      letterResult,
      loadLocalCohort,
      localCohort,
      lcohBusy,
      monitoring,
      radiograph,
      runEstimate,
      setEstimateDomain,
      setFbAge,
      setFbConfidence,
      setFbMethod,
      setFbNote,
      setFbRater,
      submitFeedback,
      toggleDeclaredFlag,
      tw3Config
    } = useBoneAge();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Bone Age \xB7 20-bone staging (13 RUS + 7 carpal)",
        subtitle: "TW3 scores RUS and carpal SEPARATELY and defines no combined 20-bone age (that is a TW2 construct) \u2014 all 20 are staged for per-bone visibility \xB7 letters A\u2013I, doctor-graded \xB7 Indian (Khadilkar) adult-height context",
        badge: boneMetrics && boneMetrics.hasBone ? "TW3 bone age set" : "Grade the film",
        badgeVariant: "info"
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "linear-gradient(135deg,#eef2ff,#faf5ff)", border: "1.5px solid #ddd6fe", borderRadius: "16px", padding: "18px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#6b21a8", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "10px" } }, "1 \xB7 Attach hand X\u2011ray \u2192 bone age"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("label", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "4px", padding: "18px 22px", border: "1.5px dashed #c7d2fe", borderRadius: "12px", background: "white", cursor: tw3Config && tw3Config.ai_estimate_available ? "pointer" : "not-allowed", textAlign: "center", minWidth: "190px" } }, /* @__PURE__ */ React.createElement("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "none", stroke: "#7c3aed", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }), /* @__PURE__ */ React.createElement("polyline", { points: "17 8 12 3 7 8" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "3", x2: "12", y2: "15" })), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "700", color: "#7c3aed" } }, "Attach left-hand film"), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10px", color: "#a78bfa" } }, "DICOM \xB7 PNG \xB7 JPEG \xB7 runs locally"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "file",
        accept: ".dcm,image/*",
        style: { display: "none" },
        disabled: !(tw3Config && tw3Config.ai_estimate_available),
        onChange: (e) => {
          const f = e.target.files && e.target.files[0];
          if (f) runEstimate(f);
          e.target.value = "";
        }
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "170px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Image source"), /* @__PURE__ */ React.createElement("select", { value: estimateDomain, onChange: (e) => setEstimateDomain(e.target.value), className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "11px" } }, IMAGE_DOMAINS.map(([v, label]) => /* @__PURE__ */ React.createElement("option", { key: v, value: v }, label))), /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", margin: "8px 0 3px" } }, "Declare image issues"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "4px" } }, DECLARABLE_FLAGS2.map(([code, label]) => {
      const on = declaredFlags.includes(code);
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: code,
          onClick: () => toggleDeclaredFlag(code),
          title: code,
          style: {
            fontSize: "10px",
            fontWeight: "700",
            padding: "2px 7px",
            borderRadius: "999px",
            cursor: "pointer",
            border: on ? "1px solid #dc2626" : "1px solid #cbd5e1",
            background: on ? "#fee2e2" : "white",
            color: on ? "#991b1b" : "#64748b"
          }
        },
        on ? "\u2715 " : "",
        label
      );
    })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", color: "#94a3b8", marginTop: "3px", lineHeight: "1.4" } }, "Any of these makes the AI estimate abstain \u2014 a whole-hand model can't read these films.")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, minWidth: "200px" } }, aiBusy && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#4338ca", fontWeight: "600" } }, "Analysing locally\u2026"), aiEstimate && aiEstimate.error && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b45309", fontWeight: "600" } }, aiEstimate.error), aiEstimate && aiEstimate.accepted === false && /* @__PURE__ */ React.createElement("div", { style: { background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "10px", padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: "#991b1b" } }, "\u26A0 Manual assessment required"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10.5px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.5" } }, aiEstimate.message), aiEstimate.quality && aiEstimate.quality.hard_flags.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#7f1d1d", marginTop: "5px", fontWeight: "700" } }, "Flags: ", aiEstimate.quality.hard_flags.map((f) => f.replace(/_/g, " ")).join(", ")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9.5px", color: "#94a3b8", marginTop: "5px" } }, "No AI age is shown \u2014 grade the bones manually below.")), aiEstimate && aiEstimate.available === false && aiEstimate.accepted !== false && aiEstimate.message && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#b45309", fontWeight: "600" } }, aiEstimate.message), aiEstimate && aiEstimate.bone_age_years != null && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#6b21a8", fontWeight: "700" } }, "AI screening estimate (Greulich\u2013Pyle, not TW3)"), /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", color: "#5b21b6", lineHeight: 1 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "34px" } }, aiEstimate.bone_age_years), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "14px" } }, "yr")), aiEstimate.ci_low_years != null && aiEstimate.ci_high_years != null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#7c3aed", fontWeight: "700", marginTop: "3px" } }, String(aiEstimate.interval_kind).startsWith("conformal") ? `${Math.round(parseFloat(aiEstimate.interval_coverage) * 100)}% interval` : "Likely range", " ", aiEstimate.ci_low_years, "\u2013", aiEstimate.ci_high_years, " yr", /* @__PURE__ */ React.createElement("span", { style: { fontWeight: "500", color: "#a78bfa" } }, " ", String(aiEstimate.interval_kind).startsWith("conformal") ? `(conformal \xB7 \xB1${aiEstimate.uncertainty_months} mo${aiEstimate.interval_group ? ` \xB7 ${aiEstimate.interval_group}` : ""}, held-out RSNA)` : `(\xB1${aiEstimate.uncertainty_months} mo MAE \u2014 approx, not calibrated)`)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#7c3aed", marginTop: "2px" } }, "Greulich\u2013Pyle whole-image \xB7 NOT TW3", aiEstimate.model_version ? ` \xB7 ${aiEstimate.model_version}` : ""), aiEstimate.range_warning && /* @__PURE__ */ React.createElement("div", { role: "alert", style: { fontSize: "10px", color: "#991b1b", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "7px", padding: "6px 8px", marginTop: "6px", lineHeight: "1.5" } }, "\u26A0 ", aiEstimate.range_warning), aiEstimate.quality_warning && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#b45309", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "7px", padding: "6px 8px", marginTop: "6px", lineHeight: "1.5" } }, "\u26A0 ", aiEstimate.quality_warning), (aiEstimate.image_domain_conflict || aiEstimate.image_domain_source === "auto-detected") && (() => {
      const conflict = aiEstimate.image_domain_conflict;
      const label = {
        film_photo: "photo of a film",
        compressed: "compressed export",
        digital_diagnostic: "digital radiograph",
        unknown: "undetermined"
      };
      const tone = conflict ? { bg: "#fef2f2", border: "#fecaca", head: "#991b1b", body: "#b91c1c" } : { bg: "#f8fafc", border: "#e2e8f0", head: "#334155", body: "#64748b" };
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", background: tone.bg, border: `1px solid ${tone.border}`, borderRadius: "7px", padding: "7px 9px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: tone.head } }, conflict ? "\u26A0 Declared source disagrees with the image" : `Image source detected: ${label[aiEstimate.image_domain] || aiEstimate.image_domain}`, !conflict && aiEstimate.image_domain_confidence && /* @__PURE__ */ React.createElement("span", { style: { fontWeight: "600", color: tone.body } }, " \xB7 ", aiEstimate.image_domain_confidence, " confidence")), conflict && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: tone.body, marginTop: "3px", lineHeight: "1.5" } }, "You marked this a digital radiograph; the file looks like a", " ", label[aiEstimate.image_domain_detected] || aiEstimate.image_domain_detected, ". Your declaration stands \u2014 the estimate is being treated as you marked it."), (aiEstimate.image_domain_evidence || []).length > 0 && /* @__PURE__ */ React.createElement("ul", { style: { margin: "4px 0 0 14px", padding: 0, fontSize: "9.5px", color: tone.body, lineHeight: "1.55" } }, aiEstimate.image_domain_evidence.map((e, i) => /* @__PURE__ */ React.createElement("li", { key: i }, e))), !conflict && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9.5px", color: tone.body, marginTop: "4px" } }, "Not what this is? Change ", /* @__PURE__ */ React.createElement("strong", null, "Image source"), " above \u2014 your choice always overrides the detection."));
    })(), aiEstimate.population_note && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b", marginTop: "6px", lineHeight: "1.5" } }, aiEstimate.population_note), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b", marginTop: "8px", lineHeight: "1.5" } }, "A screening cross-check only \u2014 it is not entered as the TW3 bone age. Grade the bones for the clinical result.")))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "14px", paddingTop: "14px", borderTop: "1px dashed #ddd6fe" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#6b21a8", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "8px" } }, "Is this right? Suggest the correct bone age"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("div", { style: { minWidth: "120px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Correct bone age (yr)"), /* @__PURE__ */ React.createElement("input", { type: "number", step: "0.1", min: "0", max: "25", value: fbAge, onChange: (e) => setFbAge(e.target.value), placeholder: "e.g. 11.5", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } })), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "130px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Method used"), /* @__PURE__ */ React.createElement("select", { value: fbMethod, onChange: (e) => setFbMethod(e.target.value), className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("option", { value: "tw3-rus" }, "TW3-RUS"), /* @__PURE__ */ React.createElement("option", { value: "greulich-pyle" }, "Greulich\u2013Pyle"), /* @__PURE__ */ React.createElement("option", { value: "clinical" }, "Clinical judgement"), /* @__PURE__ */ React.createElement("option", { value: "other" }, "Other"))), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "110px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Confidence"), /* @__PURE__ */ React.createElement("select", { value: fbConfidence, onChange: (e) => setFbConfidence(e.target.value), className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("option", { value: "high" }, "High"), /* @__PURE__ */ React.createElement("option", { value: "medium" }, "Medium"), /* @__PURE__ */ React.createElement("option", { value: "low" }, "Low"))), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "120px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Your initials / ID"), /* @__PURE__ */ React.createElement("input", { value: fbRater, onChange: (e) => setFbRater(e.target.value), placeholder: "e.g. DR", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } })), /* @__PURE__ */ React.createElement("button", { onClick: submitFeedback, disabled: fbBusy, style: { padding: "8px 14px", background: "#7c3aed", color: "white", border: "none", borderRadius: "8px", fontSize: "12px", fontWeight: "700", cursor: fbBusy ? "wait" : "pointer" } }, fbBusy ? "Saving\u2026" : "Submit suggestion")), /* @__PURE__ */ React.createElement("input", { value: fbNote, onChange: (e) => setFbNote(e.target.value), placeholder: "Optional note (e.g. which bones drove the difference)", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "11px", marginTop: "8px" } }), fbMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "11px", fontWeight: "700", color: fbMsg.type === "ok" ? "#16a34a" : "#b45309" } }, fbMsg.text), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "10px", color: "#a78bfa", lineHeight: 1.5 } }, "Your correction is logged as training evidence to improve accuracy over time. It does ", /* @__PURE__ */ React.createElement("strong", null, "not"), " change this patient's reported result.")), tw3Config && !tw3Config.ai_estimate_available && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8" } }, "Bone-age model not installed yet. To enable: ", /* @__PURE__ */ React.createElement("code", null, "python -m backend.ai.train_boneage")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#7c3aed", lineHeight: "1.5" } }, "Whole-image AI estimate \u2014 the clinician verifies each result. The full doctor-graded 20-bone TW3 workflow (grading, licensed tables, scores) is built and can be re-enabled when needed.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "18px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "10px" } }, "2 \xB7 Bone Age Report"), (() => {
      const L = letterResult || assessment && assessment.letters;
      const rusAge = L && L.rus ? L.rus.twiii_age_years : null;
      const carpalAge = L && L.carpal ? L.carpal.twiii_age_years : null;
      const aiYears = aiEstimate && aiEstimate.bone_age_years != null ? aiEstimate.bone_age_years : null;
      if (rusAge != null) return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#0f766e", textTransform: "uppercase", letterSpacing: ".05em" } }, "TW3 bone age \xB7 TWIII-RUS"), /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", color: "#0f766e", lineHeight: 1.1 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "34px" } }, rusAge), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "14px" } }, "yr"), carpalAge != null && /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#475569", fontWeight: "700" } }, "  \xB7  carpal ", carpalAge, " yr")));
      if (aiYears != null) return (
        // Secondary treatment: the whole-image AI is screening
        /* triage only, so it renders smaller and boxed -- clearly
           subordinate to the authoritative TW3 age above. */
        /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px", background: "#faf5ff", border: "1px dashed #d8b4fe", borderRadius: "10px", padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "9px", fontWeight: "800", color: "white", background: "#a78bfa", borderRadius: "99px", padding: "2px 7px", textTransform: "uppercase", letterSpacing: ".05em" } }, "AI screening"), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10px", fontWeight: "700", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em" } }, "Bone age \xB7 from X-ray")), /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", color: "#6b21a8", lineHeight: 1.1, marginTop: "4px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "26px" } }, aiYears), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px" } }, "yr")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#7c3aed", marginTop: "2px" } }, "Whole-image estimate", aiEstimate.ci_low_years != null ? ` \xB7 ${aiEstimate.interval_kind === "conformal" ? Math.round(parseFloat(aiEstimate.interval_coverage) * 100) + "% " : ""}${aiEstimate.ci_low_years}\u2013${aiEstimate.ci_high_years} yr` : "", " \u2014 not TW3; the clinician verifies. Grade the bones for the authoritative age."))
      );
      return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px", fontSize: "12px", color: "#94a3b8" } }, "Attach a left\u2011hand X\u2011ray above to get the bone age.");
    })(), (() => {
      const Lc = letterResult || assessment && assessment.letters;
      if (!Lc) return null;
      const rows = [
        ["TWIII \xB7 RUS", Lc.rus && Lc.rus.twiii_age_years, "#0f766e"],
        ["TWII \xB7 RUS", Lc.rus && Lc.rus.twii_age_years, "#0f766e"],
        ["TWII'20 \xB7 20-bone", Lc.tw20 && Lc.tw20.age_years, "#5b21b6"],
        ["TWIII \xB7 carpal", Lc.carpal && Lc.carpal.twiii_age_years, "#b45309"]
      ].filter((r) => r[1] != null);
      if (rows.length < 2) return null;
      return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "12px 14px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "8px" } }, "Standard comparison \xB7 same staging"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "8px" } }, rows.map(([label, age2, color]) => /* @__PURE__ */ React.createElement("div", { key: label, style: { background: "white", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "8px 10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", fontWeight: "800", color, textTransform: "uppercase", letterSpacing: ".04em" } }, label), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "20px", fontWeight: "900", color, lineHeight: 1.15 } }, age2, " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700" } }, "yr"))))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Differences reflect the scoring ", /* @__PURE__ */ React.createElement("strong", null, "standard / reference tables"), ", not the child's radiograph. RUS and carpal bone ages are reported separately \u2014 never averaged."));
    })(), (() => {
      const L = letterResult || assessment && assessment.letters;
      const tw3 = L && L.rus && L.rus.twiii_age_years != null ? L.rus.twiii_age_years : boneAge !== "" ? parseFloat(boneAge) : null;
      const gp = aiEstimate && aiEstimate.bone_age_years != null ? aiEstimate.bone_age_years : null;
      const carpal = L && L.carpal && L.carpal.twiii_age_years != null ? L.carpal.twiii_age_years : null;
      const rows = [
        ["TW3-RUS", tw3, "#0f766e"],
        ["GP model estimate", gp, "#6b21a8"],
        ["TW3 carpal", carpal, "#b45309"]
      ].filter((r) => r[1] != null && !isNaN(r[1]));
      if (rows.length < 2) return null;
      const vals = rows.map((r) => Number(r[1]));
      const spread = Math.max(...vals) - Math.min(...vals);
      const agree = spread <= 1;
      return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "14px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "8px" } }, "Cross-check \xB7 independent methods"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "8px" } }, rows.map(([label, age2, color], i) => /* @__PURE__ */ React.createElement("div", { key: label, style: { background: i === 0 ? "#f0fdfa" : "#faf5ff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "8px 10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", fontWeight: "800", color, textTransform: "uppercase", letterSpacing: ".04em" } }, label, i === 0 ? " \xB7 default" : ""), /* @__PURE__ */ React.createElement("div", { style: { fontSize: i === 0 ? "22px" : "18px", fontWeight: "900", color, lineHeight: 1.15 } }, Number(age2).toFixed(1), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700" } }, "yr"))))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", fontWeight: "700", color: agree ? "#16a34a" : "#b45309" } }, agree ? `\u2713 Methods agree \u2014 within ${spread.toFixed(1)} yr` : `\u26A0 Methods differ by ${spread.toFixed(1)} yr \u2014 re-check staging or image quality`), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "4px", fontSize: "10px", color: "#94a3b8", lineHeight: 1.5 } }, "TW3-RUS is the authoritative result. The others are an independent cross-check \u2014 agreement builds trust; disagreement usually means a mis-staged bone or a low-quality film."));
    })(), radiograph && /* @__PURE__ */ React.createElement("div", { style: { marginBottom: "12px", background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: "10px", padding: "10px 12px", fontSize: "11px", color: "#0f766e", lineHeight: "1.75" } }, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "800", textTransform: "uppercase", fontSize: "10px", letterSpacing: ".05em", marginBottom: "4px" } }, "Automated film analysis"), /* @__PURE__ */ React.createElement("div", null, "Image \xB7 ", radiograph.source_format || "\u2014", radiograph.width && radiograph.height ? ` \xB7 ${radiograph.width}\xD7${radiograph.height}` : "", " \xB7 laterality ", radiograph.laterality || "n/a", " \xB7 quality ", String(radiograph.quality_status || "\u2014").replace(/_/g, " "), radiograph.source_domain ? ` \xB7 ${String(radiograph.source_domain).replace(/_/g, " ")}` : ""), aiEstimate && aiEstimate.bone_age_years != null && /* @__PURE__ */ React.createElement("div", null, "AI whole-image estimate ", /* @__PURE__ */ React.createElement("span", { style: { color: "#64748b" } }, "(screening, not TW3)"), " \xB7 ", /* @__PURE__ */ React.createElement("strong", null, aiEstimate.bone_age_years, " yr"), aiEstimate.val_mae_months ? ` \xB7 \xB1~${Math.round(aiEstimate.val_mae_months)} mo` : ""), /* @__PURE__ */ React.createElement("div", null, "Bones auto-located \xB7 ", Object.keys(boxes).length, "/20", Object.keys(boxes).length === 0 ? " \u2014 draw boxes below, or train the localizer (backend/ai/LOCALIZE.md)" : ""), /* @__PURE__ */ React.createElement("div", null, "Per-bone TW3 stages \xB7 ", /* @__PURE__ */ React.createElement("strong", null, "doctor-graded below"), " ", /* @__PURE__ */ React.createElement("span", { style: { color: "#64748b" } }, "(automatic staging is the next AI step \u2014 needs the staging model)"))), /* @__PURE__ */ React.createElement("details", { style: { marginTop: "4px" }, open: true }, /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", fontSize: "11px", fontWeight: "700", color: "#7c3aed", listStyle: "none", padding: "4px 0" } }, "\u25B8 Detailed 20-bone report (per-bone staging \xB7 RUS & carpal kept separate)"), (() => {
      const rep = boneReport;
      const yrs = (v) => v === null || v === void 0 ? "\u2014" : v + " yr";
      const num = (v) => v === null || v === void 0 ? "\u2014" : v;
      const visChip = (v) => {
        const map = { STAGED: ["#dcfce7", "#166534"], NOT_VISIBLE: ["#fef3c7", "#92400e"], NOT_SCORABLE: ["#fee2e2", "#991b1b"], NOT_STAGED: ["#f1f5f9", "#94a3b8"] };
        const [bg, fg] = map[v] || map.NOT_STAGED;
        return /* @__PURE__ */ React.createElement("span", { style: { background: bg, color: fg, fontSize: "9px", fontWeight: "800", padding: "1px 6px", borderRadius: "999px", letterSpacing: "0.02em" } }, v.replace("_", " "));
      };
      const rows = rep ? rep.per_bone_results : [];
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px" } }, /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "11px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { textAlign: "left", color: "#64748b", borderBottom: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700" } }, "#"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700" } }, "Bone"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700" } }, "Sys"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700" } }, "Stage"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700" } }, "Visibility"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700", textAlign: "right" } }, "Points"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 6px", fontWeight: "700", textAlign: "right" } }, "% of max"))), /* @__PURE__ */ React.createElement("tbody", null, rows.map((b) => /* @__PURE__ */ React.createElement("tr", { key: b.bone_id, style: { borderBottom: "1px solid #f1f5f9", background: b.system === "CARPAL" ? "#fafafa" : "white" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", color: "#94a3b8" } }, b.display_order), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", fontWeight: "600", color: "#1e293b" } }, b.anatomical_name), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", color: "#64748b" } }, b.system === "CARPAL" ? "Carpal" : "RUS"), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", fontWeight: "700", color: "#5b21b6" } }, b.stage && !b.stage.startsWith("NOT_") ? b.stage : "\u2014"), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px" } }, visChip(b.visibility)), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", textAlign: "right", color: "#475569" } }, num(b.points)), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 6px", textAlign: "right", color: "#475569" } }, b.pct_of_bone_max != null ? b.pct_of_bone_max + "%" : "\u2014"))), rows.length === 0 && /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", { colSpan: "7", style: { padding: "10px 6px", color: "#94a3b8" } }, "Grade the bones below to build the report."))))), rep && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "10px", padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: "0.05em" } }, "RUS (13 bones)"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", marginTop: "4px" } }, "Staged ", rep.completeness.rus_staged, "/13 \xB7 score ", num(rep.rus.total_score)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "800", color: "#5b21b6", marginTop: "2px" } }, "TWIII age ", yrs(rep.rus.twiii_age_years), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10px", fontWeight: "600", color: "#94a3b8" } }, "\xB7 TWII ", yrs(rep.rus.twii_age_years)))), /* @__PURE__ */ React.createElement("div", { style: { background: "#fafafa", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" } }, "Carpal (7 bones) \xB7 separate"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#475569", marginTop: "4px" } }, "Staged ", rep.completeness.carpal_staged, "/7 \xB7 score ", num(rep.carpal.total_score)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "800", color: "#334155", marginTop: "2px" } }, "TWIII age ", yrs(rep.carpal.twiii_age_years), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10px", fontWeight: "600", color: "#94a3b8" } }, "\xB7 never averaged with RUS")))), rep && rep.scoring_note && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10px", color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "8px 10px", lineHeight: "1.5" } }, rep.scoring_note), rep && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, rep.mandatory_disclaimer));
    })())), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em" } }, "Local validation cohort"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "Films read independently by two clinicians, frozen and never used for training. This is the only measurement that describes accuracy on ", /* @__PURE__ */ React.createElement("em", null, "your"), " patients \u2014 published figures describe someone else's.")), /* @__PURE__ */ React.createElement("button", { onClick: loadLocalCohort, disabled: lcohBusy, style: lcBtn("#475569", lcohBusy) }, lcohBusy ? "Loading\u2026" : localCohort ? "Refresh" : "Load cohort")), localCohort && (() => {
      const sv = localCohort.survey || {};
      const ev = localCohort.evaluation || {};
      const strata = sv.strata || {};
      const target = localCohort.target_size || 0;
      const perStratum = localCohort.min_per_stratum || 0;
      const eligible = sv.n_eligible || 0;
      const pct = target ? Math.min(100, Math.round(eligible / target * 100)) : 0;
      const mo = (v) => v == null ? "\u2014" : `${v} mo`;
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "6px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155" } }, "Eligible films"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#64748b" } }, eligible, " of ", target, " \xB7 at least ", sv.min_readers || 2, " independent reads each")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", height: "8px", background: "#e2e8f0", borderRadius: "999px", overflow: "hidden" } }, /* @__PURE__ */ React.createElement("div", { style: { width: `${pct}%`, height: "100%", background: pct >= 100 ? "#059669" : "#6366f1" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "10px" } }, (localCohort.strata || []).map((name) => {
        const have = strata[name] || 0;
        const ok = have >= perStratum;
        return /* @__PURE__ */ React.createElement("div", { key: name, style: { flex: "1 1 120px", background: "white", border: `1px solid ${ok ? "#a7f3d0" : "#fecaca"}`, borderRadius: "8px", padding: "8px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b" } }, name.replace(":", " \xB7 ")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "16px", fontWeight: "800", color: ok ? "#059669" : "#b91c1c" } }, have, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "600", color: "#94a3b8" } }, " / ", perStratum)));
      })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "8px", lineHeight: "1.5" } }, "Every stratum needs its minimum before the cohort can be frozen. Published Indian data show TW3 is ", /* @__PURE__ */ React.createElement("strong", null, "worst of three methods in pubertal boys"), ", so a cohort thin in any stratum hides the subgroup that matters most.")), !sv.ready_to_freeze && (sv.reasons || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#92400e" } }, "Not ready to freeze"), /* @__PURE__ */ React.createElement("ul", { style: { margin: "6px 0 0 16px", padding: 0, fontSize: "10px", color: "#78350f", lineHeight: "1.6" } }, sv.reasons.map((r, i) => /* @__PURE__ */ React.createElement("li", { key: i }, r)))), sv.rejected && Object.values(sv.rejected).some((n) => n > 0) && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10px", color: "#64748b" } }, "Excluded: ", Object.entries(sv.rejected).filter(([, n]) => n > 0).map(([k, n]) => `${k.replace(/_/g, " ")} ${n}`).join(" \xB7 ")), ev.available ? /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 160px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#4338ca" } }, "Model error on your films"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "20px", fontWeight: "800", color: "#3730a3" } }, mo((ev.headline || {}).mae_months)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#6366f1" } }, (ev.provenance || {}).n_evaluated || 0, " films evaluated")), /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 160px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b" } }, "Disagreement between your readers"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "20px", fontWeight: "800", color: "#334155" } }, mo((ev.reader_disagreement || {}).mean_spread_months)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8" } }, "the floor this should be read against"))), (ev.interpretation || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "8px", padding: "10px" } }, ev.interpretation.map((line, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { fontSize: "11px", color: "#14532d", lineHeight: "1.6", marginTop: i ? "6px" : 0 } }, line))), ((ev.by_stratum || {}).subgroups || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "11px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { background: "#f8fafc" } }, /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "6px 8px", color: "#64748b", fontWeight: "700" } }, "Stratum"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px", color: "#64748b", fontWeight: "700" } }, "Films"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px", color: "#64748b", fontWeight: "700" } }, "MAE"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px", color: "#64748b", fontWeight: "700" } }, "Bias"))), /* @__PURE__ */ React.createElement("tbody", null, ev.by_stratum.subgroups.map((row, i) => {
        const name = (row.group || {}).stratum || "\u2014";
        const thin = (row.n || 0) < perStratum;
        return /* @__PURE__ */ React.createElement("tr", { key: i, style: { borderTop: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", color: "#334155" } }, name.replace(":", " \xB7 ")), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", textAlign: "right", color: thin ? "#b91c1c" : "#64748b" } }, row.n, thin ? " \u26A0" : ""), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", textAlign: "right", fontWeight: "700", color: "#334155" } }, mo(row.mae_months)), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", textAlign: "right", color: "#64748b" } }, row.signed_bias_months == null ? "\u2014" : `${row.signed_bias_months > 0 ? "+" : ""}${row.signed_bias_months} mo`));
      }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "6px", lineHeight: "1.5" } }, "\u26A0 marks a stratum below the minimum count \u2014 its figure is too imprecise to support a claim. The reference standard is a consensus of independent expert reads, ", /* @__PURE__ */ React.createElement("strong", null, "not ground truth"), "; a model inside the readers' own spread is within the band where the reference is uncertain, not better than the readers."))) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "8px", padding: "10px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "700", color: "#475569" } }, "No local accuracy figure yet"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b", marginTop: "4px", lineHeight: "1.5" } }, ev.reason || "Freeze the cohort once every stratum is complete.")));
    })()), /* @__PURE__ */ React.createElement(BoneAgeAdvanced, null));
  }

  // frontend/src/panels/RecordPanel.jsx
  var { useState: useState5, useEffect: useEffect4, useCallback, useRef: useRef2 } = React;
  async function api(url, init) {
    const r = await fetch(url, init);
    const data = await r.json().catch(() => null);
    const detail = data && data.detail;
    return {
      ok: r.ok,
      status: r.status,
      data,
      error: r.ok ? null : typeof detail === "string" ? detail : `HTTP ${r.status}`
    };
  }
  var json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  var TRIAGE = {
    routine_monitoring: { label: "Routine monitoring", variant: "mid" },
    discuss_with_paediatrician: { label: "Discuss with paediatrician", variant: "mid" },
    specialist_soon: { label: "Specialist review soon", variant: "high" }
  };
  var SEVERITY = {
    urgent: { label: "Urgent", variant: "high" },
    attention: { label: "Attention", variant: "mid" },
    info: { label: "Info", variant: "info" },
    insufficient_data: { label: "Not assessed", variant: "neutral" }
  };
  var OBS_LABEL = {
    height: "Height",
    weight: "Weight",
    bmi: "BMI",
    head_circumference: "Head circ.",
    sitting_height: "Sitting height",
    arm_span: "Arm span",
    systolic_bp: "Systolic BP",
    diastolic_bp: "Diastolic BP"
  };
  var card = { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "14px 16px", marginTop: "14px" };
  var h4 = { fontSize: "10px", fontWeight: 800, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" };
  var btn = (bg, disabled) => ({
    padding: "7px 14px",
    background: disabled ? "#cbd5e1" : bg,
    color: "white",
    border: "none",
    borderRadius: "9px",
    fontSize: "12px",
    fontWeight: 700,
    cursor: disabled ? "not-allowed" : "pointer"
  });
  var numOrBlank = (e) => e.target.value === "" ? "" : parseFloat(e.target.value);
  var plain = (text) => String(text || "").replace(/^implausible_decrease:\s*/, "").replace(/\s*Re-check, or resubmit with allow_implausible_change=true\.?/, " Re-check the measurement.");
  function RecordPanel() {
    const {
      patientMrn,
      patientName,
      examDate,
      sexEntered,
      dob,
      height,
      weight,
      systolic,
      diastolic,
      heightOk,
      weightOk,
      bpOk
    } = useRecord();
    const [record, setRecord] = useState5(null);
    const [notFound, setNotFound] = useState5(false);
    const [timeline, setTimeline] = useState5(null);
    const [assessment, setAssessment] = useState5(null);
    const [msg, setMsg] = useState5(null);
    const [busy, setBusy] = useState5(false);
    const [ctx, setCtx] = useState5({
      mother_height_cm: "",
      father_height_cm: "",
      parental_height_source: "",
      gestational_age_weeks: "",
      birth_weight_g: ""
    });
    const [pub, setPub] = useState5({
      breast_stage: "",
      genital_stage: "",
      pubic_hair_stage: "",
      testicular_volume_ml: "",
      menarche_date: ""
    });
    const [extra, setExtra] = useState5({ head_circumference: "", sitting_height: "", arm_span: "" });
    const [parentSummary, setParentSummary] = useState5(null);
    const mrnRef = useRef2(patientMrn);
    mrnRef.current = patientMrn;
    const recordIdRef = useRef2(null);
    useEffect4(() => {
      recordIdRef.current = null;
      setRecord(null);
      setNotFound(false);
      setTimeline(null);
      setAssessment(null);
      setMsg(null);
      setParentSummary(null);
    }, [patientMrn]);
    const loadDetails = useCallback(async (id) => {
      const [t, a] = await Promise.all([
        api(`/api/patients/${id}/timeline`),
        api(`/api/clinical/patients/${id}/assessment`)
      ]);
      if (recordIdRef.current !== id) return;
      if (t.ok) setTimeline(t.data);
      if (a.ok) setAssessment(a.data);
      if (!t.ok || !a.ok) setMsg({ type: "err", text: t.error || a.error });
    }, []);
    const adopt = (p) => {
      recordIdRef.current = p.id;
      setRecord(p);
      setNotFound(false);
      setParentSummary(null);
      setCtx({
        mother_height_cm: p.mother_height_cm ?? "",
        father_height_cm: p.father_height_cm ?? "",
        parental_height_source: p.parental_height_source ?? "",
        gestational_age_weeks: p.gestational_age_weeks ?? "",
        birth_weight_g: p.birth_weight_g ?? ""
      });
      loadDetails(p.id);
    };
    const openRecord = async () => {
      if (!patientMrn.trim()) {
        setMsg({ type: "err", text: "Enter the MRN in the patient bar first." });
        return;
      }
      setBusy(true);
      setMsg(null);
      const code = patientMrn.trim();
      const r = await api("/api/patients/lookup", json("POST", { code }));
      setBusy(false);
      if (mrnRef.current.trim() !== code) return;
      if (r.status === 404) {
        setRecord(null);
        setNotFound(true);
        return;
      }
      if (!r.ok) {
        setMsg({ type: "err", text: r.error });
        return;
      }
      adopt(r.data);
    };
    const createRecord = async () => {
      if (!sexEntered || !dob) {
        setMsg({ type: "err", text: "Creating a record needs biological sex and date of birth (not just age) in Demographics." });
        return;
      }
      if (!window.confirm(`Create a new record for MRN ${patientMrn.trim()} (${sexEntered === "boys" ? "male" : "female"}, born ${dob})?`)) return;
      setBusy(true);
      setMsg(null);
      const r = await api("/api/patients", json("POST", {
        patient_code: patientMrn.trim(),
        sex: sexEntered,
        date_of_birth: `${dob}T00:00:00`,
        name: patientName.trim() || null
      }));
      setBusy(false);
      if (!r.ok) {
        setMsg({ type: "err", text: r.error });
        return;
      }
      adopt(r.data);
      setMsg({ type: "ok", text: "Record created." });
    };
    const mismatches = [];
    if (record) {
      if (!sexEntered)
        mismatches.push("select biological sex in Demographics to confirm this is the right child");
      else if (record.sex_at_birth !== sexEntered)
        mismatches.push(`sex: record ${record.sex_at_birth === "boys" ? "male" : "female"}, screen ${sexEntered === "boys" ? "male" : "female"}`);
      if (dob && record.date_of_birth && record.date_of_birth !== dob)
        mismatches.push(`date of birth: record ${record.date_of_birth}, screen ${dob}`);
    }
    const writable = !!record && mismatches.length === 0 && !busy;
    const visitValues = {
      height: heightOk ? height : null,
      weight: weightOk ? weight : null,
      systolic_bp: bpOk ? systolic : null,
      diastolic_bp: bpOk ? diastolic : null,
      head_circumference: extra.head_circumference === "" ? null : extra.head_circumference,
      sitting_height: extra.sitting_height === "" ? null : extra.sitting_height,
      arm_span: extra.arm_span === "" ? null : extra.arm_span
    };
    const visitEntries = Object.entries(visitValues).filter(([, v]) => v !== null);
    const saveVisit = async (allowDrop = false) => {
      if (!writable || !examDate) return;
      setBusy(true);
      setMsg(null);
      const r = await api(`/api/patients/${record.id}/visits`, json("POST", {
        observed_at: `${examDate}T00:00:00`,
        allow_implausible_change: allowDrop,
        ...visitValues
      }));
      setBusy(false);
      if (!r.ok) {
        if (!allowDrop && /implausible_decrease/.test(r.error || "") && window.confirm(`${plain(r.error)}

Save anyway? Only if you have re-measured and the value is correct.`)) {
          return saveVisit(true);
        }
        setMsg({ type: "err", text: plain(r.error) });
        return;
      }
      const warn = r.data.warnings.length ? ` Warnings: ${r.data.warnings.join("; ")}` : "";
      setMsg({ type: warn ? "warn" : "ok", text: `Visit of ${examDate} saved (${r.data.saved.map((s) => s.obs_type).join(", ")}).${warn}` });
      setExtra({ head_circumference: "", sitting_height: "", arm_span: "" });
      loadDetails(record.id);
    };
    const saveContext = async () => {
      if (!writable) return;
      const body = {};
      Object.entries(ctx).forEach(([k, v]) => {
        body[k] = v === "" ? null : v;
      });
      setBusy(true);
      setMsg(null);
      const r = await api(`/api/patients/${record.id}`, json("PATCH", body));
      setBusy(false);
      if (!r.ok) {
        setMsg({ type: "err", text: r.error });
        return;
      }
      adopt(r.data);
      setMsg({ type: "ok", text: "Clinical context saved." });
    };
    const savePuberty = async () => {
      if (!writable || !examDate) return;
      const body = { assessed_at: `${examDate}T00:00:00` };
      Object.entries(pub).forEach(([k, v]) => {
        if (v === "") return;
        body[k] = k === "menarche_date" ? `${v}T00:00:00` : Number(v);
      });
      if (Object.keys(body).length === 1) {
        setMsg({ type: "err", text: "Enter at least one Tanner stage." });
        return;
      }
      setBusy(true);
      setMsg(null);
      const r = await api(`/api/patients/${record.id}/puberty`, json("POST", body));
      setBusy(false);
      if (!r.ok) {
        setMsg({ type: "err", text: r.error });
        return;
      }
      setPub({ breast_stage: "", genital_stage: "", pubic_hair_stage: "", testicular_volume_ml: "", menarche_date: "" });
      setMsg({ type: "ok", text: `Puberty assessment of ${examDate} saved.` });
      loadDetails(record.id);
    };
    const releaseParentSummary = async () => {
      if (!record) return;
      if (!window.confirm("Generate the plain-language summary for the parent? Release it only after you have reviewed the findings yourself.")) return;
      const r = await api(`/api/clinical/patients/${record.id}/parent-summary?release=true`);
      if (!r.ok) {
        setMsg({ type: "err", text: r.error });
        return;
      }
      setParentSummary(r.data);
    };
    const isGirl = record ? record.sex_at_birth === "girls" : sexEntered === "girls";
    const stageSelect = (key, label) => /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, label), /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "input-field",
        style: { width: "100%" },
        value: pub[key],
        onChange: (e) => setPub((p) => ({ ...p, [key]: e.target.value }))
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014"),
      [1, 2, 3, 4, 5].map((n) => /* @__PURE__ */ React.createElement("option", { key: n, value: n }, "Tanner ", n))
    ));
    const triage = assessment && TRIAGE[assessment.triage.level];
    const findings = assessment ? assessment.findings.filter((f) => f.severity !== "insufficient_data") : [];
    const notAssessed = assessment ? assessment.findings.filter((f) => f.severity === "insufficient_data") : [];
    const ah = assessment && assessment.adult_height;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Patient Record \xB7 Growth history, findings & triage",
        subtitle: "Saved visits, growth velocity, Tanner staging and the clinical rules engine",
        badge: triage ? triage.label : null,
        badgeVariant: triage ? triage.variant : "info"
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { ...card, display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#334155", flex: "1 1 200px" } }, record ? /* @__PURE__ */ React.createElement(React.Fragment, null, "Record ", /* @__PURE__ */ React.createElement("strong", null, record.patient_code), " \xB7 ", record.sex_at_birth === "boys" ? "Male" : "Female", " \xB7 born ", record.date_of_birth || "unknown") : /* @__PURE__ */ React.createElement(React.Fragment, null, "MRN in patient bar: ", /* @__PURE__ */ React.createElement("strong", null, patientMrn.trim() || "\u2014"))), /* @__PURE__ */ React.createElement("button", { onClick: openRecord, disabled: busy || !patientMrn.trim(), style: btn("#4f46e5", busy || !patientMrn.trim()) }, record ? "Reload" : "Open record"), notFound && /* @__PURE__ */ React.createElement("button", { onClick: createRecord, disabled: busy, style: btn("#0f766e", busy) }, "Create record")), notFound && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#64748b", marginTop: "6px" } }, "No record with this MRN. Check the MRN before creating a new one."), msg && /* @__PURE__ */ React.createElement("div", { role: "status", style: {
      marginTop: "10px",
      fontSize: "12px",
      lineHeight: 1.5,
      borderRadius: "8px",
      padding: "8px 12px",
      background: msg.type === "err" ? "#fef2f2" : msg.type === "warn" ? "#fffbeb" : "#f0fdf4",
      color: msg.type === "err" ? "#991b1b" : msg.type === "warn" ? "#92400e" : "#166534"
    } }, msg.text), mismatches.length > 0 && /* @__PURE__ */ React.createElement("div", { role: "alert", style: { marginTop: "10px", background: "#fef2f2", border: "1.5px solid #fca5a5", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#991b1b", lineHeight: 1.6 } }, /* @__PURE__ */ React.createElement("strong", null, "Nothing can be saved until the record is confirmed"), " (", mismatches.join("; "), "). If the details genuinely differ, check the MRN \u2014 the wrong record may be open."), !record ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Open a patient record",
        hint: "Enter the MRN in the patient bar and open the record \u2014 or create one (needs sex and date of birth). Visits, velocity, Tanner staging, findings and triage then appear here."
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, assessment && /* @__PURE__ */ React.createElement("div", { style: { ...card, background: triage && triage.variant === "high" ? "#fff1f2" : "#fffbeb", borderColor: triage && triage.variant === "high" ? "#fecaca" : "#fde68a" } }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Triage"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: triage.label, variant: triage.variant }), assessment.triage.specialties.length > 0 && /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", color: "#475569" } }, "\u2192 ", assessment.triage.specialties.join(", "))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#334155", marginTop: "8px", lineHeight: 1.6 } }, assessment.triage.guidance), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10.5px", color: "#64748b", marginTop: "6px" } }, assessment.disclaimer)), assessment && /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Findings ", assessment.as_of_age_years != null && `\xB7 as of ${assessment.as_of_age_years} y`), findings.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#475569" } }, "No rule fired on the recorded data. This is not an all-clear: see what could not be assessed below.") : findings.map((f) => /* @__PURE__ */ React.createElement("div", { key: f.rule_id, style: { padding: "8px 0", borderBottom: "1px solid #eef2f7" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: SEVERITY[f.severity].label, variant: SEVERITY[f.severity].variant }), /* @__PURE__ */ React.createElement("strong", { style: { fontSize: "12.5px", color: "#1e293b" } }, f.title), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10px", color: "#94a3b8" } }, "confidence: ", f.confidence)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11.5px", color: "#475569", marginTop: "4px", lineHeight: 1.55 } }, f.rationale), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "3px" } }, "Source: ", f.source))), notAssessed.length > 0 && /* @__PURE__ */ React.createElement("details", { style: { marginTop: "8px" } }, /* @__PURE__ */ React.createElement("summary", { style: { fontSize: "11px", fontWeight: 700, color: "#64748b", cursor: "pointer" } }, "Not assessed \u2014 missing data (", notAssessed.length, ")"), /* @__PURE__ */ React.createElement("ul", { style: { margin: "6px 0 0", paddingLeft: "18px", fontSize: "11px", color: "#64748b", lineHeight: 1.6 } }, notAssessed.map((f) => /* @__PURE__ */ React.createElement("li", { key: f.rule_id }, f.title, f.rationale ? ` \u2014 ${f.rationale}` : ""))))), ah && /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Adult height \u2014 three different quantities"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#334155", lineHeight: 1.7 } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, ah.genetic_target ? ah.genetic_target.label : "Mid-parental target", ":"), " ", ah.genetic_target ? `${ah.genetic_target.target_cm.toFixed(1)} cm (range ${ah.genetic_target.range_cm[0].toFixed(0)}\u2013${ah.genetic_target.range_cm[1].toFixed(0)}; parental heights ${ah.genetic_target.parental_height_source})` : "needs both parents\u2019 heights"), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, ah.predicted_adult_height.label, ":"), " ", ah.predicted_adult_height.available ? `${ah.predicted_adult_height.predicted_cm.toFixed(1)} \xB1 ${ah.predicted_adult_height.interval_cm} cm` : ah.predicted_adult_height.status), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, ah.from_bone_age.label, ":"), " ", ah.from_bone_age.available ? `${ah.from_bone_age.predicted_cm} cm` : ah.from_bone_age.status || ah.from_bone_age.reason || "not available")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10.5px", color: "#94a3b8", marginTop: "6px", lineHeight: 1.5 } }, ah.note)), /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Record this visit \xB7 exam date ", examDate || "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11.5px", color: "#475569", marginBottom: "8px" } }, "From Demographics / Labs: ", visitEntries.filter(([k]) => ["height", "weight", "systolic_bp", "diastolic_bp"].includes(k)).map(([k, v]) => `${OBS_LABEL[k]} ${v}`).join(" \xB7 ") || "nothing entered yet", height !== "" && !heightOk || weight !== "" && !weightOk || (systolic !== "" || diastolic !== "") && !bpOk ? " \xB7 implausible values are not sent" : ""), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Head circumference",
        value: extra.head_circumference,
        unit: "cm",
        step: "0.1",
        onChange: (e) => setExtra((x) => ({ ...x, head_circumference: numOrBlank(e) }))
      }
    ), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Sitting height",
        value: extra.sitting_height,
        unit: "cm",
        step: "0.1",
        onChange: (e) => setExtra((x) => ({ ...x, sitting_height: numOrBlank(e) }))
      }
    ), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Arm span",
        value: extra.arm_span,
        unit: "cm",
        step: "0.1",
        onChange: (e) => setExtra((x) => ({ ...x, arm_span: numOrBlank(e) }))
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => saveVisit(false),
        disabled: !writable || !examDate || visitEntries.length === 0,
        style: btn("#4f46e5", !writable || !examDate || visitEntries.length === 0)
      },
      "Save visit"
    ), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "10.5px", color: "#94a3b8", marginLeft: "8px" } }, "Saved together or not at all \xB7 BMI is derived by the server"))), /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Tanner staging \xB7 exam date ", examDate || "\u2014"), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, isGirl ? stageSelect("breast_stage", "Breast (B)") : stageSelect("genital_stage", "Genital (G)"), stageSelect("pubic_hair_stage", "Pubic hair (PH)"), isGirl ? /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Menarche date (if reached)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "date",
        className: "input-field",
        style: { width: "100%" },
        value: pub.menarche_date,
        max: (/* @__PURE__ */ new Date()).toISOString().split("T")[0],
        onChange: (e) => setPub((p) => ({ ...p, menarche_date: e.target.value }))
      }
    )) : /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Testicular volume",
        value: pub.testicular_volume_ml,
        unit: "mL",
        step: "1",
        onChange: (e) => setPub((p) => ({ ...p, testicular_volume_ml: e.target.value }))
      }
    )), /* @__PURE__ */ React.createElement("button", { onClick: savePuberty, disabled: !writable || !examDate, style: { ...btn("#7c3aed", !writable || !examDate), marginTop: "10px" } }, "Save Tanner staging")), /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Clinical context (used by the target-height, SGA and puberty rules)"), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Mother's height",
        value: ctx.mother_height_cm,
        unit: "cm",
        step: "0.1",
        onChange: (e) => setCtx((c) => ({ ...c, mother_height_cm: numOrBlank(e) })),
        problem: rangeProblem("parentHeight", ctx.mother_height_cm)
      }
    ), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Father's height",
        value: ctx.father_height_cm,
        unit: "cm",
        step: "0.1",
        onChange: (e) => setCtx((c) => ({ ...c, father_height_cm: numOrBlank(e) })),
        problem: rangeProblem("parentHeight", ctx.father_height_cm)
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Parental heights were"), /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "input-field",
        style: { width: "100%" },
        value: ctx.parental_height_source,
        onChange: (e) => setCtx((c) => ({ ...c, parental_height_source: e.target.value }))
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014"),
      /* @__PURE__ */ React.createElement("option", { value: "measured" }, "Measured"),
      /* @__PURE__ */ React.createElement("option", { value: "reported" }, "Reported (less reliable)")
    )), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Gestational age at birth",
        value: ctx.gestational_age_weeks,
        unit: "wk",
        step: "0.1",
        onChange: (e) => setCtx((c) => ({ ...c, gestational_age_weeks: numOrBlank(e) }))
      }
    ), /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Birth weight",
        value: ctx.birth_weight_g,
        unit: "g",
        step: "10",
        onChange: (e) => setCtx((c) => ({ ...c, birth_weight_g: numOrBlank(e) }))
      }
    )), /* @__PURE__ */ React.createElement("button", { onClick: saveContext, disabled: !writable, style: { ...btn("#0f766e", !writable), marginTop: "10px" } }, "Save clinical context")), timeline && /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Measurement history"), Object.keys(timeline.observations).length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#64748b" } }, "No measurements recorded yet.") : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { borderCollapse: "collapse", fontSize: "11.5px", width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { color: "#64748b", textAlign: "left" } }, /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 8px" } }, "Measure"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 8px" } }, "Date"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 8px" } }, "Age"), /* @__PURE__ */ React.createElement("th", { style: { padding: "4px 8px" } }, "Value"))), /* @__PURE__ */ React.createElement("tbody", null, Object.entries(timeline.observations).flatMap(([k, rows]) => rows.map((r) => /* @__PURE__ */ React.createElement("tr", { key: r.id, style: { borderTop: "1px solid #eef2f7" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px" } }, OBS_LABEL[k] || k, r.method === "derived" ? " (derived)" : ""), /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px" } }, r.observed_at.slice(0, 10)), /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px" } }, r.age_years != null ? `${r.age_years.toFixed(2)} y` : "\u2014"), /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", fontWeight: 700 } }, r.value, " ", r.unit))))))), timeline.velocities && timeline.velocities.height && timeline.velocities.height.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Height velocity"), timeline.velocities.height.map((v, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { fontSize: "11.5px", color: "#334155", padding: "2px 0" } }, v.from_age_years != null ? `${v.from_age_years.toFixed(2)}\u2013${v.to_age_years.toFixed(2)} y: ` : "", v.available && v.velocity_per_year != null ? /* @__PURE__ */ React.createElement("strong", null, v.velocity_per_year.toFixed(1), " cm/yr") : v.status || "not computable", v.velocity_sds != null ? ` \xB7 SDS ${v.velocity_sds.toFixed(2)}` : "", v.flags && v.flags.length ? ` \xB7 ${v.flags.join(", ")}` : "")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "4px" } }, "Velocity centiles need the Indian velocity reference, not yet installed; rates are shown without a centile rather than against an invented one.")), timeline.puberty.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Tanner history"), timeline.puberty.map((p, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { fontSize: "11.5px", color: "#334155", padding: "2px 0" } }, p.assessed_at.slice(0, 10), ": ", [
      p.breast_stage && `B${p.breast_stage}`,
      p.genital_stage && `G${p.genital_stage}`,
      p.pubic_hair_stage && `PH${p.pubic_hair_stage}`,
      p.testicular_volume_ml && `${p.testicular_volume_ml} mL`,
      p.menarche_date && `menarche ${p.menarche_date.slice(0, 10)}`
    ].filter(Boolean).join(" \xB7 "))))), /* @__PURE__ */ React.createElement("div", { style: card }, /* @__PURE__ */ React.createElement("div", { style: h4 }, "Parent summary (clinician release)"), !parentSummary ? /* @__PURE__ */ React.createElement("button", { onClick: releaseParentSummary, style: btn("#475569", false) }, "Review & release summary\u2026") : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#334155", lineHeight: 1.7 } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, "What was looked at:"), " ", parentSummary.what_was_looked_at), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, "What was noticed:"), " ", parentSummary.what_was_noticed.join(" ")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, "What to do:"), " ", parentSummary.what_to_do), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("strong", null, "Questions to ask:"), " ", parentSummary.questions_to_ask.join(" ")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#92400e", marginTop: "4px" } }, parentSummary.important)))));
  }

  // frontend/src/app.jsx
  var { useState: useState6, useMemo, useEffect: useEffect5, useRef: useRef3 } = React;
  function App() {
    const [activeTab, setActiveTab] = useState6("overview");
    const [growthChartMeasure, setGrowthChartMeasure] = useState6("combined");
    const [showChart, setShowChart] = useState6(false);
    const [patientName, setPatientName] = useState6("");
    const [patientMrn, setPatientMrn] = useState6("");
    const [examDate, setExamDate] = useState6(() => (/* @__PURE__ */ new Date()).toISOString().split("T")[0]);
    const [growthSeries, setGrowthSeries] = useState6({
      boys: { height: null, weight: null, bmi: null },
      girls: { height: null, weight: null, bmi: null }
    });
    const [growthSeriesLoading, setGrowthSeriesLoading] = useState6(true);
    const [growthPoint, setGrowthPoint] = useState6({ height: null, weight: null, bmi: null });
    const [growthBmiCutoffs, setGrowthBmiCutoffs] = useState6(null);
    const [adultHeightStats, setAdultHeightStats] = useState6(null);
    const [age, setAge] = useState6("");
    const [dob, setDob] = useState6("");
    const [gender, setGender] = useState6("");
    const [height, setHeight] = useState6("");
    const [weight, setWeight] = useState6("");
    const [creatinine, setCreatinine] = useState6("");
    const [albuminuria, setAlbuminuria] = useState6("");
    const [systolic, setSystolic] = useState6("");
    const [diastolic, setDiastolic] = useState6("");
    const [ast, setAst] = useState6("");
    const [alt, setAlt] = useState6("");
    const [platelets, setPlatelets] = useState6("");
    const [fraxMofEntered, setFraxMofEntered] = useState6("");
    const [fraxHfEntered, setFraxHfEntered] = useState6("");
    const [timeline, setTimeline] = useState6([]);
    const boneAgeState = useBoneAgeState();
    const {
      DECLARABLE_FLAGS: DECLARABLE_FLAGS2,
      boneAge,
      setBoneAge,
      boneAgeSource,
      setBoneAgeSource,
      rusStages,
      setRusStages,
      carpalStages,
      setCarpalStages,
      tw3Config,
      setTw3Config,
      letterResult,
      setLetterResult,
      boneReport,
      setBoneReport,
      patientCode,
      setPatientCode,
      assessment,
      setAssessment,
      lcMsg,
      setLcMsg,
      lcBusy,
      setLcBusy,
      showAudit,
      setShowAudit,
      radiograph,
      setRadiograph,
      coverage,
      setCoverage,
      covBusy,
      setCovBusy,
      monitoring,
      setMonitoring,
      monBusy,
      setMonBusy,
      localCohort,
      setLocalCohort,
      lcohBusy,
      setLcohBusy,
      adjItems,
      setAdjItems,
      adjBusy,
      setAdjBusy,
      adjReviewer,
      setAdjReviewer,
      adjMsg,
      setAdjMsg,
      ltTables,
      setLtTables,
      ltStatus,
      setLtStatus,
      ltSection,
      setLtSection,
      ltSex,
      setLtSex,
      ltMsg,
      setLtMsg,
      ltBusy,
      setLtBusy,
      boxes,
      setBoxes,
      locImg,
      setLocImg,
      locBusy,
      setLocBusy,
      locMsg,
      setLocMsg,
      selBone,
      setSelBone,
      locDrag,
      locRef,
      boxesRef,
      aiEstimate,
      setAiEstimate,
      estimateDomain,
      setEstimateDomain,
      declaredFlags,
      setDeclaredFlags,
      lastFilm,
      setLastFilm,
      fbAge,
      setFbAge,
      fbMethod,
      setFbMethod,
      fbConfidence,
      setFbConfidence,
      fbRater,
      setFbRater,
      fbNote,
      setFbNote,
      fbMsg,
      setFbMsg,
      fbBusy,
      setFbBusy,
      aiBusy,
      setAiBusy,
      fatherHeight,
      setFatherHeight,
      motherHeight,
      setMotherHeight
    } = boneAgeState;
    const {
      ethnicity,
      setEthnicity,
      smokeCat,
      setSmokeCat,
      diabetes,
      setDiabetes,
      cholRatio,
      setCholRatio,
      sbpSD,
      setSbpSD,
      qAF,
      setQAF,
      qTreatedHtn,
      setQTreatedHtn,
      qRA,
      setQRA,
      qCKD,
      setQCKD,
      qMigraine,
      setQMigraine,
      qSLE,
      setQSLE,
      qSMI,
      setQSMI,
      qAtypAntipsy,
      setQAtypAntipsy,
      qCortico,
      setQCortico,
      qED,
      setQED,
      qFhCvd,
      setQFhCvd
    } = useQriskInputs();
    const evalAge = useMemo(() => age !== "" ? parseFloat(age) : 9, [age]);
    const ageParts = useMemo(() => computeAgeParts(dob), [dob]);
    const handleDobChange = (e) => {
      const v = e.target.value;
      setDob(v);
      const p = computeAgeParts(v);
      if (p) setAge(Math.round(p.decimal * 10) / 10);
    };
    const handleAgeChange = (e) => {
      setAge(e.target.value === "" ? "" : parseFloat(e.target.value));
      if (dob) setDob("");
    };
    const evalGender = useMemo(() => gender !== "" ? gender : "girls", [gender]);
    const evalHeight = useMemo(() => height !== "" ? parseFloat(height) : 131.5, [height]);
    const evalWeight = useMemo(() => weight !== "" ? parseFloat(weight) : 28.2, [weight]);
    const evalCreatinine = useMemo(() => creatinine !== "" ? parseFloat(creatinine) : 0.5, [creatinine]);
    const evalAst = useMemo(() => ast !== "" ? parseFloat(ast) : 25, [ast]);
    const evalAlt = useMemo(() => alt !== "" ? parseFloat(alt) : 20, [alt]);
    const evalPlatelets = useMemo(() => platelets !== "" ? parseFloat(platelets) : 250, [platelets]);
    const ageOk = inRange("age", age), sexOk = gender !== "";
    const heightOk = inRange("height", height), weightOk = inRange("weight", weight);
    const hasManualGrowth = ageOk && sexOk && heightOk && weightOk;
    const hasManualRenal = ageOk && sexOk && heightOk && inRange("creatinine", creatinine);
    const hasManualLiver = ageOk && inRange("ast", ast) && inRange("alt", alt) && inRange("platelets", platelets);
    const hasManualFrax = inRange("fraxPct", fraxMofEntered) && inRange("fraxPct", fraxHfEntered);
    const bpOk = inRange("systolic", systolic) && inRange("diastolic", diastolic) && diastolic < systolic;
    const sexEntered = sexOk ? gender : null;
    const ageEntered = ageOk ? evalAge : null;
    const growthMetrics = useMemo(() => {
      const bmiVal = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : 0;
      const hM = growthPoint.height, wM = growthPoint.weight, bM = growthPoint.bmi;
      const heightZ = hM && hM.available ? hM.z : null;
      const weightZ = wM && wM.available ? wM.z : null;
      const bmiZ = bM && bM.available ? bM.z : null;
      const heightPct = hM && hM.available ? hM.percentile : null;
      const weightPct = wM && wM.available ? wM.percentile : null;
      const bmiPct = bM && bM.available ? bM.percentile : null;
      const gs = growthSeries[evalGender];
      const heightAgeObj = ageForMedianFromSeries(gs.height, evalHeight);
      const weightAgeObj = ageForMedianFromSeries(gs.weight, evalWeight);
      const ref = {
        htMean: hM && hM.available ? hM.median_for_age : null,
        htSD: spreadFromSeries(gs.height, evalAge),
        wtMean: wM && wM.available ? wM.median_for_age : null,
        wtSD: spreadFromSeries(gs.weight, evalAge)
      };
      let stuntingClass = "Insufficient data", stuntingVariant = "mid";
      if (heightZ !== null) {
        stuntingClass = "Normal";
        stuntingVariant = "low";
        if (heightZ < -3) {
          stuntingClass = "Severe stunting";
          stuntingVariant = "high";
        } else if (heightZ < -2) {
          stuntingClass = "Stunted";
          stuntingVariant = "high";
        } else if (heightZ > 3) {
          stuntingClass = "Very tall";
          stuntingVariant = "mid";
        } else if (heightZ > 2) {
          stuntingClass = "Tall stature";
          stuntingVariant = "mid";
        }
      }
      const bmiCutoffs = growthBmiCutoffs && growthBmiCutoffs.available ? [growthBmiCutoffs.overweight_cutoff, growthBmiCutoffs.obesity_cutoff] : null;
      let underweightClass = "Insufficient data", underweightVariant = "mid";
      if (bmiZ !== null) {
        underweightClass = "Normal";
        underweightVariant = "low";
        if (bmiZ < -3) {
          underweightClass = "Severe thinness";
          underweightVariant = "high";
        } else if (bmiZ < -2) {
          underweightClass = "Thinness";
          underweightVariant = "high";
        } else if (bmiCutoffs) {
          const [c23, c27] = bmiCutoffs;
          if (bmiVal >= c27) {
            underweightClass = "Obese";
            underweightVariant = "high";
          } else if (bmiVal >= c23) {
            underweightClass = "Overweight";
            underweightVariant = "mid";
          }
        } else {
          if (bmiZ > 2) {
            underweightClass = "Obese";
            underweightVariant = "high";
          } else if (bmiZ > 1) {
            underweightClass = "Overweight";
            underweightVariant = "mid";
          }
        }
      } else if (weightZ !== null) {
        underweightClass = "Normal";
        underweightVariant = "low";
        if (weightZ < -3) {
          underweightClass = "Severe underweight";
          underweightVariant = "high";
        } else if (weightZ < -2) {
          underweightClass = "Underweight";
          underweightVariant = "high";
        } else if (weightZ < -1) {
          underweightClass = "Mild underweight";
          underweightVariant = "mid";
        }
      }
      return {
        heightZ,
        weightZ,
        bmiZ,
        heightPct,
        weightPct,
        bmiPct,
        bmiVal,
        stuntingClass,
        stuntingVariant,
        underweightClass,
        underweightVariant,
        heightAge: heightAgeObj,
        weightAge: weightAgeObj,
        ref,
        weightAvailable: !!(wM && wM.available)
      };
    }, [evalAge, evalGender, evalHeight, evalWeight, growthPoint, growthSeries, growthBmiCutoffs]);
    const renalCalc = useServerCalc(hasManualRenal ? { url: withQuery("/api/renal/egfr", {
      sex: gender,
      age: evalAge,
      creatinine_mg_dl: evalCreatinine,
      height_cm: evalHeight,
      weight_kg: weightOk ? evalWeight : null,
      albuminuria: albuminuria || null
    }) } : null);
    const renalMetrics = useMemo(() => {
      const r = renalCalc.data;
      if (!r || !r.available) {
        return {
          ready: false,
          loading: renalCalc.loading,
          error: renalCalc.error,
          reason: r && !r.available ? r.reason : null
        };
      }
      const riskVariant = { low: "low", moderate: "mid", high: "high", very_high: "high" };
      const g = r.gfr_category && r.gfr_category.code;
      const variant = r.kdigo_risk ? riskVariant[r.kdigo_risk.level] : g === "G3a" ? "mid" : ["G3b", "G4", "G5"].includes(g) ? "high" : "info";
      return {
        ready: true,
        result: r,
        egfr: r.primary.value,
        stageVariant: variant,
        category: g || null
      };
    }, [renalCalc.data, renalCalc.loading, renalCalc.error]);
    const liverCalc = useServerCalc(hasManualLiver ? { url: withQuery("/api/hepatic/fib4", {
      age: evalAge,
      ast: evalAst,
      alt: evalAlt,
      platelets: evalPlatelets
    }) } : null);
    const liverMetrics = useMemo(() => {
      const r = liverCalc.data;
      if (!r || !r.available) {
        return {
          ready: false,
          loading: liverCalc.loading,
          error: liverCalc.error,
          reason: r && !r.available ? r.reason : null
        };
      }
      const variant = { low: "low", indeterminate: "mid", high: "high" }[r.category] || "info";
      return { ready: true, result: r, fib4: r.fib4, variant, interpretation: r.category_label };
    }, [liverCalc.data, liverCalc.loading, liverCalc.error]);
    const bpCalc = useServerCalc(ageOk && bpOk ? { url: withQuery("/api/vitals/blood-pressure", {
      age: evalAge,
      sbp: systolic,
      dbp: diastolic,
      sex: sexEntered,
      height_cm: heightOk ? evalHeight : null
    }) } : null);
    const fraxMetrics = useMemo(() => {
      if (!hasManualFrax) return { mofProb: null, hfProb: null, isHighMof: false, isHighHf: false };
      const mofProb = parseFloat(fraxMofEntered), hfProb = parseFloat(fraxHfEntered);
      return { mofProb, hfProb, isHighMof: mofProb >= 20, isHighHf: hfProb >= 3 };
    }, [hasManualFrax, fraxMofEntered, fraxHfEntered]);
    const chronicityStatus = useMemo(() => {
      if (timeline.length < 2) return { status: "Add at least 2 snapshots (\u2265 90 days apart) to assess CKD chronicity.", cls: "risk-badge-neutral", bgClass: "bg-slate-50 border-slate-200 text-slate-500" };
      const sorted = [...timeline].sort((a, b) => new Date(a.date) - new Date(b.date));
      const diffDays = Math.ceil((new Date(sorted[sorted.length - 1].date) - new Date(sorted[0].date)) / 864e5);
      if (diffDays < 90) return { status: `Observation window: ${diffDays} days \u2014 need 90 days minimum to confirm chronicity.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
      const damaged = (e) => e.egfr < 60 || e.albuminuria === "A2" || e.albuminuria === "A3";
      const initDmg = damaged(sorted[0]);
      const curDmg = damaged(sorted[sorted.length - 1]);
      if (initDmg && curDmg) return { status: `Chronicity CONFIRMED \u2014 Persistent indicators across ${diffDays}-day window.`, bgClass: "bg-rose-50 border-rose-200 text-rose-700 font-bold" };
      if (!initDmg && !curDmg) return { status: `No CKD marker (eGFR < 60 or albuminuria A2/A3) in the first or latest snapshot over ${diffDays} days. Unrecorded albuminuria does not exclude CKD.`, bgClass: "bg-slate-50 border-slate-200 text-slate-600" };
      return { status: `Transient profile \u2014 a marker was present at only one end of the ${diffDays}-day window.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
    }, [timeline]);
    const generalMetrics = useMemo(() => {
      const bmi = evalWeight / Math.pow(evalHeight / 100, 2);
      const bmiAdult = ageOk && evalAge >= 18;
      let bmiCat = null, bmiVariant = "info";
      if (bmiAdult) {
        bmiCat = "Normal";
        bmiVariant = "low";
        if (bmi < 18.5) {
          bmiCat = "Underweight";
          bmiVariant = "mid";
        } else if (bmi >= 27.5) {
          bmiCat = "Obese";
          bmiVariant = "high";
        } else if (bmi >= 23) {
          bmiCat = "Overweight";
          bmiVariant = "mid";
        }
      }
      return { bmi, bmiAdult, bmiCat, bmiVariant };
    }, [ageOk, evalAge, evalHeight, evalWeight]);
    useEffect5(() => {
      const params = new URLSearchParams(window.location.search);
      if (params.get("report") !== "1") return;
      document.body.classList.add("report-mode");
      const r = window.__PCW_REPORT__ || {};
      if (r.sex === "boys" || r.sex === "girls") setGender(r.sex);
      if (r.age) setAge(r.age);
      if (r.height) setHeight(r.height);
      if (r.weight) setWeight(r.weight);
      if (r.patient_name) setPatientName(r.patient_name);
      if (r.patient_mrn) setPatientMrn(r.patient_mrn);
      if (r.exam_date) setExamDate(r.exam_date);
      setActiveTab("growth");
      setGrowthChartMeasure("combined");
      setShowChart(true);
    }, []);
    useEffect5(() => {
      fetch("/api/bone-age/config").then((r) => r.json()).then(setTw3Config).catch(() => {
      });
    }, []);
    useEffect5(() => {
      let cancelled = false;
      const sexAtFetch = evalGender;
      setGrowthSeriesLoading(true);
      Promise.all(
        ["height", "weight", "bmi"].map(
          (m) => fetch(`/api/growth/chart?measure=${m}&sex=${sexAtFetch}`).then((r) => r.json()).then((d) => [m, d])
        )
      ).then((pairs) => {
        if (cancelled) return;
        const mismatched = pairs.filter(([, d]) => d && d.sex && d.sex !== sexAtFetch);
        if (mismatched.length) {
          console.error("Growth chart: API returned data for the wrong sex -- discarding", { requested: sexAtFetch, mismatched });
          setGrowthSeriesLoading(false);
          return;
        }
        setGrowthSeries((prev) => ({ ...prev, [sexAtFetch]: Object.fromEntries(pairs) }));
        setGrowthSeriesLoading(false);
      }).catch(() => {
        if (!cancelled) setGrowthSeriesLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }, [evalGender]);
    useEffect5(() => {
      if (!hasManualGrowth || evalAge > 19) {
        setGrowthPoint({ height: null, weight: null, bmi: null });
        setGrowthBmiCutoffs(null);
        return;
      }
      let cancelled = false;
      const bmiVal = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : 0;
      const withValue = { height: evalHeight, weight: evalWeight, bmi: bmiVal };
      Promise.all(
        ["height", "weight", "bmi"].map(
          (m) => fetch(`/api/growth/point?measure=${m}&sex=${evalGender}&age=${evalAge}&value=${withValue[m]}`).then((r) => r.json()).then((d) => [m, d])
        )
      ).then((pairs) => {
        if (!cancelled) setGrowthPoint(Object.fromEntries(pairs));
      }).catch(() => {
      });
      fetch(`/api/growth/bmi-cutoffs?sex=${evalGender}&age=${evalAge}`).then((r) => r.json()).then((d) => {
        if (!cancelled) setGrowthBmiCutoffs(d);
      }).catch(() => {
      });
      return () => {
        cancelled = true;
      };
    }, [hasManualGrowth, evalAge, evalGender, evalHeight, evalWeight]);
    useEffect5(() => {
      if (!sexEntered) {
        setAdultHeightStats(null);
        return;
      }
      let cancelled = false;
      fetch(`/api/growth/reference-stats?measure=height&sex=${sexEntered}&age=18`).then((r) => r.json()).then((d) => {
        if (!cancelled) setAdultHeightStats(d);
      }).catch(() => {
      });
      return () => {
        cancelled = true;
      };
    }, [sexEntered]);
    useEffect5(() => {
      const rid = assessment && assessment.radiograph_id;
      if (rid && (!radiograph || radiograph.radiograph_id !== rid)) {
        setRadiograph((r) => ({ ...r || {}, radiograph_id: rid }));
      }
    }, [assessment]);
    useEffect5(() => {
      if (!sexEntered) {
        setLetterResult(null);
        setBoneReport(null);
        return;
      }
      const carp = {};
      Object.entries(carpalStages).forEach(([n, g]) => carp[carpalCode2(n)] = g);
      const aiYrs = aiEstimate && aiEstimate.bone_age_years != null ? aiEstimate.bone_age_years : null;
      const id = setTimeout(() => {
        fetch("/api/bone-age/letters-score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sex: sexEntered, rus_stages: rusStages, carpal_stages: carp })
        }).then((r) => r.ok ? r.json() : null).then((d) => {
          if (d) setLetterResult(d);
        }).catch(() => {
        });
        fetch("/api/bone-age/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sex: sexEntered,
            rus_stages: rusStages,
            carpal_stages: carp,
            chronological_age_years: ageEntered,
            ai_estimate_years: aiYrs
          })
        }).then((r) => r.ok ? r.json() : null).then((d) => {
          if (d) setBoneReport(d);
        }).catch(() => {
        });
      }, 250);
      return () => clearTimeout(id);
    }, [rusStages, carpalStages, sexEntered, ageEntered, aiEstimate]);
    const boneMetrics = useMemo(() => {
      const ba = boneAge !== "" ? parseFloat(boneAge) : null;
      const hasBone = inRange("boneAge", ba) && ageOk;
      const fh = fatherHeight !== "" ? parseFloat(fatherHeight) : null;
      const mh = motherHeight !== "" ? parseFloat(motherHeight) : null;
      let mph = null, mphLow = null, mphHigh = null;
      if (sexOk && inRange("parentHeight", fh) && inRange("parentHeight", mh)) {
        mph = sexEntered === "boys" ? (fh + mh + 13) / 2 : (fh + mh - 13) / 2;
        mphLow = mph - 8.5;
        mphHigh = mph + 8.5;
      }
      if (!hasBone && mph === null) return null;
      const diff = hasBone ? ba - evalAge : null;
      const autoCat = hasBone ? maturationCategory(ba, evalAge) : null;
      const pct = hasBone && sexOk ? pctAdultHeightAt(ba, sexEntered) : null;
      const skeletalPah = pct && pct > 0 && heightOk ? evalHeight / (pct / 100) : null;
      const skeletalCalibrated = pct !== null;
      const predictedPah = skeletalPah;
      const remaining = predictedPah !== null && heightOk ? predictedPah - evalHeight : null;
      const predVsTarget = predictedPah !== null && mph !== null ? predictedPah - mph : null;
      const withinTarget = predictedPah !== null && mphLow !== null ? predictedPah >= mphLow && predictedPah <= mphHigh : null;
      const adultAvailable = adultHeightStats && adultHeightStats.available;
      const adultMedian = adultAvailable ? adultHeightStats.p50 : 170;
      const adult = [adultMedian];
      const zFor = (v) => v !== null ? zForValueFromCentileStats(adultHeightStats, v) : null;
      const pctFor = (z) => z !== null ? Math.min(99.9, Math.max(0.1, normalCDF(z) * 100)) : null;
      const predZ = zFor(predictedPah), predPct = pctFor(predZ);
      const mphZ = zFor(mph), mphPct = pctFor(mphZ);
      return {
        ba,
        hasBone,
        diff,
        autoCat,
        pct,
        skeletalPah,
        skeletalCalibrated,
        predictedPah,
        predVsTarget,
        remaining,
        predZ,
        predPct,
        mph,
        mphLow,
        mphHigh,
        mphZ,
        mphPct,
        withinTarget,
        adult
      };
    }, [boneAge, ageOk, sexOk, heightOk, sexEntered, evalAge, evalHeight, fatherHeight, motherHeight, adultHeightStats]);
    const boneAgeHandlers = useBoneAgeHandlers({
      adjReviewer,
      age,
      aiEstimate,
      assessment,
      boxes,
      sexEntered,
      ageEntered,
      boxesRef,
      carpalStages,
      coverage,
      declaredFlags,
      estimateDomain,
      fbAge,
      fbConfidence,
      fbMethod,
      fbNote,
      fbRater,
      height,
      lastFilm,
      locDrag,
      locImg,
      locRef,
      ltTables,
      monitoring,
      patientCode,
      radiograph,
      rusStages,
      setAdjBusy,
      setAdjItems,
      setAdjMsg,
      setAiBusy,
      setAiEstimate,
      setAssessment,
      setBoneAge,
      setBoneAgeSource,
      setBoxes,
      setCarpalStages,
      setCovBusy,
      setCoverage,
      setDeclaredFlags,
      setFbAge,
      setFbBusy,
      setFbMsg,
      setFbNote,
      setLastFilm,
      setLcBusy,
      setLcMsg,
      setLocBusy,
      setLocImg,
      setLocMsg,
      setLcohBusy,
      setLocalCohort,
      setLtBusy,
      setLtMsg,
      setLtStatus,
      setLtTables,
      setMonBusy,
      setMonitoring,
      setRadiograph,
      setRusStages,
      setSelBone,
      setShowAudit,
      showAudit
    });
    const {
      LC_API,
      lcLocked,
      unsavedStaging,
      saveDraft,
      bonesIntoGrids,
      calculateAssessment,
      approveAssessment,
      reviseAssessment,
      toggleAudit,
      submitFeedback,
      runEstimate,
      toggleDeclaredFlag,
      attachImage,
      loadCoverage,
      loadMonitoring,
      loadAdjudication,
      resolveAdjudication,
      loadLetterTables,
      setLtPoint,
      curveToText,
      setLtCurve,
      setLtSexCurve,
      useGridAsReference,
      setRefExpected,
      saveLetterTables,
      setImageDomain,
      analysisUrl,
      localizeBones,
      addOrSelectBox,
      clearBox,
      saveBoxes,
      startBoxDrag,
      onLocMove,
      endLocDrag,
      lcBtn,
      loadLocalCohort
    } = boneAgeHandlers;
    const qriskInAgeRange = ageOk && sexOk && evalAge >= 25 && evalAge <= 84;
    const qriskCalc = useServerCalc(qriskInAgeRange && heightOk && weightOk ? { url: "/api/cvd/qrisk3", body: {
      sex: gender,
      age: evalAge,
      height_cm: evalHeight,
      weight_kg: evalWeight,
      ethnicity,
      smoke: smokeCat,
      diabetes,
      cholesterol_ratio: inRange("cholRatio", cholRatio) ? parseFloat(cholRatio) : null,
      systolic_bp: inRange("systolic", systolic) ? systolic : null,
      sbp_sd: inRange("sbpSD", sbpSD) ? parseFloat(sbpSD) : null,
      AF: qAF === "yes",
      treatedhyp: qTreatedHtn === "yes",
      ra: qRA === "yes",
      renal: qCKD === "yes",
      migraine: qMigraine === "yes",
      sle: qSLE === "yes",
      semi: qSMI === "yes",
      atypicalantipsy: qAtypAntipsy === "yes",
      corticosteroids: qCortico === "yes",
      impotence2: gender === "boys" && qED === "yes",
      fh_cvd: qFhCvd === "yes"
    } } : null);
    const qriskMetrics = useMemo(() => {
      const r = qriskCalc.data;
      const base = {
        inAgeRange: qriskInAgeRange,
        bodySizeOk: heightOk && weightOk,
        loading: qriskCalc.loading,
        error: qriskCalc.error
      };
      if (!r || !r.available) return { ...base, risk: null, reason: r && !r.available ? r.reason : null };
      const band = { high: "High (\u2265 20%)", moderate: "Moderate (10\u201320%)", low: "Low (< 10%)" }[r.band];
      const variant = { high: "high", moderate: "mid", low: "low" }[r.band];
      const labels = {
        cholesterol_ratio: "cholesterol ratio",
        systolic_bp: "systolic BP",
        sbp_sd: "SBP variability (SD)"
      };
      const imputed = (r.imputed_fields || []).filter((f) => f !== "townsend").map((f) => labels[f] || f);
      return {
        ...base,
        risk: r.risk_percent,
        typical: r.healthy_person_percent,
        band,
        variant,
        imputed,
        bmiClamped: r.bmi_clamped
      };
    }, [qriskCalc.data, qriskCalc.loading, qriskCalc.error, qriskInAgeRange, heightOk, weightOk]);
    const moduleStatus = useMemo(() => {
      const growthAvailable = hasManualGrowth && growthMetrics.heightPct != null;
      const growthState = !growthAvailable ? "none" : variantToState([growthMetrics.stuntingVariant, growthMetrics.underweightVariant].includes("high") ? "high" : [growthMetrics.stuntingVariant, growthMetrics.underweightVariant].includes("mid") ? "mid" : "low");
      const boneReady = boneMetrics && boneMetrics.hasBone;
      const boneState = !boneReady ? "none" : Math.abs(boneMetrics.diff) > 2 ? "borderline" : "normal";
      return {
        growth: {
          state: growthState,
          value: growthAvailable ? growthMetrics.heightPct.toFixed(0) + "th" : "\u2014",
          unit: "ht pct",
          label: !hasManualGrowth ? "Enter age, sex, height & weight" : !growthAvailable ? "Age outside 0\u201319y growth reference" : `${growthMetrics.stuntingClass} \xB7 ${growthMetrics.underweightClass}`,
          title: "Growth"
        },
        boneage: {
          state: boneState,
          value: boneReady ? (boneMetrics.diff >= 0 ? "+" : "") + boneMetrics.diff.toFixed(1) : "\u2014",
          unit: "yr vs CA",
          label: boneReady ? boneMetrics.diff > 1 ? "Advanced maturation" : boneMetrics.diff < -1 ? "Delayed maturation" : "Concordant with age" : "Set a TW3 bone age",
          title: "Bone Age"
        },
        renal: {
          state: renalMetrics.ready ? variantToState(renalMetrics.stageVariant) : "none",
          value: renalMetrics.ready ? renalMetrics.egfr.toFixed(0) : "\u2014",
          unit: "mL/min/1.73m\xB2",
          label: renalMetrics.ready ? renalMetrics.category ? `${renalMetrics.category}${renalMetrics.result.albuminuria_category ? renalMetrics.result.albuminuria_category.code : ""} \xB7 ${renalMetrics.result.kdigo_risk ? renalMetrics.result.kdigo_risk.label : "add ACR for KDIGO risk"}` : "No KDIGO category under 2 y" : !hasManualRenal ? "Enter serum creatinine" : renalMetrics.reason || (renalMetrics.error ? "Calculation failed" : "Calculating\u2026"),
          title: "Renal (eGFR)"
        },
        liver: {
          state: liverMetrics.ready ? variantToState(liverMetrics.variant) : "none",
          value: liverMetrics.ready ? liverMetrics.fib4.toFixed(2) : "\u2014",
          unit: "FIB-4",
          label: liverMetrics.ready ? liverMetrics.interpretation : !hasManualLiver ? "Enter AST, ALT & platelets" : liverMetrics.reason || (liverMetrics.error ? "Calculation failed" : "Calculating\u2026"),
          title: "Liver (FIB-4)"
        },
        frax: {
          state: hasManualFrax ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "high" : "normal" : "none",
          value: hasManualFrax ? fraxMetrics.mofProb.toFixed(1) : "\u2014",
          unit: "% MOF 10-yr",
          label: hasManualFrax ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "At/above US treatment threshold" : "Below US treatment threshold" : "Enter the official FRAX result",
          title: "FRAX (entered)"
        },
        qrisk: {
          state: qriskMetrics.risk !== null ? variantToState(qriskMetrics.variant) : "none",
          value: qriskMetrics.risk !== null ? qriskMetrics.risk.toFixed(1) : "\u2014",
          unit: "% CVD 10-yr",
          label: qriskMetrics.risk !== null ? qriskMetrics.band : "Age 25\u201384 + BMI required",
          title: "QRISK3 CVD"
        }
      };
    }, [
      hasManualGrowth,
      hasManualRenal,
      hasManualLiver,
      hasManualFrax,
      growthMetrics,
      boneMetrics,
      renalMetrics,
      liverMetrics,
      fraxMetrics,
      qriskMetrics
    ]);
    const resetAll = () => {
      if (!window.confirm("Clear all patient data and results? This cannot be undone.")) return;
      setPatientName("");
      setPatientMrn("");
      setExamDate((/* @__PURE__ */ new Date()).toISOString().split("T")[0]);
      setAge("");
      setDob("");
      setGender("");
      setHeight("");
      setWeight("");
      setCreatinine("");
      setAlbuminuria("");
      setSystolic("");
      setDiastolic("");
      setAst("");
      setAlt("");
      setPlatelets("");
      setFraxMofEntered("");
      setFraxHfEntered("");
      setTimeline([]);
      setActiveTab("overview");
      setBoneAge("");
      setBoneAgeSource("manual");
      setRusStages({});
      setCarpalStages({});
      setPatientCode("");
      setAssessment(null);
      setLcMsg(null);
      setShowAudit(false);
      setRadiograph(null);
      setAiEstimate(null);
      setFatherHeight("");
      setMotherHeight("");
      setEthnicity(2);
      setSmokeCat(0);
      setDiabetes(0);
      setCholRatio("");
      setSbpSD("");
      setQAF("no");
      setQTreatedHtn("no");
      setQRA("no");
      setQCKD("no");
      setQMigraine("no");
      setQSLE("no");
      setQSMI("no");
      setQAtypAntipsy("no");
      setQCortico("no");
      setQED("no");
      setQFhCvd("no");
    };
    const canLogSnapshot = hasManualRenal && renalMetrics.ready;
    const logCurrentData = () => {
      if (!canLogSnapshot) return;
      setTimeline((prev) => [{
        id: Date.now().toString(),
        date: examDate || (/* @__PURE__ */ new Date()).toISOString().split("T")[0],
        age: evalAge,
        height: evalHeight,
        weight: weightOk ? evalWeight : null,
        creatinine: evalCreatinine,
        egfr: Number(renalMetrics.egfr.toFixed(1)),
        fib4: liverMetrics.ready ? liverMetrics.fib4 : null,
        albuminuria: albuminuria !== "" ? albuminuria : null
      }, ...prev]);
    };
    const exportGrowthReportPdf = async () => {
      try {
        const res = await fetch("/api/growth/report.pdf", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sex: evalGender,
            age: evalAge,
            height: evalHeight || 0,
            weight: evalWeight || 0,
            patient_name: patientName,
            patient_mrn: patientMrn,
            exam_date: examDate
          })
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail && detail.detail || `PDF export failed (HTTP ${res.status})`);
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `growth-report-${evalGender}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 5e3);
      } catch (err) {
        console.error("exportGrowthReportPdf: server-side PDF export failed, falling back to browser print", err);
        alert("Server-side PDF export is unavailable (" + err.message + '). Falling back to the browser Print dialog -- please uncheck "Headers and footers" in More settings before saving as PDF.');
        printGrowthReport();
      }
    };
    const printGrowthReport = () => {
      const exportSanity = validateHeightReferenceSanity(growthSeries[evalGender].height, evalGender);
      if (!exportSanity.ok) {
        console.error("printGrowthReport: refusing to export PDF -- height reference data failed sanity validation", { sex: evalGender, ...exportSanity });
        alert("Growth chart reference data failed a sanity check and cannot be exported. Please retry or contact support.");
        return;
      }
      const chartEl = document.getElementById("growth-chart-print");
      const svg = chartEl ? chartEl.innerHTML : "";
      const g = growthMetrics;
      const row = (k, v) => `<tr><td style="padding:4px 12px 4px 0;color:#64748b">${k}</td><td style="padding:4px 0;font-weight:700">${v}</td></tr>`;
      const fmtZ = (z) => z === null || z === void 0 ? "\u2014" : (z >= 0 ? "+" : "") + z.toFixed(2);
      const fmtP = (p) => p === null || p === void 0 ? "\u2014" : p.toFixed(1) + "th";
      const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
      const win = window.open("", "_blank", "width=820,height=1000");
      if (!win) {
        alert("Please allow pop-ups to print the growth report.");
        return;
      }
      const chartLabel = growthChartMeasure === "combined" ? "Height & Weight (combined chart)" : MEASURE_META.bmi.label;
      win.document.write(`<!DOCTYPE html><html><head><title>Growth Report</title>
              <style>body{font-family:Inter,Arial,sans-serif;color:#1e293b;margin:14mm}
              h1{font-size:18px;margin:0 0 2px}.sub{color:#64748b;font-size:11px;margin-bottom:14px}
              .chart-sheet{width:190mm;height:277mm;margin:0 auto;display:flex;align-items:center;justify-content:center}
              .chart-sheet svg{width:100%;height:100%}
              table{border-collapse:collapse;font-size:12px;margin-top:10px}
              .foot{margin-top:18px;font-size:10px;color:#94a3b8;line-height:1.5;border-top:1px solid #e5e7eb;padding-top:8px}
              @media print{@page{size:A4;margin:10mm}.chart-sheet{page-break-after:always}}</style></head><body>
              <h1>Pediatric Growth Report</h1>
              <div class="sub" style="font-weight:700;color:#334155">${esc(patientName || "Unnamed patient")} \xB7 MRN ${esc(patientMrn || "\u2014")} \xB7 Exam ${esc(examDate)}</div>
              <div class="sub">Reference: ${esc(growthSeries[evalGender].height && growthSeries[evalGender].height.reference || "WHO + IAP 2015")} \xB7 ${esc(chartLabel)} \xB7 ${(/* @__PURE__ */ new Date()).toLocaleDateString()}</div>
              <div class="chart-sheet">${svg}</div>
              <table>
                ${row("Sex", evalGender === "girls" ? "Female" : "Male")}
                ${row("Chronological age", evalAge.toFixed(1) + " yrs")}
                ${row("Height", esc(evalHeight) + " cm  \xB7  z " + fmtZ(g.heightZ) + "  \xB7  " + fmtP(g.heightPct) + " pct")}
                ${row("Weight", esc(evalWeight) + " kg" + (g.weightAvailable ? "  \xB7  z " + fmtZ(g.weightZ) + "  \xB7  " + fmtP(g.weightPct) + " pct" : "  (weight-for-age n/a at this age \u2014 use BMI)"))}
                ${row("BMI", g.bmiVal.toFixed(1) + " kg/m\xB2  \xB7  z " + fmtZ(g.bmiZ) + "  \xB7  " + fmtP(g.bmiPct) + " pct")}
                ${row("Height status", g.stuntingClass)}
                ${row("Weight / BMI status", g.underweightClass)}
                ${row("Height age", esc(g.heightAge.label))}
              </table>
              <div class="foot">Decision support only \u2014 not a diagnostic device. A clinician must verify all results.
              Percentiles computed with the LMS method: WHO 2006 reference under 5 years; IAP 2015 (Khadilkar) Indian reference for height, weight and BMI from 5-18 years. The IAP 2015 curves were fit from the paper's own published percentile tables (the authors' original L,M,S triplets are unpublished) \u2014 overweight/obesity for 5-18y use the IAP/IOTF 23 and 27 adult-equivalent BMI cutoffs rather than a fixed z-score.</div>
              </body></html>`);
      win.document.close();
      win.focus();
      setTimeout(() => win.print(), 350);
    };
    const exportFullReport = () => {
      const win = window.open("", "_blank", "width=820,height=1000");
      if (!win) {
        alert("Please allow pop-ups to print the report.");
        return;
      }
      const esc = (s) => String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
      const stateColor = { high: "#dc2626", borderline: "#d97706", normal: "#16a34a", none: "#94a3b8" };
      const rows = ["growth", "boneage", "renal", "liver", "frax", "qrisk"].map((k) => {
        const m = moduleStatus[k];
        return `<tr>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7;font-weight:600">${esc(m.title)}</td>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7"><b>${esc(m.value)}</b> <span style="color:#94a3b8;font-size:11px">${esc(m.unit)}</span></td>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7;color:${stateColor[m.state]};font-weight:700">${m.state === "none" ? "\u2014" : esc(m.label)}</td>
              </tr>`;
      }).join("");
      const idLine = `${esc(patientName || "Unnamed patient")} \xB7 MRN ${esc(patientMrn || "\u2014")} \xB7 ${age !== "" ? esc(age) + " yr" : "\u2014 yr"} \xB7 ${gender === "boys" ? "Male" : gender === "girls" ? "Female" : "\u2014"} \xB7 Exam ${esc(examDate)}`;
      win.document.write(`<!DOCTYPE html><html><head><title>Clinical Summary \u2014 ${esc(patientName || "patient")}</title>
              <style>body{font-family:Inter,Arial,sans-serif;color:#1e293b;margin:16mm}
              h1{font-size:20px;margin:0 0 4px}.sub{color:#334155;font-size:12px;font-weight:600;margin-bottom:16px}
              table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
              th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;padding:0 12px 6px;border-bottom:1.5px solid #e2e8f0}
              .foot{margin-top:20px;font-size:10px;color:#94a3b8;line-height:1.6;border-top:1px solid #e5e7eb;padding-top:10px}
              @media print{@page{size:A4;margin:12mm}}</style></head><body>
              <h1>Pediatric Clinical Summary</h1>
              <div class="sub">${idLine}</div>
              <table><thead><tr><th>Module</th><th>Result</th><th>Interpretation</th></tr></thead><tbody>${rows}</tbody></table>
              <div class="foot">Decision support only \u2014 not a diagnostic device. A clinician must verify every value. A "\u2014" interpretation means that module had insufficient input. References: Khadilkar 2015 \xB7 TW3-C (Chinese) RUS \u2014 provisional research curve (\xB10.5y, digitized from a published figure); NOT Tanner\u2013Whitehouse TW3 \xB7 QRISK3-2017 \xB7 CKD-EPI 2021 \xB7 Bedside Schwartz 2009 \xB7 CKiD U25 2021 \xB7 KDIGO \xB7 AAP 2017 / ACC-AHA 2017 BP \xB7 FRAX: result from the official University of Sheffield calculator, entered by the clinician (threshold = US NOF/BHOF) \xB7 FIB-4 (Sterling et al.).</div>
              </body></html>`);
      win.document.close();
      win.focus();
      setTimeout(() => win.print(), 300);
    };
    const TABS = [
      { id: "overview", label: "Overview" },
      { id: "growth", label: "Growth" },
      { id: "record", label: "Patient Record" },
      { id: "boneage", label: "Bone Age" },
      { id: "renal", label: "Renal GFR" },
      { id: "liver", label: "FIB-4 Liver" },
      { id: "frax", label: "FRAX" },
      { id: "qrisk", label: "QRISK3 CVD" },
      { id: "timeline", label: "Ledger" }
    ];
    const labsRelevant = ["renal", "liver", "qrisk", "timeline", "overview"].includes(activeTab);
    const clinicalState = {
      // The whole bone-age domain as ONE slice: its state module, its handler
      // module, and the few values App derives from them. Listing the names
      // again here (and a third time in useBoneAge) is what let a wired-up
      // handler reach a panel as undefined -- the button rendered and did
      // nothing. Spreading the bags makes that impossible by construction.
      boneAge: {
        ...boneAgeState,
        ...boneAgeHandlers,
        age,
        boneMetrics,
        evalAge,
        evalGender,
        evalHeight,
        height
      },
      age,
      dob,
      gender,
      height,
      weight,
      evalAge,
      evalHeight,
      evalWeight,
      patientName,
      patientMrn,
      examDate,
      liverMetrics,
      hasManualLiver,
      bpCalc,
      renalMetrics,
      hasManualRenal,
      creatinine,
      fraxMetrics,
      hasManualFrax,
      fraxMofEntered,
      setFraxMofEntered,
      fraxHfEntered,
      setFraxHfEntered,
      canLogSnapshot,
      sexEntered,
      heightOk,
      weightOk,
      bpOk,
      // ── the input column's slice (useInputs): the ONLY setters for the
      // shared measurements, because it is the only thing that writes them
      setGender,
      setHeight,
      setWeight,
      handleAgeChange,
      handleDobChange,
      ageParts,
      labsRelevant,
      setCreatinine,
      setAlbuminuria,
      systolic,
      setSystolic,
      diastolic,
      setDiastolic,
      ast,
      setAst,
      alt,
      setAlt,
      platelets,
      setPlatelets,
      // ── the shell's slice (useShell): header, identity bar, tabs
      resetAll,
      exportFullReport,
      TABS,
      activeTab,
      setPatientName,
      setPatientMrn,
      setExamDate,
      albuminuria,
      assessment,
      cholRatio,
      chronicityStatus,
      diabetes,
      ethnicity,
      evalGender,
      exportGrowthReportPdf,
      growthChartMeasure,
      growthMetrics,
      growthSeries,
      hasManualGrowth,
      logCurrentData,
      moduleStatus,
      printGrowthReport,
      qAF,
      qAtypAntipsy,
      qCKD,
      qCortico,
      qED,
      qFhCvd,
      qMigraine,
      qRA,
      qSLE,
      qSMI,
      qTreatedHtn,
      qriskMetrics,
      sbpSD,
      setActiveTab,
      setCholRatio,
      setDiabetes,
      setEthnicity,
      setGrowthChartMeasure,
      setQAF,
      setQAtypAntipsy,
      setQCKD,
      setQCortico,
      setQED,
      setQFhCvd,
      setQMigraine,
      setQRA,
      setQSLE,
      setQSMI,
      setQTreatedHtn,
      setSbpSD,
      setShowChart,
      setSmokeCat,
      setTimeline,
      showChart,
      smokeCat,
      timeline
    };
    return /* @__PURE__ */ React.createElement(ClinicalStateProvider, { value: clinicalState }, /* @__PURE__ */ React.createElement("div", { className: "app-shell" }, /* @__PURE__ */ React.createElement(AppHeader, null), /* @__PURE__ */ React.createElement(PatientIdentityBar, null), /* @__PURE__ */ React.createElement("main", { className: "app-main" }, /* @__PURE__ */ React.createElement(InputColumn, null), /* @__PURE__ */ React.createElement("div", { className: "result-column" }, /* @__PURE__ */ React.createElement(TabBar, null), /* @__PURE__ */ React.createElement("div", { className: "card-lg result-panel" }, activeTab === "overview" && /* @__PURE__ */ React.createElement(OverviewPanel, null), activeTab === "growth" && /* @__PURE__ */ React.createElement(GrowthPanel, null), activeTab === "boneage" && /* @__PURE__ */ React.createElement(BoneAgePanel, null), activeTab === "record" && /* @__PURE__ */ React.createElement(RecordPanel, null), activeTab === "renal" && /* @__PURE__ */ React.createElement(RenalPanel, null), activeTab === "liver" && /* @__PURE__ */ React.createElement(LiverPanel, null), activeTab === "frax" && /* @__PURE__ */ React.createElement(FraxPanel, null), activeTab === "qrisk" && /* @__PURE__ */ React.createElement(QriskPanel, null), activeTab === "timeline" && /* @__PURE__ */ React.createElement(LedgerPanel, null)), /* @__PURE__ */ React.createElement("div", { className: "card no-print", style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#0891b2", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "General Health Indicators")), /* @__PURE__ */ React.createElement("div", { className: "general-grid" }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Body Mass Index"), heightOk && weightOk ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "28px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, generalMetrics.bmi.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "kg/m\xB2")), generalMetrics.bmiAdult ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: generalMetrics.bmiCat, variant: generalMetrics.bmiVariant })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "4px" } }, "Asian adult cutoffs: Normal < 23, OW \u2265 23, Obese \u2265 27.5")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "6px", lineHeight: "1.5" } }, ageOk ? "Under 18: interpret with BMI-for-age on the Growth tab, not adult cut-offs." : "Enter age to categorise (adult cut-offs apply from 18 y).")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "6px 0" } }, "Enter height & weight")), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Blood Pressure"), !(bpOk && ageOk) ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "6px 0" } }, "Enter age and a plausible systolic & diastolic BP") : !bpCalc.data ? /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "6px 0" } }, bpCalc.error ? "Calculation failed: " + bpCalc.error : "Calculating\u2026") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "28px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, systolic, "/", diastolic), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "mmHg \xB7 MAP ", bpCalc.data.map)), bpCalc.data.available ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px" } }, /* @__PURE__ */ React.createElement(
      StatusBadge,
      {
        text: bpCalc.data.category_label,
        variant: { normal: "low", elevated: "mid", stage1: "mid", stage2: "high", severe: "high" }[bpCalc.data.category]
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "4px", lineHeight: "1.5" } }, bpCalc.data.guideline, " \xB7 ", bpCalc.data.notes.join(" "))) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "6px", lineHeight: "1.5" } }, bpCalc.data.reason))))))), /* @__PURE__ */ React.createElement("footer", { className: "clinical-footer" }, "Reference: Khadilkar V et al. (2015) Indian Pediatrics \xB7 TW3 (Tanner-Whitehouse 3, 2001) \xB7 QRISK3-2017 (Hippisley-Cox, BMJ 2017; ClinRisk LGPL) \xB7 CKD-EPI 2021 \xB7 Modified Bedside Schwartz (2009) \xB7 FRAX (official calculator result, entered) \xB7 FIB-4 (Sterling et al.) \xB7 For clinical decision support only.")));
  }
  var root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(/* @__PURE__ */ React.createElement(App, null));
})();
