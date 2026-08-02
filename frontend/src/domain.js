/**
 * Bone-age domain constants and maturity helpers.
 *
 * Extracted from app.jsx (M6). No React, no state -- pure data and functions,
 * so they are importable by a test or another surface without dragging the
 * application in.
 *
 * TW3_CONFIG stays EMPTY on purpose: the per-stage points and the
 * %-of-adult-height table are copyrighted and must be entered from a licensed
 * copy (see backend/tw3/TW3-BOOK-REQUEST.md). Leaving it empty disables the
 * skeletal prediction rather than guessing it.
 */

        // ═══════════════════════════════════════════════════════════════════════════
        //  GROWTH — all percentile/LMS math (WHO under-5 blended with IAP 2015 India
        //  5-18y, PCHIP dense sampling, edge-slope-continuity-validated) lives in the
        //  Python growth engine: backend/growth/ (who_reference.py, iap_reference.py,
        //  blend.py, curve_builder.py, validation.py), served via backend/api_growth.py
        //  as GET /api/growth/chart, /point, /bmi-cutoffs, /reference-stats, /validate.
        //  This frontend fetches and renders that data (see the growthSeries/growthPoint
        //  useEffects in App(), and the GrowthChart component) -- it does not recompute
        //  percentiles, z-scores, or curve shapes itself. See tests/growth/ for the
        //  automated validation suite (pytest).
        // ═══════════════════════════════════════════════════════════════════════════

        // ═══════════════════════════════════════════════════════════════════════════
        //  TW3-C RUS (Chinese) skeletal maturity — scoring lives in the BACKEND
        // ═══════════════════════════════════════════════════════════════════════════
        //  The 13 RUS bones are graded 1–8 by the clinician; the deterministic engine
        //  (backend/tw3/scoring.py) sums the sex-specific points → RUS maturity score →
        //  bone age. The frontend NEVER re-implements the scoring: it fetches the bone
        //  list + allowed grades from /api/bone-age/config and posts confirmed grades to
        //  /api/bone-age/score (single source of truth — directive §38). The score→age
        //  curve is currently PROVISIONAL (digitized); the backend flags this.
        //
        //  The skeletal adult-height prediction below still needs a clinician-supplied
        //  "% of adult height attained by bone age" reference; leaving it empty disables
        //  ONLY that prediction — nothing is guessed.
        const TW3_CONFIG = {
          pctAdultHeight:{ boys: [], girls: [] },
        };

        // Report layout (Tanner–Whitehouse body). Labels match the clinical report;
        // the 7 carpals + TWII/TWIII/TWII'20 scoring are wired in with the original-TW3
        // engine switch. RUS codes map to the backend bone codes.
        const REPORT_RUS = [
          ['radius','Radius'], ['ulna','Ulna'], ['mc1','First metacarpal'],
          ['mc3','Third metacarpal'], ['mc5','Fifth metacarpal'],
          ['pp1','Proximal Phalanx Thumb'], ['pp3','Proximal Phalanx III'], ['pp5','Proximal Phalanx V'],
          ['mp3','Middle Phalanx III'], ['mp5','Middle Phalanx V'],
          ['dp1','Distal Phalanx Thumb'], ['dp3','Distal Phalanx III'], ['dp5','Distal Phalanx V'],
        ];
        const REPORT_CARPALS = ['Capitate','Hamate','Triquetral','Lunate','Scaphoid','Trapezium','Trapezoid'];
        const LETTER_STAGES = ['A','B','C','D','E','F','G','H','I'];
        // Carpal display name <-> backend bone code (lowercase, matches CARPAL_BONES).
        const carpalCode = (name) => name.toLowerCase();
        const carpalName = (code) => code.charAt(0).toUpperCase() + code.slice(1);
        // Acquisition domains (directive §16) — must be tracked separately.
        const IMAGE_DOMAINS = [
          ['digital_diagnostic', 'Digital · DICOM / PACS / direct'],
          ['compressed', 'Compressed · WhatsApp / screenshot'],
          ['film_photo', 'Photo of film · phone camera'],
          ['unknown', 'Unknown'],
        ];
        const LOW_TRUST_DOMAINS = ['compressed', 'film_photo'];

        // Linear interpolation over ascending [x, y] anchor points; null if <2 anchors.
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

        // Skeletal adult-height prediction: % of adult height attained at this bone age →
        // predicted adult height = current height ÷ (% / 100). Needs the licensed
        // pctAdultHeight reference; returns null (not a guess) when absent.
        function pctAdultHeightAt(boneAge, sex) {
          return interpAnchors(TW3_CONFIG.pctAdultHeight && TW3_CONFIG.pctAdultHeight[sex], boneAge);
        }

        function maturationCategory(boneAge, chronoAge) {
          const diff = boneAge - chronoAge;
          if (diff > 1.0) return 'accelerated';
          if (diff < -1.0) return 'retarded';
          return 'average';
        }

        // ═══════════════════════════════════════════════════════════════════════════
        //  QRISK3-2017 — 10-year cardiovascular risk (Hippisley-Cox et al., BMJ 2017)
        // ═══════════════════════════════════════════════════════════════════════════
        //  Coefficients are the ClinRisk open-source release (qrisk.org/src.php),
        //  published under the GNU LGPL specifically so the algorithm can be
        //  reimplemented faithfully. Values are transcribed verbatim from that source.
        //  Ethnicity index: 1 White/not-stated · 2 Indian · 3 Pakistani · 4 Bangladeshi
        //    · 5 Other Asian · 6 Black Caribbean · 7 Black African · 8 Chinese · 9 Other
        //  smoke_cat: 0 non · 1 ex · 2 light(<10) · 3 moderate(10–19) · 4 heavy(20+)
        //  Validated for ages 25–84. Note: derived on a UK cohort; the South-Asian
        //  ethnicity terms partly (not fully) capture excess Indian risk — interpret

export { TW3_CONFIG, REPORT_RUS, REPORT_CARPALS, LETTER_STAGES, carpalCode,
         carpalName, IMAGE_DOMAINS, LOW_TRUST_DOMAINS, interpAnchors,
         pctAdultHeightAt, maturationCategory };
