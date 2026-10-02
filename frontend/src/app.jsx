/**
 * Pediatric Clinical Workspace -- browser application.
 *
 * Extracted VERBATIM from the inline `<script type="text/babel">` block in
 * frontend/index.html (M6). Built to frontend/app.js by build.mjs; the browser
 * loads the built file, never this one.
 *
 * React and ReactDOM are vendored UMD globals (see index.html), so they are
 * referenced directly rather than imported -- that is why there is no
 * `import React from "react"` here, and why build.mjs marks them external.
 *
 * Indentation is intentionally left exactly as it was inside the HTML. Three
 * multi-line template literals in here emit report HTML, and leading
 * whitespace inside a backtick string is significant -- re-indenting would
 * silently change generated report output. Cosmetic re-indentation can happen
 * when the file is split into components, one region at a time, with the
 * literals handled deliberately.
 *
 * The stateless layers now live in sibling modules (domain, growthMath,
 * charts, ui). eGFR, FIB-4, blood pressure and QRISK3 are computed by the
 * backend (serverCalc.js) -- there is no clinical calculator in this bundle. What remains here is the App component itself,
 * which holds ~95 useState hooks; splitting its tab panels out needs a state
 * strategy (context or a reducer), not a mechanical move, so it is left
 * whole deliberately rather than half-cut.
 */
        const { useState, useMemo, useEffect, useRef } = React;

