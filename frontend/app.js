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

  // frontend/src/qrisk3.js
  var QRISK3_FEMALE = {
    survivor: 0.988876402378082,
    Iethrisk: [
      0,
      0,
      0.2804031433299542,
      0.562989941420754,
      0.2959000085111652,
      0.0727853798779825,
      -0.1707213550885732,
      -0.3937104331487497,
      -0.3263249528353027,
      -0.1712705688324178
    ],
    Ismoke: [0, 0.1338683378654626, 0.5620085801243854, 0.6674959337750255, 0.8494817764483085],
    c: {
      age1: -8.138810924772619,
      age2: 0.797333766896991,
      bmi1: 0.2923609227546005,
      bmi2: -4.1513300213837665,
      rati: 0.1533803582080255,
      sbp: 0.0131314884071034,
      sbps5: 0.0078894541014586,
      town: 0.0772237905885901,
      AF: 1.5923354969269663,
      atypicalantipsy: 0.2523764207011556,
      corticosteroids: 0.5952072530460185,
      migraine: 0.301267260870345,
      ra: 0.2136480343518194,
      renal: 0.6519456949384583,
      semi: 0.1255530805882018,
      sle: 0.7588093865426769,
      treatedhyp: 0.50931593683423,
      type1: 1.7267977510537347,
      type2: 1.0688773244615468,
      fh_cvd: 0.4544531902089621
    },
    // age_1 (age1×var) and age_2 (age2×var) interaction terms
    i1: {
      s1: -4.705716178585189,
      s2: -2.7430383403573337,
      s3: -0.8660808882939218,
      s4: 0.9024156236971065,
      AF: 19.93803488954656,
      corticosteroids: -0.9840804523593628,
      migraine: 1.7634979587872999,
      renal: -3.5874047731694114,
      sle: 19.690303738638292,
      treatedhyp: 11.872809733921812,
      type1: -1.2444332714320747,
      type2: 6.86523420000096,
      bmi1: 23.80262341214174,
      bmi2: -71.18494769208701,
      fh_cvd: 0.9946780794043513,
      sbp: 0.0341318423386155,
      town: -1.0301180802035639
    },
    i2: {
      s1: -0.075589244643193,
      s2: -0.1195119287486707,
      s3: -0.1036630639757192,
      s4: -0.1399185359171839,
      AF: -0.0761826510111625,
      corticosteroids: -0.1200536494674247,
      migraine: -0.0655869178986999,
      renal: -0.2268887308644251,
      sle: 0.0773479496790163,
      treatedhyp: 9685782358817e-16,
      type1: -0.2872406462448895,
      type2: -0.0971122525906955,
      bmi1: 0.5236995893366443,
      bmi2: 0.0457441901223238,
      fh_cvd: -0.076885051698423,
      sbp: -0.0015082501423272,
      town: -0.0315934146749623
    },
    center: { rati: 3.47632646560669, sbp: 123.13001251220703, sbps5: 9.002537727355957, town: 0.392308831214905 }
  };
  var QRISK3_MALE = {
    survivor: 0.977268040180206,
    Iethrisk: [
      0,
      0,
      0.2771924876030828,
      0.4744636071493127,
      0.5296172991968937,
      0.035100159186299,
      -0.3580789966932792,
      -0.4005648523216514,
      -0.4152279288983017,
      -0.2632134813474997
    ],
    Ismoke: [0, 0.1912822286338898, 0.5524158819264555, 0.6383505302750607, 0.7898381988185802],
    c: {
      age1: -17.839781666005575,
      age2: 0.0022964880605765,
      bmi1: 2.456277666053636,
      bmi2: -8.301112231471135,
      rati: 0.1734019685632711,
      sbp: 0.0129101265425533,
      sbps5: 0.0102519142912905,
      town: 0.0332682012772873,
      AF: 0.8820923692805466,
      atypicalantipsy: 0.1304687985517351,
      corticosteroids: 0.4548539975044554,
      impotence2: 0.2225185908670538,
      migraine: 0.2558417807415991,
      ra: 0.2097065801395657,
      renal: 0.7185326128827438,
      semi: 0.1213303988204716,
      sle: 0.4401572174457522,
      treatedhyp: 0.5165987108269547,
      type1: 1.2343425521675175,
      type2: 0.8594207143093222,
      fh_cvd: 0.5405546900939016
    },
    i1: {
      s1: -0.2101113393351635,
      s2: 0.7526867644750319,
      s3: 0.9931588755640579,
      s4: 2.1331163414389076,
      AF: 3.4896675530623207,
      corticosteroids: 1.1708133653489108,
      impotence2: -1.506400985745431,
      migraine: 2.349115987140244,
      renal: -0.5065671632722369,
      treatedhyp: 6.511458109853267,
      type1: 5.337986487800653,
      type2: 3.646181740622131,
      bmi1: 31.004952956033886,
      bmi2: -111.29157184391643,
      fh_cvd: 2.7808628508531887,
      sbp: 0.0188585244698659,
      town: -0.1007554870063731
    },
    i2: {
      s1: -4985487027533e-16,
      s2: -7987563331739e-16,
      s3: -0.0083706184266251,
      s4: -7840031915564e-16,
      AF: -3499560834064e-16,
      corticosteroids: -2496045095297e-16,
      impotence2: -0.0011058218441227,
      migraine: 1989644604148e-16,
      renal: -0.0018325930166499,
      treatedhyp: 6383805310417e-16,
      type1: 6409780808753e-16,
      type2: -0.0024695695588868,
      bmi1: 0.0050380102356322,
      bmi2: -0.0130744830025243,
      fh_cvd: -247918099074e-15,
      sbp: -127187419159e-16,
      town: -932996423233e-16
    },
    center: { rati: 4.300998687744141, sbp: 128.5715789794922, sbps5: 8.756621360778809, town: 0.52630490064621 }
  };
  function qrisk3(p) {
    const isFemale = p.sex === "girls";
    const M = isFemale ? QRISK3_FEMALE : QRISK3_MALE;
    const age = p.age;
    if (!(age >= 25 && age <= 84)) return null;
    const bmiRaw = p.bmi;
    const bmi = Math.min(Math.max(bmiRaw, 20), 40);
    const dage = age / 10, dbmi = bmi / 10;
    let age1, age2;
    if (isFemale) {
      age1 = Math.pow(dage, -2) - 0.053274843841791;
      age2 = dage - 4.332503318786621;
    } else {
      age1 = Math.pow(dage, -1) - 0.234766781330109;
      age2 = Math.pow(dage, 3) - 77.2840805053711;
    }
    let bmi1, bmi2;
    if (isFemale) {
      bmi1 = Math.pow(dbmi, -2) - 0.154946178197861;
      bmi2 = Math.pow(dbmi, -2) * Math.log(dbmi) - 0.144462317228317;
    } else {
      bmi1 = Math.pow(dbmi, -2) - 0.149176135659218;
      bmi2 = Math.pow(dbmi, -2) * Math.log(dbmi) - 0.141913309693336;
    }
    const rati = (typeof p.rati === "number" ? p.rati : M.center.rati) - M.center.rati;
    const sbp = (typeof p.sbp === "number" ? p.sbp : M.center.sbp) - M.center.sbp;
    const sbps5 = (typeof p.sbps5 === "number" ? p.sbps5 : 0) - M.center.sbps5;
    const town = (typeof p.town === "number" ? p.town : 0) - M.center.town;
    const c = M.c, i1 = M.i1, i2 = M.i2;
    let a = 0;
    a += M.Iethrisk[p.ethnicity || 1] || 0;
    a += M.Ismoke[p.smoke || 0] || 0;
    a += age1 * c.age1 + age2 * c.age2 + bmi1 * c.bmi1 + bmi2 * c.bmi2;
    a += rati * c.rati + sbp * c.sbp + sbps5 * c.sbps5 + town * c.town;
    const B = {
      AF: p.af,
      atypicalantipsy: p.atypicalantipsy,
      corticosteroids: p.corticosteroids,
      migraine: p.migraine,
      ra: p.ra,
      renal: p.renal,
      semi: p.semi,
      sle: p.sle,
      treatedhyp: p.treatedhyp,
      type1: p.diabetes === 1,
      type2: p.diabetes === 2,
      fh_cvd: p.fh_cvd
    };
    if (!isFemale) B.impotence2 = p.impotence2;
    for (const k in B) if (B[k] && typeof c[k] === "number") a += c[k];
    const sKey = ["", "s1", "s2", "s3", "s4"][p.smoke || 0];
    if (sKey) {
      a += age1 * (i1[sKey] || 0) + age2 * (i2[sKey] || 0);
    }
    a += age1 * (bmi1 * i1.bmi1 + bmi2 * i1.bmi2) + age2 * (bmi1 * i2.bmi1 + bmi2 * i2.bmi2);
    a += age1 * (sbp * i1.sbp) + age2 * (sbp * i2.sbp);
    a += age1 * (town * i1.town) + age2 * (town * i2.town);
    for (const k in B) {
      if (!B[k]) continue;
      if (typeof i1[k] === "number") a += age1 * i1[k];
      if (typeof i2[k] === "number") a += age2 * i2[k];
    }
    const risk = 100 * (1 - Math.pow(M.survivor, Math.exp(a)));
    return risk;
  }
  function normalCDF(z) {
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const d = 0.39894228 * Math.exp(-z * z / 2);
    const p = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z >= 0 ? 1 - p : p;
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
    boys: { p3: [157, 159], p97: [186, 187] },
    girls: { p3: [146, 147], p97: [170, 171] }
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
    const inRange = (v, [lo, hi]) => v !== null && v >= lo && v <= hi;
    const ok = inRange(p3At18, bounds.p3) && inRange(p97At18, bounds.p97);
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
    const a0 = heightData.age_min, a1 = heightData.age_max;
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
    const plan = computeSquareGrid(plotWidth, a1 - a0, 1, ymax - ymin, yMajor);
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
    return /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", style: { maxWidth: `${width}px`, display: "block" }, xmlns: "http://www.w3.org/2000/svg" }, /* @__PURE__ */ React.createElement("rect", { x: "0", y: "0", width, height, fill: theme.page }), /* @__PURE__ */ React.createElement("rect", { x: "14", y: "14", width: width - 28, height: "40", fill: "#ffffff", rx: "4" }), /* @__PURE__ */ React.createElement("text", { x: width / 2, y: "40", textAnchor: "middle", fontSize: "16.5", fontWeight: "800", fill: "#1e293b" }, "WHO 2006 & IAP 2015 combined ", theme.name, " Chart \u2014 Height & Weight, 0\u201318 Years"), /* @__PURE__ */ React.createElement("rect", { x: m.l, y: m.t, width: plotR - m.l, height: plotB - m.t, fill: IAP_PAPER, stroke: IAP_GRID_MAJOR, strokeWidth: "1.2" }), yminors.map((v, i) => /* @__PURE__ */ React.createElement("line", { key: "ym" + i, x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), xminors.map((a, i) => /* @__PURE__ */ React.createElement("line", { key: "xmi" + i, x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MINOR, strokeWidth: "0.5" })), yticks.map((v) => /* @__PURE__ */ React.createElement("g", { key: "y" + v }, /* @__PURE__ */ React.createElement("line", { x1: m.l, y1: sy(v), x2: plotR, y2: sy(v), stroke: IAP_GRID_MAJOR, strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { x: m.l - 8, y: sy(v) + 3, textAnchor: "end", fontSize: "10", fill: "#57534e" }, v))), xticks.map((a) => /* @__PURE__ */ React.createElement("g", { key: "x" + a }, /* @__PURE__ */ React.createElement("line", { x1: sx(a), y1: m.t, x2: sx(a), y2: plotB, stroke: IAP_GRID_MAJOR, strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { x: sx(a), y: plotB + 16, textAnchor: "middle", fontSize: "10", fill: "#57534e" }, a))), /* @__PURE__ */ React.createElement("text", { x: (m.l + plotR) / 2, y: height - 46, textAnchor: "middle", fontSize: "12", fontWeight: "700", fill: "#334155" }, "Age in Years"), /* @__PURE__ */ React.createElement("text", { x: 24, y: (m.t + plotB) / 2, textAnchor: "middle", fontSize: "12", fontWeight: "700", fill: "#334155", transform: `rotate(-90 24 ${(m.t + plotB) / 2})` }, "Height in CM and Weight in KG"), renderCurveGroup(heightCurves, "height"), renderCurveGroup(weightCurves, "weight"), weightSerial.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: theme.point, strokeWidth: "1.6", strokeDasharray: "5,3", points: weightSerial.map((p) => `${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ") }), weightSerial.map((p, i) => /* @__PURE__ */ React.createElement("circle", { key: "ws" + i, cx: sx(p.age), cy: sy(p.value), r: "3", fill: "#ffffff", stroke: theme.point, strokeWidth: "1.5" })), heightSerial.length > 1 && /* @__PURE__ */ React.createElement("polyline", { fill: "none", stroke: theme.point, strokeWidth: "1.6", strokeDasharray: "5,3", points: heightSerial.map((p) => `${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ") }), heightSerial.map((p, i) => /* @__PURE__ */ React.createElement("circle", { key: "hs" + i, cx: sx(p.age), cy: sy(p.value), r: "3", fill: "#ffffff", stroke: theme.point, strokeWidth: "1.5" })), ageYears >= a0 && ageYears <= a1 && (heightValue > 0 || weightValue > 0) && /* @__PURE__ */ React.createElement("line", { x1: sx(ageYears), y1: m.t, x2: sx(ageYears), y2: plotB, stroke: theme.point, strokeWidth: "1", strokeDasharray: "2,3", opacity: "0.55" }), heightValue > 0 && !heightOutOfRange && ageYears >= a0 && ageYears <= a1 && labelBadge(heightValue, ageYears, "cm"), weightValue > 0 && !weightOutOfRange && ageYears >= a0 && ageYears <= a1 && labelBadge(weightValue, ageYears, "kg"), outOfRange && /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement("rect", { x: "14", y: "58", width: width - 28, height: "24", fill: "#fef2f2", stroke: "#fecaca", strokeWidth: "1", rx: "4" }), /* @__PURE__ */ React.createElement("text", { x: width / 2, y: "74", textAnchor: "middle", fontSize: "11", fontWeight: "800", fill: "#b91c1c" }, "\u26A0 Patient value is outside standard chart range.", heightOutOfRange ? ` Height ${heightValue}cm` : "", heightOutOfRange && weightOutOfRange ? " and" : "", weightOutOfRange ? ` Weight ${weightValue}kg` : "", " ", "not plotted \u2014 axis is fixed to the standard 0\u2013", ymax, " reference range.")), /* @__PURE__ */ React.createElement("text", { x: m.l, y: height - 26, fontSize: "8.5", fill: "#6b7280" }, heightData.reference), /* @__PURE__ */ React.createElement("text", { x: m.l, y: height - 14, fontSize: "8.5", fill: "#6b7280" }, 'Decision support only \u2014 not diagnostic; a clinician must verify all results. Red line = 3rd height percentile ("short below this line").'));
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
  function FraxToggleRow({ label, value, setter }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f8fafc" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "600", color: "#475569" } }, label), /* @__PURE__ */ React.createElement("div", { className: "toggle-pill" }, /* @__PURE__ */ React.createElement("button", { className: `toggle-btn ${value === "yes" ? "toggle-on" : "toggle-off"}`, onClick: () => setter("yes") }, "Yes"), /* @__PURE__ */ React.createElement("button", { className: `toggle-btn ${value === "no" ? "toggle-on" : "toggle-off"}`, onClick: () => setter("no") }, "No")));
  }
  function InputWithUnit({ label, value, onChange, placeholder, step, unit, accent }) {
    return /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, label), /* @__PURE__ */ React.createElement("div", { style: { position: "relative", display: "flex", alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        step: step || "any",
        placeholder: placeholder || "\u2014",
        value,
        onChange,
        className: "input-field",
        style: {
          paddingRight: unit ? "44px" : "12px",
          color: accent || "#1e293b",
          minWidth: 0,
          width: "100%"
        }
      }
    ), unit && /* @__PURE__ */ React.createElement("span", { style: { position: "absolute", right: "10px", fontSize: "10px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", pointerEvents: "none", whiteSpace: "nowrap" } }, unit)));
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
    return { metrics: s.fraxMetrics, hasManual: s.hasManualFrax };
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
      age: s.age,
      cholRatio: s.cholRatio,
      diabetes: s.diabetes,
      ethnicity: s.ethnicity,
      evalGender: s.evalGender,
      height: s.height,
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
      smokeCat: s.smokeCat,
      systolic: s.systolic,
      weight: s.weight
    };
  }
  function useLedger() {
    const s = useClinicalState();
    return {
      age: s.age,
      albuminuria: s.albuminuria,
      assessment: s.assessment,
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
    const s = useClinicalState();
    return {
      DECLARABLE_FLAGS: s.DECLARABLE_FLAGS,
      LC_API: s.LC_API,
      addOrSelectBox: s.addOrSelectBox,
      adjBusy: s.adjBusy,
      adjItems: s.adjItems,
      adjMsg: s.adjMsg,
      adjReviewer: s.adjReviewer,
      age: s.age,
      aiBusy: s.aiBusy,
      aiEstimate: s.aiEstimate,
      analysisUrl: s.analysisUrl,
      assessment: s.assessment,
      attachImage: s.attachImage,
      boneAge: s.boneAge,
      boneAgeSource: s.boneAgeSource,
      boneMetrics: s.boneMetrics,
      boneReport: s.boneReport,
      bonesIntoGrids: s.bonesIntoGrids,
      boxes: s.boxes,
      carpalStages: s.carpalStages,
      clearBox: s.clearBox,
      covBusy: s.covBusy,
      coverage: s.coverage,
      curveToText: s.curveToText,
      declaredFlags: s.declaredFlags,
      endLocDrag: s.endLocDrag,
      estimateDomain: s.estimateDomain,
      evalAge: s.evalAge,
      evalGender: s.evalGender,
      evalHeight: s.evalHeight,
      fatherHeight: s.fatherHeight,
      fbAge: s.fbAge,
      fbBusy: s.fbBusy,
      fbConfidence: s.fbConfidence,
      fbMethod: s.fbMethod,
      fbMsg: s.fbMsg,
      fbNote: s.fbNote,
      fbRater: s.fbRater,
      height: s.height,
      lcBtn: s.lcBtn,
      lcBusy: s.lcBusy,
      lcLocked: s.lcLocked,
      lcMsg: s.lcMsg,
      letterResult: s.letterResult,
      loadAdjudication: s.loadAdjudication,
      loadCoverage: s.loadCoverage,
      loadLetterTables: s.loadLetterTables,
      loadLocalCohort: s.loadLocalCohort,
      loadMonitoring: s.loadMonitoring,
      localCohort: s.localCohort,
      lcohBusy: s.lcohBusy,
      locBusy: s.locBusy,
      locImg: s.locImg,
      locMsg: s.locMsg,
      locRef: s.locRef,
      localizeBones: s.localizeBones,
      ltBusy: s.ltBusy,
      ltMsg: s.ltMsg,
      ltSection: s.ltSection,
      ltSex: s.ltSex,
      ltStatus: s.ltStatus,
      ltTables: s.ltTables,
      monBusy: s.monBusy,
      monitoring: s.monitoring,
      motherHeight: s.motherHeight,
      onLocMove: s.onLocMove,
      patientCode: s.patientCode,
      radiograph: s.radiograph,
      resolveAdjudication: s.resolveAdjudication,
      reviseAssessment: s.reviseAssessment,
      runEstimate: s.runEstimate,
      rusStages: s.rusStages,
      saveBoxes: s.saveBoxes,
      saveDraft: s.saveDraft,
      saveLetterTables: s.saveLetterTables,
      selBone: s.selBone,
      setAdjReviewer: s.setAdjReviewer,
      setAssessment: s.setAssessment,
      setBoneAge: s.setBoneAge,
      setBoneAgeSource: s.setBoneAgeSource,
      setCarpalStages: s.setCarpalStages,
      setEstimateDomain: s.setEstimateDomain,
      setFatherHeight: s.setFatherHeight,
      setFbAge: s.setFbAge,
      setFbConfidence: s.setFbConfidence,
      setFbMethod: s.setFbMethod,
      setFbNote: s.setFbNote,
      setFbRater: s.setFbRater,
      setImageDomain: s.setImageDomain,
      setLcBusy: s.setLcBusy,
      setLcMsg: s.setLcMsg,
      setLocImg: s.setLocImg,
      setLtCurve: s.setLtCurve,
      setLtPoint: s.setLtPoint,
      setLtSection: s.setLtSection,
      setLtSex: s.setLtSex,
      setLtSexCurve: s.setLtSexCurve,
      setLtTables: s.setLtTables,
      setMotherHeight: s.setMotherHeight,
      setPatientCode: s.setPatientCode,
      setRefExpected: s.setRefExpected,
      setRusStages: s.setRusStages,
      setShowAudit: s.setShowAudit,
      showAudit: s.showAudit,
      startBoxDrag: s.startBoxDrag,
      submitFeedback: s.submitFeedback,
      toggleAudit: s.toggleAudit,
      toggleDeclaredFlag: s.toggleDeclaredFlag,
      tw3Config: s.tw3Config,
      useGridAsReference: s.useGridAsReference
    };
  }

  // frontend/src/boneAgeHandlers.js
  function useBoneAgeHandlers(s) {
    const {
      adjReviewer,
      age,
      aiEstimate,
      approverName,
      assessment,
      boxes,
      boxesRef,
      carpalStages,
      coverage,
      declaredFlags,
      estimateDomain,
      evalAge,
      evalGender,
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
      if (evalGender !== "boys" && evalGender !== "girls") {
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
              sex: evalGender,
              chronological_age_years: age !== "" ? Number(age) : null,
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
    const calculateAssessment = async () => {
      if (!assessment) return;
      setLcBusy(true);
      setLcMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/calculate`, { method: "POST" });
        const d = await res.json();
        if (!res.ok) {
          setLcMsg({ type: "err", text: d.detail || "calculate failed" });
        } else {
          setAssessment(d);
          if (d.bone_age_years != null) {
            setBoneAge(Number(d.bone_age_years.toFixed(1)));
            setBoneAgeSource("rus");
          }
          setLcMsg({ type: "ok", text: `Calculated \xB7 RUS ${d.total_rus_score} \u2192 ${d.bone_age_years} yr` });
        }
      } catch (e) {
        setLcMsg({ type: "err", text: String(e.message || e) });
      } finally {
        setLcBusy(false);
      }
    };
    const approveAssessment = async () => {
      if (!assessment) return;
      if (!approverName.trim()) {
        setLcMsg({ type: "err", text: "Enter the approving doctor name." });
        return;
      }
      setLcBusy(true);
      setLcMsg(null);
      try {
        const res = await fetch(`${LC_API}/${assessment.id}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved_by: approverName.trim() })
        });
        const d = await res.json();
        if (!res.ok) setLcMsg({ type: "err", text: d.detail || "approve failed" });
        else {
          setAssessment(d);
          setLcMsg({ type: "ok", text: `Approved by ${d.approved_by}` });
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
          sex: evalGender === "boys" || evalGender === "girls" ? evalGender : null,
          chronological_age_years: evalAge || null,
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
      if (evalGender !== "boys" && evalGender !== "girls") {
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
        fd.append("sex", evalGender);
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
      const rus = { ...rusStages };
      const carp = {};
      Object.entries(carpalStages).forEach(([n, g]) => carp[carpalCode(n)] = g);
      setLtTables((prev) => {
        const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
        t.reference_cases = [{
          id: "clinic-ref-1",
          sex: evalGender === "girls" ? "girls" : "boys",
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
      _emptyLt,
      loadLetterTables,
      setLtPoint,
      curveToText,
      parseCurve,
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
  var { useState, useRef, useEffect } = React;
  var DECLARABLE_FLAGS = [
    ["FRACTURE", "Fracture"],
    ["CAST_OR_HARDWARE", "Cast / hardware"],
    ["WRONG_LATERALITY", "Wrong side"],
    ["CLIPPED_DIGITS", "Clipped anatomy"],
    ["SEVERE_DEFORMITY", "Deformity"],
    ["FOREIGN_OBJECT", "Foreign object"]
  ];
  function useBoneAgeState() {
    const [boneAge, setBoneAge] = useState("");
    const [boneAgeSource, setBoneAgeSource] = useState("manual");
    const [rusStages, setRusStages] = useState({});
    const [carpalStages, setCarpalStages] = useState({});
    const [tw3Config, setTw3Config] = useState(null);
    const [rusResult, setRusResult] = useState(null);
    const [letterResult, setLetterResult] = useState(null);
    const [boneReport, setBoneReport] = useState(null);
    const [patientCode, setPatientCode] = useState("");
    const [approverName, setApproverName] = useState("");
    const [assessment, setAssessment] = useState(null);
    const [lcMsg, setLcMsg] = useState(null);
    const [lcBusy, setLcBusy] = useState(false);
    const [showAudit, setShowAudit] = useState(false);
    const [radiograph, setRadiograph] = useState(null);
    const [coverage, setCoverage] = useState(null);
    const [covBusy, setCovBusy] = useState(false);
    const [monitoring, setMonitoring] = useState(null);
    const [monBusy, setMonBusy] = useState(false);
    const [localCohort, setLocalCohort] = useState(null);
    const [lcohBusy, setLcohBusy] = useState(false);
    const [adjItems, setAdjItems] = useState(null);
    const [adjBusy, setAdjBusy] = useState(false);
    const [adjReviewer, setAdjReviewer] = useState("");
    const [adjMsg, setAdjMsg] = useState(null);
    const [ltTables, setLtTables] = useState(null);
    const [ltStatus, setLtStatus] = useState(null);
    const [ltSection, setLtSection] = useState("rus");
    const [ltSex, setLtSex] = useState("boys");
    const [ltMsg, setLtMsg] = useState(null);
    const [ltBusy, setLtBusy] = useState(false);
    const [boxes, setBoxes] = useState({});
    const [locImg, setLocImg] = useState(null);
    const [locBusy, setLocBusy] = useState(false);
    const [locMsg, setLocMsg] = useState(null);
    const [selBone, setSelBone] = useState(null);
    const locDrag = useRef(null);
    const locRef = useRef(null);
    const boxesRef = useRef({});
    useEffect(() => {
      boxesRef.current = boxes;
    }, [boxes]);
    const [aiEstimate, setAiEstimate] = useState(null);
    const [estimateDomain, setEstimateDomain] = useState("unknown");
    const [declaredFlags, setDeclaredFlags] = useState([]);
    const [lastFilm, setLastFilm] = useState(null);
    const [fbAge, setFbAge] = useState("");
    const [fbMethod, setFbMethod] = useState("tw3-rus");
    const [fbConfidence, setFbConfidence] = useState("medium");
    const [fbRater, setFbRater] = useState("");
    const [fbNote, setFbNote] = useState("");
    const [fbMsg, setFbMsg] = useState(null);
    const [fbBusy, setFbBusy] = useState(false);
    const [aiBusy, setAiBusy] = useState(false);
    const [fatherHeight, setFatherHeight] = useState("");
    const [motherHeight, setMotherHeight] = useState("");
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
      rusResult,
      setRusResult,
      letterResult,
      setLetterResult,
      boneReport,
      setBoneReport,
      patientCode,
      setPatientCode,
      approverName,
      setApproverName,
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

  // frontend/src/qriskState.js
  var { useState: useState2 } = React;
  function useQriskInputs() {
    const [ethnicity, setEthnicity] = useState2(2);
    const [smokeCat, setSmokeCat] = useState2(0);
    const [diabetes, setDiabetes] = useState2(0);
    const [cholRatio, setCholRatio] = useState2("");
    const [sbpSD, setSbpSD] = useState2("");
    const [qAF, setQAF] = useState2("no");
    const [qTreatedHtn, setQTreatedHtn] = useState2("no");
    const [qRA, setQRA] = useState2("no");
    const [qCKD, setQCKD] = useState2("no");
    const [qMigraine, setQMigraine] = useState2("no");
    const [qSLE, setQSLE] = useState2("no");
    const [qSMI, setQSMI] = useState2("no");
    const [qAtypAntipsy, setQAtypAntipsy] = useState2("no");
    const [qCortico, setQCortico] = useState2("no");
    const [qED, setQED] = useState2("no");
    const [qFhCvd, setQFhCvd] = useState2("no");
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
  function RenalPanel() {
    const { metrics, hasManual } = useRenal();
    const { evalAge, age, height } = usePatient();
    const renalMetrics = metrics;
    const hasManualRenal = hasManual;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Renal Workspace \xB7 eGFR",
        subtitle: `Multi-equation clearance monitoring \xB7 ${renalMetrics.formulaName}`,
        badge: hasManualRenal ? `Stage ${renalMetrics.ckdStage}` : null,
        badgeVariant: hasManualRenal ? renalMetrics.stageVariant : "info"
      }
    ), !hasManualRenal ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter serum creatinine",
        hint: "Serum creatinine \u2014 plus age, sex and height \u2014 is required to estimate GFR. No value is shown until it is entered."
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { ...heroTone(renalMetrics.stageVariant), borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b", marginBottom: "8px" } }, "Estimated GFR"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: renalMetrics.stageVariant === "high" ? "#b91c1c" : renalMetrics.stageVariant === "mid" ? "#b45309" : "#15803d", lineHeight: 1 } }, renalMetrics.egfr.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#6366f1", fontWeight: "600" } }, "mL/min/1.73 m\xB2")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#818cf8", marginTop: "4px" } }, "via ", renalMetrics.formulaName)), /* @__PURE__ */ React.createElement("div", { style: { textAlign: "right" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: `Stage ${renalMetrics.ckdStage} \xB7 ${renalMetrics.ckdStageDesc}`, variant: renalMetrics.stageVariant }), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "11px", color: "#6366f1", fontWeight: "600" } }, renalMetrics.isPediatric ? "\u25B8 Pediatric Mode" : "\u25B8 Adult Mode"))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" } }, "KDIGO CKD Stage Map"), /* @__PURE__ */ React.createElement("div", { className: "ckd-stage" }, [
      ["G1", "\u2265 90", "Normal"],
      ["G2", "60\u201389", "Mild \u2193"],
      ["G3", "30\u201359", "Mod \u2193"],
      ["G4", "15\u201329", "Severe \u2193"],
      ["G5", "< 15", "Failure"]
    ].map(([stage, range, desc]) => /* @__PURE__ */ React.createElement("div", { key: stage, className: `ckd-chip ${renalMetrics.ckdStage === stage ? `ckd-active-${stage.toLowerCase()}` : "ckd-inactive"}` }, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", fontSize: "11px" } }, stage), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", marginTop: "2px", fontWeight: "600", opacity: 0.85 } }, range), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", marginTop: "1px", opacity: 0.7 } }, desc))))), !renalMetrics.isPediatric && /* @__PURE__ */ React.createElement("div", { className: "secondary-grid", style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" } }, "Cockcroft-Gault CrCl"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "22px", fontWeight: "900", color: "#334155" } }, renalMetrics.cg ? renalMetrics.cg.toFixed(1) : "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "mL/min")), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" } }, "MDRD Clearance"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "22px", fontWeight: "900", color: "#334155" } }, renalMetrics.mdrd ? renalMetrics.mdrd.toFixed(1) : "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "2px" } }, "mL/min/1.73 m\xB2")))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "KDIGO G1 \u2265 90 \xB7 G2 60\u201389 \xB7 G3 30\u201359 \xB7 G4 15\u201329 \xB7 G5 < 15 mL/min/1.73 m\xB2"));
  }

  // frontend/src/panels/LiverPanel.jsx
  function LiverPanel() {
    const { metrics, hasManual } = useLiver();
    const { evalAge, age, height } = usePatient();
    const liverMetrics = metrics;
    const hasManualLiver = hasManual;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "Liver Fibrosis \xB7 FIB-4 Index",
        subtitle: "Non-invasive hepatic fibrosis staging \u2014 Age \xB7 AST \xB7 ALT \xB7 Platelets",
        badge: hasManualLiver ? liverMetrics.interpretation : null,
        badgeVariant: hasManualLiver ? liverMetrics.variant : "info"
      }
    ), !hasManualLiver ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter AST, ALT & platelets",
        hint: "FIB-4 needs AST, ALT and platelet count (plus age). No score is shown until all three are entered."
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { ...heroTone(liverMetrics.variant), borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b", marginBottom: "8px" } }, "FIB-4 Score"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: liverMetrics.variant === "high" ? "#b91c1c" : liverMetrics.variant === "mid" ? "#b45309" : "#15803d", lineHeight: 1 } }, liverMetrics.fib4.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#64748b", fontWeight: "600" } }, "index")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, "Formula: (Age \xD7 AST) / (Platelets \xD7 \u221AALT)")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(StatusBadge, { text: liverMetrics.interpretation, variant: liverMetrics.variant }), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#64748b", marginTop: "10px", maxWidth: "200px", lineHeight: "1.5" } }, liverMetrics.details))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "20px", background: "#f8fafc", borderRadius: "12px", padding: "16px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "12px" } }, "Risk Scale"), /* @__PURE__ */ React.createElement("div", { style: { position: "relative", height: "10px", borderRadius: "99px", background: "linear-gradient(to right, #22c55e 0%, #22c55e 48%, #eab308 48%, #eab308 74%, #ef4444 74%, #ef4444 100%)" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: "-4px", left: `${Math.min(Math.max(liverMetrics.fib4 / 5 * 100, 1), 99)}%`, width: "18px", height: "18px", borderRadius: "50%", background: "white", border: "3px solid #334155", transform: "translateX(-50%)", boxShadow: "0 1px 4px rgba(0,0,0,0.2)" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", fontWeight: "700", color: "#94a3b8" } }, /* @__PURE__ */ React.createElement("span", null, "0"), /* @__PURE__ */ React.createElement("span", { style: { color: "#16a34a" } }, "Low < 1.30"), /* @__PURE__ */ React.createElement("span", { style: { color: "#d97706" } }, "Indeterminate 1.30\u20132.67"), /* @__PURE__ */ React.createElement("span", { style: { color: "#dc2626" } }, "High > 2.67"))), evalAge < 18 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#92400e", lineHeight: "1.6" } }, "\u26A0 FIB-4 is not validated in pediatric cohorts (age < 18). Interpret with caution.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "FIB-4 ranges \u2014 Low: < 1.30 \xB7 Indeterminate: 1.30\u20132.67 \xB7 High: \u2265 2.67", evalAge > 65 ? "  (Age > 65 \u2014 indeterminate threshold adjusted to 2.0)" : ""));
  }

  // frontend/src/panels/FraxPanel.jsx
  function FraxPanel() {
    const { metrics, hasManual } = useFrax();
    const { evalAge, age, height, weight } = usePatient();
    const fraxMetrics = metrics;
    const hasManualFrax = hasManual;
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "FRAX Plus \xB7 10-Year Fracture Risk",
        subtitle: "India (Asian) \xB7 No femoral neck BMD \xB7 Sheffield intervention thresholds",
        badge: hasManualFrax ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "High Risk" : "Low Risk" : null,
        badgeVariant: hasManualFrax ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "high" : "low" : "info"
      }
    ), !hasManualFrax ? /* @__PURE__ */ React.createElement(
      EmptyState,
      {
        title: "Enter age, sex, height & weight",
        hint: "FRAX estimates 10-year fracture risk from demographics plus the risk factors on the left. No probability is shown until the core measurements are entered."
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, evalAge < 40 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#92400e", lineHeight: "1.6" } }, "\u26A0 FRAX is calibrated for ages 40\u201390. Current age adjusted to the age-40 baseline model."), /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(fraxMetrics.isHighMof ? "high" : "low"), borderRadius: "16px", padding: "22px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "Major Osteoporotic Fracture"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: fraxMetrics.isHighMof ? "#dc2626" : "#16a34a", lineHeight: 1 } }, fraxMetrics.mofProb.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "10-yr probability \u2014 spine, hip, forearm, shoulder")), /* @__PURE__ */ React.createElement(StatusBadge, { text: fraxMetrics.isHighMof ? "High Risk \u2265 20%" : "Low Risk < 20%", variant: fraxMetrics.isHighMof ? "high" : "low" })), /* @__PURE__ */ React.createElement(ProbBar, { prob: fraxMetrics.mofProb, maxProb: 40, threshold: 20 })), /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(fraxMetrics.isHighHf ? "high" : "low"), borderRadius: "16px", padding: "22px", marginTop: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "Hip Fracture"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: fraxMetrics.isHighHf ? "#dc2626" : "#16a34a", lineHeight: 1 } }, fraxMetrics.hfProb.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "10-yr probability of hip fracture")), /* @__PURE__ */ React.createElement(StatusBadge, { text: fraxMetrics.isHighHf ? "High Risk \u2265 3%" : "Low Risk < 3%", variant: fraxMetrics.isHighHf ? "high" : "low" })), /* @__PURE__ */ React.createElement(ProbBar, { prob: fraxMetrics.hfProb, maxProb: 15, threshold: 3 }))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "20px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "Sheffield thresholds: Treatment recommended when MOF \u2265 20% or Hip Fracture \u2265 3% (10-year absolute risk)."));
  }

  // frontend/src/panels/OverviewPanel.jsx
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
    })), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#4338ca", lineHeight: "1.7" } }, "Enter patient data in the left panel \u2014 every module recalculates automatically. A grey dot means that module still needs input; green / amber / red reflect the result. Decision support only \u2014 a clinician must verify every value."));
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
    const inRange = evalAge >= 0 && evalAge <= 19;
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
    ) : !inRange ? /* @__PURE__ */ React.createElement(
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
    const { age, cholRatio, diabetes, ethnicity, evalGender, height, qAF, qAtypAntipsy, qCKD, qCortico, qED, qFhCvd, qMigraine, qRA, qSLE, qSMI, qTreatedHtn, qriskMetrics, sbpSD, setCholRatio, setDiabetes, setEthnicity, setQAF, setQAtypAntipsy, setQCKD, setQCortico, setQED, setQFhCvd, setQMigraine, setQRA, setQSLE, setQSMI, setQTreatedHtn, setSbpSD, setSmokeCat, smokeCat, systolic, weight } = useQrisk();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement(
      SectionHeader,
      {
        title: "QRISK3 \xB7 10-Year Cardiovascular Risk",
        subtitle: "Hippisley-Cox 2017 (ClinRisk open source) \xB7 South-Asian ethnicity aware",
        badge: qriskMetrics.risk !== null ? qriskMetrics.band : "Age 25\u201384",
        badgeVariant: qriskMetrics.risk !== null ? qriskMetrics.variant : "neutral"
      }
    ), !qriskMetrics.inAgeRange && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "10px", padding: "12px 14px", fontSize: "12px", color: "#92400e", lineHeight: "1.6" } }, "\u26A0 QRISK3 is validated for ages 25\u201384. Set the patient's age in that range (Demographics) to compute risk."), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Ethnicity"), /* @__PURE__ */ React.createElement("select", { value: ethnicity, onChange: (e) => setEthnicity(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 1 }, "White / not stated"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Indian"), /* @__PURE__ */ React.createElement("option", { value: 3 }, "Pakistani"), /* @__PURE__ */ React.createElement("option", { value: 4 }, "Bangladeshi"), /* @__PURE__ */ React.createElement("option", { value: 5 }, "Other Asian"), /* @__PURE__ */ React.createElement("option", { value: 6 }, "Black Caribbean"), /* @__PURE__ */ React.createElement("option", { value: 7 }, "Black African"), /* @__PURE__ */ React.createElement("option", { value: 8 }, "Chinese"), /* @__PURE__ */ React.createElement("option", { value: 9 }, "Other"))), /* @__PURE__ */ React.createElement("div", { className: "split-grid" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Smoking"), /* @__PURE__ */ React.createElement("select", { value: smokeCat, onChange: (e) => setSmokeCat(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 0 }, "Non-smoker"), /* @__PURE__ */ React.createElement("option", { value: 1 }, "Ex-smoker"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Light (< 10/day)"), /* @__PURE__ */ React.createElement("option", { value: 3 }, "Moderate (10\u201319/day)"), /* @__PURE__ */ React.createElement("option", { value: 4 }, "Heavy (20+/day)"))), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Diabetes"), /* @__PURE__ */ React.createElement("select", { value: diabetes, onChange: (e) => setDiabetes(parseInt(e.target.value)), className: "input-field", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("option", { value: 0 }, "None"), /* @__PURE__ */ React.createElement("option", { value: 1 }, "Type 1"), /* @__PURE__ */ React.createElement("option", { value: 2 }, "Type 2")))), /* @__PURE__ */ React.createElement("div", { className: "split-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Total : HDL Cholesterol ratio", value: cholRatio, onChange: (e) => setCholRatio(e.target.value), placeholder: "e.g. 4.0", step: "0.1", unit: "ratio" }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "SBP variability (SD, optional)", value: sbpSD, onChange: (e) => setSbpSD(e.target.value), placeholder: "mmHg SD", step: "0.1", unit: "SD" })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", lineHeight: "1.5" } }, "Uses BMI (from height/weight) and systolic BP from the left panel. Blank cholesterol ratio / SBP-SD contribute neutrally (QRISK3 convention). Townsend deprivation is set to 0 (UK-only index)."), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "6px 14px" } }, /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Atrial fibrillation", value: qAF, setter: setQAF }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "On BP treatment", value: qTreatedHtn, setter: setQTreatedHtn }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "CKD stage 3\u20135", value: qCKD, setter: setQCKD }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Rheumatoid arthritis", value: qRA, setter: setQRA }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Migraine", value: qMigraine, setter: setQMigraine }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "SLE (lupus)", value: qSLE, setter: setQSLE }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Severe mental illness", value: qSMI, setter: setQSMI }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Atypical antipsychotics", value: qAtypAntipsy, setter: setQAtypAntipsy }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Regular corticosteroids", value: qCortico, setter: setQCortico }), evalGender === "boys" && /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Erectile dysfunction", value: qED, setter: setQED }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Family history of CVD", value: qFhCvd, setter: setQFhCvd }))), qriskMetrics.risk !== null && /* @__PURE__ */ React.createElement("div", { style: { ...heroTone(qriskMetrics.variant), borderRadius: "16px", padding: "22px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" } }, "10-Year CVD Risk"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontSize: "44px", fontWeight: "900", color: qriskMetrics.variant === "high" ? "#dc2626" : qriskMetrics.variant === "mid" ? "#d97706" : "#16a34a", lineHeight: 1 } }, qriskMetrics.risk.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "18px", fontWeight: "700", color: "#64748b" } }, "%")), qriskMetrics.typical !== null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "Healthy baseline (same age/sex/ethnicity): ", qriskMetrics.typical.toFixed(1), "%")), /* @__PURE__ */ React.createElement(StatusBadge, { text: qriskMetrics.band, variant: qriskMetrics.variant })), /* @__PURE__ */ React.createElement(ProbBar, { prob: qriskMetrics.risk, maxProb: 40, threshold: 10 })), qriskMetrics.risk !== null && (() => {
      const imp = [];
      if (qriskMetrics.missingRatio) imp.push("cholesterol ratio");
      if (systolic === "") imp.push("systolic BP");
      if (sbpSD === "") imp.push("SBP variability (SD)");
      return imp.length ? /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "10.5px", color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "7px 10px", lineHeight: "1.5" } }, "\u26A0 Estimated with defaulted inputs: ", /* @__PURE__ */ React.createElement("strong", null, imp.join(", ")), ". Enter these for a patient-specific score.") : null;
    })(), qriskMetrics.risk === null && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "12px", padding: "14px 16px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: "#991b1b" } }, "QRISK3 not applicable"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.5" } }, !qriskMetrics.inAgeRange ? "QRISK3 is validated only for adults aged 25\u201384. This patient is outside that range \u2014 no score is shown." : "Enter height and weight (BMI) to compute the score.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "10px", padding: "12px 14px", fontSize: "11px", color: "#4338ca", lineHeight: "1.7" } }, /* @__PURE__ */ React.createElement("strong", null, "India note:"), " QRISK3 is derived on a UK cohort. Its Indian/South-Asian ethnicity term raises risk relative to White, but studies suggest it may still under-estimate true risk in Indians. Treat \u2265 10% as the usual statin-consideration threshold, and interpret alongside the ", /* @__PURE__ */ React.createElement("strong", null, "Lipid Association of India"), " risk stratification and ICMR guidance. QRISK3 does not apply to established CVD, familial hypercholesterolaemia, or type-appropriate secondary prevention."), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "18px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "QRISK3-2017 \xB7 Hippisley-Cox J et al., BMJ 2017;357:j2099 \xB7 ClinRisk open-source coefficients (GNU LGPL), verified against the CRAN QRISK3 reference. Clinician must verify \u2014 decision support only, not a diagnostic device."));
  }

  // frontend/src/panels/LedgerPanel.jsx
  function LedgerPanel() {
    const { age, albuminuria, assessment, chronicityStatus, creatinine, height, logCurrentData, setTimeline, timeline, weight } = useLedger();
    return /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column", gap: "16px" } }, /* @__PURE__ */ React.createElement("div", { className: "timeline-header" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("h3", { style: { fontSize: "13px", fontWeight: "800", color: "#334155" } }, "CKD Progression Ledger"), /* @__PURE__ */ React.createElement("p", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "3px" } }, "Session snapshots \u2014 chronicity assessment over \u2265 90 days")), /* @__PURE__ */ React.createElement("div", { className: "timeline-actions" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: logCurrentData,
        style: { padding: "7px 16px", background: "#4f46e5", color: "white", border: "none", borderRadius: "9px", fontSize: "12px", fontWeight: "700", cursor: "pointer", boxShadow: "0 1px 4px rgba(79,70,229,0.3)", transition: "background 0.15s" },
        onMouseEnter: (e) => e.target.style.background = "#4338ca",
        onMouseLeave: (e) => e.target.style.background = "#4f46e5"
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
    })())), timeline.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 0", gap: "12px", textAlign: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "52px", height: "52px", borderRadius: "50%", background: "#f1f5f9", display: "flex", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#94a3b8", strokeWidth: "2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M12 5v14M5 12l7 7 7-7" }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "700", color: "#64748b" } }, "No snapshots logged yet"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, 'Enter patient data and click "Log Snapshot" to begin tracking.')) : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto", borderRadius: "12px", border: "1px solid #e2e8f0" }, className: "custom-scrollbar" }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", minWidth: "580px", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { background: "#f8fafc", borderBottom: "1px solid #e2e8f0" } }, ["Date", "Age", "Ht / Wt", "SCr", "eGFR", "ACR", "FIB-4"].map((h) => /* @__PURE__ */ React.createElement("th", { key: h, style: { padding: "10px 12px", textAlign: "left", fontWeight: "800", color: "#64748b", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" } }, h)))), /* @__PURE__ */ React.createElement("tbody", null, timeline.map((item, idx) => /* @__PURE__ */ React.createElement("tr", { key: item.id, style: { borderBottom: "1px solid #f1f5f9", background: idx % 2 === 0 ? "white" : "#fafbfc" } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#1e293b" } }, item.date), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", color: "#475569" } }, item.age.toFixed(1), " y"), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", color: "#64748b" } }, item.height, " / ", item.weight), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#475569" } }, item.creatinine), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "800", color: "#4f46e5" } }, item.egfr), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("span", { style: { padding: "2px 8px", borderRadius: "99px", fontSize: "10px", fontWeight: "700", background: "#eef2ff", color: "#4338ca", border: "1px solid #c7d2fe" } }, item.albuminuria)), /* @__PURE__ */ React.createElement("td", { style: { padding: "10px 12px", fontWeight: "700", color: "#059669" } }, item.fib4 !== null ? item.fib4 : "\u2014")))))));
  }

  // frontend/src/panels/BoneAgePanel.jsx
  function BoneAgePanel() {
    const {
      DECLARABLE_FLAGS: DECLARABLE_FLAGS2,
      LC_API,
      addOrSelectBox,
      adjBusy,
      adjItems,
      adjMsg,
      adjReviewer,
      age,
      aiBusy,
      aiEstimate,
      analysisUrl,
      assessment,
      attachImage,
      boneAge,
      boneAgeSource,
      boneMetrics,
      boneReport,
      bonesIntoGrids,
      boxes,
      carpalStages,
      clearBox,
      covBusy,
      coverage,
      curveToText,
      declaredFlags,
      endLocDrag,
      estimateDomain,
      evalAge,
      evalGender,
      evalHeight,
      fatherHeight,
      fbAge,
      fbBusy,
      fbConfidence,
      fbMethod,
      fbMsg,
      fbNote,
      fbRater,
      height,
      lcBtn,
      lcBusy,
      lcLocked,
      lcMsg,
      letterResult,
      loadAdjudication,
      loadCoverage,
      loadLetterTables,
      loadLocalCohort,
      loadMonitoring,
      localCohort,
      lcohBusy,
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
      runEstimate,
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
      setEstimateDomain,
      setFatherHeight,
      setFbAge,
      setFbConfidence,
      setFbMethod,
      setFbNote,
      setFbRater,
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
      submitFeedback,
      toggleAudit,
      toggleDeclaredFlag,
      tw3Config,
      useGridAsReference
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
    })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", color: "#94a3b8", marginTop: "3px", lineHeight: "1.4" } }, "Any of these makes the AI estimate abstain \u2014 a whole-hand model can't read these films.")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, minWidth: "200px" } }, aiBusy && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#4338ca", fontWeight: "600" } }, "Analysing locally\u2026"), aiEstimate && aiEstimate.error && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#b45309", fontWeight: "600" } }, aiEstimate.error), aiEstimate && aiEstimate.accepted === false && /* @__PURE__ */ React.createElement("div", { style: { background: "#fef2f2", border: "1.5px solid #fecaca", borderRadius: "10px", padding: "10px 12px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: "#991b1b" } }, "\u26A0 Manual assessment required"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10.5px", color: "#b91c1c", marginTop: "4px", lineHeight: "1.5" } }, aiEstimate.message), aiEstimate.quality && aiEstimate.quality.hard_flags.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#7f1d1d", marginTop: "5px", fontWeight: "700" } }, "Flags: ", aiEstimate.quality.hard_flags.map((f) => f.replace(/_/g, " ")).join(", ")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9.5px", color: "#94a3b8", marginTop: "5px" } }, "No AI age is shown \u2014 grade the bones manually below.")), aiEstimate && aiEstimate.available === false && aiEstimate.accepted !== false && aiEstimate.message && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#b45309", fontWeight: "600" } }, aiEstimate.message), aiEstimate && aiEstimate.bone_age_years != null && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#6b21a8", fontWeight: "700" } }, "Bone age from this X\u2011ray"), /* @__PURE__ */ React.createElement("div", { style: { fontWeight: "900", color: "#5b21b6", lineHeight: 1 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "34px" } }, aiEstimate.bone_age_years), " ", /* @__PURE__ */ React.createElement("span", { style: { fontSize: "14px" } }, "yr")), aiEstimate.ci_low_years != null && aiEstimate.ci_high_years != null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#7c3aed", fontWeight: "700", marginTop: "3px" } }, aiEstimate.interval_kind === "conformal" ? `${Math.round(parseFloat(aiEstimate.interval_coverage) * 100)}% interval` : "Likely range", " ", aiEstimate.ci_low_years, "\u2013", aiEstimate.ci_high_years, " yr", /* @__PURE__ */ React.createElement("span", { style: { fontWeight: "500", color: "#a78bfa" } }, " ", aiEstimate.interval_kind === "conformal" ? `(conformal \xB7 \xB1${aiEstimate.uncertainty_months} mo, held-out RSNA)` : `(\xB1${aiEstimate.uncertainty_months} mo MAE \u2014 approx, not calibrated)`)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#7c3aed", marginTop: "2px" } }, "Greulich\u2013Pyle whole-image \xB7 NOT TW3", aiEstimate.model_version ? ` \xB7 ${aiEstimate.model_version}` : ""), aiEstimate.quality_warning && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#b45309", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "7px", padding: "6px 8px", marginTop: "6px", lineHeight: "1.5" } }, "\u26A0 ", aiEstimate.quality_warning), aiEstimate.population_note && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#64748b", marginTop: "6px", lineHeight: "1.5" } }, aiEstimate.population_note), /* @__PURE__ */ React.createElement("button", { onClick: () => {
      setBoneAge(Number(aiEstimate.bone_age_years.toFixed(1)));
      setBoneAgeSource("manual");
    }, style: { marginTop: "8px", padding: "6px 12px", background: "#16a34a", color: "white", border: "none", borderRadius: "8px", fontSize: "11px", fontWeight: "700", cursor: "pointer" } }, "Use as bone age")))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "14px", paddingTop: "14px", borderTop: "1px dashed #ddd6fe" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#6b21a8", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "8px" } }, "Is this right? Suggest the correct bone age"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("div", { style: { minWidth: "120px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Correct bone age (yr)"), /* @__PURE__ */ React.createElement("input", { type: "number", step: "0.1", min: "0", max: "25", value: fbAge, onChange: (e) => setFbAge(e.target.value), placeholder: "e.g. 11.5", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } })), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "130px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Method used"), /* @__PURE__ */ React.createElement("select", { value: fbMethod, onChange: (e) => setFbMethod(e.target.value), className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("option", { value: "tw3-rus" }, "TW3-RUS"), /* @__PURE__ */ React.createElement("option", { value: "greulich-pyle" }, "Greulich\u2013Pyle"), /* @__PURE__ */ React.createElement("option", { value: "clinical" }, "Clinical judgement"), /* @__PURE__ */ React.createElement("option", { value: "other" }, "Other"))), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "110px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Confidence"), /* @__PURE__ */ React.createElement("select", { value: fbConfidence, onChange: (e) => setFbConfidence(e.target.value), className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } }, /* @__PURE__ */ React.createElement("option", { value: "high" }, "High"), /* @__PURE__ */ React.createElement("option", { value: "medium" }, "Medium"), /* @__PURE__ */ React.createElement("option", { value: "low" }, "Low"))), /* @__PURE__ */ React.createElement("div", { style: { minWidth: "120px" } }, /* @__PURE__ */ React.createElement("label", { style: { fontSize: "9px", fontWeight: "800", color: "#7c3aed", textTransform: "uppercase", letterSpacing: ".05em", display: "block", marginBottom: "3px" } }, "Your initials / ID"), /* @__PURE__ */ React.createElement("input", { value: fbRater, onChange: (e) => setFbRater(e.target.value), placeholder: "e.g. DR", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "12px" } })), /* @__PURE__ */ React.createElement("button", { onClick: submitFeedback, disabled: fbBusy, style: { padding: "8px 14px", background: "#7c3aed", color: "white", border: "none", borderRadius: "8px", fontSize: "12px", fontWeight: "700", cursor: fbBusy ? "wait" : "pointer" } }, fbBusy ? "Saving\u2026" : "Submit suggestion")), /* @__PURE__ */ React.createElement("input", { value: fbNote, onChange: (e) => setFbNote(e.target.value), placeholder: "Optional note (e.g. which bones drove the difference)", className: "input-field", style: { padding: "7px 8px", width: "100%", fontSize: "11px", marginTop: "8px" } }), fbMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "11px", fontWeight: "700", color: fbMsg.type === "ok" ? "#16a34a" : "#b45309" } }, fbMsg.text), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "10px", color: "#a78bfa", lineHeight: 1.5 } }, "Your correction is logged as training evidence to improve accuracy over time. It does ", /* @__PURE__ */ React.createElement("strong", null, "not"), " change this patient's reported result.")), tw3Config && !tw3Config.ai_estimate_available && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#94a3b8" } }, "Bone-age model not installed yet. To enable: ", /* @__PURE__ */ React.createElement("code", null, "python -m backend.ai.train_boneage")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "10px", color: "#7c3aed", lineHeight: "1.5" } }, "Whole-image AI estimate \u2014 the clinician verifies each result. The full doctor-graded 20-bone TW3 workflow (grading, licensed tables, scores) is built and can be re-enabled when needed.")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "18px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "800", color: "#334155", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: "10px" } }, "2 \xB7 Bone Age Report"), (() => {
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
    })()), /* @__PURE__ */ React.createElement("details", { style: { marginTop: "16px", display: "none" } }, /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", fontWeight: "800", fontSize: "12px", color: "#7c3aed", padding: "8px 0", listStyle: "none" } }, "\u2699 Advanced \xB7 manual grading, save & approve, adult-height"), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "800", color: "#6b21a8", textTransform: "uppercase", letterSpacing: "0.05em" } }, "Manual TW3 grading \xB7 left hand\u2013wrist \xB7 stages A\u2013I"), /* @__PURE__ */ React.createElement("button", { onClick: () => {
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
    }, disabled: lcBusy, style: lcBtn("#475569", lcBusy) }, "Load saved"), assessment && lcLocked && /* @__PURE__ */ React.createElement("button", { onClick: reviseAssessment, disabled: lcBusy, style: lcBtn("#0891b2", lcBusy) }, "Open revision"), assessment && /* @__PURE__ */ React.createElement("button", { onClick: toggleAudit, disabled: lcBusy, style: lcBtn("#64748b", lcBusy) }, showAudit ? "Hide audit" : "Audit")), assessment && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "11px", color: "#475569" } }, "Record #", assessment.id, " \xB7 rev ", assessment.revision, " \xB7 ", /* @__PURE__ */ React.createElement("strong", { style: { textTransform: "uppercase" } }, assessment.assessment_status), " ", "\xB7 ", assessment.rus_staged_count, "/13 RUS + ", assessment.carpal_staged_count, "/7 carpal staged"), lcMsg && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", fontWeight: "700", color: lcMsg.type === "ok" ? "#059669" : "#dc2626" } }, lcMsg.text), showAudit && assessment && assessment.audit && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", maxHeight: "160px", overflowY: "auto", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "8px", fontFamily: "ui-monospace, Menlo, Consolas, monospace", fontSize: "10px", color: "#475569" } }, assessment.audit.map((e, i) => /* @__PURE__ */ React.createElement("div", { key: i }, e.timestamp ? e.timestamp.slice(0, 19).replace("T", " ") : "", " \xB7 ", e.event_type, " \xB7 ", e.actor, e.reason ? " \xB7 " + e.reason : ""))), assessment && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("label", { style: { ...lcBtn("#0f766e", lcBusy || lcLocked), display: "inline-block" } }, radiograph ? "Replace film" : "Attach film", /* @__PURE__ */ React.createElement(
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
    ), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Source"), /* @__PURE__ */ React.createElement("div", { style: { padding: "10px 12px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "9px", fontSize: "12px", fontWeight: "700", color: "#475569" } }, boneAge === "" ? "Not set" : boneAgeSource === "rus" ? "From RUS staging" : "Manual entry"))), /* @__PURE__ */ React.createElement("div", { className: "split-grid", style: { marginTop: "12px" } }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Father's Height", value: fatherHeight, onChange: (e) => setFatherHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm (optional)", unit: "cm" }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Mother's Height", value: motherHeight, onChange: (e) => setMotherHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm (optional)", unit: "cm" })), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "12px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "10px", padding: "12px 14px", fontSize: "11px", color: "#64748b", lineHeight: "1.6" } }, "The TW3 bone age is derived only from the 20 doctor-confirmed bone stages above (RUS + carpal) via the licensed TW3 tables \u2014 never from the whole-image AI, which is a rough screening triage only. Automatic per-bone staging from the X-ray is not yet available (it needs stage-labelled training data the clinic is now collecting)."), !boneMetrics ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: "12px", padding: "36px 0", textAlign: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "52px", height: "52px", borderRadius: "50%", background: "#f5f3ff", display: "flex", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#a78bfa", strokeWidth: "2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M18 8a6 6 0 0 0-9.33-5" }), /* @__PURE__ */ React.createElement("path", { d: "M6 16a6 6 0 0 0 9.33 5" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "2", x2: "12", y2: "22" }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "13px", fontWeight: "700", color: "#64748b" } }, "Set a TW3 bone age or both parents' heights"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", maxWidth: "320px", lineHeight: "1.6" } }, "Stage the left hand\u2013wrist film above (TW3 RUS), or enter a TW3 bone age manually. Add parents' heights for the genetic target. Current height is taken from Demographics.")) : /* @__PURE__ */ React.createElement("div", null, boneMetrics.mph !== null ? /* @__PURE__ */ React.createElement("div", { className: "hero-result", style: { background: "linear-gradient(135deg,#f5f3ff,#eef2ff)", border: "1.5px solid #ddd6fe", borderRadius: "16px", padding: "24px", marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.08em", color: "#7c3aed", marginBottom: "8px" } }, "Mid-Parental Target Height"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "10px" } }, /* @__PURE__ */ React.createElement("span", { className: "hero-value", style: { fontWeight: "900", color: "#5b21b6", lineHeight: 1 } }, boneMetrics.mph.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "13px", color: "#7c3aed", fontWeight: "600" } }, "cm")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#8b5cf6", marginTop: "4px" } }, "\u2248 ", Math.floor(boneMetrics.mph / 30.48), "\u2032", Math.round(boneMetrics.mph / 2.54 % 12), "\u2033 \xB7 genetic target from parents (Tanner) \xB7 range ", boneMetrics.mphLow.toFixed(0), "\u2013", boneMetrics.mphHigh.toFixed(0), " cm")), /* @__PURE__ */ React.createElement("div", { style: { textAlign: "right" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: "Genetic target \u2014 not a prediction", variant: "info" }), boneMetrics.mphPct !== null && /* @__PURE__ */ React.createElement("div", { style: { marginTop: "10px", fontSize: "12px", color: "#7c3aed", fontWeight: "700" } }, boneMetrics.mphPct.toFixed(1), "th centile (Khadilkar)"))) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "12px", padding: "16px", fontSize: "13px", fontWeight: "700", color: "#7c3aed", lineHeight: "1.6" } }, "Add both parents' heights for the mid-parental (genetic target) height and its \xB18.5 cm range."), boneMetrics.mph !== null && (() => {
      const lo = boneMetrics.mphLow, hi = boneMetrics.mphHigh, span = hi - lo;
      const marker = boneMetrics.predictedPah !== null ? boneMetrics.predictedPah : boneMetrics.mph;
      const pos = Math.min(Math.max((marker - lo) / span * 100, 1), 99);
      return /* @__PURE__ */ React.createElement("div", { style: { marginTop: "14px", background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e2e8f0" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "relative", height: "10px", borderRadius: "99px", background: "#e9d5ff" } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: "-3px", left: `${pos}%`, width: "16px", height: "16px", borderRadius: "50%", background: "white", border: "3px solid #7c3aed", transform: "translateX(-50%)", boxShadow: "0 1px 4px rgba(0,0,0,0.2)" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", fontWeight: "700", color: "#94a3b8" } }, /* @__PURE__ */ React.createElement("span", null, lo.toFixed(0), " cm"), /* @__PURE__ */ React.createElement("span", { style: { color: "#7c3aed" } }, "target range \xB18.5 cm", boneMetrics.predictedPah !== null ? " \xB7 marker = skeletal prediction" : ""), /* @__PURE__ */ React.createElement("span", null, hi.toFixed(0), " cm")));
    })(), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "16px", background: boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? "#f8fafc" : "#fffbeb", border: boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? "1px solid #e2e8f0" : "1px solid #fde68a", borderRadius: "12px", padding: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b" } }, "Predicted Adult Height \xB7 TW3 skeletal"), boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "24px", fontWeight: "900", color: "#1e293b" } }, boneMetrics.predictedPah.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "11px", color: "#94a3b8", marginLeft: "5px" } }, "cm"))), boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.predPct !== null ? `${boneMetrics.predPct.toFixed(1)}th centile \xB7 ` : "", boneMetrics.pct.toFixed(1), "% of adult height attained at bone age ", boneMetrics.ba.toFixed(1), " yr", boneMetrics.remaining !== null ? ` \xB7 ${boneMetrics.remaining.toFixed(1)} cm left to grow` : ""), boneMetrics.predVsTarget !== null && /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", fontWeight: "700", marginTop: "8px", color: boneMetrics.withinTarget ? "#059669" : "#d97706" } }, boneMetrics.predVsTarget >= 0 ? "+" : "", boneMetrics.predVsTarget.toFixed(1), " cm vs genetic target \xB7 ", boneMetrics.withinTarget ? "within" : "outside", " mid-parental channel")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#92400e", lineHeight: "1.7", marginTop: "4px" } }, /* @__PURE__ */ React.createElement("strong", null, "Calibration required \u2014 no value shown by design."), " A skeletal prediction needs the licensed TW3 \u201C% of adult height attained by bone age\u201D reference (or another validated method) in ", /* @__PURE__ */ React.createElement("code", null, "TW3_CONFIG.pctAdultHeight"), ". The mid-parental target above is a ", /* @__PURE__ */ React.createElement("em", null, "genetic target"), ", not a prediction, and is never substituted here.")), /* @__PURE__ */ React.createElement("div", { className: "secondary-grid", style: { marginTop: "16px" } }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Bone Age vs Chronological"), boneMetrics.hasBone ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "26px", fontWeight: "900", color: Math.abs(boneMetrics.diff) > 2 ? "#d97706" : "#1e293b", lineHeight: 1 } }, boneMetrics.diff >= 0 ? "+" : "", boneMetrics.diff.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "yr")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.diff > 1 ? "Advanced maturation" : boneMetrics.diff < -1 ? "Delayed maturation" : "Concordant with age")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, "No bone age set")), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Genetic Target on Khadilkar"), boneMetrics.mph !== null && boneMetrics.mphZ !== null ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "26px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, boneMetrics.mphZ >= 0 ? "+" : "", boneMetrics.mphZ.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "SDS")), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "11px", color: "#94a3b8", marginTop: "4px" } }, boneMetrics.mphPct.toFixed(1), "th percentile \xB7 target vs ", evalGender === "boys" ? "male" : "female", " adult (", boneMetrics.adult[0], " cm)")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8" } }, "Add parents' heights for target SDS"))), /* @__PURE__ */ React.createElement(MetricRow, { label: "Current Height", value: evalHeight.toFixed(1), unit: "cm", sub: `Chronological age ${evalAge.toFixed(1)} yr` })), /* @__PURE__ */ React.createElement("details", { className: "clinical-notes" }, /* @__PURE__ */ React.createElement("summary", null, "Clinical notes \xB7 TW3 workflow & Indian-population context"), /* @__PURE__ */ React.createElement("div", { className: "clinical-notes-body" }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#4338ca", lineHeight: "1.7", marginBottom: "10px" } }, /* @__PURE__ */ React.createElement("strong", null, "TW3 workflow:"), " use a ", /* @__PURE__ */ React.createElement("strong", null, "left"), " hand\u2013wrist PA radiograph. Stage all ", /* @__PURE__ */ React.createElement("strong", null, "20 bones"), " \u2014 13 RUS (radius, ulna, metacarpals 1\xB73\xB75, proximal/middle/distal phalanges 1\xB73\xB75) and 7 carpals \u2014 with the original TW3 letters A\u2192I. RUS and carpal maturity scores convert to ", /* @__PURE__ */ React.createElement("strong", null, "separate"), " bone ages (never averaged). Two independent reads within \xB10.5 yr is acceptable. Bayley\u2013Pinneau and Greulich\u2013Pyle are ", /* @__PURE__ */ React.createElement("strong", null, "not"), " used."), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#92400e", lineHeight: "1.7" } }, /* @__PURE__ */ React.createElement("strong", null, "Indian-population note:"), " No India-specific TW3 reference exists. In validation on Indian children, ", /* @__PURE__ */ React.createElement("strong", null, "TW3 was the most accurate"), " of the common methods (Shah et al., 2021, 851 children), which is why it is used here. However, skeletal maturation in Indian children differs from Western standards: boys run roughly ", /* @__PURE__ */ React.createElement("strong", null, "~6 months behind"), " and girls vary (delayed pre-puberty, sometimes advanced in early puberty) (Patel 2012; Khadilkar 2022). Scoring uses ", /* @__PURE__ */ React.createElement("strong", null, "TW3-C (Chinese)"), " tables as the closest freely-available reference \u2014 ", /* @__PURE__ */ React.createElement("strong", null, "no numeric correction is applied automatically"), ". Interpret borderline results, and ", /* @__PURE__ */ React.createElement("strong", null, "pubertal boys especially"), ", with clinical correlation."))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "auto", paddingTop: "18px", borderTop: "1px solid #f1f5f9", fontSize: "11px", color: "#94a3b8", lineHeight: "1.7" } }, "TW3: Tanner, Healy, Goldstein & Cameron (2001) \u2014 licensed reference values required for scoring & skeletal height prediction. Mid-parental target: Tanner (open). Adult-height SDS/centile vs Khadilkar (WHO\u2013IAP) 18-yr reference. Clinician must verify \u2014 not a diagnostic device.")));
  }

  // frontend/src/app.jsx
  var { useState: useState3, useMemo, useEffect: useEffect2, useRef: useRef2 } = React;
  function App() {
    const [activeTab, setActiveTab] = useState3("overview");
    const [growthChartMeasure, setGrowthChartMeasure] = useState3("combined");
    const [showChart, setShowChart] = useState3(false);
    const [patientName, setPatientName] = useState3("");
    const [patientMrn, setPatientMrn] = useState3("");
    const [examDate, setExamDate] = useState3(() => (/* @__PURE__ */ new Date()).toISOString().split("T")[0]);
    const [growthSeries, setGrowthSeries] = useState3({
      boys: { height: null, weight: null, bmi: null },
      girls: { height: null, weight: null, bmi: null }
    });
    const [growthSeriesLoading, setGrowthSeriesLoading] = useState3(true);
    const [growthPoint, setGrowthPoint] = useState3({ height: null, weight: null, bmi: null });
    const [growthBmiCutoffs, setGrowthBmiCutoffs] = useState3(null);
    const [adultHeightStats, setAdultHeightStats] = useState3(null);
    const [age, setAge] = useState3("");
    const [dob, setDob] = useState3("");
    const [gender, setGender] = useState3("");
    const [height, setHeight] = useState3("");
    const [weight, setWeight] = useState3("");
    const [creatinine, setCreatinine] = useState3("");
    const [albuminuria, setAlbuminuria] = useState3("");
    const [systolic, setSystolic] = useState3("");
    const [diastolic, setDiastolic] = useState3("");
    const [ast, setAst] = useState3("");
    const [alt, setAlt] = useState3("");
    const [platelets, setPlatelets] = useState3("");
    const [prevFracture, setPrevFracture] = useState3("no");
    const [parentHipFracture, setParentHipFracture] = useState3("no");
    const [smoking, setSmoking] = useState3("no");
    const [glucocorticoids, setGlucocorticoids] = useState3("no");
    const [rheumatoid, setRheumatoid] = useState3("no");
    const [secondaryOsteo, setSecondaryOsteo] = useState3("no");
    const [alcohol, setAlcohol] = useState3("no");
    const [timeline, setTimeline] = useState3([]);
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
      rusResult,
      setRusResult,
      letterResult,
      setLetterResult,
      boneReport,
      setBoneReport,
      patientCode,
      setPatientCode,
      approverName,
      setApproverName,
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
    } = useBoneAgeState();
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
    const evalAlbuminuria = useMemo(() => albuminuria !== "" ? albuminuria : "A1", [albuminuria]);
    const evalSystolic = useMemo(() => systolic !== "" ? parseFloat(systolic) : 110, [systolic]);
    const evalDiastolic = useMemo(() => diastolic !== "" ? parseFloat(diastolic) : 70, [diastolic]);
    const evalAst = useMemo(() => ast !== "" ? parseFloat(ast) : 25, [ast]);
    const evalAlt = useMemo(() => alt !== "" ? parseFloat(alt) : 20, [alt]);
    const evalPlatelets = useMemo(() => platelets !== "" ? parseFloat(platelets) : 250, [platelets]);
    const hasManualGrowth = age !== "" && gender !== "" && height !== "" && weight !== "";
    const hasManualRenal = age !== "" && gender !== "" && height !== "" && creatinine !== "";
    const hasManualLiver = age !== "" && ast !== "" && alt !== "" && platelets !== "";
    const hasManualFrax = age !== "" && gender !== "" && height !== "" && weight !== "";
    const hasGeneral = height !== "" && weight !== "" && systolic !== "" && diastolic !== "";
    const loadPreset = (type) => {
      if (type === "child") {
        setAge(9);
        setGender("girls");
        setHeight(120.9);
        setWeight(22.4);
        setCreatinine(0.5);
        setAlbuminuria("A1");
        setSystolic(104);
        setDiastolic(64);
        setAst(22);
        setAlt(18);
        setPlatelets(280);
        setPrevFracture("no");
        setParentHipFracture("no");
        setSmoking("no");
        setGlucocorticoids("no");
        setRheumatoid("no");
        setSecondaryOsteo("no");
        setAlcohol("no");
      } else {
        setAge(58);
        setGender("boys");
        setHeight(171);
        setWeight(79.5);
        setCreatinine(1.35);
        setAlbuminuria("A2");
        setSystolic(138);
        setDiastolic(88);
        setAst(44);
        setAlt(42);
        setPlatelets(165);
        setPrevFracture("yes");
        setParentHipFracture("no");
        setSmoking("yes");
        setGlucocorticoids("yes");
        setRheumatoid("no");
        setSecondaryOsteo("yes");
        setAlcohol("no");
      }
    };
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
    const renalMetrics = useMemo(() => {
      const isPediatric = evalAge < 18;
      let egfr = 0, formulaName = "";
      if (isPediatric) {
        egfr = 0.413 * evalHeight / evalCreatinine;
        formulaName = "Modified Bedside Schwartz (2009)";
      } else {
        const isFemale = evalGender === "girls";
        const kappa = isFemale ? 0.7 : 0.9, alpha = isFemale ? -0.241 : -0.302;
        const gConst = isFemale ? 1.012 : 1;
        const term1 = evalCreatinine / kappa;
        egfr = 142 * Math.pow(Math.min(term1, 1), alpha) * Math.pow(Math.max(term1, 1), -1.2) * Math.pow(0.9938, evalAge) * gConst;
        formulaName = "2021 CKD-EPI Creatinine";
      }
      let cg = null, mdrd = null;
      if (!isPediatric && evalWeight > 0) {
        const isFemale = evalGender === "girls";
        cg = (140 - evalAge) * evalWeight / (72 * evalCreatinine) * (isFemale ? 0.85 : 1);
        mdrd = 175 * Math.pow(evalCreatinine, -1.154) * Math.pow(evalAge, -0.203) * (isFemale ? 0.742 : 1);
      }
      let ckdStage = "G1", ckdStageDesc = "Normal / High", stageVariant = "low";
      if (egfr < 15) {
        ckdStage = "G5";
        ckdStageDesc = "Kidney Failure";
        stageVariant = "high";
      } else if (egfr < 30) {
        ckdStage = "G4";
        ckdStageDesc = "Severely Decreased";
        stageVariant = "high";
      } else if (egfr < 60) {
        ckdStage = "G3";
        ckdStageDesc = "Moderately Decreased";
        stageVariant = "mid";
      } else if (egfr < 90) {
        ckdStage = "G2";
        ckdStageDesc = "Mildly Decreased";
        stageVariant = "mid";
      }
      return { egfr, formulaName, cg, mdrd, ckdStage, ckdStageDesc, stageVariant, isPediatric };
    }, [evalAge, evalGender, evalHeight, evalWeight, evalCreatinine]);
    const liverMetrics = useMemo(() => {
      const fib4 = evalAge * evalAst / (evalPlatelets * Math.sqrt(evalAlt));
      let interpretation = "Low Risk", variant = "low", details = "Low probability of advanced fibrosis.";
      const highThresh = 2.67, midThresh = evalAge > 65 ? 2 : 1.3;
      if (fib4 > highThresh) {
        interpretation = "High Risk";
        variant = "high";
        details = "High risk of advanced liver fibrosis \u2014 referral recommended.";
      } else if (fib4 > midThresh) {
        interpretation = "Indeterminate";
        variant = "mid";
        details = "Intermediate range \u2014 further evaluation required.";
      }
      return { fib4, interpretation, variant, details };
    }, [evalAge, evalAst, evalAlt, evalPlatelets]);
    const fraxMetrics = useMemo(() => {
      const fraxAge = Math.min(Math.max(evalAge, 40), 90);
      const hMeter = evalHeight / 100;
      const bmi = evalWeight / (hMeter * hMeter);
      let mofLogit = -3.8 + 0.055 * (fraxAge - 50) - 0.035 * (bmi - 25);
      let hfLogit = -5.8 + 0.085 * (fraxAge - 50) - 0.055 * (bmi - 25);
      if (evalGender === "girls") {
        mofLogit += 0.35;
        hfLogit += 0.45;
      }
      if (prevFracture === "yes") {
        mofLogit += 1.15;
        hfLogit += 1.05;
      }
      if (parentHipFracture === "yes") {
        mofLogit += 0.95;
        hfLogit += 1.25;
      }
      if (smoking === "yes") {
        mofLogit += 0.35;
        hfLogit += 0.45;
      }
      if (glucocorticoids === "yes") {
        mofLogit += 0.85;
        hfLogit += 0.95;
      }
      if (rheumatoid === "yes") {
        mofLogit += 0.45;
        hfLogit += 0.55;
      }
      if (secondaryOsteo === "yes") {
        mofLogit += 0.35;
        hfLogit += 0.35;
      }
      if (alcohol === "yes") {
        mofLogit += 0.25;
        hfLogit += 0.35;
      }
      const mofProb = 100 / (1 + Math.exp(-mofLogit));
      const hfProb = 100 / (1 + Math.exp(-hfLogit));
      return { mofProb, hfProb, isHighMof: mofProb >= 20, isHighHf: hfProb >= 3, fraxAge };
    }, [evalAge, evalGender, evalHeight, evalWeight, prevFracture, parentHipFracture, smoking, glucocorticoids, rheumatoid, secondaryOsteo, alcohol]);
    const chronicityStatus = useMemo(() => {
      if (timeline.length < 2) return { status: "Add at least 2 snapshots (\u2265 90 days apart) to assess CKD chronicity.", cls: "risk-badge-neutral", bgClass: "bg-slate-50 border-slate-200 text-slate-500" };
      const sorted = [...timeline].sort((a, b) => new Date(a.date) - new Date(b.date));
      const diffDays = Math.ceil((new Date(sorted[sorted.length - 1].date) - new Date(sorted[0].date)) / 864e5);
      if (diffDays < 90) return { status: `Observation window: ${diffDays} days \u2014 need 90 days minimum to confirm chronicity.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
      const initDmg = sorted[0].egfr < 60 || sorted[0].albuminuria !== "A1";
      const curDmg = sorted[sorted.length - 1].egfr < 60 || sorted[sorted.length - 1].albuminuria !== "A1";
      if (initDmg && curDmg) return { status: `Chronicity CONFIRMED \u2014 Persistent indicators across ${diffDays}-day window.`, bgClass: "bg-rose-50 border-rose-200 text-rose-700 font-bold" };
      return { status: `Transient profile \u2014 markers did not persist over ${diffDays} days.`, bgClass: "bg-emerald-50 border-emerald-200 text-emerald-700" };
    }, [timeline]);
    const generalMetrics = useMemo(() => {
      const bmi = evalWeight / Math.pow(evalHeight / 100, 2);
      const map = evalDiastolic + (evalSystolic - evalDiastolic) / 3;
      let bmiCat = "Normal", bmiVariant = "low";
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
      let mapCat = "Normal", mapVariant = "low";
      if (map < 70) {
        mapCat = "Low";
        mapVariant = "mid";
      } else if (map > 100) {
        mapCat = "Elevated";
        mapVariant = "mid";
      } else if (map > 110) {
        mapCat = "High";
        mapVariant = "high";
      }
      return { bmi, bmiCat, bmiVariant, map, mapCat, mapVariant };
    }, [evalHeight, evalWeight, evalSystolic, evalDiastolic]);
    useEffect2(() => {
      const params = new URLSearchParams(window.location.search);
      if (params.get("report") !== "1") return;
      document.body.classList.add("report-mode");
      const qSex = params.get("sex");
      if (qSex === "boys" || qSex === "girls") setGender(qSex);
      const qAge = params.get("age");
      if (qAge) setAge(qAge);
      const qHeight = params.get("height");
      if (qHeight) setHeight(qHeight);
      const qWeight = params.get("weight");
      if (qWeight) setWeight(qWeight);
      const qName = params.get("patient_name");
      if (qName) setPatientName(qName);
      const qMrn = params.get("patient_mrn");
      if (qMrn) setPatientMrn(qMrn);
      const qExam = params.get("exam_date");
      if (qExam) setExamDate(qExam);
      setActiveTab("growth");
      setGrowthChartMeasure("combined");
      setShowChart(true);
    }, []);
    useEffect2(() => {
      fetch("/api/bone-age/config").then((r) => r.json()).then(setTw3Config).catch(() => {
      });
    }, []);
    useEffect2(() => {
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
    useEffect2(() => {
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
    }, [evalAge, evalGender, evalHeight, evalWeight]);
    useEffect2(() => {
      let cancelled = false;
      fetch(`/api/growth/reference-stats?measure=height&sex=${evalGender}&age=19`).then((r) => r.json()).then((d) => {
        if (!cancelled) setAdultHeightStats(d);
      }).catch(() => {
      });
      return () => {
        cancelled = true;
      };
    }, [evalGender]);
    useEffect2(() => {
      const rid = assessment && assessment.radiograph_id;
      if (rid && (!radiograph || radiograph.radiograph_id !== rid)) {
        setRadiograph((r) => ({ ...r || {}, radiograph_id: rid }));
      }
    }, [assessment]);
    useEffect2(() => {
      if (evalGender !== "boys" && evalGender !== "girls") {
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
          body: JSON.stringify({ sex: evalGender, rus_stages: rusStages, carpal_stages: carp })
        }).then((r) => r.ok ? r.json() : null).then((d) => {
          if (d) setLetterResult(d);
        }).catch(() => {
        });
        fetch("/api/bone-age/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sex: evalGender,
            rus_stages: rusStages,
            carpal_stages: carp,
            chronological_age_years: evalAge > 0 ? evalAge : null,
            ai_estimate_years: aiYrs
          })
        }).then((r) => r.ok ? r.json() : null).then((d) => {
          if (d) setBoneReport(d);
        }).catch(() => {
        });
      }, 250);
      return () => clearTimeout(id);
    }, [rusStages, carpalStages, evalGender, evalAge, aiEstimate]);
    const rusMetrics = useMemo(() => ({
      staged: rusResult ? rusResult.staged_count : 0,
      total: tw3Config && tw3Config.bones ? tw3Config.bones.length : 13,
      score: rusResult ? rusResult.total_rus_score : 0,
      calibrated: rusResult ? rusResult.calibrated : tw3Config ? true : false,
      complete: rusResult ? rusResult.complete : false,
      suggestedAge: rusResult ? rusResult.bone_age_years : null,
      status: rusResult ? rusResult.status : null,
      provisional: rusResult ? rusResult.provisional_curve : tw3Config ? tw3Config.provisional_curve : false
    }), [rusResult, tw3Config]);
    const boneMetrics = useMemo(() => {
      const ba = boneAge !== "" ? parseFloat(boneAge) : null;
      const hasBone = ba !== null && !isNaN(ba) && evalHeight > 0;
      const fh = fatherHeight !== "" ? parseFloat(fatherHeight) : null;
      const mh = motherHeight !== "" ? parseFloat(motherHeight) : null;
      let mph = null, mphLow = null, mphHigh = null;
      if (fh && mh && fh > 0 && mh > 0) {
        mph = evalGender === "boys" ? (fh + mh + 13) / 2 : (fh + mh - 13) / 2;
        mphLow = mph - 8.5;
        mphHigh = mph + 8.5;
      }
      if (!hasBone && mph === null) return null;
      const diff = hasBone ? ba - evalAge : null;
      const autoCat = hasBone ? maturationCategory(ba, evalAge) : null;
      const pct = hasBone ? pctAdultHeightAt(ba, evalGender) : null;
      const skeletalPah = pct && pct > 0 ? evalHeight / (pct / 100) : null;
      const skeletalCalibrated = pct !== null;
      const predictedPah = skeletalPah;
      const remaining = predictedPah !== null && evalHeight > 0 ? predictedPah - evalHeight : null;
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
    }, [boneAge, evalAge, evalGender, evalHeight, fatherHeight, motherHeight, adultHeightStats]);
    const {
      LC_API,
      lcLocked,
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
      _emptyLt,
      loadLetterTables,
      setLtPoint,
      curveToText,
      parseCurve,
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
    } = useBoneAgeHandlers({
      adjReviewer,
      age,
      aiEstimate,
      approverName,
      assessment,
      boxes,
      boxesRef,
      carpalStages,
      coverage,
      declaredFlags,
      estimateDomain,
      evalAge,
      evalGender,
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
    const qriskMetrics = useMemo(() => {
      const bmi = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : null;
      const inAgeRange = evalAge >= 25 && evalAge <= 84;
      const p = {
        sex: evalGender,
        age: evalAge,
        bmi,
        ethnicity,
        smoke: smokeCat,
        diabetes,
        rati: cholRatio !== "" ? parseFloat(cholRatio) : void 0,
        sbp: systolic !== "" ? parseFloat(systolic) : void 0,
        sbps5: sbpSD !== "" ? parseFloat(sbpSD) : void 0,
        af: qAF === "yes",
        treatedhyp: qTreatedHtn === "yes",
        ra: qRA === "yes",
        renal: qCKD === "yes",
        migraine: qMigraine === "yes",
        sle: qSLE === "yes",
        semi: qSMI === "yes",
        atypicalantipsy: qAtypAntipsy === "yes",
        corticosteroids: qCortico === "yes",
        impotence2: qED === "yes",
        fh_cvd: qFhCvd === "yes"
      };
      const risk = bmi && inAgeRange ? qrisk3(p) : null;
      const typical = bmi && inAgeRange ? qrisk3({
        sex: evalGender,
        age: evalAge,
        bmi: 25,
        ethnicity,
        smoke: 0,
        diabetes: 0,
        rati: 4,
        sbp: 125,
        sbps5: 0,
        town: 0
      }) : null;
      let band = "low", variant = "low";
      if (risk !== null) {
        if (risk >= 20) {
          band = "High (\u2265 20%)";
          variant = "high";
        } else if (risk >= 10) {
          band = "Moderate (10\u201320%)";
          variant = "mid";
        } else {
          band = "Low (< 10%)";
          variant = "low";
        }
      }
      const missingSbp = systolic === "", missingRatio = cholRatio === "";
      return { risk, typical, band, variant, inAgeRange, bmi, missingSbp, missingRatio };
    }, [
      evalGender,
      evalAge,
      evalHeight,
      evalWeight,
      ethnicity,
      smokeCat,
      diabetes,
      cholRatio,
      systolic,
      sbpSD,
      qAF,
      qTreatedHtn,
      qRA,
      qCKD,
      qMigraine,
      qSLE,
      qSMI,
      qAtypAntipsy,
      qCortico,
      qED,
      qFhCvd
    ]);
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
          state: hasManualRenal ? variantToState(renalMetrics.stageVariant) : "none",
          value: hasManualRenal ? renalMetrics.egfr.toFixed(0) : "\u2014",
          unit: "mL/min/1.73m\xB2",
          label: hasManualRenal ? `CKD ${renalMetrics.ckdStage} \xB7 ${renalMetrics.ckdStageDesc}` : "Enter serum creatinine",
          title: "Renal (eGFR)"
        },
        liver: {
          state: hasManualLiver ? variantToState(liverMetrics.variant) : "none",
          value: hasManualLiver ? liverMetrics.fib4.toFixed(2) : "\u2014",
          unit: "FIB-4",
          label: hasManualLiver ? liverMetrics.interpretation : "Enter AST, ALT & platelets",
          title: "Liver (FIB-4)"
        },
        frax: {
          state: hasManualFrax ? fraxMetrics.isHighMof || fraxMetrics.isHighHf ? "high" : "normal" : "none",
          value: hasManualFrax ? fraxMetrics.mofProb.toFixed(1) : "\u2014",
          unit: "% MOF 10-yr",
          label: hasManualFrax ? fraxMetrics.isHighMof ? "High fracture risk" : "Low fracture risk" : "Enter age, sex, height & weight",
          title: "FRAX"
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
      setPrevFracture("no");
      setParentHipFracture("no");
      setSmoking("no");
      setGlucocorticoids("no");
      setRheumatoid("no");
      setSecondaryOsteo("no");
      setAlcohol("no");
      setTimeline([]);
      setActiveTab("overview");
      setBoneAge("");
      setBoneAgeSource("manual");
      setRusStages({});
      setCarpalStages({});
      setPatientCode("");
      setApproverName("");
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
    const logCurrentData = () => {
      setTimeline((prev) => [{
        id: Date.now().toString(),
        date: (/* @__PURE__ */ new Date()).toISOString().split("T")[0],
        age: evalAge,
        height: evalHeight,
        weight: evalWeight,
        creatinine: evalCreatinine,
        egfr: Number(renalMetrics.egfr.toFixed(1)),
        fib4: liverMetrics ? Number(liverMetrics.fib4.toFixed(2)) : null,
        albuminuria: evalAlbuminuria
      }, ...prev]);
    };
    const exportGrowthReportPdf = async () => {
      const params = new URLSearchParams({
        sex: evalGender,
        age: String(evalAge),
        height: String(evalHeight || 0),
        weight: String(evalWeight || 0),
        patient_name: patientName,
        patient_mrn: patientMrn,
        exam_date: examDate
      });
      try {
        const res = await fetch(`/api/growth/report.pdf?${params.toString()}`);
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
              <div class="sub" style="font-weight:700;color:#334155">${patientName || "Unnamed patient"} \xB7 MRN ${patientMrn || "\u2014"} \xB7 Exam ${examDate}</div>
              <div class="sub">Reference: ${growthSeries[evalGender].height && growthSeries[evalGender].height.reference || "WHO + IAP 2015"} \xB7 ${chartLabel} \xB7 ${(/* @__PURE__ */ new Date()).toLocaleDateString()}</div>
              <div class="chart-sheet">${svg}</div>
              <table>
                ${row("Sex", evalGender === "girls" ? "Female" : "Male")}
                ${row("Chronological age", evalAge.toFixed(1) + " yrs")}
                ${row("Height", evalHeight + " cm  \xB7  z " + fmtZ(g.heightZ) + "  \xB7  " + fmtP(g.heightPct) + " pct")}
                ${row("Weight", evalWeight + " kg" + (g.weightAvailable ? "  \xB7  z " + fmtZ(g.weightZ) + "  \xB7  " + fmtP(g.weightPct) + " pct" : "  (weight-for-age n/a at this age \u2014 use BMI)"))}
                ${row("BMI", g.bmiVal.toFixed(1) + " kg/m\xB2  \xB7  z " + fmtZ(g.bmiZ) + "  \xB7  " + fmtP(g.bmiPct) + " pct")}
                ${row("Height status", g.stuntingClass)}
                ${row("Weight / BMI status", g.underweightClass)}
                ${row("Height age", g.heightAge.label)}
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
              <div class="foot">Decision support only \u2014 not a diagnostic device. A clinician must verify every value. A "\u2014" interpretation means that module had insufficient input. References: Khadilkar 2015 \xB7 TW3-C (Chinese) RUS \u2014 provisional research curve (\xB10.5y, digitized from a published figure); NOT Tanner\u2013Whitehouse TW3 \xB7 QRISK3-2017 \xB7 CKD-EPI 2021 \xB7 Bedside Schwartz 2009 \xB7 FRAX India Asian \xB7 FIB-4 (Sterling et al.).</div>
              </body></html>`);
      win.document.close();
      win.focus();
      setTimeout(() => win.print(), 300);
    };
    const TABS = [
      { id: "overview", label: "Overview" },
      { id: "growth", label: "Growth" },
      { id: "boneage", label: "Bone Age" },
      { id: "renal", label: "Renal GFR" },
      { id: "liver", label: "FIB-4 Liver" },
      { id: "frax", label: "FRAX Plus" },
      { id: "qrisk", label: "QRISK3 CVD" },
      { id: "timeline", label: "Ledger" }
    ];
    const labsRelevant = ["renal", "liver", "qrisk", "timeline", "overview"].includes(activeTab);
    const fraxRelevant = ["frax", "overview"].includes(activeTab);
    const clinicalState = {
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
      platelets,
      renalMetrics,
      hasManualRenal,
      creatinine,
      fraxMetrics,
      hasManualFrax,
      DECLARABLE_FLAGS: DECLARABLE_FLAGS2,
      LC_API,
      addOrSelectBox,
      adjBusy,
      adjItems,
      adjMsg,
      adjReviewer,
      aiBusy,
      aiEstimate,
      analysisUrl,
      attachImage,
      boneAge,
      boneAgeSource,
      boneMetrics,
      boneReport,
      bonesIntoGrids,
      boxes,
      carpalStages,
      clearBox,
      covBusy,
      coverage,
      curveToText,
      declaredFlags,
      endLocDrag,
      estimateDomain,
      fatherHeight,
      fbAge,
      fbBusy,
      fbConfidence,
      fbMethod,
      fbMsg,
      fbNote,
      fbRater,
      lcBtn,
      lcBusy,
      lcLocked,
      lcMsg,
      letterResult,
      loadAdjudication,
      loadCoverage,
      loadLetterTables,
      loadMonitoring,
      locBusy,
      locImg,
      locMsg,
      locRef,
      localCohort,
      lcohBusy,
      loadLocalCohort,
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
      runEstimate,
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
      setEstimateDomain,
      setFatherHeight,
      setFbAge,
      setFbConfidence,
      setFbMethod,
      setFbNote,
      setFbRater,
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
      submitFeedback,
      toggleAudit,
      toggleDeclaredFlag,
      tw3Config,
      useGridAsReference,
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
      systolic,
      timeline
    };
    return /* @__PURE__ */ React.createElement(ClinicalStateProvider, { value: clinicalState }, /* @__PURE__ */ React.createElement("div", { className: "app-shell" }, /* @__PURE__ */ React.createElement("header", { style: { background: "white", borderBottom: "1px solid #e8ecf0", position: "sticky", top: 0, zIndex: 50, boxShadow: "0 1px 4px rgba(0,0,0,0.05)" } }, /* @__PURE__ */ React.createElement("div", { className: "app-header-inner" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "12px" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "36px", height: "36px", borderRadius: "10px", background: "linear-gradient(135deg,#4f46e5,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "white", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M22 12h-4l-3 9L9 3l-3 9H2" }))), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "app-title", style: { fontSize: "15px", fontWeight: "900", color: "#0f172a", lineHeight: 1.2 } }, "Pediatric Clinical Workspace"), /* @__PURE__ */ React.createElement("div", { className: "app-subtitle", style: { fontSize: "10px", fontWeight: "700", color: "#94a3b8", letterSpacing: "0.06em", textTransform: "uppercase" } }, "Growth \xB7 TW3 Bone Age \xB7 QRISK3 \xB7 Renal \xB7 FRAX \xB7 FIB-4"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 } }, /* @__PURE__ */ React.createElement(
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
    )))), /* @__PURE__ */ React.createElement("div", { className: "patient-bar no-print" }, /* @__PURE__ */ React.createElement("div", { className: "patient-bar-inner" }, /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "2 1 200px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-name" }, "Patient name"), /* @__PURE__ */ React.createElement("input", { id: "pt-name", type: "text", value: patientName, onChange: (e) => setPatientName(e.target.value), placeholder: "Full name" })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 130px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-mrn" }, "MRN / ID"), /* @__PURE__ */ React.createElement("input", { id: "pt-mrn", type: "text", value: patientMrn, onChange: (e) => setPatientMrn(e.target.value), placeholder: "e.g. 004821" })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 140px" } }, /* @__PURE__ */ React.createElement("label", { htmlFor: "pt-date" }, "Exam date"), /* @__PURE__ */ React.createElement("input", { id: "pt-date", type: "date", value: examDate, onChange: (e) => setExamDate(e.target.value) })), /* @__PURE__ */ React.createElement("div", { className: "patient-field", style: { flex: "1 1 120px" } }, /* @__PURE__ */ React.createElement("label", null, "Age / Sex"), /* @__PURE__ */ React.createElement("div", { className: "patient-reflect" }, age !== "" ? `${age} yr` : "\u2014 yr", " \xB7 ", gender === "boys" ? "Male" : gender === "girls" ? "Female" : "\u2014")), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: exportFullReport,
        title: "Print a combined summary of every module",
        style: { marginLeft: "auto", alignSelf: "center", display: "flex", alignItems: "center", gap: "7px", padding: "8px 16px", background: "#4f46e5", color: "white", border: "none", borderRadius: "9px", fontSize: "13px", fontWeight: "700", cursor: "pointer", whiteSpace: "nowrap" }
      },
      /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "6 9 6 2 18 2 18 9" }), /* @__PURE__ */ React.createElement("path", { d: "M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" }), /* @__PURE__ */ React.createElement("rect", { x: "6", y: "14", width: "12", height: "8" })),
      "Export report"
    ))), /* @__PURE__ */ React.createElement("main", { className: "app-main" }, /* @__PURE__ */ React.createElement("div", { className: "input-column" }, /* @__PURE__ */ React.createElement("div", { className: "card", style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#4f46e5", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "Demographics"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontSize: "9px", fontWeight: "700", color: "#cbd5e1", textTransform: "uppercase", letterSpacing: "0.05em" } }, "Required")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "14px" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Chronological Age",
        value: age,
        onChange: handleAgeChange,
        placeholder: "e.g. 9.5",
        step: "0.1",
        unit: "yrs",
        unitPosition: "right",
        accent: "#4f46e5"
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
    ))), ageParts ? /* @__PURE__ */ React.createElement("div", { style: { marginTop: "8px", fontSize: "11px", color: "#4338ca", background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: "8px", padding: "7px 10px", lineHeight: "1.5" } }, "Age ", /* @__PURE__ */ React.createElement("strong", null, ageParts.years, " yr ", ageParts.months, " mo ", ageParts.days, " d"), /* @__PURE__ */ React.createElement("span", { style: { color: "#818cf8" } }, " \xB7 used as ", ageParts.decimal.toFixed(1), " yr in calculations")) : /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px", fontSize: "10px", color: "#94a3b8", lineHeight: "1.4" } }, "Enter an age directly, or a date of birth to compute it automatically.")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Biological Sex"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px" } }, /* @__PURE__ */ React.createElement("button", { className: `gender-btn ${gender === "boys" ? "gender-active" : "gender-inactive"}`, onClick: () => setGender("boys") }, "\u2642 Male"), /* @__PURE__ */ React.createElement("button", { className: `gender-btn ${gender === "girls" ? "gender-active" : "gender-inactive"}`, onClick: () => setGender("girls") }, "\u2640 Female"))), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Height", value: height, onChange: (e) => setHeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "cm", unit: "cm" }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Weight", value: weight, onChange: (e) => setWeight(e.target.value === "" ? "" : parseFloat(e.target.value)), placeholder: "kg", unit: "kg" })))), /* @__PURE__ */ React.createElement("div", { className: `card${labsRelevant ? "" : " section-dim"}`, style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#0891b2", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "Clinical Labs & Parameters")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "14px" } }, /* @__PURE__ */ React.createElement(
      InputWithUnit,
      {
        label: "Serum Creatinine",
        value: creatinine,
        onChange: (e) => setCreatinine(e.target.value === "" ? "" : parseFloat(e.target.value)),
        placeholder: "mg/dL",
        step: "0.01",
        unit: "mg/dL",
        accent: "#0891b2"
      }
    ), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Albuminuria / ACR Stage"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: "8px" } }, [["A1", "< 30 mg/g"], ["A2", "30\u2013300 mg/g"], ["A3", "> 300 mg/g"]].map(([lv, desc]) => /* @__PURE__ */ React.createElement("button", { key: lv, className: `alb-btn ${albuminuria === lv ? "alb-active" : "alb-inactive"}`, onClick: () => setAlbuminuria(lv) }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", fontWeight: "800", color: albuminuria === lv ? "#4338ca" : "#334155" } }, lv), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "9px", color: "#94a3b8", marginTop: "2px" } }, desc))))), /* @__PURE__ */ React.createElement("div", { className: "form-grid" }, /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Systolic BP", value: systolic, onChange: (e) => setSystolic(e.target.value === "" ? "" : parseInt(e.target.value)), placeholder: "mmHg", unit: "mmHg" }), /* @__PURE__ */ React.createElement(InputWithUnit, { label: "Diastolic BP", value: diastolic, onChange: (e) => setDiastolic(e.target.value === "" ? "" : parseInt(e.target.value)), placeholder: "mmHg", unit: "mmHg" })), /* @__PURE__ */ React.createElement("div", { style: { paddingTop: "12px", borderTop: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("label", { className: "field-label", style: { marginBottom: "10px" } }, "Hepatic Enzymes & Platelets"), /* @__PURE__ */ React.createElement("div", { className: "liver-grid" }, [
      ["AST", "SGOT \xB7 U/L", ast, (e) => setAst(e.target.value === "" ? "" : parseFloat(e.target.value))],
      ["ALT", "SGPT \xB7 U/L", alt, (e) => setAlt(e.target.value === "" ? "" : parseFloat(e.target.value))],
      ["PLT", "\xD710\xB3 / \xB5L", platelets, (e) => setPlatelets(e.target.value === "" ? "" : parseFloat(e.target.value))]
    ].map(([lbl, sub, val, fn]) => /* @__PURE__ */ React.createElement("div", { key: lbl, style: { display: "flex", flexDirection: "column", alignItems: "stretch" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", fontWeight: "800", color: "#334155", textAlign: "center", display: "block", marginBottom: "2px" } }, lbl), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "9px", fontWeight: "600", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", textAlign: "center", display: "block", marginBottom: "6px" } }, sub), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        placeholder: "\u2014",
        value: val,
        onChange: fn,
        className: "input-field",
        style: { textAlign: "center", padding: "9px 8px", width: "100%", boxSizing: "border-box" }
      }
    ))))))), /* @__PURE__ */ React.createElement("div", { className: `card${fraxRelevant ? "" : " section-dim"}`, style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#d97706", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "FRAX Risk Factors"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontSize: "9px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" } }, "India \xB7 No BMD")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Previous Fracture", value: prevFracture, setter: setPrevFracture }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Parent Hip Fracture", value: parentHipFracture, setter: setParentHipFracture }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Current Smoking", value: smoking, setter: setSmoking }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Glucocorticoids", value: glucocorticoids, setter: setGlucocorticoids }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Rheumatoid Arthritis", value: rheumatoid, setter: setRheumatoid }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Secondary Osteoporosis", value: secondaryOsteo, setter: setSecondaryOsteo }), /* @__PURE__ */ React.createElement(FraxToggleRow, { label: "Alcohol \u2265 3 units/day", value: alcohol, setter: setAlcohol })))), /* @__PURE__ */ React.createElement("div", { className: "result-column" }, /* @__PURE__ */ React.createElement("div", { className: "card tab-card", style: { padding: "6px" } }, /* @__PURE__ */ React.createElement("div", { className: "tab-scroll custom-scrollbar" }, TABS.map((tab) => /* @__PURE__ */ React.createElement(
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
    )))), /* @__PURE__ */ React.createElement("div", { className: "card-lg result-panel" }, activeTab === "overview" && /* @__PURE__ */ React.createElement(OverviewPanel, null), activeTab === "growth" && /* @__PURE__ */ React.createElement(GrowthPanel, null), activeTab === "boneage" && /* @__PURE__ */ React.createElement(BoneAgePanel, null), activeTab === "renal" && /* @__PURE__ */ React.createElement(RenalPanel, null), activeTab === "liver" && /* @__PURE__ */ React.createElement(LiverPanel, null), activeTab === "frax" && /* @__PURE__ */ React.createElement(FraxPanel, null), activeTab === "qrisk" && /* @__PURE__ */ React.createElement(QriskPanel, null), activeTab === "timeline" && /* @__PURE__ */ React.createElement(LedgerPanel, null)), /* @__PURE__ */ React.createElement("div", { className: "card no-print", style: { padding: "20px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px", paddingBottom: "12px", borderBottom: "1px solid #f1f5f9" } }, /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: "#0891b2", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "section-label" }, "General Health Indicators")), /* @__PURE__ */ React.createElement("div", { className: "general-grid" }, /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Body Mass Index"), height !== "" && weight !== "" ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "28px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, generalMetrics.bmi.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "kg/m\xB2")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: generalMetrics.bmiCat, variant: generalMetrics.bmiVariant })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "4px" } }, "Asian cutoffs: Normal < 23, OW \u2265 23, Obese \u2265 27.5")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "6px 0" } }, "Enter height & weight")), /* @__PURE__ */ React.createElement("div", { style: { background: "#f8fafc", borderRadius: "12px", padding: "14px 16px", border: "1px solid #e8ecf0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" } }, "Mean Arterial Pressure"), systolic !== "" && diastolic !== "" ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: "8px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: "28px", fontWeight: "900", color: "#1e293b", lineHeight: 1 } }, generalMetrics.map.toFixed(1)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: "12px", color: "#94a3b8" } }, "mmHg")), /* @__PURE__ */ React.createElement("div", { style: { marginTop: "6px" } }, /* @__PURE__ */ React.createElement(StatusBadge, { text: generalMetrics.mapCat, variant: generalMetrics.mapVariant })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: "10px", color: "#94a3b8", marginTop: "4px" } }, "Normal range: 70\u2013100 mmHg")) : /* @__PURE__ */ React.createElement("div", { style: { fontSize: "12px", color: "#94a3b8", padding: "6px 0" } }, "Enter systolic & diastolic BP")))))), /* @__PURE__ */ React.createElement("footer", { className: "clinical-footer" }, "Reference: Khadilkar V et al. (2015) Indian Pediatrics \xB7 TW3 (Tanner-Whitehouse 3, 2001) \xB7 QRISK3-2017 (Hippisley-Cox, BMJ 2017; ClinRisk LGPL) \xB7 CKD-EPI 2021 \xB7 Modified Bedside Schwartz (2009) \xB7 FRAX India Asian \xB7 FIB-4 (Sterling et al.) \xB7 For clinical decision support only.")));
  }
  var root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(/* @__PURE__ */ React.createElement(App, null));
})();
