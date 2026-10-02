/**
 * Growth maths that reads server-provided series.
 *
 * Extracted from app.jsx (M6). Deliberately NOT a re-implementation of the
 * growth engine: every function here reads the already-fetched backend series
 * (like reading a value off a printed chart), which is why the frontend never
 * recomputes LMS or the WHO/IAP blend.
 *
 * zForValueFromCentileStats carries a scope limit -- see its comment. It is
 * only valid for near-symmetric measures, and tests/frontend/
 * test_centile_ladder_scope.py fails if a second caller appears.
 */
        // exaggerates every derived z-score/percentile (audit F-2).
        const IQR_TO_SD = 1.3489795;

        // Standard-normal quantiles of the 7 published centiles, ascending. Used to
        // invert an observed value against a reference distribution WITHOUT assuming
        // normality: interpolate the value across the real (LMS-derived, possibly
        // skewed) percentile anchors from /api/growth/reference-stats, giving the
        // EXACT z at each published centile and a monotone estimate between them.
        // This mirrors what /api/growth/point does continuously, from the already
        // fetched 7-point distribution (no extra request). See tests/growth/
        // test_adult_height_zscore.py for the parity check against the backend.
        //
        // SCOPE LIMIT (M1.2): beyond P3/P97 this extends the centile ladder in a
        // STRAIGHT LINE, which is only correct where the distribution is close to
        // symmetric. Its one caller is adult height at 19y, where WHO's L is ~1 --
        // measured error at +/-3 SD there is 0.000, so it is right for that use.
        // It would NOT be right for weight or BMI, which are strongly right-skewed:
        // the equivalent backend path was mis-scoring their tails by up to 0.81 SD
        // until it was switched to an LMS-shaped tail (iap_reference._lms_tail_z).
        // The backend cannot be mirrored here because L,M,S are not sent to the
        // client. So: do NOT reuse this for a skewed measure -- call
        // /api/growth/point, which is exact for every measure. Guarded by
        // tests/frontend/test_centile_ladder_scope.py.
        const CENTILE_Z = [[3,-1.8807936],[10,-1.2815516],[25,-0.6744898],[50,0.0],[75,0.6744898],[90,1.2815516],[97,1.8807936]];
        function zForValueFromCentileStats(stats, value) {
          if (!stats || !stats.available || !(value > 0)) return null;
          const pts = CENTILE_Z
            .map(([c, z]) => [stats['p' + c], z])
            .filter((p) => typeof p[0] === 'number');
          if (pts.length < 2) return null;
          pts.sort((a, b) => a[0] - b[0]);   // ascending by value
          const lerp = (x0, z0, x1, z1) => (x1 === x0 ? z0 : z0 + (value - x0) / (x1 - x0) * (z1 - z0));
          const n = pts.length;
          if (value <= pts[0][0]) return lerp(pts[0][0], pts[0][1], pts[1][0], pts[1][1]);
          if (value >= pts[n - 1][0]) return lerp(pts[n - 2][0], pts[n - 2][1], pts[n - 1][0], pts[n - 1][1]);
          for (let i = 0; i < n - 1; i++) {
            if (value >= pts[i][0] && value <= pts[i + 1][0]) return lerp(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
          }
          return null;
        }

        // Everything below reads the ALREADY-FETCHED backend series (growthSeries state,
        // from /api/growth/chart -- see the useEffect in App()) rather than recomputing
        // any LMS/blend math client-side. This is array search over server-provided
        // points (like reading a value off a printed chart with a ruler), not a
        // re-implementation of the growth calculation itself.

        // Age (years) at which the median (P50) curve equals the child's value -- i.e.
        // "height age" / "weight age". Searches the dense P50 series already fetched for
        // the chart, so it's pixel-for-pixel consistent with what's drawn.
        function ageForMedianFromSeries(seriesForMeasure, value) {
          if (!seriesForMeasure || !(value > 0)) return { decimal: null, label: "N/A" };
          const p50 = seriesForMeasure.centiles && seriesForMeasure.centiles['50'];
          if (!p50 || p50.length < 2) return { decimal: null, label: "N/A" };
          const first = p50[0][1], last = p50[p50.length - 1][1];
          if (value < first) return { decimal: null, label: `Below ${p50[0][0].toFixed(1)} yr median` };
          if (value > last) return { decimal: null, label: `Above ${p50[p50.length - 1][0].toFixed(1)} yr median` };
          for (let i = 0; i < p50.length - 1; i++) {
            const [ageCur, cur] = p50[i], [ageNxt, nxt] = p50[i + 1];
            if ((value >= cur && value <= nxt) || (value <= cur && value >= nxt)) {
              const frac = nxt === cur ? 0 : (value - cur) / (nxt - cur);
              const dec = ageCur + frac * (ageNxt - ageCur);
              return { decimal: dec, label: `${dec.toFixed(1)} yrs` };
            }
          }
          return { decimal: null, label: "N/A" };
        }

        // Display-only ~1-SD spread, derived from the already-fetched 75th/25th
        // centiles as SD = (P75 - P25) / 1.3489795 (the correct IQR->SD factor for
        // a roughly-normal measure; the old /2 understated it ~1.48x -- audit F-2).
        // Median/point z-scoring itself comes from /api/growth/point (growthPoint
        // state), not from any local calculation.
        function spreadFromSeries(seriesForMeasure, ageYears) {
          const c = seriesForMeasure && seriesForMeasure.centiles;
          if (!c || !c['75'] || !c['25']) return null;
          const nearestIdx = (arr) => {
            let best = 0, bestDiff = Infinity;
            for (let i = 0; i < arr.length; i++) {
              const diff = Math.abs(arr[i][0] - ageYears);
              if (diff < bestDiff) { bestDiff = diff; best = i; }
            }
            return best;
          };
          const i75 = nearestIdx(c['75']), i25 = nearestIdx(c['25']);
          return (c['75'][i75][1] - c['25'][i25][1]) / IQR_TO_SD;
        }

        // SDS bar: maps z from -4..+4 to 0..100%
        function sdsToPercent(z) { return Math.min(Math.max(((z + 4) / 8) * 100, 2), 98); }

        // Probability bar: maps % to 0..100% capped
        function probToPercent(p, max) { return Math.min(Math.max((p / max) * 100, 1), 99); }

        // Standard normal CDF (Abramowitz & Stegun 26.2.17, |error| < 7.5e-8).
        // Moved here from qrisk3.js when QRISK3 moved to the backend: its only
        // remaining user is the adult-height percentile in app.jsx.
        function normalCDF(z) {
          const t = 1 / (1 + 0.2316419 * Math.abs(z));
          const d = 0.39894228 * Math.exp(-z * z / 2);
          const p = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
          return z >= 0 ? 1 - p : p;
        }

export { normalCDF, IQR_TO_SD, CENTILE_Z, zForValueFromCentileStats,
         ageForMedianFromSeries, spreadFromSeries, sdsToPercent,
         probToPercent };
