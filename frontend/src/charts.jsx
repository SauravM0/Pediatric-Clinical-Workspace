/**
 * Growth chart SVG rendering.
 *
 * Extracted from app.jsx (M6). Draws the centile curves from the dense series
 * the backend supplies; the same markup is reused for the printable report.
 *
 * COMBINED_CHART_YMAX is pinned per sex rather than derived -- the reference
 * wall chart uses 195 for boys and 175 for girls, and a generic round-up rule
 * reproduces 195 but overshoots girls to 180. Guarded by
 * tests/frontend/test_growth_chart_axis.py.
 */
import { sdsToPercent } from "./growthMath.js";

        function SDSBar({ z }) {
          const left = sdsToPercent(z);
          return (
            <div style={{ paddingTop: '8px', paddingBottom: '4px' }}>
              <div className="sds-track">
                <div className="sds-marker" style={{ left: `${left}%` }}></div>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', marginTop:'6px', fontSize:'9px', fontWeight:'700', color:'#94a3b8', letterSpacing:'0.05em', textTransform:'uppercase' }}>
                <span>−4</span><span>−2</span><span>0</span><span>+2</span><span>+4</span>
              </div>
            </div>
          );
        }

        // ── Growth centile chart (SVG). Draws the 3/10/25/50/75/90/97 WHO curves
        //    for the chosen measure and auto-plots the patient point + serial visits.
        //    The same SVG markup is reused for the printable report. ──────────────
        const MEASURE_META = {
          height: { label: 'Height-for-age', short: 'Height', unit: 'cm' },
          weight: { label: 'Weight-for-age', short: 'Weight', unit: 'kg' },
          bmi:    { label: 'BMI-for-age',    short: 'BMI',    unit: 'kg/m2' },
        };
        // Header colour per sex, matching the familiar IAP wall-chart (girls pink,
        // boys blue). Curves are drawn black on a tan grid like the printed chart;
        // the 3rd percentile is red ("short/low below this line").
        const GENDER_THEME = {
          boys:  { name: 'Boys',  header: '#2f5bb7', point: '#1d4ed8', page: '#bcd4ef' },
          girls: { name: 'Girls', header: '#c74a86', point: '#be185d', page: '#e3a6df' },
        };
        const IAP_INK = '#1f2937', IAP_RED = '#dc2626';
        const IAP_GRID_MAJOR = '#c9b98c', IAP_GRID_MINOR = '#e4dcc2', IAP_PAPER = '#fbf7ea';
        // Combined chart's Y-axis ceiling, matching the printed WHO 2006 + IAP 2015
        // wall chart's own top gridline per sex -- NOT the same number for both:
        // the reference chart uses 195 for boys but only 175 for girls. A generic
        // "round the tallest curve value up to the next multiple of 5" rule
        // happens to reproduce 195 for boys but overshoots to 180 for girls (see
        // growth-chart-codebase-investigation-report.md, S6/S9), so it's fixed per
        // sex here instead. See GrowthChartCombined for the fallback if real data
        // ever exceeds this ceiling.
        const COMBINED_CHART_YMAX = { boys: 195, girls: 175 };

        // Hard sanity check on the fetched height reference data, run immediately
        // before render/export -- NOT a clinical algorithm, just a known-good
        // fingerprint (published WHO/IAP height-for-age P3/P97 at 18y, the same
        // figures verified in growth-chart-codebase-investigation-report.md) used
        // to catch data-binding regressions (wrong sex served, wrong measure,
        // corrupted/truncated response) before a wrong chart ever reaches the
        // screen or a PDF. Tight enough to catch a sex swap (boys vs girls differ
        // by ~15-16cm at both percentiles here), loose enough to tolerate the
        // engine's own PCHIP/blend rounding.
        const CHART_VALIDATION_18Y = {
          // Bounds follow the wall chart's traced height lines at 18 y (boys
          // P3 160.3 / P97 187.0; girls P3 147.1 / P97 169.6), which differ from the
          // published table by up to ~2 cm at P3 and ~1 cm at P97.
          boys:  { p3: [159, 161.5], p97: [186, 188] },
          girls: { p3: [146, 148], p97: [169, 171] },
        };
        function centileValueAtAge(centileSeries, targetAge) {
          if (!Array.isArray(centileSeries) || !centileSeries.length) return null;
          let best = null, bestDist = Infinity;
          for (const [a, v] of centileSeries) {
            const d = Math.abs(a - targetAge);
            if (d < bestDist) { bestDist = d; best = v; }
          }
          return bestDist <= 0.15 ? best : null; // dense sampling is 0.1y steps -- should always hit
        }
        function validateHeightReferenceSanity(heightData, sex) {
          const bounds = CHART_VALIDATION_18Y[sex];
          if (!bounds || !heightData || !heightData.centiles) {
            return { ok: false, reason: 'missing height data or unrecognized sex', p3At18: null, p97At18: null, expected: bounds || null };
          }
          const p3At18 = centileValueAtAge(heightData.centiles['3'], 18);
          const p97At18 = centileValueAtAge(heightData.centiles['97'], 18);
          const inRange = (v, [lo, hi]) => v !== null && v >= lo && v <= hi;
          const ok = inRange(p3At18, bounds.p3) && inRange(p97At18, bounds.p97);
          return { ok, reason: ok ? null : 'height P3/P97 at 18y outside expected reference range', p3At18, p97At18, expected: bounds };
        }

        // Square-cell grid planner. A distorted grid (unequal pixel width/height per
        // minor cell) makes the printed chart unusable for manual plotting, and so
        // does an unpredictable number of minor boxes between two major gridlines --
        // if the axis jumps "0" to "10", there must be exactly GRID_SUBDIVS boxes
        // between them, every time, or the chart can't be read/plotted against with
        // confidence. So both minor steps are always exactly majorStep/GRID_SUBDIVS
        // (never solved for via an aspect-ratio target or rounded to a "close enough"
        // count), and the plot's pixel height is *derived* from that -- not the other
        // way around -- so the two axes come out pixel-square with zero drift.
        const GRID_SUBDIVS = 5; // minor boxes per major gridline, both axes
        function computeSquareGrid(plotWidth, xRange, xMajorStep, yRange, yMajorStep) {
          const xMinorStep = xMajorStep / GRID_SUBDIVS;
          const yMinorStep = yMajorStep / GRID_SUBDIVS;
          const cellPx = plotWidth * xMinorStep / xRange;
          const plotHeight = cellPx * yRange / yMinorStep;
          return { xMinorStep, yMinorStep, cellPx, plotHeight };
        }

        // Clinical growth chart drawn in the authentic IAP style (tan grid, black
        // percentile lines, red 3rd line, right-edge percentile labels), gender-themed,
        // auto-plotting the patient point + serial visits. Vector SVG — crisp & printable.
        function GrowthChart({ measure, sex, ageYears, value, series = [], chartData, width = 780 }) {
          const meta = MEASURE_META[measure];
          const theme = GENDER_THEME[sex] || GENDER_THEME.boys;
          if (!chartData || !chartData.centiles) {
            return <div style={{ fontSize:'12px', color:'#94a3b8', padding:'20px' }}>Loading reference data…</div>;
          }
          // Last-line-of-defense identity guard -- see GrowthChartCombined for the
          // matching check and full rationale.
          if (chartData.sex !== sex || chartData.measure !== measure) {
            return <div style={{ fontSize:'12px', color:'#b91c1c', padding:'20px' }}>Growth chart data does not match the selected sex/measure — refusing to render. Please retry.</div>;
          }
          // chartData comes verbatim from GET /api/growth/chart -- dense (age, value)
          // points per centile, already computed (WHO/IAP blend + PCHIP smoothing) by the
          // Python growth engine. This component only maps those points to pixels; it
          // does not compute or interpolate percentile values itself.
          const centileKeys = Object.keys(chartData.centiles).map(Number).sort((a, b) => a - b);
          const a0 = chartData.age_min, a1 = chartData.age_max;
          const m = { l: 58, r: 50, t: 46, b: 52 };

          const curves = centileKeys.map((c) => {
            const pts = chartData.centiles[c].map(([a, v]) => ({ a, v }));
            return { c, pts, last: pts[pts.length - 1] || null };
          });

          let ymin = Infinity, ymax = -Infinity;
          curves.forEach((cu) => cu.pts.forEach((p) => { ymin = Math.min(ymin, p.v); ymax = Math.max(ymax, p.v); }));
          if (value > 0) { ymin = Math.min(ymin, value); ymax = Math.max(ymax, value); }
          const pad = (ymax - ymin) * 0.05 || 1;
          ymin -= pad; ymax += pad;

          // Square-cell grid: every minor box is a true pixel square with the minor
          // step dividing the major step exactly (see computeSquareGrid) -- no drift,
          // no stretched cells near the bold lines -- so a value read off the printed
          // grid is proportionally correct on both axes.
          const yStep = (ymax - ymin) > 60 ? 20 : (ymax - ymin) > 25 ? 10 : 5;
          const plotWidth = width - m.l - m.r;
          const plan = computeSquareGrid(plotWidth, a1 - a0, 1, ymax - ymin, yStep);
          const height = m.t + plan.plotHeight + m.b;
          const sx = (a) => m.l + (a - a0) / (a1 - a0) * plotWidth;
          const sy = (v) => (height - m.b) - (v - ymin) / (ymax - ymin) * plan.plotHeight;
          const linePath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.a).toFixed(1)},${sy(p.v).toFixed(1)}`).join(' ');

          const plotR = width - m.r, plotB = height - m.b;
          const xticks = []; for (let a = Math.ceil(a0); a <= Math.floor(a1); a++) xticks.push(a);
          // Minor gridlines are anchored to the same phase as the major gridlines
          // (multiples of the major step), not to a0/ymin directly -- otherwise the
          // minor grid drifts out of sync with the bold major lines even though
          // yMinorStep divides yStep exactly.
          const xMinorStart = Math.floor(a0 / 1) * 1;
          const xminors = []; for (let a = xMinorStart; a <= a1 + 1e-6; a += plan.xMinorStep) if (a >= a0 - 1e-6) xminors.push(a);
          const yMinorStart = Math.floor(ymin / yStep) * yStep;
          const yticks = []; for (let v = Math.ceil(ymin / yStep) * yStep; v <= ymax; v += yStep) yticks.push(v);
          const yminors = []; for (let v = yMinorStart; v <= ymax + 1e-6; v += plan.yMinorStep) if (v >= ymin - 1e-6) yminors.push(v);
          const serialPts = [...series].filter(s => s.value > 0 && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);

          return (
            <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ maxWidth:`${width}px`, display:'block' }} xmlns="http://www.w3.org/2000/svg">
              <rect x="0" y="0" width={width} height={height} fill="#ffffff" />
              {/* Header */}
              <rect x="0" y="0" width={width} height="34" fill={theme.header} />
              <text x={m.l} y="15" fontSize="12.5" fontWeight="800" fill="#ffffff">IAP-style {meta.label} · {theme.name}</text>
              <text x={m.l} y="28" fontSize="8.5" fill="#ffffff" opacity="0.9">{chartData.reference} · LMS · percentiles 3–97 · ages {Math.round(a0)}–{Math.round(a1)} yr</text>
              {/* Plot paper + grid */}
              <rect x={m.l} y={m.t} width={plotR-m.l} height={plotB-m.t} fill={IAP_PAPER} stroke={IAP_GRID_MAJOR} strokeWidth="1.2" />
              {yminors.map((v,i)=>(<line key={'ym'+i} x1={m.l} y1={sy(v)} x2={plotR} y2={sy(v)} stroke={IAP_GRID_MINOR} strokeWidth="0.5" />))}
              {xminors.map((a,i)=>(<line key={'xmi'+i} x1={sx(a)} y1={m.t} x2={sx(a)} y2={plotB} stroke={IAP_GRID_MINOR} strokeWidth="0.5" />))}
              {yticks.map((v) => (
                <g key={'y'+v}>
                  <line x1={m.l} y1={sy(v)} x2={plotR} y2={sy(v)} stroke={IAP_GRID_MAJOR} strokeWidth="0.9" />
                  <text x={m.l-6} y={sy(v)+3} textAnchor="end" fontSize="9" fill="#6b7280">{v}</text>
                </g>
              ))}
              {xticks.map((a) => (
                <g key={'x'+a}>
                  <line x1={sx(a)} y1={m.t} x2={sx(a)} y2={plotB} stroke={IAP_GRID_MAJOR} strokeWidth="0.9" />
                  <text x={sx(a)} y={plotB+14} textAnchor="middle" fontSize="9" fill="#6b7280">{a}</text>
                </g>
              ))}
              <text x={(m.l+plotR)/2} y={height-5} textAnchor="middle" fontSize="10" fontWeight="700" fill="#475569">Age (years)</text>
              <text x={15} y={(m.t+plotB)/2} textAnchor="middle" fontSize="10" fontWeight="700" fill="#475569" transform={`rotate(-90 15 ${(m.t+plotB)/2})`}>{meta.short} ({meta.unit})</text>
              {/* Percentile lines (black; 3rd red) + right labels */}
              {curves.map((cu) => {
                const isMed = cu.c === 50, isLow = cu.c === 3;
                const col = isLow ? IAP_RED : IAP_INK;
                const last = cu.last;
                return (
                  <g key={cu.c}>
                    <path d={linePath(cu.pts)} fill="none" stroke={col} strokeWidth={isMed ? 2 : isLow ? 1.7 : 1.1} />
                    {last && <text x={sx(last.a)+3} y={sy(last.v)+3} fontSize="8.5" fontWeight={isMed||isLow ? '800' : '600'} fill={col}>{cu.c}{isLow && measure==='height' ? '  (short below)' : isLow && measure!=='bmi' ? '  (low below)' : ''}</text>}
                  </g>
                );
              })}
              {/* Serial trajectory */}
              {serialPts.length>1 && <polyline fill="none" stroke={theme.point} strokeWidth="1.6" strokeDasharray="5,3" points={serialPts.map(p=>`${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(' ')} />}
              {serialPts.map((p,i)=>(<circle key={'s'+i} cx={sx(p.age)} cy={sy(p.value)} r="3" fill="#ffffff" stroke={theme.point} strokeWidth="1.5" />))}
              {/* Patient point + callout */}
              {value>0 && ageYears>=a0 && ageYears<=a1 && (
                <g>
                  <line x1={sx(ageYears)} y1={m.t} x2={sx(ageYears)} y2={plotB} stroke={theme.point} strokeWidth="0.9" strokeDasharray="2,3" opacity="0.6" />
                  <circle cx={sx(ageYears)} cy={sy(value)} r="5.5" fill={theme.point} stroke="#ffffff" strokeWidth="2.5" />
                  <rect x={sx(ageYears) > plotR-92 ? sx(ageYears)-94 : sx(ageYears)+9} y={sy(value)-21} width="86" height="17" rx="4" fill={theme.point} />
                  <text x={sx(ageYears) > plotR-92 ? sx(ageYears)-51 : sx(ageYears)+52} y={sy(value)-9} textAnchor="middle" fontSize="9.5" fontWeight="800" fill="#ffffff">{Number(value).toFixed(1)} {meta.unit} @ {ageYears.toFixed(1)} y</text>
                </g>
              )}
            </svg>
          );
        }

        // Combined A4-format chart: height (upper curve cluster) and weight (lower
        // cluster) plotted on ONE shared numeric axis, exactly like the printed
        // WHO 2006 + IAP 2015 wall chart -- the axis serves both cm and kg because the
        // two clusters occupy non-overlapping vertical bands at these ages. The grid is
        // built with computeSquareGrid so every minor box is a true pixel square (like
        // the reference chart's fine mesh) and the overall plot approximates an A4
        // sheet, so a printed copy can be used for manual plotting.
        function GrowthChartCombined({ sex, ageYears, heightValue, weightValue, heightData, weightData, heightSeries = [], weightSeries = [], width = 850 }) {
          const theme = GENDER_THEME[sex] || GENDER_THEME.boys;
          if (!heightData || !heightData.centiles || !weightData || !weightData.centiles) {
            return <div style={{ fontSize:'12px', color:'#94a3b8', padding:'20px' }}>Loading reference data…</div>;
          }
          // Last-line-of-defense identity guard: every /api/growth/chart response
          // echoes back the sex and measure it was actually computed for. Refuse to
          // render if either data object doesn't match what this chart was asked to
          // show (wrong sex prop wired to a stale/mismatched fetch, a caller passing
          // the wrong measure's payload, etc.) -- a mismatched chart should error
          // loudly, never silently render the wrong sex's or wrong measure's curves.
          if (heightData.sex !== sex || weightData.sex !== sex) {
            return <div style={{ fontSize:'12px', color:'#b91c1c', padding:'20px' }}>Growth chart data does not match the selected sex — refusing to render. Please retry.</div>;
          }
          if (heightData.measure !== 'height' || weightData.measure !== 'weight') {
            return <div style={{ fontSize:'12px', color:'#b91c1c', padding:'20px' }}>Growth chart data does not match the expected measure — refusing to render. Please retry.</div>;
          }
          // Hard validation: the fetched height curve must reproduce the known-good
          // published P3/P97 values at 18y for this sex (see CHART_VALIDATION_18Y).
          // This is the check most likely to catch a subtle data-binding bug that
          // slips past the sex/measure identity guard above (e.g. a corrupted
          // response body that still self-reports the right sex/measure) --
          // log it loudly and refuse to render or let it reach a printed/exported
          // PDF rather than show a chart that merely looks plausible.
          const heightSanity = validateHeightReferenceSanity(heightData, sex);
          if (!heightSanity.ok) {
            console.error('GrowthChartCombined: height reference data failed sanity validation -- refusing to render/export', { sex, ...heightSanity });
            return <div style={{ fontSize:'12px', color:'#b91c1c', padding:'20px' }}>Growth chart reference data failed a sanity check for {theme.name.toLowerCase()} height (P3/P97 at 18y out of expected range) — refusing to render. Please retry.</div>;
          }
          const centileKeys = Object.keys(heightData.centiles).map(Number).sort((a, b) => a - b);
          // X axis is the wall chart's own frame: origin (0,0), age 0-18.
          const a0 = 0, a1 = Math.max(18, heightData.age_max);
          const m = { l: 70, r: 160, t: 70, b: 110 };
          const plotR = width - m.r;

          const heightCurves = centileKeys.map((c) => ({ c, pts: heightData.centiles[c].map(([a, v]) => ({ a, v })) }));
          const weightCurves = centileKeys.map((c) => ({ c, pts: weightData.centiles[c].map(([a, v]) => ({ a, v })) }));

          let dataMax = 0;
          [...heightCurves, ...weightCurves].forEach((cu) => cu.pts.forEach((p) => { dataMax = Math.max(dataMax, p.v); }));
          if (heightValue > 0) dataMax = Math.max(dataMax, heightValue);
          if (weightValue > 0) dataMax = Math.max(dataMax, weightValue);
          // The Y-axis ceiling is a FIXED constant matching the printed WHO 2006 +
          // IAP 2015 wall chart's own top gridline per sex (195 boys / 175 girls) --
          // it must never move based on what data happens to be plotted. Rescaling
          // the axis to fit an outlier patient value would silently distort every
          // curve and gridline on the chart relative to the standard reference,
          // making it unsafe to eyeball against a printed copy. If a patient's
          // actual height/weight falls outside this fixed range, the chart still
          // renders at the standard scale and a warning is shown instead (see
          // outOfRange below) -- the value is simply not plottable on this chart,
          // not a reason to redraw the chart around it. The dynamic round-up rule
          // only applies in the (should-never-happen) case sex isn't boys/girls.
          const fixedYmax = COMBINED_CHART_YMAX[sex];
          const ymax = fixedYmax || Math.ceil((dataMax * 1.03) / 5) * 5;
          const ymin = 0;
          // Patient values that exceed the fixed axis simply aren't plottable on this
          // chart -- flagged with a warning (below) rather than used to rescale it.
          const heightOutOfRange = heightValue > 0 && heightValue > ymax;
          const weightOutOfRange = weightValue > 0 && weightValue > ymax;
          const outOfRange = heightOutOfRange || weightOutOfRange;

          // Square-cell grid: major gridlines every 5 units (matching the reference
          // wall chart's own labelling, both sexes), minor gridlines every 1 unit --
          // exactly GRID_SUBDIVS (5) boxes between each pair of labels, always, on
          // both axes -- via computeSquareGrid, so the plot is pixel-square with zero
          // drift and the box count between labels is always predictable.
          const yMajor = 5;
          const plotWidth = plotR - m.l;
          const squarePlan = computeSquareGrid(plotWidth, a1 - a0, 1, ymax - ymin, yMajor);
          // Over the 13-year Khadilkar span a pixel-square grid would be ~2.4x taller
          // than wide (far past an A4 sheet), so the plot is capped at 1.5x its width;
          // the gridline COUNTS (5 minor boxes per labelled line) are unchanged.
          // The printed chart has 4 minor boxes per year on x (every 3 months) and 5 per
          // 5 units on y -- measured off the original images, not GRID_SUBDIVS.
          const plan = { ...squarePlan, xMinorStep: 0.25, plotHeight: Math.min(squarePlan.plotHeight, plotWidth * 1.5) };
          const height = m.t + plan.plotHeight + m.b;
          const plotB = height - m.b;
          const sx = (a) => m.l + (a - a0) / (a1 - a0) * plotWidth;
          const sy = (v) => plotB - (v - ymin) / (ymax - ymin) * plan.plotHeight;
          const linePath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.a).toFixed(1)},${sy(p.v).toFixed(1)}`).join(' ');

          const yticks = []; for (let v = 0; v <= ymax; v += yMajor) yticks.push(v);
          const yminors = []; for (let v = 0; v <= ymax + 1e-6; v += plan.yMinorStep) yminors.push(v);
          const xticks = []; for (let a = Math.ceil(a0); a <= Math.floor(a1); a += 1) xticks.push(a);
          const xminors = []; for (let a = a0; a <= a1 + 1e-6; a += plan.xMinorStep) xminors.push(Math.round(a * 10000) / 10000);

          // Same fixed-axis rule applies to historical timeline points: an outlier
          // past measurement is excluded from the plot rather than used to rescale
          // the chart. It's simply not plottable on this fixed-range chart.
          const heightSerial = [...heightSeries].filter(s => s.value > 0 && s.value <= ymax && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);
          const weightSerial = [...weightSeries].filter(s => s.value > 0 && s.value <= ymax && s.age >= a0 && s.age <= a1).sort((a, b) => a.age - b.age);

          const renderCurveGroup = (curves, quantity) => curves.map((cu) => {
            const isMed = cu.c === 50, isLow = cu.c === 3, isHeight = quantity === 'height';
            const col = (isLow && isHeight) ? IAP_RED : IAP_INK;
            const last = cu.pts[cu.pts.length - 1];
            return (
              <g key={quantity + cu.c}>
                <path d={linePath(cu.pts)} fill="none" stroke={col} strokeWidth={isMed ? 2.2 : (isLow && isHeight) ? 1.8 : 1.1} />
                {last && (
                  <text x={sx(last.a) + 4} y={sy(last.v) + 3} fontSize="9.5" fontWeight={isMed || (isLow && isHeight) ? '800' : '600'} fill={col}>
                    {cu.c}{isLow && isHeight ? ' (Short below this line)' : ''}
                  </text>
                )}
              </g>
            );
          });

          const labelBadge = (v, atAge, unit) => {
            const cx = sx(atAge), cy = sy(v);
            const flip = cx > plotR - 112;
            return (
              <g>
                <circle cx={cx} cy={cy} r="5.5" fill={theme.point} stroke="#ffffff" strokeWidth="2.5" />
                <rect x={flip ? cx - 112 : cx + 9} y={cy - 21} width="102" height="17" rx="4" fill={theme.point} />
                <text x={flip ? cx - 61 : cx + 60} y={cy - 9} textAnchor="middle" fontSize="9.5" fontWeight="800" fill="#ffffff">{Number(v).toFixed(1)} {unit} @ {ageYears.toFixed(1)} y</text>
              </g>
            );
          };

          return (
            <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ maxWidth:`${width}px`, display:'block' }} xmlns="http://www.w3.org/2000/svg">
              <rect x="0" y="0" width={width} height={height} fill={theme.page} />
              <rect x="14" y="14" width={width-28} height="40" fill="#ffffff" rx="4" />
              <text x={width/2} y="40" textAnchor="middle" fontSize="16.5" fontWeight="800" fill="#1e293b">WHO 2006 &amp; IAP 2015 combined {theme.name} Chart — Height &amp; Weight, 0–18 Years</text>
              {/* Plot paper + dense reference-style grid */}
              <rect x={m.l} y={m.t} width={plotR-m.l} height={plotB-m.t} fill={IAP_PAPER} stroke={IAP_GRID_MAJOR} strokeWidth="1.2" />
              {yminors.map((v,i)=>(<line key={'ym'+i} x1={m.l} y1={sy(v)} x2={plotR} y2={sy(v)} stroke={IAP_GRID_MINOR} strokeWidth="0.5" />))}
              {xminors.map((a,i)=>(<line key={'xmi'+i} x1={sx(a)} y1={m.t} x2={sx(a)} y2={plotB} stroke={IAP_GRID_MINOR} strokeWidth="0.5" />))}
              {yticks.map((v) => (
                <g key={'y'+v}>
                  <line x1={m.l} y1={sy(v)} x2={plotR} y2={sy(v)} stroke={IAP_GRID_MAJOR} strokeWidth="1" />
                  <text x={m.l-8} y={sy(v)+3} textAnchor="end" fontSize="10" fill="#57534e">{v}</text>
                </g>
              ))}
              {xticks.map((a) => (
                <g key={'x'+a}>
                  <line x1={sx(a)} y1={m.t} x2={sx(a)} y2={plotB} stroke={IAP_GRID_MAJOR} strokeWidth="1" />
                  <text x={sx(a)} y={plotB+16} textAnchor="middle" fontSize="10" fill="#57534e">{a}</text>
                </g>
              ))}
              <text x={(m.l+plotR)/2} y={height-46} textAnchor="middle" fontSize="12" fontWeight="700" fill="#334155">Age in Years</text>
              <text x={24} y={(m.t+plotB)/2} textAnchor="middle" fontSize="12" fontWeight="700" fill="#334155" transform={`rotate(-90 24 ${(m.t+plotB)/2})`}>Height in CM and Weight in KG</text>

              {renderCurveGroup(heightCurves, 'height')}
              {renderCurveGroup(weightCurves, 'weight')}

              {weightSerial.length>1 && <polyline fill="none" stroke={theme.point} strokeWidth="1.6" strokeDasharray="5,3" points={weightSerial.map(p=>`${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(' ')} />}
              {weightSerial.map((p,i)=>(<circle key={'ws'+i} cx={sx(p.age)} cy={sy(p.value)} r="3" fill="#ffffff" stroke={theme.point} strokeWidth="1.5" />))}
              {heightSerial.length>1 && <polyline fill="none" stroke={theme.point} strokeWidth="1.6" strokeDasharray="5,3" points={heightSerial.map(p=>`${sx(p.age).toFixed(1)},${sy(p.value).toFixed(1)}`).join(' ')} />}
              {heightSerial.map((p,i)=>(<circle key={'hs'+i} cx={sx(p.age)} cy={sy(p.value)} r="3" fill="#ffffff" stroke={theme.point} strokeWidth="1.5" />))}

              {ageYears>=a0 && ageYears<=a1 && (heightValue>0 || weightValue>0) && (
                <line x1={sx(ageYears)} y1={m.t} x2={sx(ageYears)} y2={plotB} stroke={theme.point} strokeWidth="1" strokeDasharray="2,3" opacity="0.55" />
              )}
              {heightValue>0 && !heightOutOfRange && ageYears>=a0 && ageYears<=a1 && labelBadge(heightValue, ageYears, 'cm')}
              {weightValue>0 && !weightOutOfRange && ageYears>=a0 && ageYears<=a1 && labelBadge(weightValue, ageYears, 'kg')}

              {outOfRange && (
                <g>
                  <rect x="14" y="58" width={width-28} height="24" fill="#fef2f2" stroke="#fecaca" strokeWidth="1" rx="4" />
                  <text x={width/2} y="74" textAnchor="middle" fontSize="11" fontWeight="800" fill="#b91c1c">
                    ⚠ Patient value is outside standard chart range.
                    {heightOutOfRange ? ` Height ${heightValue}cm` : ''}
                    {heightOutOfRange && weightOutOfRange ? ' and' : ''}
                    {weightOutOfRange ? ` Weight ${weightValue}kg` : ''}
                    {' '}not plotted — axis is fixed to the standard 0–{ymax} reference range.
                  </text>
                </g>
              )}

              <text x={m.l} y={height-26} fontSize="8.5" fill="#6b7280">{heightData.reference}{(heightData.wall_chart_traced_centiles || []).length ? ' · height & weight lines drawn from the IAP wall chart' : ''}</text>
              <text x={m.l} y={height-14} fontSize="8.5" fill="#6b7280">Decision support only — not diagnostic; a clinician must verify all results. Red line = 3rd height percentile ("short below this line").</text>
            </svg>
          );
        }

export { SDSBar, MEASURE_META, GENDER_THEME, COMBINED_CHART_YMAX,
         CHART_VALIDATION_18Y, centileValueAtAge,
         validateHeightReferenceSanity, computeSquareGrid, GrowthChart,
         GrowthChartCombined };