import { carpalCode, pctAdultHeightAt, maturationCategory } from "./domain.js";
import { zForValueFromCentileStats, ageForMedianFromSeries, spreadFromSeries, normalCDF } from "./growthMath.js";
import { useServerCalc, withQuery } from "./serverCalc.js";
import { MEASURE_META, CHART_VALIDATION_18Y, validateHeightReferenceSanity } from "./charts.jsx";
import { StatusBadge, variantToState, computeAgeParts } from "./ui.jsx";
import { ClinicalStateProvider } from "./state.jsx";
import { inRange } from "./clinicalRanges.js";
import { useBoneAgeHandlers } from "./boneAgeHandlers.js";
import { useBoneAgeState } from "./boneAgeState.js";
import { AppHeader, PatientIdentityBar, TabBar } from "./shell.jsx";
import { InputColumn } from "./panels/InputColumn.jsx";
import { useQriskInputs } from "./qriskState.js";
import { RenalPanel } from "./panels/RenalPanel.jsx";
import { LiverPanel } from "./panels/LiverPanel.jsx";
import { FraxPanel } from "./panels/FraxPanel.jsx";
import { OverviewPanel } from "./panels/OverviewPanel.jsx";
import { GrowthPanel } from "./panels/GrowthPanel.jsx";
import { QriskPanel } from "./panels/QriskPanel.jsx";
import { LedgerPanel } from "./panels/LedgerPanel.jsx";
import { BoneAgePanel } from "./panels/BoneAgePanel.jsx";
import { RecordPanel } from "./panels/RecordPanel.jsx";

        function App() {
          const [activeTab, setActiveTab] = useState('overview');
          const [growthChartMeasure, setGrowthChartMeasure] = useState('combined');
          const [showChart, setShowChart] = useState(false);  // growth chart dropdown — collapsed by default; numbers are the primary read
          // Patient identity — a clinical result must be attributable to a
          // patient (safety + medico-legal). Held here and stamped onto exports.
          const [patientName, setPatientName] = useState("");
          const [patientMrn, setPatientMrn] = useState("");
          const [examDate, setExamDate] = useState(() => new Date().toISOString().split('T')[0]);
          // All growth-chart math (WHO/IAP blend, LMS, PCHIP dense sampling) lives in the
          // Python engine (backend/growth) and is served via /api/growth/*. The frontend
          // only fetches and renders -- it does not recompute percentiles, z-scores, or
          // curve shapes itself. growthSeries holds the dense percentile series,
          // keyed as growthSeries[sex][measure] -- NOT just by measure -- so a
          // boys fetch and a girls fetch can never collide in the same slot no
          // matter what order their responses arrive in (see the fetch effect
          // below for the belt-and-suspenders sex-echo check on top of this).
          // growthPoint holds the current patient's z-score/percentile per
          // measure (depends on age/sex/height/weight).
          const [growthSeries, setGrowthSeries] = useState({
            boys: { height: null, weight: null, bmi: null },
            girls: { height: null, weight: null, bmi: null },
          });
          const [growthSeriesLoading, setGrowthSeriesLoading] = useState(true);
          const [growthPoint, setGrowthPoint] = useState({ height: null, weight: null, bmi: null });
          const [growthBmiCutoffs, setGrowthBmiCutoffs] = useState(null);
          const [adultHeightStats, setAdultHeightStats] = useState(null); // /api/growth/reference-stats, for bone-age PAH context
          const [age, setAge] = useState("");
          const [dob, setDob] = useState("");   // date of birth — auto-derives age
          const [gender, setGender] = useState("");
          const [height, setHeight] = useState("");
          const [weight, setWeight] = useState("");
          const [creatinine, setCreatinine] = useState("");
          const [albuminuria, setAlbuminuria] = useState("");
          const [systolic, setSystolic] = useState("");
          const [diastolic, setDiastolic] = useState("");
          const [ast, setAst] = useState("");
          const [alt, setAlt] = useState("");
          const [platelets, setPlatelets] = useState("");
          // FRAX: the two ten-year probabilities from the OFFICIAL calculator, typed
          // in by the clinician. Nothing here computes FRAX (see FraxPanel.jsx).
          const [fraxMofEntered, setFraxMofEntered] = useState("");
          const [fraxHfEntered, setFraxHfEntered] = useState("");
          const [timeline, setTimeline] = useState([]);
          // ── Bone-age workspace state (boneAgeState.js) ──
          // Sixty-odd bindings, their two refs and the boxesRef sync effect.
          // Destructured flat so every reference below is unchanged; App still
          // owns the state (the hook runs in App's render), the module just
          // groups the declarations with the domain they belong to.
          const boneAgeState = useBoneAgeState();
          const {
            DECLARABLE_FLAGS,
            boneAge, setBoneAge, boneAgeSource, setBoneAgeSource,
            rusStages, setRusStages, carpalStages, setCarpalStages,
            tw3Config, setTw3Config,
            letterResult, setLetterResult, boneReport, setBoneReport,
            patientCode, setPatientCode,
            assessment, setAssessment, lcMsg, setLcMsg, lcBusy, setLcBusy,
            showAudit, setShowAudit, radiograph, setRadiograph,
            coverage, setCoverage, covBusy, setCovBusy,
            monitoring, setMonitoring, monBusy, setMonBusy,
            localCohort, setLocalCohort, lcohBusy, setLcohBusy,
            adjItems, setAdjItems, adjBusy, setAdjBusy,
            adjReviewer, setAdjReviewer, adjMsg, setAdjMsg,
            ltTables, setLtTables, ltStatus, setLtStatus,
            ltSection, setLtSection, ltSex, setLtSex,
            ltMsg, setLtMsg, ltBusy, setLtBusy,
            boxes, setBoxes, locImg, setLocImg, locBusy, setLocBusy,
            locMsg, setLocMsg, selBone, setSelBone,
            locDrag, locRef, boxesRef,
            aiEstimate, setAiEstimate, estimateDomain, setEstimateDomain,
            declaredFlags, setDeclaredFlags, lastFilm, setLastFilm,
            fbAge, setFbAge, fbMethod, setFbMethod,
            fbConfidence, setFbConfidence, fbRater, setFbRater,
            fbNote, setFbNote, fbMsg, setFbMsg, fbBusy, setFbBusy,
            aiBusy, setAiBusy,
            fatherHeight, setFatherHeight, motherHeight, setMotherHeight,
          } = boneAgeState;

          // ── QRISK3 cardiovascular inputs (qriskState.js) ──
          // Destructured flat so every reference below is unchanged; App still
          // owns the state, the hook just groups its declaration and defaults.
          const {
            ethnicity, setEthnicity, smokeCat, setSmokeCat, diabetes, setDiabetes,
            cholRatio, setCholRatio, sbpSD, setSbpSD,
            qAF, setQAF, qTreatedHtn, setQTreatedHtn, qRA, setQRA, qCKD, setQCKD,
            qMigraine, setQMigraine, qSLE, setQSLE, qSMI, setQSMI,
            qAtypAntipsy, setQAtypAntipsy, qCortico, setQCortico,
            qED, setQED, qFhCvd, setQFhCvd,
          } = useQriskInputs();

          const evalAge = useMemo(() => age !== "" ? parseFloat(age) : 9.0, [age]);
          const ageParts = useMemo(() => computeAgeParts(dob), [dob]);

          // Date of birth and Chronological Age are two ways to say the same
          // thing — enter either. Setting a DOB derives the decimal age; typing
          // an age by hand clears the DOB so the two never silently disagree.
          const handleDobChange = (e) => {
            const v = e.target.value;
            setDob(v);
            const p = computeAgeParts(v);
            if (p) setAge(Math.round(p.decimal * 10) / 10);   // 1 decimal, e.g. 22.3
          };
          const handleAgeChange = (e) => {
            setAge(e.target.value === "" ? "" : parseFloat(e.target.value));
            if (dob) setDob("");   // manual age overrides the derived DOB
          };

          const evalGender = useMemo(() => gender !== "" ? gender : 'girls', [gender]);
          const evalHeight = useMemo(() => height !== "" ? parseFloat(height) : 131.5, [height]);
          const evalWeight = useMemo(() => weight !== "" ? parseFloat(weight) : 28.2, [weight]);
          const evalCreatinine = useMemo(() => creatinine !== "" ? parseFloat(creatinine) : 0.50, [creatinine]);
          const evalAst = useMemo(() => ast !== "" ? parseFloat(ast) : 25, [ast]);
          const evalAlt = useMemo(() => alt !== "" ? parseFloat(alt) : 20, [alt]);
          const evalPlatelets = useMemo(() => platelets !== "" ? parseFloat(platelets) : 250, [platelets]);

          // A module shows a result only when every input it uses is ENTERED and
          // PLAUSIBLE (clinicalRanges.js). The eval* values above carry placeholder
          // defaults so the maths never sees an empty string; these gates are what
          // stop those placeholders -- or a typo such as creatinine 0 -- from ever
          // reaching a displayed, logged or printed result.
          const ageOk = inRange('age', age), sexOk = gender !== "";
          const heightOk = inRange('height', height), weightOk = inRange('weight', weight);
          const hasManualGrowth = ageOk && sexOk && heightOk && weightOk;
          const hasManualRenal = ageOk && sexOk && heightOk && inRange('creatinine', creatinine);
          const hasManualLiver = ageOk && inRange('ast', ast) && inRange('alt', alt) && inRange('platelets', platelets);
          const hasManualFrax = inRange('fraxPct', fraxMofEntered) && inRange('fraxPct', fraxHfEntered);
          const bpOk = inRange('systolic', systolic) && inRange('diastolic', diastolic) && diastolic < systolic;
          // Sex and age AS ENTERED, or null. evalGender falls back to 'girls' and
          // evalAge to 9.0, so a guard written as "evalGender !== 'boys' &&
          // evalGender !== 'girls'" can never fire: with sex unset, bone-age
          // assessments were saved as girls and the AI model was run as a girl.
          // Anything that PERSISTS, SENDS or DISPLAYS sex/age must use these.
          const sexEntered = sexOk ? gender : null;
          const ageEntered = ageOk ? evalAge : null;

          const growthMetrics = useMemo(() => {
            const bmiVal = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : 0;
            // z-score/percentile per measure come from /api/growth/point (growthPoint
            // state) -- computed server-side by the Python growth engine (WHO under 5y
            // blended with IAP 2015 5-18y). See the useEffect above that populates it.
            const hM = growthPoint.height, wM = growthPoint.weight, bM = growthPoint.bmi;
            const heightZ = hM && hM.available ? hM.z : null;
            const weightZ = wM && wM.available ? wM.z : null;
            const bmiZ    = bM && bM.available ? bM.z : null;
            const heightPct = hM && hM.available ? hM.percentile : null;
            const weightPct = wM && wM.available ? wM.percentile : null;
            const bmiPct    = bM && bM.available ? bM.percentile : null;
            const gs = growthSeries[evalGender];
            const heightAgeObj = ageForMedianFromSeries(gs.height, evalHeight);
            const weightAgeObj = ageForMedianFromSeries(gs.weight, evalWeight);
            const ref = {
              htMean: hM && hM.available ? hM.median_for_age : null,
              htSD: spreadFromSeries(gs.height, evalAge),
              wtMean: wM && wM.available ? wM.median_for_age : null,
              wtSD: spreadFromSeries(gs.weight, evalAge),
            };

            // Height status — WHO height-for-age z cut-offs.
            let stuntingClass = "Insufficient data", stuntingVariant = "mid";
            if (heightZ !== null) {
              stuntingClass = "Normal"; stuntingVariant = "low";
              if (heightZ < -3) { stuntingClass = "Severe stunting"; stuntingVariant = "high"; }
              else if (heightZ < -2) { stuntingClass = "Stunted"; stuntingVariant = "high"; }
              else if (heightZ > 3) { stuntingClass = "Very tall"; stuntingVariant = "mid"; }
              else if (heightZ > 2) { stuntingClass = "Tall stature"; stuntingVariant = "mid"; }
            }
            // Weight/nutrition status — prefer BMI-for-age (valid to 19y); fall back to
            // weight-for-age z only where WHO provides it. Thinness always comes from BMI
            // z (<-2 thin, <-3 severe). Overweight/obese use the IAP/IOTF 23/27
            // adult-equivalent cutoff curves for 5-18y (the Indian-specific definition the
            // paper mandates instead of a fixed BMI z-score, fetched from
            // /api/growth/bmi-cutoffs), falling back to WHO's +1/+2 SD outside that range.
            const bmiCutoffs = growthBmiCutoffs && growthBmiCutoffs.available
              ? [growthBmiCutoffs.overweight_cutoff, growthBmiCutoffs.obesity_cutoff] : null;
            let underweightClass = "Insufficient data", underweightVariant = "mid";
            if (bmiZ !== null) {
              underweightClass = "Normal"; underweightVariant = "low";
              if (bmiZ < -3) { underweightClass = "Severe thinness"; underweightVariant = "high"; }
              else if (bmiZ < -2) { underweightClass = "Thinness"; underweightVariant = "high"; }
              else if (bmiCutoffs) {
                const [c23, c27] = bmiCutoffs;
                if (bmiVal >= c27) { underweightClass = "Obese"; underweightVariant = "high"; }
                else if (bmiVal >= c23) { underweightClass = "Overweight"; underweightVariant = "mid"; }
              } else {
                if (bmiZ > 2) { underweightClass = "Obese"; underweightVariant = "high"; }
                else if (bmiZ > 1) { underweightClass = "Overweight"; underweightVariant = "mid"; }
              }
            } else if (weightZ !== null) {
              underweightClass = "Normal"; underweightVariant = "low";
              if (weightZ < -3) { underweightClass = "Severe underweight"; underweightVariant = "high"; }
              else if (weightZ < -2) { underweightClass = "Underweight"; underweightVariant = "high"; }
              else if (weightZ < -1) { underweightClass = "Mild underweight"; underweightVariant = "mid"; }
            }
            return {
              heightZ, weightZ, bmiZ, heightPct, weightPct, bmiPct, bmiVal,
              stuntingClass, stuntingVariant, underweightClass, underweightVariant,
              heightAge: heightAgeObj, weightAge: weightAgeObj, ref,
              weightAvailable: !!(wM && wM.available),
            };
          }, [evalAge, evalGender, evalHeight, evalWeight, growthPoint, growthSeries, growthBmiCutoffs]);

          // ── Renal, liver: computed by the BACKEND (step 2) ─────────────────────
          // backend/renal and backend/hepatic hold the only implementations, with
          // every equation's age limits enforced and tested. Requests are made only
          // when the inputs are entered and plausible, so no placeholder is ever sent.
          const renalCalc = useServerCalc(hasManualRenal ? { url: withQuery('/api/renal/egfr', {
            sex: gender, age: evalAge, creatinine_mg_dl: evalCreatinine, height_cm: evalHeight,
            weight_kg: weightOk ? evalWeight : null, albuminuria: albuminuria || null,
          }) } : null);
          const renalMetrics = useMemo(() => {
            const r = renalCalc.data;
            if (!r || !r.available) {
              return { ready: false, loading: renalCalc.loading, error: renalCalc.error,
                       reason: r && !r.available ? r.reason : null };
            }
            // Variant follows the KDIGO heat map when albuminuria is recorded. Without
            // it the risk level is unknown -- 'info', never a reassuring green.
            const riskVariant = { low: 'low', moderate: 'mid', high: 'high', very_high: 'high' };
            const g = r.gfr_category && r.gfr_category.code;
            const variant = r.kdigo_risk ? riskVariant[r.kdigo_risk.level]
              : (g === 'G3a' ? 'mid' : ['G3b', 'G4', 'G5'].includes(g) ? 'high' : 'info');
            return { ready: true, result: r, egfr: r.primary.value, stageVariant: variant,
                     category: g || null };
          }, [renalCalc.data, renalCalc.loading, renalCalc.error]);

          const liverCalc = useServerCalc(hasManualLiver ? { url: withQuery('/api/hepatic/fib4', {
            age: evalAge, ast: evalAst, alt: evalAlt, platelets: evalPlatelets,
          }) } : null);
          const liverMetrics = useMemo(() => {
            const r = liverCalc.data;
            if (!r || !r.available) {
              return { ready: false, loading: liverCalc.loading, error: liverCalc.error,
                       reason: r && !r.available ? r.reason : null };
            }
            const variant = { low: 'low', indeterminate: 'mid', high: 'high' }[r.category] || 'info';
            return { ready: true, result: r, fib4: r.fib4, variant, interpretation: r.category_label };
          }, [liverCalc.data, liverCalc.loading, liverCalc.error]);

          // Sex and height are sent when entered: under 13 the AAP 2017 category is
          // by centile for age, sex and height (once the clinic installs the tables).
          const bpCalc = useServerCalc(ageOk && bpOk ? { url: withQuery('/api/vitals/blood-pressure', {
            age: evalAge, sbp: systolic, dbp: diastolic,
            sex: sexEntered, height_cm: heightOk ? evalHeight : null,
          }) } : null);

          // Entered from the official FRAX calculator -- never computed here. The
          // 20% / 3% comparison is the US NOF/BHOF intervention threshold, and the
          // panel says so; it is not an Indian or a universal threshold.
          const fraxMetrics = useMemo(() => {
            if (!hasManualFrax) return { mofProb: null, hfProb: null, isHighMof: false, isHighHf: false };
            const mofProb = parseFloat(fraxMofEntered), hfProb = parseFloat(fraxHfEntered);
            return { mofProb, hfProb, isHighMof: mofProb >= 20, isHighHf: hfProb >= 3 };
          }, [hasManualFrax, fraxMofEntered, fraxHfEntered]);

          const chronicityStatus = useMemo(() => {
            if (timeline.length < 2) return { status: "Add at least 2 snapshots (≥ 90 days apart) to assess CKD chronicity.", cls: "risk-badge-neutral", bgClass: "bg-slate-50 border-slate-200 text-slate-500" };
            const sorted = [...timeline].sort((a,b) => new Date(a.date)-new Date(b.date));
            const diffDays = Math.ceil((new Date(sorted[sorted.length-1].date) - new Date(sorted[0].date)) / 86400000);
            if (diffDays < 90) return { status: `Observation window: ${diffDays} days — need 90 days minimum to confirm chronicity.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
            // An UNRECORDED albuminuria is not a marker of damage -- only A2/A3 is.
            const damaged = (e) => e.egfr < 60 || e.albuminuria === 'A2' || e.albuminuria === 'A3';
            const initDmg = damaged(sorted[0]);
            const curDmg = damaged(sorted[sorted.length-1]);
            if (initDmg && curDmg) return { status: `Chronicity CONFIRMED — Persistent indicators across ${diffDays}-day window.`, bgClass: "bg-rose-50 border-rose-200 text-rose-700 font-bold" };
            // "Transient" is only true when a marker was present at one end. With no
            // marker at either end the honest statement is that none was recorded --
            // an unrecorded albuminuria cannot rule CKD out.
            if (!initDmg && !curDmg) return { status: `No CKD marker (eGFR < 60 or albuminuria A2/A3) in the first or latest snapshot over ${diffDays} days. Unrecorded albuminuria does not exclude CKD.`, bgClass: "bg-slate-50 border-slate-200 text-slate-600" };
            return { status: `Transient profile — a marker was present at only one end of the ${diffDays}-day window.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
          }, [timeline]);

          const generalMetrics = useMemo(() => {
            const bmi = evalWeight / Math.pow(evalHeight/100, 2);
            // Asian adult BMI categories apply from 18 years only. A child's BMI is
            // judged against BMI-for-age (Growth tab), never an adult cut-off.
            const bmiAdult = ageOk && evalAge >= 18;
            let bmiCat = null, bmiVariant = "info";
            if (bmiAdult) {
              bmiCat = "Normal"; bmiVariant = "low";
              if (bmi < 18.5) { bmiCat = "Underweight"; bmiVariant = "mid"; }
              else if (bmi >= 27.5) { bmiCat = "Obese"; bmiVariant = "high"; }
              else if (bmi >= 23.0) { bmiCat = "Overweight"; bmiVariant = "mid"; }
            }
            // Highest band first: checking > 100 before > 110 made "High" unreachable.
            return { bmi, bmiAdult, bmiCat, bmiVariant };
          }, [ageOk, evalAge, evalHeight, evalWeight]);

          // Report/export mode: when loaded as ?report=1 with window.__PCW_REPORT__ set
          // (used by the server-side PDF exporter, backend/api_growth_report.py, driving a
          // headless browser to this exact URL), pre-fill patient state from the query
          // string, jump straight to the growth chart, and switch on the report-mode CSS
          // class (hides header/sidebar/tab bar/in-page buttons -- see the .report-mode
          // rules in <style>) so the exported PDF is a clean single-purpose report
          // rendered by the SAME live chart component/data pipeline as the interactive
          // app, not a second hand-built document.
          useEffect(() => {
            const params = new URLSearchParams(window.location.search);
            if (params.get('report') !== '1') return;
            document.body.classList.add('report-mode');
            // The patient arrives via window.__PCW_REPORT__, injected by the PDF
            // exporter before this script runs -- never in the URL, where name,
            // MRN and measurements used to sit (access log, browser history).
            const r = window.__PCW_REPORT__ || {};
            if (r.sex === 'boys' || r.sex === 'girls') setGender(r.sex);
            if (r.age) setAge(r.age);
            if (r.height) setHeight(r.height);
            if (r.weight) setWeight(r.weight);
            if (r.patient_name) setPatientName(r.patient_name);
            if (r.patient_mrn) setPatientMrn(r.patient_mrn);
            if (r.exam_date) setExamDate(r.exam_date);
            setActiveTab('growth');
            setGrowthChartMeasure('combined');
            setShowChart(true);  // force the chart open so the exported PDF always renders it, even though it is collapsed on screen
          }, []);

          // TW3-C RUS staging is scored by the BACKEND deterministic engine.
          // Fetch the bone list + allowed grades once.
          useEffect(() => {
            fetch('/api/bone-age/config').then(r => r.json()).then(setTw3Config).catch(() => {});
          }, []);

          // Dense percentile chart series (WHO<5y blended with IAP 2015 5-18y, PCHIP
          // dense-sampled) -- depends only on sex, not on the current measurement, so it's
          // fetched once per sex and reused for every render of the chart/report.
          useEffect(() => {
            let cancelled = false;
            const sexAtFetch = evalGender;
            setGrowthSeriesLoading(true);
            Promise.all(
              ['height', 'weight', 'bmi'].map((m) =>
                fetch(`/api/growth/chart?measure=${m}&sex=${sexAtFetch}`).then(r => r.json()).then(d => [m, d])
              )
            ).then((pairs) => {
              // Guard against out-of-order responses: if the user changed sex again
              // before this (earlier) sex's fetches resolved, discard this result --
              // otherwise a slow "girls" response could land after a fast "boys" one
              // and silently overwrite the curves with the wrong sex's data while the
              // chart's title/theme/axis (driven directly by evalGender) already show boys.
              if (cancelled) return;
              // Belt-and-suspenders: /api/growth/chart echoes back the sex it actually
              // served in each response body. If that ever disagrees with sexAtFetch --
              // a backend routing bug, a proxy/cache serving a stale response, anything --
              // refuse to bind it rather than silently rendering boys curves under a
              // girls (or vice versa) title/theme/axis.
              const mismatched = pairs.filter(([, d]) => d && d.sex && d.sex !== sexAtFetch);
              if (mismatched.length) {
                console.error('Growth chart: API returned data for the wrong sex -- discarding', { requested: sexAtFetch, mismatched });
                setGrowthSeriesLoading(false);
                return;
              }
              // Keyed as growthSeries[sex][measure]: writing into this fetch's own
              // sexAtFetch slot can never clobber the other sex's already-cached data,
              // even if responses from two different sex's fetches are in flight at once.
              setGrowthSeries((prev) => ({ ...prev, [sexAtFetch]: Object.fromEntries(pairs) }));
              setGrowthSeriesLoading(false);
            }).catch(() => { if (!cancelled) setGrowthSeriesLoading(false); });
            return () => { cancelled = true; };
          }, [evalGender]);

          // This patient's z-score/percentile per measure, and the IAP/IOTF BMI
          // overweight-obesity cutoffs at their current age -- both computed server-side.
          useEffect(() => {
            // The growth references end at 19 y and the API rejects older ages
            // with 422; an adult simply has no growth centile to fetch.
            // Also skipped until the measurements are really entered: the request
            // otherwise carries the placeholders (girls, 9.0 y, 131.5 cm, 28.2 kg).
            if (!hasManualGrowth || evalAge > 19) {
              setGrowthPoint({ height: null, weight: null, bmi: null });
              setGrowthBmiCutoffs(null);
              return;
            }
            let cancelled = false;
            const bmiVal = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : 0;
            const withValue = { height: evalHeight, weight: evalWeight, bmi: bmiVal };
            Promise.all(
              ['height', 'weight', 'bmi'].map((m) =>
                fetch(`/api/growth/point?measure=${m}&sex=${evalGender}&age=${evalAge}&value=${withValue[m]}`)
                  .then(r => r.json()).then(d => [m, d])
              )
            ).then((pairs) => { if (!cancelled) setGrowthPoint(Object.fromEntries(pairs)); }).catch(() => {});
            fetch(`/api/growth/bmi-cutoffs?sex=${evalGender}&age=${evalAge}`).then(r => r.json())
              .then((d) => { if (!cancelled) setGrowthBmiCutoffs(d); }).catch(() => {});
            return () => { cancelled = true; };
          }, [hasManualGrowth, evalAge, evalGender, evalHeight, evalWeight]);

          // Adult-height distribution for the bone-age target/prediction context.
          // Age 18.0 is the LAST point of the IAP 2015 (Khadilkar) reference the
          // panel names. It used to ask for 19, where IAP has no data and the engine
          // silently answered with WHO (boys' median 176.5 vs IAP 173.6 cm), so an
          // Indian child's target SDS was scored against the wrong population.
          // Must match ADULT_REFERENCE_AGE_YEARS in backend/clinical_service.py.
          useEffect(() => {
            if (!sexEntered) { setAdultHeightStats(null); return; }
            let cancelled = false;
            fetch(`/api/growth/reference-stats?measure=height&sex=${sexEntered}&age=18`)
              .then(r => r.json()).then((d) => { if (!cancelled) setAdultHeightStats(d); }).catch(() => {});
            return () => { cancelled = true; };
          }, [sexEntered]);

          // When a saved assessment with a film is loaded, surface its radiograph so
          // the localization panel (and analysis image) appear without re-attaching.
          useEffect(() => {
            const rid = assessment && assessment.radiograph_id;
            if (rid && (!radiograph || radiograph.radiograph_id !== rid)) {
              setRadiograph(r => ({ ...(r || {}), radiograph_id: rid }));
            }
          }, [assessment]);

          // Live original-TW3 letter scoring for the report: recomputes RUS + carpal
          // scores/ages as the doctor grades. Numbers stay '—' until licensed tables exist.
          useEffect(() => {
            if (!sexEntered) { setLetterResult(null); setBoneReport(null); return; }
            const carp = {}; Object.entries(carpalStages).forEach(([n, g]) => carp[carpalCode(n)] = g);
            const aiYrs = (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null;
            const id = setTimeout(() => {
              fetch('/api/bone-age/letters-score', { method:'POST', headers:{ 'Content-Type':'application/json' },
                body: JSON.stringify({ sex: sexEntered, rus_stages: rusStages, carpal_stages: carp }) })
                .then(r => r.ok ? r.json() : null).then(d => { if (d) setLetterResult(d); }).catch(() => {});
              // Structured 20-bone report (directive S-BA-4): the backend composes
              // it; the UI only renders. Recomputes as the doctor grades.
              fetch('/api/bone-age/report', { method:'POST', headers:{ 'Content-Type':'application/json' },
                body: JSON.stringify({ sex: sexEntered, rus_stages: rusStages, carpal_stages: carp,
                  chronological_age_years: ageEntered, ai_estimate_years: aiYrs }) })
                .then(r => r.ok ? r.json() : null).then(d => { if (d) setBoneReport(d); }).catch(() => {});
            }, 250);
            return () => clearTimeout(id);
          }, [rusStages, carpalStages, sexEntered, ageEntered, aiEstimate]);

          const boneMetrics = useMemo(() => {
            const ba = boneAge !== "" ? parseFloat(boneAge) : null;
            // Bone age vs chronological age needs a REAL chronological age: with age
            // blank, the difference used to be taken against the 9.0 placeholder.
            const hasBone = inRange('boneAge', ba) && ageOk;

            // Mid-parental (genetic target) height — Tanner. Open, non-proprietary.
            const fh = fatherHeight !== "" ? parseFloat(fatherHeight) : null;
            const mh = motherHeight !== "" ? parseFloat(motherHeight) : null;
            let mph = null, mphLow = null, mphHigh = null;
            // Needs the entered sex: the formula differs by sex (+13 / -13 cm), and
            // an unset sex used to fall through to the girls' formula.
            if (sexOk && inRange('parentHeight', fh) && inRange('parentHeight', mh)) {
              mph = sexEntered === 'boys' ? (fh + mh + 13) / 2 : (fh + mh - 13) / 2;
              mphLow = mph - 8.5; mphHigh = mph + 8.5;  // ±8.5 cm target range (Tanner); not literally ±2 SD
            }

            if (!hasBone && mph === null) return null;

            const diff = hasBone ? ba - evalAge : null;
            const autoCat = hasBone ? maturationCategory(ba, evalAge) : null;

            // Skeletal adult-height prediction — ONLY if the licensed TW3 %-attained
            // reference is present; otherwise null (never fabricated).
            const pct = (hasBone && sexOk) ? pctAdultHeightAt(ba, sexEntered) : null;
            const skeletalPah = (pct && pct > 0 && heightOk) ? evalHeight / (pct / 100) : null;
            const skeletalCalibrated = pct !== null;

            // Two DISTINCT clinical quantities -- NEVER conflated (audit F-1):
            //   * Mid-parental height (mph) = the GENETIC TARGET: where the child is
            //     expected to land given the parents. Open Tanner method.
            //   * Skeletal predicted adult height (predictedPah) = a CHILD-SPECIFIC
            //     prediction from the child's own bone age + current height. Needs the
            //     licensed %-attained table; null until calibrated.
            // A prediction is not a target and one is never substituted for the other
            // (the old code showed mph under the "Predicted Adult Height" headline).
            // The clinically useful signal is their DIFFERENCE: does the child's own
            // trajectory fall inside the genetic channel?
            const predictedPah = skeletalPah;   // child-specific; null until calibrated
            const remaining = (predictedPah !== null && heightOk) ? predictedPah - evalHeight : null;
            const predVsTarget = (predictedPah !== null && mph !== null) ? predictedPah - mph : null;
            const withinTarget = (predictedPah !== null && mphLow !== null)
              ? (predictedPah >= mphLow && predictedPah <= mphHigh) : null;

            // Population context (IAP 18y adult-height reference from the same growth
            // engine): a percentile for EACH quantity that exists, computed by
            // inverting the real (LMS-derived, skewed) distribution
            // (zForValueFromCentileStats -- NOT a symmetric SD proxy; audit F-2), and
            // kept separate so a target's percentile is never labelled a prediction's.
            const adultAvailable = adultHeightStats && adultHeightStats.available;
            const adultMedian = adultAvailable ? adultHeightStats.p50 : 170;
            const adult = [adultMedian];
            const zFor = (v) => (v !== null ? zForValueFromCentileStats(adultHeightStats, v) : null);
            const pctFor = (z) => (z !== null ? Math.min(99.9, Math.max(0.1, normalCDF(z) * 100)) : null);
            const predZ = zFor(predictedPah), predPct = pctFor(predZ);
            const mphZ = zFor(mph), mphPct = pctFor(mphZ);

            return { ba, hasBone, diff, autoCat, pct, skeletalPah, skeletalCalibrated,
                     predictedPah, predVsTarget, remaining, predZ, predPct,
                     mph, mphLow, mphHigh, mphZ, mphPct, withinTarget, adult };
          }, [boneAge, ageOk, sexOk, heightOk, sexEntered, evalAge, evalHeight, fatherHeight, motherHeight, adultHeightStats]);

          // ── Assessment lifecycle (persisted via /api/bone-age/assessments) ──────────
          // Bone-age workflow handlers, lifted out of App. See
          // boneAgeHandlers.js for why the handlers move but the state stays.
          const boneAgeHandlers = useBoneAgeHandlers({
            adjReviewer, age, aiEstimate, assessment, boxes, sexEntered, ageEntered,
            boxesRef, carpalStages, coverage, declaredFlags,
            estimateDomain, fbAge, fbConfidence,
            fbMethod, fbNote, fbRater, height, lastFilm, locDrag, locImg,
            locRef, ltTables, monitoring, patientCode, radiograph,
            rusStages, setAdjBusy, setAdjItems, setAdjMsg, setAiBusy,
            setAiEstimate, setAssessment, setBoneAge, setBoneAgeSource,
            setBoxes, setCarpalStages, setCovBusy, setCoverage,
            setDeclaredFlags, setFbAge, setFbBusy, setFbMsg, setFbNote,
            setLastFilm, setLcBusy, setLcMsg, setLocBusy, setLocImg,
            setLocMsg, setLcohBusy, setLocalCohort, setLtBusy, setLtMsg,
            setLtStatus, setLtTables,
            setMonBusy, setMonitoring, setRadiograph, setRusStages,
            setSelBone, setShowAudit, showAudit,
          });
          const { LC_API, lcLocked, unsavedStaging, saveDraft, bonesIntoGrids,
            calculateAssessment, approveAssessment, reviseAssessment, toggleAudit,
            submitFeedback, runEstimate, toggleDeclaredFlag, attachImage, loadCoverage,
            loadMonitoring, loadAdjudication, resolveAdjudication,
            loadLetterTables, setLtPoint, curveToText, setLtCurve,
            setLtSexCurve, useGridAsReference, setRefExpected, saveLetterTables,
            setImageDomain, analysisUrl, localizeBones, addOrSelectBox, clearBox, saveBoxes,
            startBoxDrag, onLocMove, endLocDrag, lcBtn, loadLocalCohort
          } = boneAgeHandlers;

          // QRISK3 from the backend (backend/cvd/qrisk3.py) -- the browser copy was
          // retired after matching it on 300 random patients to within 0.05 points.
          // Called only when age 25-84, sex, height and weight are entered; SBP and
          // the cholesterol ratio are sent only when entered and plausible, and the
          // backend reports every input it had to default.
          const qriskInAgeRange = ageOk && sexOk && evalAge >= 25 && evalAge <= 84;
          const qriskCalc = useServerCalc(qriskInAgeRange && heightOk && weightOk ? { url: '/api/cvd/qrisk3', body: {
            sex: gender, age: evalAge, height_cm: evalHeight, weight_kg: evalWeight,
            ethnicity, smoke: smokeCat, diabetes,
            cholesterol_ratio: inRange('cholRatio', cholRatio) ? parseFloat(cholRatio) : null,
            systolic_bp: inRange('systolic', systolic) ? systolic : null,
            sbp_sd: inRange('sbpSD', sbpSD) ? parseFloat(sbpSD) : null,
            AF: qAF === 'yes', treatedhyp: qTreatedHtn === 'yes', ra: qRA === 'yes',
            renal: qCKD === 'yes', migraine: qMigraine === 'yes', sle: qSLE === 'yes',
            semi: qSMI === 'yes', atypicalantipsy: qAtypAntipsy === 'yes',
            corticosteroids: qCortico === 'yes', impotence2: gender === 'boys' && qED === 'yes',
            fh_cvd: qFhCvd === 'yes',
          } } : null);
          const qriskMetrics = useMemo(() => {
            const r = qriskCalc.data;
            const base = { inAgeRange: qriskInAgeRange, bodySizeOk: heightOk && weightOk,
                           loading: qriskCalc.loading, error: qriskCalc.error };
            if (!r || !r.available) return { ...base, risk: null, reason: r && !r.available ? r.reason : null };
            const band = { high: 'High (≥ 20%)', moderate: 'Moderate (10–20%)', low: 'Low (< 10%)' }[r.band];
            const variant = { high: 'high', moderate: 'mid', low: 'low' }[r.band];
            // Townsend is UK-only and always defaulted (the panel says so once);
            // listing it on every result would bury the inputs that matter.
            const labels = { cholesterol_ratio: 'cholesterol ratio', systolic_bp: 'systolic BP',
                             sbp_sd: 'SBP variability (SD)' };
            const imputed = (r.imputed_fields || []).filter(f => f !== 'townsend').map(f => labels[f] || f);
            return { ...base, risk: r.risk_percent, typical: r.healthy_person_percent, band, variant,
                     imputed, bmiClamped: r.bmi_clamped };
          }, [qriskCalc.data, qriskCalc.loading, qriskCalc.error, qriskInAgeRange, heightOk, weightOk]);

          // ── Single source of truth for each clinical module's headline status ──
          // Consumed by BOTH the Overview tab cards and the tab-bar status dots,
          // so the two can never disagree. state ∈ none|normal|borderline|high.
          const moduleStatus = useMemo(() => {
            // Growth only has a meaningful status when a percentile actually
            // resolved (age within the 0-19y reference); otherwise it is n/a,
            // never a misleading amber "borderline".
            const growthAvailable = hasManualGrowth && growthMetrics.heightPct != null;
            const growthState = !growthAvailable ? 'none'
              : variantToState([growthMetrics.stuntingVariant, growthMetrics.underweightVariant]
                  .includes('high') ? 'high'
                  : [growthMetrics.stuntingVariant, growthMetrics.underweightVariant].includes('mid') ? 'mid' : 'low');
            const boneReady = boneMetrics && boneMetrics.hasBone;
            const boneState = !boneReady ? 'none' : (Math.abs(boneMetrics.diff) > 2 ? 'borderline' : 'normal');
            return {
              growth: {
                state: growthState,
                value: growthAvailable ? growthMetrics.heightPct.toFixed(0) + 'th' : '—',
                unit: 'ht pct',
                label: !hasManualGrowth ? 'Enter age, sex, height & weight'
                  : !growthAvailable ? 'Age outside 0–19y growth reference'
                  : `${growthMetrics.stuntingClass} · ${growthMetrics.underweightClass}`,
                title: 'Growth',
              },
              boneage: {
                state: boneState,
                value: boneReady ? (boneMetrics.diff >= 0 ? '+' : '') + boneMetrics.diff.toFixed(1) : '—',
                unit: 'yr vs CA',
                label: boneReady ? (boneMetrics.diff > 1 ? 'Advanced maturation' : boneMetrics.diff < -1 ? 'Delayed maturation' : 'Concordant with age') : 'Set a TW3 bone age',
                title: 'Bone Age',
              },
              renal: {
                state: renalMetrics.ready ? variantToState(renalMetrics.stageVariant) : 'none',
                value: renalMetrics.ready ? renalMetrics.egfr.toFixed(0) : '—',
                unit: 'mL/min/1.73m²',
                label: renalMetrics.ready
                  ? (renalMetrics.category
                      ? `${renalMetrics.category}${renalMetrics.result.albuminuria_category ? renalMetrics.result.albuminuria_category.code : ''} · ${renalMetrics.result.kdigo_risk ? renalMetrics.result.kdigo_risk.label : 'add ACR for KDIGO risk'}`
                      : 'No KDIGO category under 2 y')
                  : !hasManualRenal ? 'Enter serum creatinine'
                  : renalMetrics.reason || (renalMetrics.error ? 'Calculation failed' : 'Calculating…'),
                title: 'Renal (eGFR)',
              },
              liver: {
                state: liverMetrics.ready ? variantToState(liverMetrics.variant) : 'none',
                value: liverMetrics.ready ? liverMetrics.fib4.toFixed(2) : '—',
                unit: 'FIB-4',
                label: liverMetrics.ready ? liverMetrics.interpretation
                  : !hasManualLiver ? 'Enter AST, ALT & platelets'
                  : liverMetrics.reason || (liverMetrics.error ? 'Calculation failed' : 'Calculating…'),
                title: 'Liver (FIB-4)',
              },
              frax: {
                state: hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'high' : 'normal') : 'none',
                value: hasManualFrax ? fraxMetrics.mofProb.toFixed(1) : '—',
                unit: '% MOF 10-yr',
                label: hasManualFrax
                  ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'At/above US treatment threshold' : 'Below US treatment threshold')
                  : 'Enter the official FRAX result',
                title: 'FRAX (entered)',
              },
              qrisk: {
                state: qriskMetrics.risk !== null ? variantToState(qriskMetrics.variant) : 'none',
                value: qriskMetrics.risk !== null ? qriskMetrics.risk.toFixed(1) : '—',
                unit: '% CVD 10-yr',
                label: qriskMetrics.risk !== null ? qriskMetrics.band : 'Age 25–84 + BMI required',
                title: 'QRISK3 CVD',
              },
            };
          }, [hasManualGrowth, hasManualRenal, hasManualLiver, hasManualFrax,
              growthMetrics, boneMetrics, renalMetrics, liverMetrics, fraxMetrics, qriskMetrics]);

          const resetAll = () => {
            if (!window.confirm('Clear all patient data and results? This cannot be undone.')) return;
            setPatientName(""); setPatientMrn(""); setExamDate(new Date().toISOString().split('T')[0]);
            setAge(""); setDob(""); setGender(""); setHeight(""); setWeight("");
            setCreatinine(""); setAlbuminuria(""); setSystolic(""); setDiastolic("");
            setAst(""); setAlt(""); setPlatelets("");
            setFraxMofEntered(""); setFraxHfEntered("");
            setTimeline([]); setActiveTab('overview');
            setBoneAge(""); setBoneAgeSource("manual"); setRusStages({}); setCarpalStages({});
            setPatientCode(""); setAssessment(null); setLcMsg(null); setShowAudit(false); setRadiograph(null); setAiEstimate(null);
            setFatherHeight(""); setMotherHeight("");
            setEthnicity(2); setSmokeCat(0); setDiabetes(0); setCholRatio(""); setSbpSD("");
            setQAF("no"); setQTreatedHtn("no"); setQRA("no"); setQCKD("no"); setQMigraine("no");
            setQSLE("no"); setQSMI("no"); setQAtypAntipsy("no"); setQCortico("no"); setQED("no"); setQFhCvd("no");
          };

          // A snapshot records ONLY what was entered. It used to store the eval*
          // placeholders (creatinine 0.50, height 131.5, AST 25, albuminuria A1) as
          // a dated result whenever a field was blank, and the chronicity check then
          // reasoned from those invented values.
          const canLogSnapshot = hasManualRenal && renalMetrics.ready;
          const logCurrentData = () => {
            if (!canLogSnapshot) return;
            // Dated by the EXAM date in the identity bar, not today: chronicity
            // needs results >= 90 days apart, which a same-day session could never
            // record when every snapshot was stamped with today's date.
            setTimeline(prev => [{
              id: Date.now().toString(),
              date: examDate || new Date().toISOString().split('T')[0],
              age: evalAge, height: evalHeight,
              weight: weightOk ? evalWeight : null,
              creatinine: evalCreatinine,
              egfr: Number(renalMetrics.egfr.toFixed(1)),
              fib4: liverMetrics.ready ? liverMetrics.fib4 : null,
              albuminuria: albuminuria !== "" ? albuminuria : null,
            }, ...prev]);
          };

          // Open a clean, printable growth report (chart + measurements) in a new window.
          // Preferred export path: server-side headless-Chromium PDF (see
          // backend/api_growth_report.py). This calls Chrome's native
          // Page.printToPDF with displayHeaderFooter=false -- unlike
          // window.print() (the printGrowthReport() fallback below), there is
          // no interactive browser print dialog involved at all, so there's no
          // "Headers and footers" checkbox for a user to forget to uncheck:
          // the date/title/about:blank-URL/page-number browser furniture
          // simply never gets a chance to render. Falls back to the older
          // window.print() flow (with a warning) only if the backend call
          // itself fails (e.g. Playwright not installed on this deployment).
          const exportGrowthReportPdf = async () => {
            // POST: the patient's name, MRN and measurements go in the body, never
            // in a URL (server access log, browser history).
            try {
              const res = await fetch('/api/growth/report.pdf', { method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sex: evalGender, age: evalAge, height: evalHeight || 0, weight: evalWeight || 0,
                                       patient_name: patientName, patient_mrn: patientMrn, exam_date: examDate }) });
              if (!res.ok) {
                const detail = await res.json().catch(() => null);
                throw new Error((detail && detail.detail) || `PDF export failed (HTTP ${res.status})`);
              }
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = `growth-report-${evalGender}.pdf`;
              document.body.appendChild(a); a.click(); document.body.removeChild(a);
              setTimeout(() => URL.revokeObjectURL(url), 5000);
            } catch (err) {
              console.error('exportGrowthReportPdf: server-side PDF export failed, falling back to browser print', err);
              alert('Server-side PDF export is unavailable (' + err.message + '). Falling back to the browser Print dialog -- please uncheck "Headers and footers" in More settings before saving as PDF.');
              printGrowthReport();
            }
          };

          const printGrowthReport = () => {
            // Hard gate: re-run the same height-reference sanity check the chart
            // component itself uses (CHART_VALIDATION_18Y) before ever opening the
            // print/export window. The component already refuses to render bad
            // data, but printGrowthReport is the actual PDF-export trigger -- this
            // makes the "no export on failed validation" guarantee explicit and
            // independent of whatever happens to be in the DOM at click time.
            const exportSanity = validateHeightReferenceSanity(growthSeries[evalGender].height, evalGender);
            if (!exportSanity.ok) {
              console.error('printGrowthReport: refusing to export PDF -- height reference data failed sanity validation', { sex: evalGender, ...exportSanity });
              alert('Growth chart reference data failed a sanity check and cannot be exported. Please retry or contact support.');
              return;
            }
            const chartEl = document.getElementById('growth-chart-print');
            const svg = chartEl ? chartEl.innerHTML : '';
            const g = growthMetrics;
            const row = (k, v) => `<tr><td style="padding:4px 12px 4px 0;color:#64748b">${k}</td><td style="padding:4px 0;font-weight:700">${v}</td></tr>`;
            const fmtZ = (z) => z === null || z === undefined ? '—' : (z>=0?'+':'') + z.toFixed(2);
            const fmtP = (p) => p === null || p === undefined ? '—' : p.toFixed(1) + 'th';
            // Every user-typed value is escaped before it is written into the report
            // document -- a name such as "<img onerror=...>" would otherwise run as
            // markup in the print window. exportFullReport already did this.
            const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
            const win = window.open('', '_blank', 'width=820,height=1000');
            if (!win) { alert('Please allow pop-ups to print the growth report.'); return; }
            const chartLabel = growthChartMeasure === 'combined' ? 'Height & Weight (combined chart)' : MEASURE_META.bmi.label;
            win.document.write(`<!DOCTYPE html><html><head><title>Growth Report</title>
              <style>body{font-family:Inter,Arial,sans-serif;color:#1e293b;margin:14mm}
              h1{font-size:18px;margin:0 0 2px}.sub{color:#64748b;font-size:11px;margin-bottom:14px}
              .chart-sheet{width:190mm;height:277mm;margin:0 auto;display:flex;align-items:center;justify-content:center}
              .chart-sheet svg{width:100%;height:100%}
              table{border-collapse:collapse;font-size:12px;margin-top:10px}
              .foot{margin-top:18px;font-size:10px;color:#94a3b8;line-height:1.5;border-top:1px solid #e5e7eb;padding-top:8px}
              @media print{@page{size:A4;margin:10mm}.chart-sheet{page-break-after:always}}</style></head><body>
              <h1>Pediatric Growth Report</h1>
              <div class="sub" style="font-weight:700;color:#334155">${esc(patientName || 'Unnamed patient')} · MRN ${esc(patientMrn || '—')} · Exam ${esc(examDate)}</div>
              <div class="sub">Reference: ${esc((growthSeries[evalGender].height && growthSeries[evalGender].height.reference) || 'WHO + IAP 2015')} · ${esc(chartLabel)} · ${new Date().toLocaleDateString()}</div>
              <div class="chart-sheet">${svg}</div>
              <table>
                ${row('Sex', evalGender === 'girls' ? 'Female' : 'Male')}
                ${row('Chronological age', evalAge.toFixed(1) + ' yrs')}
                ${row('Height', esc(evalHeight) + ' cm  ·  z ' + fmtZ(g.heightZ) + '  ·  ' + fmtP(g.heightPct) + ' pct')}
                ${row('Weight', esc(evalWeight) + ' kg' + (g.weightAvailable ? '  ·  z ' + fmtZ(g.weightZ) + '  ·  ' + fmtP(g.weightPct) + ' pct' : '  (weight-for-age n/a at this age — use BMI)'))}
                ${row('BMI', g.bmiVal.toFixed(1) + ' kg/m²  ·  z ' + fmtZ(g.bmiZ) + '  ·  ' + fmtP(g.bmiPct) + ' pct')}
                ${row('Height status', g.stuntingClass)}
                ${row('Weight / BMI status', g.underweightClass)}
                ${row('Height age', esc(g.heightAge.label))}
              </table>
              <div class="foot">Decision support only — not a diagnostic device. A clinician must verify all results.
              Percentiles computed with the LMS method: WHO 2006 reference under 5 years; IAP 2015 (Khadilkar) Indian reference for height, weight and BMI from 5-18 years. The IAP 2015 curves were fit from the paper's own published percentile tables (the authors' original L,M,S triplets are unpublished) — overweight/obesity for 5-18y use the IAP/IOTF 23 and 27 adult-equivalent BMI cutoffs rather than a fixed z-score.</div>
              </body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => win.print(), 350);
          };

          // Combined one-page clinical summary across every module, stamped with
          // patient identity. Reads the same moduleStatus single-source-of-truth
          // the Overview cards use, so the printed summary can never disagree with
          // what is on screen. The growth chart keeps its own dedicated PDF export
          // (exportGrowthReportPdf) -- this is the numeric cross-module summary.
          const exportFullReport = () => {
            const win = window.open('', '_blank', 'width=820,height=1000');
            if (!win) { alert('Please allow pop-ups to print the report.'); return; }
            const esc = (s) => String(s == null ? '' : s).replace(/[&<>]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;' }[c]));
            const stateColor = { high:'#dc2626', borderline:'#d97706', normal:'#16a34a', none:'#94a3b8' };
            const rows = ['growth','boneage','renal','liver','frax','qrisk'].map((k) => {
              const m = moduleStatus[k];
              return `<tr>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7;font-weight:600">${esc(m.title)}</td>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7"><b>${esc(m.value)}</b> <span style="color:#94a3b8;font-size:11px">${esc(m.unit)}</span></td>
                <td style="padding:9px 12px;border-bottom:1px solid #eef2f7;color:${stateColor[m.state]};font-weight:700">${m.state === 'none' ? '—' : esc(m.label)}</td>
              </tr>`;
            }).join('');
            const idLine = `${esc(patientName || 'Unnamed patient')} · MRN ${esc(patientMrn || '—')} · ${age !== '' ? esc(age) + ' yr' : '— yr'} · ${gender === 'boys' ? 'Male' : gender === 'girls' ? 'Female' : '—'} · Exam ${esc(examDate)}`;
            win.document.write(`<!DOCTYPE html><html><head><title>Clinical Summary — ${esc(patientName || 'patient')}</title>
              <style>body{font-family:Inter,Arial,sans-serif;color:#1e293b;margin:16mm}
              h1{font-size:20px;margin:0 0 4px}.sub{color:#334155;font-size:12px;font-weight:600;margin-bottom:16px}
              table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
              th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;padding:0 12px 6px;border-bottom:1.5px solid #e2e8f0}
              .foot{margin-top:20px;font-size:10px;color:#94a3b8;line-height:1.6;border-top:1px solid #e5e7eb;padding-top:10px}
              @media print{@page{size:A4;margin:12mm}}</style></head><body>
              <h1>Pediatric Clinical Summary</h1>
              <div class="sub">${idLine}</div>
              <table><thead><tr><th>Module</th><th>Result</th><th>Interpretation</th></tr></thead><tbody>${rows}</tbody></table>
              <div class="foot">Decision support only — not a diagnostic device. A clinician must verify every value. A "—" interpretation means that module had insufficient input. References: Khadilkar 2015 · TW3-C (Chinese) RUS — provisional research curve (±0.5y, digitized from a published figure); NOT Tanner–Whitehouse TW3 · QRISK3-2017 · CKD-EPI 2021 · Bedside Schwartz 2009 · CKiD U25 2021 · KDIGO · AAP 2017 / ACC-AHA 2017 BP · FRAX: result from the official University of Sheffield calculator, entered by the clinician (threshold = US NOF/BHOF) · FIB-4 (Sterling et al.).</div>
              </body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => win.print(), 300);
          };

          const TABS = [
            { id: 'overview', label: 'Overview' },
            { id: 'growth',   label: 'Growth' },
            { id: 'record',   label: 'Patient Record' },
            { id: 'boneage',  label: 'Bone Age' },
            { id: 'renal',    label: 'Renal GFR' },
            { id: 'liver',    label: 'FIB-4 Liver' },
            { id: 'frax',     label: 'FRAX' },
            { id: 'qrisk',    label: 'QRISK3 CVD' },
            { id: 'timeline', label: 'Ledger' },
          ];

          // Which left-panel sections the active tab actually consumes. The panel
          // stays live and fully editable (results still auto-update) -- irrelevant
          // sections are just visually de-emphasised so entry is faster and quieter.
          // Demographics is never dimmed: it drives every module.
          const labsRelevant = ['renal','liver','qrisk','timeline','overview'].includes(activeTab);

          // The slice the extracted panels read. Deliberately explicit rather
          // than spreading everything: a panel should not be able to reach a
          // value nobody decided to share with it, and the list doubles as the
          // record of what is genuinely cross-panel.
          //
          // A plain object, not a useMemo: it aggregates ~120 values that change
          // on nearly every render, so memoising bought nothing and cost a
          // hand-maintained dependency array -- and a wrong entry there is a
          // temporal-dead-zone crash at mount, not a merely stale value.
          const clinicalState = {
            // The whole bone-age domain as ONE slice: its state module, its handler
            // module, and the few values App derives from them. Listing the names
            // again here (and a third time in useBoneAge) is what let a wired-up
            // handler reach a panel as undefined -- the button rendered and did
            // nothing. Spreading the bags makes that impossible by construction.
            boneAge: { ...boneAgeState, ...boneAgeHandlers,
                       age, boneMetrics, evalAge, evalGender, evalHeight, height },
            age, dob, gender, height, weight,
            evalAge, evalHeight, evalWeight,
            patientName, patientMrn, examDate,
            liverMetrics, hasManualLiver, bpCalc,
            renalMetrics, hasManualRenal, creatinine,
            fraxMetrics, hasManualFrax,
            fraxMofEntered, setFraxMofEntered, fraxHfEntered, setFraxHfEntered,
            canLogSnapshot,
            sexEntered, heightOk, weightOk, bpOk,
            // ── the input column's slice (useInputs): the ONLY setters for the
            // shared measurements, because it is the only thing that writes them
            setGender, setHeight, setWeight,
            handleAgeChange, handleDobChange, ageParts,
            labsRelevant,
            setCreatinine, setAlbuminuria,
            systolic, setSystolic, diastolic, setDiastolic,
            ast, setAst, alt, setAlt, platelets, setPlatelets,
            // ── the shell's slice (useShell): header, identity bar, tabs
            resetAll, exportFullReport, TABS, activeTab,
            setPatientName, setPatientMrn, setExamDate,
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
            timeline,
          };

          return (
            <ClinicalStateProvider value={clinicalState}>
            <div className="app-shell">

              <AppHeader />
              <PatientIdentityBar />

              {/* ── MAIN ── */}
              <main className="app-main">

                <InputColumn />

                {/* ─── RIGHT COLUMN: Results ─── */}
                <div className="result-column">

                  <TabBar />

                  {/* Result Panel */}
                  <div className="card-lg result-panel">

                    {/* ══ OVERVIEW TAB ══ */}
                    {activeTab === 'overview' && <OverviewPanel />}
                    {activeTab === 'growth' && <GrowthPanel />}
                    {activeTab === 'boneage' && <BoneAgePanel />}
                    {activeTab === 'record' && <RecordPanel />}
                    {/* ══ RENAL TAB ══ */}
                    {activeTab === 'renal' && <RenalPanel />}
                    {activeTab === 'liver' && <LiverPanel />}
                    {activeTab === 'frax' && <FraxPanel />}
                    {activeTab === 'qrisk' && <QriskPanel />}
                    {activeTab === 'timeline' && <LedgerPanel />}

                  </div>

                  {/* ── General Health Strip -- not part of the growth report, hidden in report/export mode ── */}
                  <div className="card no-print" style={{ padding:'20px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'14px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
                      <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#0891b2', flexShrink:0 }}></div>
                      <span className="section-label">General Health Indicators</span>
                    </div>
                    <div className="general-grid">
                      <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e8ecf0' }}>
                        <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'6px' }}>Body Mass Index</div>
                        {heightOk && weightOk ? (
                          <>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                              <span style={{ fontSize:'28px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{generalMetrics.bmi.toFixed(1)}</span>
                              <span style={{ fontSize:'12px', color:'#94a3b8' }}>kg/m²</span>
                            </div>
                            {generalMetrics.bmiAdult ? (
                              <>
                                <div style={{ marginTop:'6px' }}>
                                  <StatusBadge text={generalMetrics.bmiCat} variant={generalMetrics.bmiVariant} />
                                </div>
                                <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'4px' }}>Asian adult cutoffs: Normal &lt; 23, OW ≥ 23, Obese ≥ 27.5</div>
                              </>
                            ) : (
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'6px', lineHeight:'1.5' }}>
                                {ageOk ? 'Under 18: interpret with BMI-for-age on the Growth tab, not adult cut-offs.' : 'Enter age to categorise (adult cut-offs apply from 18 y).'}
                              </div>
                            )}
                          </>
                        ) : <div style={{ fontSize:'12px', color:'#94a3b8', padding:'6px 0' }}>Enter height &amp; weight</div>}
                      </div>
                      <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e8ecf0' }}>
                        <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'6px' }}>Blood Pressure</div>
                        {!(bpOk && ageOk) ? (
                          <div style={{ fontSize:'12px', color:'#94a3b8', padding:'6px 0' }}>Enter age and a plausible systolic &amp; diastolic BP</div>
                        ) : !bpCalc.data ? (
                          <div style={{ fontSize:'12px', color:'#94a3b8', padding:'6px 0' }}>{bpCalc.error ? 'Calculation failed: ' + bpCalc.error : 'Calculating…'}</div>
                        ) : (
                          <>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                              <span style={{ fontSize:'28px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{systolic}/{diastolic}</span>
                              <span style={{ fontSize:'12px', color:'#94a3b8' }}>mmHg · MAP {bpCalc.data.map}</span>
                            </div>
                            {bpCalc.data.available ? (
                              <>
                                <div style={{ marginTop:'6px' }}>
                                  <StatusBadge text={bpCalc.data.category_label}
                                    variant={{ normal:'low', elevated:'mid', stage1:'mid', stage2:'high', severe:'high' }[bpCalc.data.category]} />
                                </div>
                                <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'4px', lineHeight:'1.5' }}>{bpCalc.data.guideline} · {bpCalc.data.notes.join(' ')}</div>
                              </>
                            ) : (
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'6px', lineHeight:'1.5' }}>{bpCalc.data.reason}</div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              </main>

              {/* ── FOOTER ── */}
              <footer className="clinical-footer">
                Reference: Khadilkar V et al. (2015) Indian Pediatrics · TW3 (Tanner-Whitehouse 3, 2001) · QRISK3-2017 (Hippisley-Cox, BMJ 2017; ClinRisk LGPL) · CKD-EPI 2021 · Modified Bedside Schwartz (2009) · FRAX (official calculator result, entered) · FIB-4 (Sterling et al.) · For clinical decision support only.
              </footer>

            </div>
            </ClinicalStateProvider>
          );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
