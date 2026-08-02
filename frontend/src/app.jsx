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
 * The stateless layers now live in sibling modules (domain, qrisk3,
 * growthMath, charts, ui). What remains here is the App component itself,
 * which holds ~95 useState hooks; splitting its tab panels out needs a state
 * strategy (context or a reducer), not a mechanical move, so it is left
 * whole deliberately rather than half-cut.
 */
        const { useState, useMemo, useEffect, useRef } = React;

import { TW3_CONFIG, REPORT_RUS, REPORT_CARPALS, LETTER_STAGES, carpalCode,
         carpalName, IMAGE_DOMAINS, LOW_TRUST_DOMAINS, interpAnchors,
         pctAdultHeightAt, maturationCategory } from "./domain.js";
import { QRISK3_FEMALE, QRISK3_MALE, qrisk3, normalCDF } from "./qrisk3.js";
import { IQR_TO_SD, CENTILE_Z, zForValueFromCentileStats,
         ageForMedianFromSeries, spreadFromSeries, sdsToPercent,
         probToPercent } from "./growthMath.js";
import { SDSBar, MEASURE_META, GENDER_THEME, COMBINED_CHART_YMAX,
         CHART_VALIDATION_18Y, centileValueAtAge,
         validateHeightReferenceSanity, computeSquareGrid, GrowthChart,
         GrowthChartCombined } from "./charts.jsx";
import { ProbBar, StatusBadge, MetricRow, SectionHeader, FraxToggleRow,
         InputWithUnit, EmptyState, heroTone, variantToState,
         computeAgeParts } from "./ui.jsx";

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
          const [prevFracture, setPrevFracture] = useState("no");
          const [parentHipFracture, setParentHipFracture] = useState("no");
          const [smoking, setSmoking] = useState("no");
          const [glucocorticoids, setGlucocorticoids] = useState("no");
          const [rheumatoid, setRheumatoid] = useState("no");
          const [secondaryOsteo, setSecondaryOsteo] = useState("no");
          const [alcohol, setAlcohol] = useState("no");
          const [timeline, setTimeline] = useState([]);
          const [boneAge, setBoneAge] = useState("");        // TW3 bone age (RUS-derived or manual)
          const [boneAgeSource, setBoneAgeSource] = useState("manual"); // manual | rus
          const [rusStages, setRusStages] = useState({});    // { boneCode: 'A'..'I' }
          const [carpalStages, setCarpalStages] = useState({}); // { carpalName: 'A'..'I' }
          const [tw3Config, setTw3Config] = useState(null);  // /api/bone-age/config
          const [rusResult, setRusResult] = useState(null);  // /api/bone-age/score
          const [letterResult, setLetterResult] = useState(null); // live /letters-score (RUS+carpal)
          const [boneReport, setBoneReport] = useState(null); // live /report (structured 20-bone)
          const [patientCode, setPatientCode] = useState(""); // assessment lifecycle
          const [approverName, setApproverName] = useState("");
          const [assessment, setAssessment] = useState(null); // saved lifecycle record
          const [lcMsg, setLcMsg] = useState(null);           // {type:'ok'|'err', text}
          const [lcBusy, setLcBusy] = useState(false);
          const [showAudit, setShowAudit] = useState(false);
          const [radiograph, setRadiograph] = useState(null); // attached film metadata
          const [coverage, setCoverage] = useState(null);     // /api/bone-age/coverage
          const [covBusy, setCovBusy] = useState(false);
          const [monitoring, setMonitoring] = useState(null); // /api/bone-age/monitoring
          const [monBusy, setMonBusy] = useState(false);
          const [adjItems, setAdjItems] = useState(null);     // /api/bone-age/adjudication (open)
          const [adjBusy, setAdjBusy] = useState(false);
          const [adjReviewer, setAdjReviewer] = useState(""); // the resolving clinician
          const [adjMsg, setAdjMsg] = useState(null);
          const [ltTables, setLtTables] = useState(null);     // licensed TW3 tables editor
          const [ltStatus, setLtStatus] = useState(null);
          const [ltSection, setLtSection] = useState('rus');  // rus | carpal | curves | ref
          const [ltSex, setLtSex] = useState('boys');
          const [ltMsg, setLtMsg] = useState(null);
          const [ltBusy, setLtBusy] = useState(false);
          const [boxes, setBoxes] = useState({});       // {bone_code:[x0,y0,x1,y1] in image px}
          const [locImg, setLocImg] = useState(null);   // {width,height}
          const [locBusy, setLocBusy] = useState(false);
          const [locMsg, setLocMsg] = useState(null);
          const [selBone, setSelBone] = useState(null);
          const locDrag = useRef(null);
          const locRef = useRef(null);
          const boxesRef = useRef({});          // always-current boxes (avoids stale closures)
          useEffect(() => { boxesRef.current = boxes; }, [boxes]);
          const [aiEstimate, setAiEstimate] = useState(null); // AI screening estimate
          const [estimateDomain, setEstimateDomain] = useState('unknown'); // quality gate for quick estimate
          const [declaredFlags, setDeclaredFlags] = useState([]); // clinician-declared image issues (S-BA-6 gate)
          const [lastFilm, setLastFilm] = useState(null);         // last attached film, to re-gate on flag toggle
          // Hard quality flags the clinician can declare; any one makes the AI estimate abstain.
          const DECLARABLE_FLAGS = [
            ['FRACTURE', 'Fracture'], ['CAST_OR_HARDWARE', 'Cast / hardware'],
            ['WRONG_LATERALITY', 'Wrong side'], ['CLIPPED_DIGITS', 'Clipped anatomy'],
            ['SEVERE_DEFORMITY', 'Deformity'], ['FOREIGN_OBJECT', 'Foreign object'],
          ];
          // Suggestion box — clinician's corrected bone age (self-improvement flywheel).
          const [fbAge, setFbAge] = useState('');
          const [fbMethod, setFbMethod] = useState('tw3-rus');
          const [fbConfidence, setFbConfidence] = useState('medium');
          const [fbRater, setFbRater] = useState('');
          const [fbNote, setFbNote] = useState('');
          const [fbMsg, setFbMsg] = useState(null);
          const [fbBusy, setFbBusy] = useState(false);
          const [aiBusy, setAiBusy] = useState(false);
          const [fatherHeight, setFatherHeight] = useState("");
          const [motherHeight, setMotherHeight] = useState("");

          // ── QRISK3 cardiovascular inputs ──
          const [ethnicity, setEthnicity] = useState(2);     // default Indian
          const [smokeCat, setSmokeCat] = useState(0);
          const [diabetes, setDiabetes] = useState(0);       // 0 none · 1 type1 · 2 type2
          const [cholRatio, setCholRatio] = useState("");    // total cholesterol / HDL
          const [sbpSD, setSbpSD] = useState("");            // SBP standard deviation (optional)
          const [qAF, setQAF] = useState("no");
          const [qTreatedHtn, setQTreatedHtn] = useState("no");
          const [qRA, setQRA] = useState("no");
          const [qCKD, setQCKD] = useState("no");
          const [qMigraine, setQMigraine] = useState("no");
          const [qSLE, setQSLE] = useState("no");
          const [qSMI, setQSMI] = useState("no");
          const [qAtypAntipsy, setQAtypAntipsy] = useState("no");
          const [qCortico, setQCortico] = useState("no");
          const [qED, setQED] = useState("no");
          const [qFhCvd, setQFhCvd] = useState("no");

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
          const evalAlbuminuria = useMemo(() => albuminuria !== "" ? albuminuria : 'A1', [albuminuria]);
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
            if (type === 'child') {
              setAge(9.0); setGender('girls'); setHeight(120.9); setWeight(22.4);
              setCreatinine(0.50); setAlbuminuria('A1'); setSystolic(104); setDiastolic(64);
              setAst(22); setAlt(18); setPlatelets(280);
              setPrevFracture("no"); setParentHipFracture("no"); setSmoking("no");
              setGlucocorticoids("no"); setRheumatoid("no"); setSecondaryOsteo("no"); setAlcohol("no");
            } else {
              setAge(58); setGender('boys'); setHeight(171.0); setWeight(79.5);
              setCreatinine(1.35); setAlbuminuria('A2'); setSystolic(138); setDiastolic(88);
              setAst(44); setAlt(42); setPlatelets(165);
              setPrevFracture("yes"); setParentHipFracture("no"); setSmoking("yes");
              setGlucocorticoids("yes"); setRheumatoid("no"); setSecondaryOsteo("yes"); setAlcohol("no");
            }
          };

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

          const renalMetrics = useMemo(() => {
            const isPediatric = evalAge < 18;
            let egfr = 0, formulaName = '';
            if (isPediatric) {
              egfr = (0.413 * evalHeight) / evalCreatinine;
              formulaName = "Modified Bedside Schwartz (2009)";
            } else {
              const isFemale = evalGender === 'girls';
              const kappa = isFemale ? 0.7 : 0.9, alpha = isFemale ? -0.241 : -0.302;
              const gConst = isFemale ? 1.012 : 1;
              const term1 = evalCreatinine / kappa;
              egfr = 142 * Math.pow(Math.min(term1,1), alpha) * Math.pow(Math.max(term1,1), -1.200) * Math.pow(0.9938, evalAge) * gConst;
              formulaName = "2021 CKD-EPI Creatinine";
            }
            let cg = null, mdrd = null;
            if (!isPediatric && evalWeight > 0) {
              const isFemale = evalGender === 'girls';
              cg = ((140-evalAge)*evalWeight) / (72*evalCreatinine) * (isFemale ? 0.85 : 1);
              mdrd = 175 * Math.pow(evalCreatinine,-1.154) * Math.pow(evalAge,-0.203) * (isFemale ? 0.742 : 1);
            }
            let ckdStage = 'G1', ckdStageDesc = "Normal / High", stageVariant = "low";
            if (egfr < 15) { ckdStage = 'G5'; ckdStageDesc = "Kidney Failure"; stageVariant = "high"; }
            else if (egfr < 30) { ckdStage = 'G4'; ckdStageDesc = "Severely Decreased"; stageVariant = "high"; }
            else if (egfr < 60) { ckdStage = 'G3'; ckdStageDesc = "Moderately Decreased"; stageVariant = "mid"; }
            else if (egfr < 90) { ckdStage = 'G2'; ckdStageDesc = "Mildly Decreased"; stageVariant = "mid"; }
            return { egfr, formulaName, cg, mdrd, ckdStage, ckdStageDesc, stageVariant, isPediatric };
          }, [evalAge, evalGender, evalHeight, evalWeight, evalCreatinine]);

          const liverMetrics = useMemo(() => {
            const fib4 = (evalAge * evalAst) / (evalPlatelets * Math.sqrt(evalAlt));
            let interpretation = "Low Risk", variant = "low", details = "Low probability of advanced fibrosis.";
            const highThresh = 2.67, midThresh = evalAge > 65 ? 2.0 : 1.30;
            if (fib4 > highThresh) { interpretation = "High Risk"; variant = "high"; details = "High risk of advanced liver fibrosis — referral recommended."; }
            else if (fib4 > midThresh) { interpretation = "Indeterminate"; variant = "mid"; details = "Intermediate range — further evaluation required."; }
            return { fib4, interpretation, variant, details };
          }, [evalAge, evalAst, evalAlt, evalPlatelets]);

          const fraxMetrics = useMemo(() => {
            const fraxAge = Math.min(Math.max(evalAge, 40), 90);
            const hMeter = evalHeight / 100;
            const bmi = evalWeight / (hMeter * hMeter);
            let mofLogit = -3.8 + 0.055*(fraxAge-50) - 0.035*(bmi-25);
            let hfLogit = -5.8 + 0.085*(fraxAge-50) - 0.055*(bmi-25);
            if (evalGender === 'girls') { mofLogit += 0.35; hfLogit += 0.45; }
            if (prevFracture === 'yes') { mofLogit += 1.15; hfLogit += 1.05; }
            if (parentHipFracture === 'yes') { mofLogit += 0.95; hfLogit += 1.25; }
            if (smoking === 'yes') { mofLogit += 0.35; hfLogit += 0.45; }
            if (glucocorticoids === 'yes') { mofLogit += 0.85; hfLogit += 0.95; }
            if (rheumatoid === 'yes') { mofLogit += 0.45; hfLogit += 0.55; }
            if (secondaryOsteo === 'yes') { mofLogit += 0.35; hfLogit += 0.35; }
            if (alcohol === 'yes') { mofLogit += 0.25; hfLogit += 0.35; }
            const mofProb = 100 / (1 + Math.exp(-mofLogit));
            const hfProb = 100 / (1 + Math.exp(-hfLogit));
            return { mofProb, hfProb, isHighMof: mofProb >= 20, isHighHf: hfProb >= 3, fraxAge };
          }, [evalAge, evalGender, evalHeight, evalWeight, prevFracture, parentHipFracture, smoking, glucocorticoids, rheumatoid, secondaryOsteo, alcohol]);

          const chronicityStatus = useMemo(() => {
            if (timeline.length < 2) return { status: "Add at least 2 snapshots (≥ 90 days apart) to assess CKD chronicity.", cls: "risk-badge-neutral", bgClass: "bg-slate-50 border-slate-200 text-slate-500" };
            const sorted = [...timeline].sort((a,b) => new Date(a.date)-new Date(b.date));
            const diffDays = Math.ceil((new Date(sorted[sorted.length-1].date) - new Date(sorted[0].date)) / 86400000);
            if (diffDays < 90) return { status: `Observation window: ${diffDays} days — need 90 days minimum to confirm chronicity.`, bgClass: "bg-amber-50 border-amber-200 text-amber-700" };
            const initDmg = sorted[0].egfr < 60 || sorted[0].albuminuria !== 'A1';
            const curDmg = sorted[sorted.length-1].egfr < 60 || sorted[sorted.length-1].albuminuria !== 'A1';
            if (initDmg && curDmg) return { status: `Chronicity CONFIRMED — Persistent indicators across ${diffDays}-day window.`, bgClass: "bg-rose-50 border-rose-200 text-rose-700 font-bold" };
            return { status: `Transient profile — markers did not persist over ${diffDays} days.`, bgClass: "bg-emerald-50 border-emerald-200 text-emerald-700" };
          }, [timeline]);

          const generalMetrics = useMemo(() => {
            const bmi = evalWeight / Math.pow(evalHeight/100, 2);
            const map = evalDiastolic + (evalSystolic - evalDiastolic) / 3;
            let bmiCat = "Normal", bmiVariant = "low";
            if (bmi < 18.5) { bmiCat = "Underweight"; bmiVariant = "mid"; }
            else if (bmi >= 27.5) { bmiCat = "Obese"; bmiVariant = "high"; }
            else if (bmi >= 23.0) { bmiCat = "Overweight"; bmiVariant = "mid"; }
            let mapCat = "Normal", mapVariant = "low";
            if (map < 70) { mapCat = "Low"; mapVariant = "mid"; }
            else if (map > 100) { mapCat = "Elevated"; mapVariant = "mid"; }
            else if (map > 110) { mapCat = "High"; mapVariant = "high"; }
            return { bmi, bmiCat, bmiVariant, map, mapCat, mapVariant };
          }, [evalHeight, evalWeight, evalSystolic, evalDiastolic]);

          // Report/export mode: when loaded as ?report=1&sex=...&age=...&height=...&weight=...
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
            const qSex = params.get('sex');
            if (qSex === 'boys' || qSex === 'girls') setGender(qSex);
            const qAge = params.get('age'); if (qAge) setAge(qAge);
            const qHeight = params.get('height'); if (qHeight) setHeight(qHeight);
            const qWeight = params.get('weight'); if (qWeight) setWeight(qWeight);
            const qName = params.get('patient_name'); if (qName) setPatientName(qName);
            const qMrn = params.get('patient_mrn'); if (qMrn) setPatientMrn(qMrn);
            const qExam = params.get('exam_date'); if (qExam) setExamDate(qExam);
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
          }, [evalAge, evalGender, evalHeight, evalWeight]);

          // WHO 19y adult-height distribution, for the bone-age predicted-adult-height
          // context (a different feature -- not the growth chart -- but same engine).
          useEffect(() => {
            let cancelled = false;
            fetch(`/api/growth/reference-stats?measure=height&sex=${evalGender}&age=19`)
              .then(r => r.json()).then((d) => { if (!cancelled) setAdultHeightStats(d); }).catch(() => {});
            return () => { cancelled = true; };
          }, [evalGender]);

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
            if (evalGender !== 'boys' && evalGender !== 'girls') { setLetterResult(null); setBoneReport(null); return; }
            const carp = {}; Object.entries(carpalStages).forEach(([n, g]) => carp[carpalCode(n)] = g);
            const aiYrs = (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null;
            const id = setTimeout(() => {
              fetch('/api/bone-age/letters-score', { method:'POST', headers:{ 'Content-Type':'application/json' },
                body: JSON.stringify({ sex: evalGender, rus_stages: rusStages, carpal_stages: carp }) })
                .then(r => r.ok ? r.json() : null).then(d => { if (d) setLetterResult(d); }).catch(() => {});
              // Structured 20-bone report (directive S-BA-4): the backend composes
              // it; the UI only renders. Recomputes as the doctor grades.
              fetch('/api/bone-age/report', { method:'POST', headers:{ 'Content-Type':'application/json' },
                body: JSON.stringify({ sex: evalGender, rus_stages: rusStages, carpal_stages: carp,
                  chronological_age_years: evalAge > 0 ? evalAge : null, ai_estimate_years: aiYrs }) })
                .then(r => r.ok ? r.json() : null).then(d => { if (d) setBoneReport(d); }).catch(() => {});
            }, 250);
            return () => clearTimeout(id);
          }, [rusStages, carpalStages, evalGender, evalAge, aiEstimate]);

          // Manual grading now uses original TW3 letters A–I (RUS + carpals). The
          // scores/ages stay blank until the clinic's licensed TW3 tables are wired
          // in, so no /score call is made here (no guessed numbers).

          // Normalised view of the backend result for the UI.
          const rusMetrics = useMemo(() => ({
            staged: rusResult ? rusResult.staged_count : 0,
            total: (tw3Config && tw3Config.bones ? tw3Config.bones.length : 13),
            score: rusResult ? rusResult.total_rus_score : 0,
            calibrated: rusResult ? rusResult.calibrated : (tw3Config ? true : false),
            complete: rusResult ? rusResult.complete : false,
            suggestedAge: rusResult ? rusResult.bone_age_years : null,
            status: rusResult ? rusResult.status : null,
            provisional: rusResult ? rusResult.provisional_curve : (tw3Config ? tw3Config.provisional_curve : false),
          }), [rusResult, tw3Config]);

          const boneMetrics = useMemo(() => {
            const ba = boneAge !== "" ? parseFloat(boneAge) : null;
            const hasBone = ba !== null && !isNaN(ba) && evalHeight > 0;

            // Mid-parental (genetic target) height — Tanner. Open, non-proprietary.
            const fh = fatherHeight !== "" ? parseFloat(fatherHeight) : null;
            const mh = motherHeight !== "" ? parseFloat(motherHeight) : null;
            let mph = null, mphLow = null, mphHigh = null;
            if (fh && mh && fh > 0 && mh > 0) {
              mph = evalGender === 'boys' ? (fh + mh + 13) / 2 : (fh + mh - 13) / 2;
              mphLow = mph - 8.5; mphHigh = mph + 8.5;  // ±8.5 cm target range (Tanner); not literally ±2 SD
            }

            if (!hasBone && mph === null) return null;

            const diff = hasBone ? ba - evalAge : null;
            const autoCat = hasBone ? maturationCategory(ba, evalAge) : null;

            // Skeletal adult-height prediction — ONLY if the licensed TW3 %-attained
            // reference is present; otherwise null (never fabricated).
            const pct = hasBone ? pctAdultHeightAt(ba, evalGender) : null;
            const skeletalPah = (pct && pct > 0) ? evalHeight / (pct / 100) : null;
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
            const remaining = (predictedPah !== null && evalHeight > 0) ? predictedPah - evalHeight : null;
            const predVsTarget = (predictedPah !== null && mph !== null) ? predictedPah - mph : null;
            const withinTarget = (predictedPah !== null && mphLow !== null)
              ? (predictedPah >= mphLow && predictedPah <= mphHigh) : null;

            // Population context (19y adult-height reference from the same growth
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
          }, [boneAge, evalAge, evalGender, evalHeight, fatherHeight, motherHeight, adultHeightStats]);

          // ── Assessment lifecycle (persisted via /api/bone-age/assessments) ──────────
          const LC_API = '/api/bone-age/assessments';
          const lcLocked = assessment && (assessment.assessment_status === 'approved' || assessment.assessment_status === 'superseded');

          // Persist the doctor's 20-bone letter staging as a doctor-confirmed
          // annotation (stage_system 'tw3-letters'). Scoring stays disabled until
          // licensed tables exist, so this is the data-collection stream (directive §7, §11).
          const saveDraft = async () => {
            if (!patientCode.trim()) { setLcMsg({ type:'err', text:'Enter a patient code to save.' }); return; }
            if (evalGender !== 'boys' && evalGender !== 'girls') { setLcMsg({ type:'err', text:'Set biological sex first.' }); return; }
            const carpalEntries = Object.entries(carpalStages).map(([n, g]) => [carpalCode(n), g]);
            if (Object.keys(rusStages).length === 0 && carpalEntries.length === 0) {
              setLcMsg({ type:'err', text:'Grade at least one bone.' }); return;
            }
            setLcBusy(true); setLcMsg(null);
            try {
              let a = assessment;
              if (!a || a.assessment_status === 'approved' || a.assessment_status === 'superseded') {
                const res = await fetch(LC_API, { method:'POST', headers:{ 'Content-Type':'application/json' },
                  body: JSON.stringify({ patient_code: patientCode.trim(), sex: evalGender,
                    chronological_age_years: age !== "" ? Number(age) : null,
                    stage_system: 'tw3-letters' }) });
                if (!res.ok) throw new Error((await res.json()).detail || 'create failed');
                a = await res.json();
              }
              for (const [bone, grade] of [...Object.entries(rusStages), ...carpalEntries]) {
                const r = await fetch(`${LC_API}/${a.id}/bones/${bone}`, { method:'PUT',
                  headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ stage: grade }) });
                if (r.ok) { a = await r.json(); }
                else { throw new Error((await r.json()).detail || `could not save ${bone}`); }
              }
              setAssessment(a);
              setLcMsg({ type:'ok', text:`Saved annotation · #${a.id} rev ${a.revision} · ${a.rus_staged_count}/13 RUS + ${a.carpal_staged_count}/7 carpal` });
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
            finally { setLcBusy(false); }
          };

          // Load a saved annotation's bones back into the grids (RUS + carpals).
          const bonesIntoGrids = (bones) => {
            const rus = {}, carp = {}, bx = {};
            (bones || []).forEach(b => {
              if (b.localisation_box) bx[b.bone_code] = b.localisation_box;
              if (!b.confirmed_stage) return;
              if (b.bone_group === 'carpal') carp[carpalName(b.bone_code)] = b.confirmed_stage;
              else rus[b.bone_code] = b.confirmed_stage;
            });
            setRusStages(rus); setCarpalStages(carp); setBoxes(bx);
          };

          const calculateAssessment = async () => {
            if (!assessment) return; setLcBusy(true); setLcMsg(null);
            try {
              const res = await fetch(`${LC_API}/${assessment.id}/calculate`, { method:'POST' });
              const d = await res.json();
              if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'calculate failed' }); }
              else {
                setAssessment(d);
                if (d.bone_age_years != null) { setBoneAge(Number(d.bone_age_years.toFixed(1))); setBoneAgeSource('rus'); }
                setLcMsg({ type:'ok', text:`Calculated · RUS ${d.total_rus_score} → ${d.bone_age_years} yr` });
              }
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
            finally { setLcBusy(false); }
          };

          const approveAssessment = async () => {
            if (!assessment) return;
            if (!approverName.trim()) { setLcMsg({ type:'err', text:'Enter the approving doctor name.' }); return; }
            setLcBusy(true); setLcMsg(null);
            try {
              const res = await fetch(`${LC_API}/${assessment.id}/approve`, { method:'POST',
                headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ approved_by: approverName.trim() }) });
              const d = await res.json();
              if (!res.ok) setLcMsg({ type:'err', text: d.detail || 'approve failed' });
              else { setAssessment(d); setLcMsg({ type:'ok', text:`Approved by ${d.approved_by}` }); }
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
            finally { setLcBusy(false); }
          };

          const reviseAssessment = async () => {
            if (!assessment) return; setLcBusy(true); setLcMsg(null);
            try {
              const res = await fetch(`${LC_API}/${assessment.id}/revise`, { method:'POST',
                headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ reason:'re-read' }) });
              const d = await res.json();
              if (!res.ok) setLcMsg({ type:'err', text: d.detail || 'revise failed' });
              else {
                bonesIntoGrids(d.bones); setAssessment(d); setShowAudit(false);
                setLcMsg({ type:'ok', text:`Opened revision ${d.revision} (draft)` });
              }
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
            finally { setLcBusy(false); }
          };

          const toggleAudit = async () => {
            if (!assessment) return;
            const next = !showAudit; setShowAudit(next);
            if (next) {
              try { const r = await fetch(`${LC_API}/${assessment.id}?include_audit=true`); if (r.ok) setAssessment(await r.json()); } catch {}
            }
          };

          const submitFeedback = async () => {
            const yrs = parseFloat(fbAge);
            if (!(yrs > 0)) { setFbMsg({ type:'err', text:'Enter the correct bone age in years.' }); return; }
            setFbBusy(true); setFbMsg(null);
            try {
              const body = {
                corrected_age_years: yrs,
                method: fbMethod,
                confidence: fbConfidence,
                rater_id: fbRater || null,
                sex: (evalGender === 'boys' || evalGender === 'girls') ? evalGender : null,
                chronological_age_years: evalAge || null,
                ai_estimate_years: (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null,
                ai_model_version: (aiEstimate && aiEstimate.model_version) || null,
                radiograph_id: (radiograph && radiograph.id) || null,
                assessment_id: (assessment && assessment.id) || null,
                image_domain: (radiograph && radiograph.source_domain) || estimateDomain || null,
                note: fbNote || null,
              };
              const res = await fetch('/api/bone-age/feedback', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(body) });
              const d = await res.json();
              if (!res.ok) { setFbMsg({ type:'err', text: d.detail || 'could not save' }); }
              else { setFbMsg({ type:'ok', text: d.message || 'Thanks — logged.' }); setFbAge(''); setFbNote(''); }
            } catch (e) { setFbMsg({ type:'err', text: String(e.message || e) }); }
            finally { setFbBusy(false); }
          };

          const runEstimate = async (fileObj, flags) => {
            if (evalGender !== 'boys' && evalGender !== 'girls') { setAiEstimate({ error:'Set biological sex in Demographics first.' }); return; }
            const useFlags = flags || declaredFlags;
            setLastFilm(fileObj);
            setAiBusy(true); setAiEstimate(null);
            try {
              const fd = new FormData(); fd.append('file', fileObj); fd.append('sex', evalGender);
              fd.append('image_domain', estimateDomain); fd.append('declared_flags', useFlags.join(','));
              const res = await fetch('/api/bone-age/estimate', { method:'POST', body: fd });
              const d = await res.json();
              // Keep the full response: it may be an estimate, an acceptability
              // ABSTENTION (available:false, accepted:false), or a no-model notice.
              if (!res.ok) setAiEstimate({ error: d.detail || 'estimate failed' });
              else setAiEstimate(d);
            } catch (e) { setAiEstimate({ error: String(e.message || e) }); }
            finally { setAiBusy(false); }
          };

          // Toggle a declared image issue; re-gate the last film immediately so the
          // estimate abstains/returns without needing a re-attach.
          const toggleDeclaredFlag = (code) => {
            setDeclaredFlags(prev => {
              const next = prev.includes(code) ? prev.filter(f => f !== code) : [...prev, code];
              if (lastFilm) runEstimate(lastFilm, next);
              return next;
            });
          };

          const attachImage = async (fileObj) => {
            if (!assessment) { setLcMsg({ type:'err', text:'Save the draft first, then attach a film.' }); return; }
            if (lcLocked) { setLcMsg({ type:'err', text:'Assessment is locked; open a revision to change the image.' }); return; }
            setLcBusy(true); setLcMsg(null);
            try {
              const fd = new FormData(); fd.append('file', fileObj);
              const res = await fetch(`${LC_API}/${assessment.id}/image`, { method:'POST', body: fd });
              const d = await res.json();
              if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'upload failed' }); }
              else {
                setRadiograph(d);
                setLcMsg({ type:'ok', text:`Film attached · ${d.source_format} · ${d.quality_status.replace(/_/g, ' ')}` });
                // Auto-analyse the attached film so the report populates immediately.
                runEstimate(fileObj);   // AI whole-image bone age (screening)
                localizeBones();        // auto-locate bones (if a localizer model is installed)
              }
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
            finally { setLcBusy(false); }
          };

          const loadCoverage = async () => {
            setCovBusy(true);
            try {
              const r = await fetch('/api/bone-age/coverage');
              if (r.ok) setCoverage(await r.json());
            } catch {}
            finally { setCovBusy(false); }
          };

          const loadMonitoring = async () => {
            setMonBusy(true);
            try {
              const r = await fetch('/api/bone-age/monitoring');
              if (r.ok) setMonitoring(await r.json());
            } catch {}
            finally { setMonBusy(false); }
          };

          const loadAdjudication = async () => {
            setAdjBusy(true); setAdjMsg(null);
            try {
              const r = await fetch('/api/bone-age/adjudication?status=open');
              if (r.ok) setAdjItems((await r.json()).items || []);
            } catch (e) { setAdjMsg({ type:'err', text:String(e.message||e) }); }
            finally { setAdjBusy(false); }
          };

          const resolveAdjudication = async (id, stage) => {
            if (!adjReviewer.trim()) { setAdjMsg({ type:'err', text:'Enter the reviewing clinician first.' }); return; }
            setAdjBusy(true); setAdjMsg(null);
            try {
              const r = await fetch(`/api/bone-age/adjudication/${id}/resolve`, {
                method:'POST', headers:{ 'Content-Type':'application/json' },
                body: JSON.stringify({ resolved_stage: stage, resolved_by: adjReviewer.trim() }),
              });
              if (r.ok) { setAdjMsg({ type:'ok', text:`Resolved to stage ${stage}.` }); await loadAdjudication(); }
              else { const e = await r.json(); setAdjMsg({ type:'err', text: e.detail || 'Resolve failed.' }); }
            } catch (e) { setAdjMsg({ type:'err', text:String(e.message||e) }); }
            finally { setAdjBusy(false); }
          };

          // ── Licensed TW3 table entry (original-TW3 letters) ──────────────────────
          const _emptyLt = () => ({
            method:'TW3-letters', version:'letters-clinic',
            rus_stage_to_score:{ boys:{}, girls:{} },
            carpal_stage_to_score:{ boys:{}, girls:{} },
            rus_score_to_age:{ twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} },
            carpal_score_to_age:{ twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} },
            tw20_stage_to_score:{ boys:{}, girls:{} },
            tw20_score_to_age:{ boys:[], girls:[] },
            reference_cases:[],
          });
          const loadLetterTables = async () => {
            setLtBusy(true); setLtMsg(null);
            try {
              const d = await (await fetch('/api/bone-age/letters-tables')).json();
              const t = (d.tables && d.tables.rus_stage_to_score) ? d.tables : _emptyLt();
              t.rus_stage_to_score = t.rus_stage_to_score || { boys:{}, girls:{} };
              t.carpal_stage_to_score = t.carpal_stage_to_score || { boys:{}, girls:{} };
              t.rus_score_to_age = t.rus_score_to_age || { twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} };
              t.carpal_score_to_age = t.carpal_score_to_age || { twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} };
              t.tw20_stage_to_score = t.tw20_stage_to_score || { boys:{}, girls:{} };
              t.tw20_score_to_age = t.tw20_score_to_age || { boys:[], girls:[] };
              t.reference_cases = (t.reference_cases || []).filter(c => c && !c._fill && !String(c.id||'').startsWith('example'));
              setLtTables(t); setLtStatus(d.status);
            } catch (e) { setLtMsg({ type:'err', text:String(e.message||e) }); }
            finally { setLtBusy(false); }
          };
          const setLtPoint = (group, sex, bone, letter, val) => {
            setLtTables(prev => {
              const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
              t[group][sex] = t[group][sex] || {}; t[group][sex][bone] = t[group][sex][bone] || {};
              if (val === '' || val === null) delete t[group][sex][bone][letter];
              else t[group][sex][bone][letter] = Number(val);
              return t;
            });
          };
          const curveToText = (arr) => (arr||[]).map(p => p.join(', ')).join('\n');
          const parseCurve = (text) => text.split('\n').map(l => l.trim()).filter(Boolean)
            .map(l => l.split(/[\s,]+/).map(Number)).filter(p => p.length===2 && p.every(n => !isNaN(n)));
          const setLtCurve = (group, curve, sex, text) => {
            setLtTables(prev => {
              const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
              t[group][curve] = t[group][curve] || {}; t[group][curve][sex] = parseCurve(text);
              return t;
            });
          };
          const setLtSexCurve = (group, sex, text) => {  // single [sex]->anchors curve (TWII'20)
            setLtTables(prev => {
              const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
              t[group] = t[group] || {}; t[group][sex] = parseCurve(text);
              return t;
            });
          };
          const useGridAsReference = () => {
            const rus = { ...rusStages };
            const carp = {}; Object.entries(carpalStages).forEach(([n,g]) => carp[carpalCode(n)] = g);
            setLtTables(prev => {
              const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
              t.reference_cases = [{ id:'clinic-ref-1', sex: evalGender === 'girls' ? 'girls' : 'boys',
                rus_stages: rus, carpal_stages: carp,
                expected: (t.reference_cases[0] && t.reference_cases[0].expected) || { rus_score:null, twiii_rus_age_years:null },
                tolerance_years: 0.3 }];
              return t;
            });
            setLtMsg({ type:'ok', text:'Reference stages captured from the grading grid. Now enter the reported score/age below.' });
          };
          const setRefExpected = (field, val) => {
            setLtTables(prev => {
              const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
              if (!t.reference_cases[0]) t.reference_cases[0] = { id:'clinic-ref-1', sex:'girls', rus_stages:{}, carpal_stages:{}, expected:{}, tolerance_years:0.3 };
              t.reference_cases[0].expected = t.reference_cases[0].expected || {};
              t.reference_cases[0].expected[field] = (val === '' ? null : Number(val));
              return t;
            });
          };
          const saveLetterTables = async () => {
            setLtBusy(true); setLtMsg(null);
            try {
              const r = await fetch('/api/bone-age/letters-tables', { method:'PUT',
                headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ tables: ltTables }) });
              const d = await r.json();
              if (!r.ok) { setLtMsg({ type:'err', text: d.detail || 'save failed' }); }
              else {
                setLtStatus(d.status);
                if (d.status.scoring_ready) setLtMsg({ type:'ok', text:'Saved — TW3 scoring is ON (accuracy gate passed). The report now fills with real numbers.' });
                else if (!d.status.reference_validation.all_passed && d.status.reference_validation.n_cases > 0)
                  setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: the reference case is not reproduced by these values — recheck the points/curve or the reported numbers.' });
                else if (d.status.provenance_complete === false)
                  setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: document the licensed source in the Provenance tab (book, edition, owner, who entered/verified, date).' });
                else setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: fill every bone’s points, the score→age curves, and a reference case.' });
              }
            } catch (e) { setLtMsg({ type:'err', text:String(e.message||e) }); }
            finally { setLtBusy(false); }
          };

          const setImageDomain = async (domain) => {
            if (!assessment) return;
            try {
              const res = await fetch(`${LC_API}/${assessment.id}/image-domain`, { method:'PUT',
                headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ domain }) });
              const d = await res.json();
              if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'could not set domain' }); }
              else { setRadiograph(r => ({ ...(r||{}), source_domain: d.source_domain })); }
            } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
          };

          // ── Bone localization (PEA auto-boxes + doctor correction) ──────────────────
          const analysisUrl = radiograph ? `/api/bone-age/radiographs/${radiograph.radiograph_id}/analysis` : null;
          const localizeBones = async () => {
            if (!assessment) { setLocMsg({ type:'err', text:'Save the annotation and attach a film first.' }); return; }
            setLocBusy(true); setLocMsg(null);
            try {
              const res = await fetch(`${LC_API}/${assessment.id}/localize`, { method:'POST' });
              const d = await res.json();
              if (!res.ok) { setLocMsg({ type:'err', text: d.detail || 'localize failed' }); return; }
              if (d.image_width) setLocImg({ width: d.image_width, height: d.image_height });
              if (!d.available) { setLocMsg({ type:'err', text: d.message || 'No localizer model installed.' }); return; }
              const nb = { ...boxes }; (d.boxes || []).forEach(b => { nb[b.bone_code] = b.box; });
              setBoxes(nb);
              setLocMsg({ type:'ok', text:`Auto-located ${(d.boxes||[]).length} bones — drag to correct, then Save boxes.` });
            } catch (e) { setLocMsg({ type:'err', text:String(e.message||e) }); }
            finally { setLocBusy(false); }
          };
          const addOrSelectBox = (bone) => {
            setSelBone(bone);
            setBoxes(prev => {
              if (prev[bone] || !locImg) return prev;
              const s = Math.min(locImg.width, locImg.height) * 0.16;
              const cx = locImg.width / 2, cy = locImg.height / 2;
              return { ...prev, [bone]: [cx - s/2, cy - s/2, cx + s/2, cy + s/2] };
            });
          };
          const clearBox = (bone) => setBoxes(prev => { const n = { ...prev }; delete n[bone]; return n; });
          const saveBoxes = async () => {
            if (!assessment) return; setLocBusy(true); setLocMsg(null);
            try {
              let a = assessment;
              const cur = boxesRef.current;            // read current boxes, not a stale closure
              const codes = new Set(Object.keys(cur));
              // save present boxes; clear any that were removed
              for (const [bone, box] of Object.entries(cur)) {
                const r = await fetch(`${LC_API}/${assessment.id}/bones/${bone}/box`, { method:'PUT',
                  headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ box: box.map(v => Math.round(v*10)/10) }) });
                if (r.ok) a = await r.json(); else throw new Error((await r.json()).detail || `save ${bone}`);
              }
              (a.bones || []).forEach(async b => {
                if (b.localisation_box && !codes.has(b.bone_code)) {
                  await fetch(`${LC_API}/${assessment.id}/bones/${b.bone_code}/box`, { method:'PUT',
                    headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ box: null }) });
                }
              });
              setAssessment(a);
              setLocMsg({ type:'ok', text:`Saved ${codes.size} bone box${codes.size===1?'':'es'}.` });
            } catch (e) { setLocMsg({ type:'err', text:String(e.message||e) }); }
            finally { setLocBusy(false); }
          };
          const startBoxDrag = (bone, mode, e) => {
            e.preventDefault(); e.stopPropagation();
            if (!locRef.current || !locImg) return;
            const rect = locRef.current.getBoundingClientRect();
            const scale = rect.width / locImg.width;
            locDrag.current = { bone, mode, mx:(e.clientX-rect.left)/scale, my:(e.clientY-rect.top)/scale,
              orig:[...(boxesRef.current[bone] || [0,0,0,0])] };
            setSelBone(bone);
          };
          const onLocMove = (e) => {
            const d = locDrag.current; if (!d || !locRef.current || !locImg) return;
            const rect = locRef.current.getBoundingClientRect();
            const scale = rect.width / locImg.width;
            const mx = (e.clientX-rect.left)/scale, my = (e.clientY-rect.top)/scale;
            const W = locImg.width, H = locImg.height, clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
            setBoxes(prev => {
              let [x0,y0,x1,y1] = d.orig;
              if (d.mode === 'move') {
                let dx = mx-d.mx, dy = my-d.my;
                dx = clamp(dx, -x0, W-x1); dy = clamp(dy, -y0, H-y1);
                return { ...prev, [d.bone]:[x0+dx,y0+dy,x1+dx,y1+dy] };
              }
              return { ...prev, [d.bone]:[x0, y0, clamp(mx, x0+8, W), clamp(my, y0+8, H)] };
            });
          };
          const endLocDrag = () => { locDrag.current = null; };

          const lcBtn = (bg, disabled) => ({ padding:'7px 12px', background: disabled ? '#cbd5e1' : bg,
            color:'white', border:'none', borderRadius:'8px', fontSize:'11px', fontWeight:'700',
            cursor: disabled ? 'not-allowed' : 'pointer' });

          const qriskMetrics = useMemo(() => {
            const bmi = evalHeight > 0 ? evalWeight / Math.pow(evalHeight / 100, 2) : null;
            const inAgeRange = evalAge >= 25 && evalAge <= 84;
            const p = {
              sex: evalGender, age: evalAge, bmi,
              ethnicity, smoke: smokeCat, diabetes,
              rati: cholRatio !== "" ? parseFloat(cholRatio) : undefined,
              sbp: systolic !== "" ? parseFloat(systolic) : undefined,
              sbps5: sbpSD !== "" ? parseFloat(sbpSD) : undefined,
              af: qAF === 'yes', treatedhyp: qTreatedHtn === 'yes', ra: qRA === 'yes',
              renal: qCKD === 'yes', migraine: qMigraine === 'yes', sle: qSLE === 'yes',
              semi: qSMI === 'yes', atypicalantipsy: qAtypAntipsy === 'yes',
              corticosteroids: qCortico === 'yes', impotence2: qED === 'yes', fh_cvd: qFhCvd === 'yes',
            };
            const risk = (bmi && inAgeRange) ? qrisk3(p) : null;
            // Healthy reference = same age/sex/ethnicity with OPTIMAL risk factors
            // (BMI 25, cholesterol ratio 4.0, SBP 125, no smoking/diabetes/conditions).
            // Matches QRISK3's "score of a healthy person" comparison.
            const typical = (bmi && inAgeRange) ? qrisk3({
              sex: evalGender, age: evalAge, bmi: 25, ethnicity, smoke: 0, diabetes: 0,
              rati: 4.0, sbp: 125, sbps5: 0, town: 0,
            }) : null;
            let band = 'low', variant = 'low';
            if (risk !== null) {
              if (risk >= 20) { band = 'High (≥ 20%)'; variant = 'high'; }
              else if (risk >= 10) { band = 'Moderate (10–20%)'; variant = 'mid'; }
              else { band = 'Low (< 10%)'; variant = 'low'; }
            }
            const missingSbp = systolic === "", missingRatio = cholRatio === "";
            return { risk, typical, band, variant, inAgeRange, bmi, missingSbp, missingRatio };
          }, [evalGender, evalAge, evalHeight, evalWeight, ethnicity, smokeCat, diabetes,
              cholRatio, systolic, sbpSD, qAF, qTreatedHtn, qRA, qCKD, qMigraine, qSLE,
              qSMI, qAtypAntipsy, qCortico, qED, qFhCvd]);

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
                state: hasManualRenal ? variantToState(renalMetrics.stageVariant) : 'none',
                value: hasManualRenal ? renalMetrics.egfr.toFixed(0) : '—',
                unit: 'mL/min/1.73m²',
                label: hasManualRenal ? `CKD ${renalMetrics.ckdStage} · ${renalMetrics.ckdStageDesc}` : 'Enter serum creatinine',
                title: 'Renal (eGFR)',
              },
              liver: {
                state: hasManualLiver ? variantToState(liverMetrics.variant) : 'none',
                value: hasManualLiver ? liverMetrics.fib4.toFixed(2) : '—',
                unit: 'FIB-4',
                label: hasManualLiver ? liverMetrics.interpretation : 'Enter AST, ALT & platelets',
                title: 'Liver (FIB-4)',
              },
              frax: {
                state: hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'high' : 'normal') : 'none',
                value: hasManualFrax ? fraxMetrics.mofProb.toFixed(1) : '—',
                unit: '% MOF 10-yr',
                label: hasManualFrax ? (fraxMetrics.isHighMof ? 'High fracture risk' : 'Low fracture risk') : 'Enter age, sex, height & weight',
                title: 'FRAX',
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
            setPrevFracture("no"); setParentHipFracture("no"); setSmoking("no");
            setGlucocorticoids("no"); setRheumatoid("no"); setSecondaryOsteo("no"); setAlcohol("no");
            setTimeline([]); setActiveTab('overview');
            setBoneAge(""); setBoneAgeSource("manual"); setRusStages({}); setCarpalStages({});
            setPatientCode(""); setApproverName(""); setAssessment(null); setLcMsg(null); setShowAudit(false); setRadiograph(null); setAiEstimate(null);
            setFatherHeight(""); setMotherHeight("");
            setEthnicity(2); setSmokeCat(0); setDiabetes(0); setCholRatio(""); setSbpSD("");
            setQAF("no"); setQTreatedHtn("no"); setQRA("no"); setQCKD("no"); setQMigraine("no");
            setQSLE("no"); setQSMI("no"); setQAtypAntipsy("no"); setQCortico("no"); setQED("no"); setQFhCvd("no");
          };

          const logCurrentData = () => {
            setTimeline(prev => [{
              id: Date.now().toString(),
              date: new Date().toISOString().split('T')[0],
              age: evalAge, height: evalHeight, weight: evalWeight,
              creatinine: evalCreatinine,
              egfr: Number(renalMetrics.egfr.toFixed(1)),
              fib4: liverMetrics ? Number(liverMetrics.fib4.toFixed(2)) : null,
              albuminuria: evalAlbuminuria
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
            const params = new URLSearchParams({
              sex: evalGender, age: String(evalAge), height: String(evalHeight || 0), weight: String(evalWeight || 0),
              patient_name: patientName, patient_mrn: patientMrn, exam_date: examDate,
            });
            try {
              const res = await fetch(`/api/growth/report.pdf?${params.toString()}`);
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
              <div class="sub" style="font-weight:700;color:#334155">${(patientName || 'Unnamed patient')} · MRN ${(patientMrn || '—')} · Exam ${examDate}</div>
              <div class="sub">Reference: ${(growthSeries[evalGender].height && growthSeries[evalGender].height.reference) || 'WHO + IAP 2015'} · ${chartLabel} · ${new Date().toLocaleDateString()}</div>
              <div class="chart-sheet">${svg}</div>
              <table>
                ${row('Sex', evalGender === 'girls' ? 'Female' : 'Male')}
                ${row('Chronological age', evalAge.toFixed(1) + ' yrs')}
                ${row('Height', evalHeight + ' cm  ·  z ' + fmtZ(g.heightZ) + '  ·  ' + fmtP(g.heightPct) + ' pct')}
                ${row('Weight', evalWeight + ' kg' + (g.weightAvailable ? '  ·  z ' + fmtZ(g.weightZ) + '  ·  ' + fmtP(g.weightPct) + ' pct' : '  (weight-for-age n/a at this age — use BMI)'))}
                ${row('BMI', g.bmiVal.toFixed(1) + ' kg/m²  ·  z ' + fmtZ(g.bmiZ) + '  ·  ' + fmtP(g.bmiPct) + ' pct')}
                ${row('Height status', g.stuntingClass)}
                ${row('Weight / BMI status', g.underweightClass)}
                ${row('Height age', g.heightAge.label)}
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
              <div class="foot">Decision support only — not a diagnostic device. A clinician must verify every value. A "—" interpretation means that module had insufficient input. References: Khadilkar 2015 · TW3-C (Chinese) RUS — provisional research curve (±0.5y, digitized from a published figure); NOT Tanner–Whitehouse TW3 · QRISK3-2017 · CKD-EPI 2021 · Bedside Schwartz 2009 · FRAX India Asian · FIB-4 (Sterling et al.).</div>
              </body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => win.print(), 300);
          };

          const TABS = [
            { id: 'overview', label: 'Overview' },
            { id: 'growth',   label: 'Growth' },
            { id: 'boneage',  label: 'Bone Age' },
            { id: 'renal',    label: 'Renal GFR' },
            { id: 'liver',    label: 'FIB-4 Liver' },
            { id: 'frax',     label: 'FRAX Plus' },
            { id: 'qrisk',    label: 'QRISK3 CVD' },
            { id: 'timeline', label: 'Ledger' },
          ];

          // Which left-panel sections the active tab actually consumes. The panel
          // stays live and fully editable (results still auto-update) -- irrelevant
          // sections are just visually de-emphasised so entry is faster and quieter.
          // Demographics is never dimmed: it drives every module.
          const labsRelevant = ['renal','liver','qrisk','timeline','overview'].includes(activeTab);
          const fraxRelevant = ['frax','overview'].includes(activeTab);

          return (
            <div className="app-shell">

              {/* ── HEADER ── */}
              <header style={{ background:'white', borderBottom:'1px solid #e8ecf0', position:'sticky', top:0, zIndex:50, boxShadow:'0 1px 4px rgba(0,0,0,0.05)' }}>
                <div className="app-header-inner">
                  <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                    <div style={{ width:'36px', height:'36px', borderRadius:'10px', background:'linear-gradient(135deg,#4f46e5,#7c3aed)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                      </svg>
                    </div>
                    <div>
                      <div className="app-title" style={{ fontSize:'15px', fontWeight:'900', color:'#0f172a', lineHeight:1.2 }}>Pediatric Clinical Workspace</div>
                      <div className="app-subtitle" style={{ fontSize:'10px', fontWeight:'700', color:'#94a3b8', letterSpacing:'0.06em', textTransform:'uppercase' }}>Growth · TW3 Bone Age · QRISK3 · Renal · FRAX · FIB-4</div>
                    </div>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:'8px', flexShrink:0 }}>
                    <button
                      onClick={resetAll}
                      className="reset-button"
                      style={{ display:'flex', alignItems:'center', gap:'7px', padding:'8px 18px', background:'white', border:'1.5px solid #fca5a5', borderRadius:'9px', fontSize:'13px', fontWeight:'700', color:'#dc2626', cursor:'pointer', whiteSpace:'nowrap', transition:'all 0.15s', boxShadow:'0 1px 3px rgba(220,38,38,0.08)' }}
                      onMouseEnter={e => { e.currentTarget.style.background='#fff1f2'; e.currentTarget.style.borderColor='#f87171'; }}
                      onMouseLeave={e => { e.currentTarget.style.background='white'; e.currentTarget.style.borderColor='#fca5a5'; }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.77"/>
                      </svg>
                      Reset Patient
                    </button>
                  </div>
                </div>
              </header>

              {/* ── PATIENT IDENTITY BAR (safety: every result is attributable) ── */}
              <div className="patient-bar no-print">
                <div className="patient-bar-inner">
                  <div className="patient-field" style={{ flex:'2 1 200px' }}>
                    <label htmlFor="pt-name">Patient name</label>
                    <input id="pt-name" type="text" value={patientName} onChange={e => setPatientName(e.target.value)} placeholder="Full name" />
                  </div>
                  <div className="patient-field" style={{ flex:'1 1 130px' }}>
                    <label htmlFor="pt-mrn">MRN / ID</label>
                    <input id="pt-mrn" type="text" value={patientMrn} onChange={e => setPatientMrn(e.target.value)} placeholder="e.g. 004821" />
                  </div>
                  <div className="patient-field" style={{ flex:'1 1 140px' }}>
                    <label htmlFor="pt-date">Exam date</label>
                    <input id="pt-date" type="date" value={examDate} onChange={e => setExamDate(e.target.value)} />
                  </div>
                  <div className="patient-field" style={{ flex:'1 1 120px' }}>
                    <label>Age / Sex</label>
                    <div className="patient-reflect">
                      {age !== "" ? `${age} yr` : '— yr'} · {gender === 'boys' ? 'Male' : gender === 'girls' ? 'Female' : '—'}
                    </div>
                  </div>
                  <button onClick={exportFullReport} title="Print a combined summary of every module"
                    style={{ marginLeft:'auto', alignSelf:'center', display:'flex', alignItems:'center', gap:'7px', padding:'8px 16px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'13px', fontWeight:'700', cursor:'pointer', whiteSpace:'nowrap' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                    Export report
                  </button>
                </div>
              </div>

              {/* ── MAIN ── */}
              <main className="app-main">

                {/* ─── LEFT COLUMN: Inputs ─── */}
                <div className="input-column">

                  {/* Card: Demographics */}
                  <div className="card" style={{ padding:'20px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
                      <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#4f46e5', flexShrink:0 }}></div>
                      <span className="section-label">Demographics</span>
                      <span style={{ marginLeft:'auto', fontSize:'9px', fontWeight:'700', color:'#cbd5e1', textTransform:'uppercase', letterSpacing:'0.05em' }}>Required</span>
                    </div>

                    <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
                      {/* Age or Date of birth — enter either one */}
                      <div>
                        <div className="form-grid">
                          <InputWithUnit
                            label="Chronological Age"
                            value={age}
                            onChange={handleAgeChange}
                            placeholder="e.g. 9.5"
                            step="0.1"
                            unit="yrs"
                            unitPosition="right"
                            accent="#4f46e5"
                          />
                          <div style={{ minWidth:0 }}>
                            <label className="field-label">Date of Birth</label>
                            <input
                              type="date"
                              value={dob}
                              onChange={handleDobChange}
                              max={new Date().toISOString().split('T')[0]}
                              className="input-field"
                              style={{ width:'100%', color: dob ? '#1e293b' : '#94a3b8' }}
                            />
                          </div>
                        </div>
                        {ageParts ? (
                          <div style={{ marginTop:'8px', fontSize:'11px', color:'#4338ca', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'8px', padding:'7px 10px', lineHeight:'1.5' }}>
                            Age <strong>{ageParts.years} yr {ageParts.months} mo {ageParts.days} d</strong>
                            <span style={{ color:'#818cf8' }}> · used as {ageParts.decimal.toFixed(1)} yr in calculations</span>
                          </div>
                        ) : (
                          <div style={{ marginTop:'6px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.4' }}>
                            Enter an age directly, or a date of birth to compute it automatically.
                          </div>
                        )}
                      </div>

                      {/* Gender */}
                      <div>
                        <label className="field-label">Biological Sex</label>
                        <div style={{ display:'flex', gap:'8px' }}>
                          <button className={`gender-btn ${gender === 'boys' ? 'gender-active' : 'gender-inactive'}`} onClick={() => setGender('boys')}>
                            ♂ Male
                          </button>
                          <button className={`gender-btn ${gender === 'girls' ? 'gender-active' : 'gender-inactive'}`} onClick={() => setGender('girls')}>
                            ♀ Female
                          </button>
                        </div>
                      </div>

                      {/* Height + Weight */}
                      <div className="form-grid">
                        <InputWithUnit label="Height" value={height} onChange={e => setHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm" unit="cm" />
                        <InputWithUnit label="Weight" value={weight} onChange={e => setWeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="kg" unit="kg" />
                      </div>
                    </div>
                  </div>

                  {/* Card: Labs */}
                  <div className={`card${labsRelevant ? '' : ' section-dim'}`} style={{ padding:'20px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
                      <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#0891b2', flexShrink:0 }}></div>
                      <span className="section-label">Clinical Labs & Parameters</span>
                    </div>

                    <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
                      {/* Creatinine */}
                      <InputWithUnit
                        label="Serum Creatinine"
                        value={creatinine}
                        onChange={e => setCreatinine(e.target.value === "" ? "" : parseFloat(e.target.value))}
                        placeholder="mg/dL"
                        step="0.01"
                        unit="mg/dL"
                        accent="#0891b2"
                      />

                      {/* Albuminuria */}
                      <div>
                        <label className="field-label">Albuminuria / ACR Stage</label>
                        <div style={{ display:'flex', gap:'8px' }}>
                          {[['A1','< 30 mg/g'],['A2','30–300 mg/g'],['A3','> 300 mg/g']].map(([lv, desc]) => (
                            <button key={lv} className={`alb-btn ${albuminuria === lv ? 'alb-active' : 'alb-inactive'}`} onClick={() => setAlbuminuria(lv)}>
                              <div style={{ fontSize:'12px', fontWeight:'800', color: albuminuria === lv ? '#4338ca' : '#334155' }}>{lv}</div>
                              <div style={{ fontSize:'9px', color:'#94a3b8', marginTop:'2px' }}>{desc}</div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* BP */}
                      <div className="form-grid">
                        <InputWithUnit label="Systolic BP" value={systolic} onChange={e => setSystolic(e.target.value === "" ? "" : parseInt(e.target.value))} placeholder="mmHg" unit="mmHg" />
                        <InputWithUnit label="Diastolic BP" value={diastolic} onChange={e => setDiastolic(e.target.value === "" ? "" : parseInt(e.target.value))} placeholder="mmHg" unit="mmHg" />
                      </div>

                      {/* Liver enzymes */}
                      <div style={{ paddingTop:'12px', borderTop:'1px solid #f1f5f9' }}>
                        <label className="field-label" style={{ marginBottom:'10px' }}>Hepatic Enzymes & Platelets</label>
                        <div className="liver-grid">
                          {[
                            ['AST', 'SGOT · U/L', ast, e => setAst(e.target.value === "" ? "" : parseFloat(e.target.value))],
                            ['ALT', 'SGPT · U/L', alt, e => setAlt(e.target.value === "" ? "" : parseFloat(e.target.value))],
                            ['PLT', '×10³ / µL', platelets, e => setPlatelets(e.target.value === "" ? "" : parseFloat(e.target.value))],
                          ].map(([lbl, sub, val, fn]) => (
                            <div key={lbl} style={{ display:'flex', flexDirection:'column', alignItems:'stretch' }}>
                              <span style={{ fontSize:'12px', fontWeight:'800', color:'#334155', textAlign:'center', display:'block', marginBottom:'2px' }}>{lbl}</span>
                              <span style={{ fontSize:'9px', fontWeight:'600', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', textAlign:'center', display:'block', marginBottom:'6px' }}>{sub}</span>
                              <input
                                type="number"
                                placeholder="—"
                                value={val}
                                onChange={fn}
                                className="input-field"
                                style={{ textAlign:'center', padding:'9px 8px', width:'100%', boxSizing:'border-box' }}
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Card: FRAX */}
                  <div className={`card${fraxRelevant ? '' : ' section-dim'}`} style={{ padding:'20px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'14px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
                      <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#d97706', flexShrink:0 }}></div>
                      <span className="section-label">FRAX Risk Factors</span>
                      <span style={{ marginLeft:'auto', fontSize:'9px', fontWeight:'700', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em' }}>India · No BMD</span>
                    </div>
                    <div>
                      <FraxToggleRow label="Previous Fracture" value={prevFracture} setter={setPrevFracture} />
                      <FraxToggleRow label="Parent Hip Fracture" value={parentHipFracture} setter={setParentHipFracture} />
                      <FraxToggleRow label="Current Smoking" value={smoking} setter={setSmoking} />
                      <FraxToggleRow label="Glucocorticoids" value={glucocorticoids} setter={setGlucocorticoids} />
                      <FraxToggleRow label="Rheumatoid Arthritis" value={rheumatoid} setter={setRheumatoid} />
                      <FraxToggleRow label="Secondary Osteoporosis" value={secondaryOsteo} setter={setSecondaryOsteo} />
                      <FraxToggleRow label="Alcohol ≥ 3 units/day" value={alcohol} setter={setAlcohol} />
                    </div>
                  </div>

                </div>

                {/* ─── RIGHT COLUMN: Results ─── */}
                <div className="result-column">

                  {/* Tab Bar */}
                  <div className="card tab-card" style={{ padding:'6px' }}>
                    <div className="tab-scroll custom-scrollbar">
                      {TABS.map(tab => (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`${activeTab === tab.id ? 'tab-active' : 'tab-inactive'} tab-button`}>
                          {tab.label}
                          {moduleStatus[tab.id] && (
                            <span className={`status-dot status-dot-${moduleStatus[tab.id].state}`}
                              title={moduleStatus[tab.id].label}></span>
                          )}
                          {tab.id === 'timeline' && timeline.length > 0 && (
                            <span style={{ marginLeft:'6px', background:'#4f46e5', color:'white', fontSize:'9px', fontWeight:'800', padding:'1px 6px', borderRadius:'99px' }}>{timeline.length}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Result Panel */}
                  <div className="card-lg result-panel">

                    {/* ══ OVERVIEW TAB ══ */}
                    {activeTab === 'overview' && (
                      <div style={{ flex:1 }}>
                        <SectionHeader
                          title="Patient Overview"
                          subtitle="Every module's headline at a glance — click any card to open its full workspace."
                        />
                        <div className="overview-grid" style={{ marginTop:'16px' }}>
                          {['growth','boneage','renal','liver','frax','qrisk'].map(key => {
                            const m = moduleStatus[key];
                            const accent = m.state === 'high' ? '#dc2626' : m.state === 'borderline' ? '#d97706' : m.state === 'normal' ? '#16a34a' : '#94a3b8';
                            return (
                              <button key={key} className="overview-card" onClick={() => setActiveTab(key)}>
                                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:'8px', marginBottom:'10px' }}>
                                  <span style={{ fontSize:'11px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.05em', color:'#64748b' }}>{m.title}</span>
                                  <span className={`status-dot status-dot-${m.state}`} style={{ marginLeft:0 }}></span>
                                </div>
                                <div style={{ display:'flex', alignItems:'baseline', gap:'6px' }}>
                                  <span style={{ fontSize:'30px', fontWeight:'900', color:accent, lineHeight:1 }}>{m.value}</span>
                                  <span style={{ fontSize:'11px', fontWeight:'600', color:'#94a3b8' }}>{m.unit}</span>
                                </div>
                                <div style={{ fontSize:'11px', color:'#64748b', marginTop:'6px', lineHeight:'1.5' }}>{m.label}</div>
                              </button>
                            );
                          })}
                        </div>
                        <div style={{ marginTop:'16px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#4338ca', lineHeight:'1.7' }}>
                          Enter patient data in the left panel — every module recalculates automatically. A grey dot means that module still needs input; green / amber / red reflect the result. Decision support only — a clinician must verify every value.
                        </div>
                      </div>
                    )}

                    {/* ══ GROWTH TAB ══ */}
                    {activeTab === 'growth' && (() => {
                      const gm = growthMetrics;
                      const heightSeries = timeline.map(t => ({ age: t.age, value: t.height })).filter(p => p.value > 0);
                      const weightSeries = timeline.map(t => ({ age: t.age, value: t.weight })).filter(p => p.value > 0);
                      const bmiSeries = timeline.map(t => ({ age: t.age, value: (t.height>0 ? t.weight/Math.pow(t.height/100,2) : 0) })).filter(p => p.value > 0);
                      const pctTxt = (p) => (p === null || p === undefined) ? '—' : p.toFixed(1) + 'th';
                      const zTxt = (z) => (z === null || z === undefined) ? '—' : (z >= 0 ? '+' : '') + z.toFixed(2);
                      const inRange = evalAge >= 0 && evalAge <= 19;
                      return (
                      <div style={{ flex:1 }}>
                        <div className="report-only" style={{ fontSize:'13px', fontWeight:'700', color:'#334155', borderBottom:'1px solid #e5e7eb', paddingBottom:'8px' }}>
                          {(patientName || 'Unnamed patient')} · MRN {(patientMrn || '—')} · {age !== "" ? `${age} yr` : '— yr'} · {gender === 'boys' ? 'Male' : gender === 'girls' ? 'Female' : '—'} · Exam {examDate}
                        </div>
                        <SectionHeader
                          title="Pediatric Growth Chart · WHO (<5y) + IAP 2015 India (5–18y)"
                          subtitle="Real L,M,S percentiles · height, weight & BMI · WHO under 5y, IAP 2015 India 5–18y (fit from the paper's published tables)."
                          badge={moduleStatus.growth.state !== 'none' ? moduleStatus.growth.label : null}
                          badgeVariant={moduleStatus.growth.state === 'high' ? 'high' : moduleStatus.growth.state === 'borderline' ? 'mid' : 'low'}
                        />

                        {!hasManualGrowth ? (
                          <EmptyState title="Enter patient measurements"
                            hint="Age, biological sex, height and weight are required to plot the growth chart. Values recalculate automatically as you type." />
                        ) : !inRange ? (
                          <EmptyState title="Pediatric workspace inactive"
                            hint="The growth reference covers ages 0–19 years. Enter an age in that range to use the growth engine." />
                        ) : (
                          <div style={{ marginTop:'4px' }}>
                            {/* Export PDF -- kept up top so exporting the growth report is one
                                click and never requires opening the chart below. */}
                            <div className="no-print" style={{ display:'flex', justifyContent:'flex-end', marginTop:'12px', marginBottom:'8px' }}>
                              <button onClick={exportGrowthReportPdf}
                                style={{ display:'flex', alignItems:'center', gap:'6px', padding:'8px 14px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'12px', fontWeight:'700', cursor:'pointer' }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                                Export PDF
                              </button>
                            </div>

                            {/* Summary strip */}
                            <div className="summary-grid" style={{ marginBottom:'16px' }}>
                              <div style={{ background: gm.stuntingVariant === 'low' ? '#f0fdf4' : gm.stuntingVariant === 'mid' ? '#fffbeb' : '#fff1f2', borderRadius:'12px', padding:'14px 16px', border:`1px solid ${gm.stuntingVariant === 'low' ? '#bbf7d0' : gm.stuntingVariant === 'mid' ? '#fde68a' : '#fecaca'}` }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.06em', color:'#94a3b8', marginBottom:'4px' }}>Height Status</div>
                                <div style={{ fontSize:'15px', fontWeight:'900', color: gm.stuntingVariant === 'low' ? '#16a34a' : gm.stuntingVariant === 'mid' ? '#d97706' : '#dc2626' }}>{gm.stuntingClass}</div>
                                <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'2px' }}>{pctTxt(gm.heightPct)} percentile</div>
                              </div>
                              <div style={{ background: gm.underweightVariant === 'low' ? '#f0fdf4' : gm.underweightVariant === 'mid' ? '#fffbeb' : '#fff1f2', borderRadius:'12px', padding:'14px 16px', border:`1px solid ${gm.underweightVariant === 'low' ? '#bbf7d0' : gm.underweightVariant === 'mid' ? '#fde68a' : '#fecaca'}` }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.06em', color:'#94a3b8', marginBottom:'4px' }}>Weight / BMI Status</div>
                                <div style={{ fontSize:'15px', fontWeight:'900', color: gm.underweightVariant === 'low' ? '#16a34a' : gm.underweightVariant === 'mid' ? '#d97706' : '#dc2626' }}>{gm.underweightClass}</div>
                                <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'2px' }}>BMI {pctTxt(gm.bmiPct)} percentile</div>
                              </div>
                            </div>

                            {/* Metric rows */}
                            <MetricRow label="Chronological Age" value={evalAge.toFixed(1)} unit="yrs" />
                            <MetricRow label="BMI" value={gm.bmiVal.toFixed(1)} unit="kg/m²" sub={`z ${zTxt(gm.bmiZ)} · ${pctTxt(gm.bmiPct)} pct`} />
                            <MetricRow label="Median Weight for Age" value={gm.ref.wtMean !== null ? gm.ref.wtMean.toFixed(1) : "N/A"} unit="kg" sub={`Actual: ${evalWeight} kg`} />
                            <MetricRow label="Median Height for Age" value={gm.ref.htMean !== null ? gm.ref.htMean.toFixed(1) : "N/A"} unit="cm" sub={`Actual: ${evalHeight} cm`} />
                            <MetricRow label="Height Age (HA)" value={gm.heightAge.decimal ? gm.heightAge.decimal.toFixed(1) : "N/A"} unit="yrs equiv." />
                            <MetricRow label="Weight Age (WA)" value={gm.weightAge.decimal ? gm.weightAge.decimal.toFixed(1) : "N/A"} unit="yrs equiv." />

                            {/* Height SDS with bar */}
                            <div style={{ padding:'14px 0', borderBottom:'1px solid #f1f5f9' }}>
                              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:'10px' }}>
                                <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b' }}>Height SDS ({evalAge*12 >= 60 ? 'IAP' : 'WHO'})</span>
                                <div>
                                  <span style={{ fontSize:'32px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{zTxt(gm.heightZ)}</span>
                                  <span style={{ fontSize:'11px', color:'#94a3b8', marginLeft:'6px' }}>SD</span>
                                </div>
                              </div>
                              {gm.heightZ !== null ? <SDSBar z={gm.heightZ} /> : <div style={{ fontSize:'11px', color:'#94a3b8' }}>Out of reference range.</div>}
                            </div>

                            {/* BMI SDS with bar */}
                            <div style={{ padding:'14px 0' }}>
                              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:'10px' }}>
                                <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b' }}>BMI SDS (WHO)</span>
                                <div>
                                  <span style={{ fontSize:'32px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{zTxt(gm.bmiZ)}</span>
                                  <span style={{ fontSize:'11px', color:'#94a3b8', marginLeft:'6px' }}>SD</span>
                                </div>
                              </div>
                              {gm.bmiZ !== null ? <SDSBar z={gm.bmiZ} /> : <div style={{ fontSize:'11px', color:'#94a3b8' }}>Out of reference range.</div>}
                            </div>

                            {/* ── Growth chart (optional visualisation) ── collapsed by default so the
                                numbers above stay the primary read. The H+W / BMI toggle lives inside.
                                The chart body is display-toggled (not unmounted) so PDF export -- which
                                reads this exact markup -- keeps working whether it is open or closed. */}
                            <div className="no-print" style={{ marginTop:'18px', borderTop:'1px solid #f1f5f9', paddingTop:'14px' }}>
                              <button onClick={() => setShowChart(s => !s)}
                                style={{ width:'100%', display:'flex', alignItems:'center', gap:'10px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'11px 14px', cursor:'pointer', textAlign:'left' }}>
                                <span style={{ color:'#4f46e5', fontWeight:'800', fontSize:'13px', transform: showChart ? 'rotate(90deg)' : 'none', transition:'transform 0.15s', display:'inline-block' }}>▸</span>
                                <span style={{ fontSize:'13px', fontWeight:'800', color:'#334155' }}>{showChart ? 'Hide growth chart' : 'Show growth chart'}</span>
                                <span style={{ marginLeft:'auto', fontSize:'11px', color:'#94a3b8', fontWeight:'600' }}>Optional visualisation — the numbers above are the primary read</span>
                              </button>
                            </div>

                            <div style={{ display: showChart ? 'block' : 'none', marginTop:'12px' }}>
                              {/* H+W / BMI toggle */}
                              <div className="no-print" style={{ display:'flex', gap:'4px', background:'#f1f5f9', padding:'4px', borderRadius:'10px', marginBottom:'10px', width:'fit-content' }}>
                                {[{ key:'combined', label:'Growth Chart (H+W)' }, { key:'bmi', label:'BMI' }].map(({key:mkey,label}) => (
                                  <button key={mkey} onClick={() => setGrowthChartMeasure(mkey)}
                                    className="toggle-btn"
                                    style={{ background: growthChartMeasure===mkey ? 'white' : 'transparent', color: growthChartMeasure===mkey ? '#1e293b' : '#64748b', boxShadow: growthChartMeasure===mkey ? '0 1px 3px rgba(0,0,0,0.12)' : 'none' }}>
                                    {label}
                                  </button>
                                ))}
                              </div>

                              {/* Growth centile chart (auto-filled from patient data). Sized for A4 print --
                                  see printGrowthReport() below, which prints this exact same markup. */}
                              <div id="growth-chart-print" style={{ border:'1px solid #eef2f7', borderRadius:'12px', padding:'8px', marginBottom:'16px', background:'white', overflowX:'auto' }}>
                                {growthChartMeasure === 'combined' ? (
                                  <GrowthChartCombined
                                    sex={evalGender} ageYears={evalAge}
                                    heightValue={evalHeight} weightValue={evalWeight}
                                    heightData={growthSeries[evalGender].height} weightData={growthSeries[evalGender].weight}
                                    heightSeries={heightSeries} weightSeries={weightSeries}
                                  />
                                ) : (
                                  <GrowthChart measure="bmi" sex={evalGender} ageYears={evalAge} value={gm.bmiVal} series={bmiSeries} chartData={growthSeries[evalGender].bmi} />
                                )}
                              </div>
                              {growthChartMeasure==='combined' && !gm.weightAvailable && (
                                <div style={{ fontSize:'11px', color:'#d97706', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'8px 12px', marginBottom:'12px' }}>
                                  Weight-for-age has no reference data at this age. Use BMI-for-age for weight status instead.
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                      );
                    })()}

                    {/* ══ BONE AGE TAB ══ */}
                    {activeTab === 'boneage' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
                        <SectionHeader
                          title="Bone Age · 20-bone staging (13 RUS + 7 carpal)"
                          subtitle="TW3 scores RUS and carpal SEPARATELY and defines no combined 20-bone age (that is a TW2 construct) — all 20 are staged for per-bone visibility · letters A–I, doctor-graded · Indian (Khadilkar) adult-height context"
                          badge={boneMetrics && boneMetrics.hasBone ? "TW3 bone age set" : "Grade the film"}
                          badgeVariant="info"
                        />

                        {/* TOP: attach X-ray → instant AI screening estimate (verify) */}
                        <div style={{ marginTop:'16px', background:'linear-gradient(135deg,#eef2ff,#faf5ff)', border:'1.5px solid #ddd6fe', borderRadius:'16px', padding:'18px' }}>
                          <div style={{ fontSize:'11px', fontWeight:'800', color:'#6b21a8', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'10px' }}>1 · Attach hand X‑ray → bone age</div>
                          <div style={{ display:'flex', gap:'16px', alignItems:'center', flexWrap:'wrap' }}>
                            <label style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:'4px', padding:'18px 22px', border:'1.5px dashed #c7d2fe', borderRadius:'12px', background:'white', cursor: (tw3Config && tw3Config.ai_estimate_available) ? 'pointer' : 'not-allowed', textAlign:'center', minWidth:'190px' }}>
                              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                              <span style={{ fontSize:'12px', fontWeight:'700', color:'#7c3aed' }}>Attach left-hand film</span>
                              <span style={{ fontSize:'10px', color:'#a78bfa' }}>DICOM · PNG · JPEG · runs locally</span>
                              <input type="file" accept=".dcm,image/*" style={{ display:'none' }} disabled={!(tw3Config && tw3Config.ai_estimate_available)}
                                onChange={e => { const f = e.target.files && e.target.files[0]; if (f) runEstimate(f); e.target.value = ''; }} />
                            </label>
                            <div style={{ minWidth:'170px' }}>
                              <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', marginBottom:'3px' }}>Image source</label>
                              <select value={estimateDomain} onChange={e => setEstimateDomain(e.target.value)} className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'11px' }}>
                                {IMAGE_DOMAINS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
                              </select>
                              <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', margin:'8px 0 3px' }}>Declare image issues</label>
                              <div style={{ display:'flex', flexWrap:'wrap', gap:'4px' }}>
                                {DECLARABLE_FLAGS.map(([code, label]) => {
                                  const on = declaredFlags.includes(code);
                                  return (
                                    <button key={code} onClick={() => toggleDeclaredFlag(code)} title={code}
                                      style={{ fontSize:'10px', fontWeight:'700', padding:'2px 7px', borderRadius:'999px', cursor:'pointer',
                                        border: on ? '1px solid #dc2626' : '1px solid #cbd5e1',
                                        background: on ? '#fee2e2' : 'white', color: on ? '#991b1b' : '#64748b' }}>
                                      {on ? '✕ ' : ''}{label}
                                    </button>
                                  );
                                })}
                              </div>
                              <div style={{ fontSize:'9px', color:'#94a3b8', marginTop:'3px', lineHeight:'1.4' }}>Any of these makes the AI estimate abstain — a whole-hand model can't read these films.</div>
                            </div>
                            <div style={{ flex:1, minWidth:'200px' }}>
                              {aiBusy && <div style={{ fontSize:'12px', color:'#4338ca', fontWeight:'600' }}>Analysing locally…</div>}
                              {aiEstimate && aiEstimate.error && <div style={{ fontSize:'12px', color:'#b45309', fontWeight:'600' }}>{aiEstimate.error}</div>}
                              {aiEstimate && aiEstimate.accepted === false && (
                                <div style={{ background:'#fef2f2', border:'1.5px solid #fecaca', borderRadius:'10px', padding:'10px 12px' }}>
                                  <div style={{ fontSize:'12px', fontWeight:'800', color:'#991b1b' }}>⚠ Manual assessment required</div>
                                  <div style={{ fontSize:'10.5px', color:'#b91c1c', marginTop:'4px', lineHeight:'1.5' }}>{aiEstimate.message}</div>
                                  {aiEstimate.quality && aiEstimate.quality.hard_flags.length > 0 && (
                                    <div style={{ fontSize:'10px', color:'#7f1d1d', marginTop:'5px', fontWeight:'700' }}>Flags: {aiEstimate.quality.hard_flags.map(f => f.replace(/_/g,' ')).join(', ')}</div>
                                  )}
                                  <div style={{ fontSize:'9.5px', color:'#94a3b8', marginTop:'5px' }}>No AI age is shown — grade the bones manually below.</div>
                                </div>
                              )}
                              {aiEstimate && aiEstimate.available === false && aiEstimate.accepted !== false && aiEstimate.message && (
                                <div style={{ fontSize:'11px', color:'#b45309', fontWeight:'600' }}>{aiEstimate.message}</div>
                              )}
                              {aiEstimate && aiEstimate.bone_age_years != null && (
                                <div>
                                  <div style={{ fontSize:'11px', color:'#6b21a8', fontWeight:'700' }}>Bone age from this X‑ray</div>
                                  <div style={{ fontWeight:'900', color:'#5b21b6', lineHeight:1 }}><span style={{ fontSize:'34px' }}>{aiEstimate.bone_age_years}</span> <span style={{ fontSize:'14px' }}>yr</span></div>
                                  {aiEstimate.ci_low_years != null && aiEstimate.ci_high_years != null && (
                                    <div style={{ fontSize:'11px', color:'#7c3aed', fontWeight:'700', marginTop:'3px' }}>
                                      {aiEstimate.interval_kind === 'conformal' ? `${Math.round(parseFloat(aiEstimate.interval_coverage)*100)}% interval` : 'Likely range'} {aiEstimate.ci_low_years}–{aiEstimate.ci_high_years} yr
                                      <span style={{ fontWeight:'500', color:'#a78bfa' }}> {aiEstimate.interval_kind === 'conformal' ? `(conformal · ±${aiEstimate.uncertainty_months} mo, held-out RSNA)` : `(±${aiEstimate.uncertainty_months} mo MAE — approx, not calibrated)`}</span>
                                    </div>
                                  )}
                                  <div style={{ fontSize:'10px', color:'#7c3aed', marginTop:'2px' }}>Greulich–Pyle whole-image · NOT TW3{aiEstimate.model_version ? ` · ${aiEstimate.model_version}` : ''}</div>
                                  {aiEstimate.quality_warning && (
                                    <div style={{ fontSize:'10px', color:'#b45309', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'7px', padding:'6px 8px', marginTop:'6px', lineHeight:'1.5' }}>⚠ {aiEstimate.quality_warning}</div>
                                  )}
                                  {aiEstimate.population_note && (
                                    <div style={{ fontSize:'10px', color:'#64748b', marginTop:'6px', lineHeight:'1.5' }}>{aiEstimate.population_note}</div>
                                  )}
                                  <button onClick={() => { setBoneAge(Number(aiEstimate.bone_age_years.toFixed(1))); setBoneAgeSource('manual'); }} style={{ marginTop:'8px', padding:'6px 12px', background:'#16a34a', color:'white', border:'none', borderRadius:'8px', fontSize:'11px', fontWeight:'700', cursor:'pointer' }}>Use as bone age</button>
                                </div>
                              )}
                            </div>
                          </div>
                          {/* Suggestion box — clinician's corrected bone age (self-improvement flywheel). Evidence, not the patient result. */}
                          <div style={{ marginTop:'14px', paddingTop:'14px', borderTop:'1px dashed #ddd6fe' }}>
                            <div style={{ fontSize:'11px', fontWeight:'800', color:'#6b21a8', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'8px' }}>Is this right? Suggest the correct bone age</div>
                            <div style={{ display:'flex', gap:'10px', flexWrap:'wrap', alignItems:'flex-end' }}>
                              <div style={{ minWidth:'120px' }}>
                                <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', marginBottom:'3px' }}>Correct bone age (yr)</label>
                                <input type="number" step="0.1" min="0" max="25" value={fbAge} onChange={e => setFbAge(e.target.value)} placeholder="e.g. 11.5" className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'12px' }} />
                              </div>
                              <div style={{ minWidth:'130px' }}>
                                <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', marginBottom:'3px' }}>Method used</label>
                                <select value={fbMethod} onChange={e => setFbMethod(e.target.value)} className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'12px' }}>
                                  <option value="tw3-rus">TW3-RUS</option>
                                  <option value="greulich-pyle">Greulich–Pyle</option>
                                  <option value="clinical">Clinical judgement</option>
                                  <option value="other">Other</option>
                                </select>
                              </div>
                              <div style={{ minWidth:'110px' }}>
                                <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', marginBottom:'3px' }}>Confidence</label>
                                <select value={fbConfidence} onChange={e => setFbConfidence(e.target.value)} className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'12px' }}>
                                  <option value="high">High</option>
                                  <option value="medium">Medium</option>
                                  <option value="low">Low</option>
                                </select>
                              </div>
                              <div style={{ minWidth:'120px' }}>
                                <label style={{ fontSize:'9px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em', display:'block', marginBottom:'3px' }}>Your initials / ID</label>
                                <input value={fbRater} onChange={e => setFbRater(e.target.value)} placeholder="e.g. DR" className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'12px' }} />
                              </div>
                              <button onClick={submitFeedback} disabled={fbBusy} style={{ padding:'8px 14px', background:'#7c3aed', color:'white', border:'none', borderRadius:'8px', fontSize:'12px', fontWeight:'700', cursor: fbBusy ? 'wait' : 'pointer' }}>{fbBusy ? 'Saving…' : 'Submit suggestion'}</button>
                            </div>
                            <input value={fbNote} onChange={e => setFbNote(e.target.value)} placeholder="Optional note (e.g. which bones drove the difference)" className="input-field" style={{ padding:'7px 8px', width:'100%', fontSize:'11px', marginTop:'8px' }} />
                            {fbMsg && <div style={{ marginTop:'6px', fontSize:'11px', fontWeight:'700', color: fbMsg.type === 'ok' ? '#16a34a' : '#b45309' }}>{fbMsg.text}</div>}
                            <div style={{ marginTop:'6px', fontSize:'10px', color:'#a78bfa', lineHeight:1.5 }}>Your correction is logged as training evidence to improve accuracy over time. It does <strong>not</strong> change this patient's reported result.</div>
                          </div>
                          {tw3Config && !tw3Config.ai_estimate_available && (
                            <div style={{ marginTop:'8px', fontSize:'10px', color:'#94a3b8' }}>Bone-age model not installed yet. To enable: <code>python -m backend.ai.train_boneage</code></div>
                          )}
                          <div style={{ marginTop:'8px', fontSize:'10px', color:'#7c3aed', lineHeight:'1.5' }}>Whole-image AI estimate — the clinician verifies each result. The full doctor-graded 20-bone TW3 workflow (grading, licensed tables, scores) is built and can be re-enabled when needed.</div>
                        </div>

                        {/* 2 · Bone Age Report (Tanner–Whitehouse body) */}
                        <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'18px' }}>
                          <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'10px' }}>2 · Bone Age Report</div>
                          {(() => {
                            // Show the bone age from the attached X-ray (AI). If the TW3 tables are
                            // entered and the bones graded, the exact TW3 age takes over.
                            const L = letterResult || (assessment && assessment.letters);
                            const rusAge = L && L.rus ? L.rus.twiii_age_years : null;
                            const carpalAge = L && L.carpal ? L.carpal.twiii_age_years : null;
                            const aiYears = (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null;
                            if (rusAge != null) return (
                              <div style={{ marginBottom:'12px' }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#0f766e', textTransform:'uppercase', letterSpacing:'.05em' }}>TW3 bone age · TWIII-RUS</div>
                                <div style={{ fontWeight:'900', color:'#0f766e', lineHeight:1.1 }}>
                                  <span style={{ fontSize:'34px' }}>{rusAge}</span> <span style={{ fontSize:'14px' }}>yr</span>
                                  {carpalAge != null && <span style={{ fontSize:'12px', color:'#475569', fontWeight:'700' }}>  ·  carpal {carpalAge} yr</span>}
                                </div>
                              </div>
                            );
                            if (aiYears != null) return (
                              // Secondary treatment: the whole-image AI is screening
                              /* triage only, so it renders smaller and boxed -- clearly
                                 subordinate to the authoritative TW3 age above. */
                              <div style={{ marginBottom:'12px', background:'#faf5ff', border:'1px dashed #d8b4fe', borderRadius:'10px', padding:'10px 12px' }}>
                                <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                                  <span style={{ fontSize:'9px', fontWeight:'800', color:'white', background:'#a78bfa', borderRadius:'99px', padding:'2px 7px', textTransform:'uppercase', letterSpacing:'.05em' }}>AI screening</span>
                                  <span style={{ fontSize:'10px', fontWeight:'700', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'.05em' }}>Bone age · from X-ray</span>
                                </div>
                                <div style={{ fontWeight:'900', color:'#6b21a8', lineHeight:1.1, marginTop:'4px' }}>
                                  <span style={{ fontSize:'26px' }}>{aiYears}</span> <span style={{ fontSize:'13px' }}>yr</span>
                                </div>
                                <div style={{ fontSize:'10px', color:'#7c3aed', marginTop:'2px' }}>Whole-image estimate{aiEstimate.ci_low_years != null ? ` · ${aiEstimate.interval_kind === 'conformal' ? Math.round(parseFloat(aiEstimate.interval_coverage)*100) + '% ' : ''}${aiEstimate.ci_low_years}–${aiEstimate.ci_high_years} yr` : ''} — not TW3; the clinician verifies. Grade the bones for the authoritative age.</div>
                              </div>
                            );
                            return (
                              <div style={{ marginBottom:'12px', fontSize:'12px', color:'#94a3b8' }}>Attach a left‑hand X‑ray above to get the bone age.</div>
                            );
                          })()}
                          {/* Standard comparison — same staged bones, different TW reference tables.
                              Renders ONLY when the licensed tables are entered and produce ≥1 real age
                              (otherwise stays hidden — never a row of dashes, never a guessed number). */}
                          {(() => {
                            const Lc = letterResult || (assessment && assessment.letters);
                            if (!Lc) return null;
                            const rows = [
                              ['TWIII · RUS', Lc.rus && Lc.rus.twiii_age_years, '#0f766e'],
                              ['TWII · RUS', Lc.rus && Lc.rus.twii_age_years, '#0f766e'],
                              ["TWII'20 · 20-bone", Lc.tw20 && Lc.tw20.age_years, '#5b21b6'],
                              ['TWIII · carpal', Lc.carpal && Lc.carpal.twiii_age_years, '#b45309'],
                            ].filter(r => r[1] != null);
                            if (rows.length < 2) return null;  // nothing to compare
                            return (
                              <div style={{ marginBottom:'12px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'12px 14px' }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'8px' }}>Standard comparison · same staging</div>
                                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(110px, 1fr))', gap:'8px' }}>
                                  {rows.map(([label, age, color]) => (
                                    <div key={label} style={{ background:'white', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'8px 10px' }}>
                                      <div style={{ fontSize:'9px', fontWeight:'800', color, textTransform:'uppercase', letterSpacing:'.04em' }}>{label}</div>
                                      <div style={{ fontSize:'20px', fontWeight:'900', color, lineHeight:1.15 }}>{age} <span style={{ fontSize:'11px', fontWeight:'700' }}>yr</span></div>
                                    </div>
                                  ))}
                                </div>
                                <div style={{ marginTop:'8px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>Differences reflect the scoring <strong>standard / reference tables</strong>, not the child's radiograph. RUS and carpal bone ages are reported separately — never averaged.</div>
                              </div>
                            );
                          })()}
                          {/* Cross-check · independent methods (report §4). TW3 stays default; others shown below as a trust signal. */}
                          {(() => {
                            const L = letterResult || (assessment && assessment.letters);
                            const tw3 = (L && L.rus && L.rus.twiii_age_years != null) ? L.rus.twiii_age_years
                                        : (boneAge !== '' ? parseFloat(boneAge) : null);
                            const gp = (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null;
                            const carpal = (L && L.carpal && L.carpal.twiii_age_years != null) ? L.carpal.twiii_age_years : null;
                            const rows = [
                              ['TW3-RUS', tw3, '#0f766e'],
                              ['GP model estimate', gp, '#6b21a8'],
                              ['TW3 carpal', carpal, '#b45309'],
                            ].filter(r => r[1] != null && !isNaN(r[1]));
                            if (rows.length < 2) return null;
                            const vals = rows.map(r => Number(r[1]));
                            const spread = Math.max(...vals) - Math.min(...vals);
                            const agree = spread <= 1.0;
                            return (
                              <div style={{ marginBottom:'12px', background:'#ffffff', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'14px' }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'8px' }}>Cross-check · independent methods</div>
                                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(120px, 1fr))', gap:'8px' }}>
                                  {rows.map(([label, age, color], i) => (
                                    <div key={label} style={{ background: i===0 ? '#f0fdfa' : '#faf5ff', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'8px 10px' }}>
                                      <div style={{ fontSize:'9px', fontWeight:'800', color, textTransform:'uppercase', letterSpacing:'.04em' }}>{label}{i===0 ? ' · default' : ''}</div>
                                      <div style={{ fontSize: i===0 ? '22px' : '18px', fontWeight:'900', color, lineHeight:1.15 }}>{Number(age).toFixed(1)} <span style={{ fontSize:'11px', fontWeight:'700' }}>yr</span></div>
                                    </div>
                                  ))}
                                </div>
                                <div style={{ marginTop:'8px', fontSize:'11px', fontWeight:'700', color: agree ? '#16a34a' : '#b45309' }}>
                                  {agree ? `✓ Methods agree — within ${spread.toFixed(1)} yr` : `⚠ Methods differ by ${spread.toFixed(1)} yr — re-check staging or image quality`}
                                </div>
                                <div style={{ marginTop:'4px', fontSize:'10px', color:'#94a3b8', lineHeight:1.5 }}>TW3-RUS is the authoritative result. The others are an independent cross-check — agreement builds trust; disagreement usually means a mis-staged bone or a low-quality film.</div>
                              </div>
                            );
                          })()}
                          {radiograph && (
                            <div style={{ marginBottom:'12px', background:'#f0fdfa', border:'1px solid #99f6e4', borderRadius:'10px', padding:'10px 12px', fontSize:'11px', color:'#0f766e', lineHeight:'1.75' }}>
                              <div style={{ fontWeight:'800', textTransform:'uppercase', fontSize:'10px', letterSpacing:'.05em', marginBottom:'4px' }}>Automated film analysis</div>
                              <div>Image · {radiograph.source_format || '—'}{radiograph.width && radiograph.height ? ` · ${radiograph.width}×${radiograph.height}` : ''} · laterality {radiograph.laterality || 'n/a'} · quality {String(radiograph.quality_status || '—').replace(/_/g, ' ')}{radiograph.source_domain ? ` · ${String(radiograph.source_domain).replace(/_/g, ' ')}` : ''}</div>
                              {aiEstimate && aiEstimate.bone_age_years != null && (
                                <div>AI whole-image estimate <span style={{ color:'#64748b' }}>(screening, not TW3)</span> · <strong>{aiEstimate.bone_age_years} yr</strong>{aiEstimate.val_mae_months ? ` · ±~${Math.round(aiEstimate.val_mae_months)} mo` : ''}</div>
                              )}
                              <div>Bones auto-located · {Object.keys(boxes).length}/20{Object.keys(boxes).length === 0 ? ' — draw boxes below, or train the localizer (backend/ai/LOCALIZE.md)' : ''}</div>
                              <div>Per-bone TW3 stages · <strong>doctor-graded below</strong> <span style={{ color:'#64748b' }}>(automatic staging is the next AI step — needs the staging model)</span></div>
                            </div>
                          )}
                          <details style={{ marginTop:'4px' }} open>
                          <summary style={{ cursor:'pointer', fontSize:'11px', fontWeight:'700', color:'#7c3aed', listStyle:'none', padding:'4px 0' }}>▸ Detailed 20-bone report (per-bone staging · RUS &amp; carpal kept separate)</summary>
                          {(() => {
                            const rep = boneReport;
                            const yrs = (v) => (v === null || v === undefined) ? '—' : (v + ' yr');
                            const num = (v) => (v === null || v === undefined) ? '—' : v;
                            const visChip = (v) => {
                              const map = { STAGED:['#dcfce7','#166534'], NOT_VISIBLE:['#fef3c7','#92400e'], NOT_SCORABLE:['#fee2e2','#991b1b'], NOT_STAGED:['#f1f5f9','#94a3b8'] };
                              const [bg, fg] = map[v] || map.NOT_STAGED;
                              return <span style={{ background:bg, color:fg, fontSize:'9px', fontWeight:'800', padding:'1px 6px', borderRadius:'999px', letterSpacing:'0.02em' }}>{v.replace('_',' ')}</span>;
                            };
                            const rows = rep ? rep.per_bone_results : [];
                            return (
                              <div style={{ marginTop:'6px' }}>
                                <div style={{ overflowX:'auto' }}>
                                  <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'11px' }}>
                                    <thead>
                                      <tr style={{ textAlign:'left', color:'#64748b', borderBottom:'1px solid #e2e8f0' }}>
                                        <th style={{ padding:'4px 6px', fontWeight:'700' }}>#</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700' }}>Bone</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700' }}>Sys</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700' }}>Stage</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700' }}>Visibility</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700', textAlign:'right' }}>Points</th>
                                        <th style={{ padding:'4px 6px', fontWeight:'700', textAlign:'right' }}>% of max</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {rows.map((b) => (
                                        <tr key={b.bone_id} style={{ borderBottom:'1px solid #f1f5f9', background: b.system==='CARPAL' ? '#fafafa' : 'white' }}>
                                          <td style={{ padding:'3px 6px', color:'#94a3b8' }}>{b.display_order}</td>
                                          <td style={{ padding:'3px 6px', fontWeight:'600', color:'#1e293b' }}>{b.anatomical_name}</td>
                                          <td style={{ padding:'3px 6px', color:'#64748b' }}>{b.system==='CARPAL' ? 'Carpal' : 'RUS'}</td>
                                          <td style={{ padding:'3px 6px', fontWeight:'700', color:'#5b21b6' }}>{b.stage && !b.stage.startsWith('NOT_') ? b.stage : '—'}</td>
                                          <td style={{ padding:'3px 6px' }}>{visChip(b.visibility)}</td>
                                          <td style={{ padding:'3px 6px', textAlign:'right', color:'#475569' }}>{num(b.points)}</td>
                                          <td style={{ padding:'3px 6px', textAlign:'right', color:'#475569' }}>{b.pct_of_bone_max != null ? b.pct_of_bone_max + '%' : '—'}</td>
                                        </tr>
                                      ))}
                                      {rows.length === 0 && <tr><td colSpan="7" style={{ padding:'10px 6px', color:'#94a3b8' }}>Grade the bones below to build the report.</td></tr>}
                                    </tbody>
                                  </table>
                                </div>
                                {rep && (
                                  <div style={{ marginTop:'10px', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'8px' }}>
                                    <div style={{ background:'#f5f3ff', border:'1px solid #ddd6fe', borderRadius:'10px', padding:'10px 12px' }}>
                                      <div style={{ fontSize:'10px', fontWeight:'800', color:'#7c3aed', textTransform:'uppercase', letterSpacing:'0.05em' }}>RUS (13 bones)</div>
                                      <div style={{ fontSize:'11px', color:'#475569', marginTop:'4px' }}>Staged {rep.completeness.rus_staged}/13 · score {num(rep.rus.total_score)}</div>
                                      <div style={{ fontSize:'13px', fontWeight:'800', color:'#5b21b6', marginTop:'2px' }}>TWIII age {yrs(rep.rus.twiii_age_years)} <span style={{ fontSize:'10px', fontWeight:'600', color:'#94a3b8' }}>· TWII {yrs(rep.rus.twii_age_years)}</span></div>
                                    </div>
                                    <div style={{ background:'#fafafa', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'10px 12px' }}>
                                      <div style={{ fontSize:'10px', fontWeight:'800', color:'#64748b', textTransform:'uppercase', letterSpacing:'0.05em' }}>Carpal (7 bones) · separate</div>
                                      <div style={{ fontSize:'11px', color:'#475569', marginTop:'4px' }}>Staged {rep.completeness.carpal_staged}/7 · score {num(rep.carpal.total_score)}</div>
                                      <div style={{ fontSize:'13px', fontWeight:'800', color:'#334155', marginTop:'2px' }}>TWIII age {yrs(rep.carpal.twiii_age_years)} <span style={{ fontSize:'10px', fontWeight:'600', color:'#94a3b8' }}>· never averaged with RUS</span></div>
                                    </div>
                                  </div>
                                )}
                                {rep && rep.scoring_note && (
                                  <div style={{ marginTop:'10px', fontSize:'10px', color:'#92400e', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'8px 10px', lineHeight:'1.5' }}>{rep.scoring_note}</div>
                                )}
                                {rep && (
                                  <div style={{ marginTop:'8px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>{rep.mandatory_disclaimer}</div>
                                )}
                              </div>
                            );
                          })()}
                          </details>
                        </div>

                        {/* Advanced TW3 workflow — HIDDEN per request (all code kept intact;
                            remove display:'none' below to restore manual grading / tables / etc.) */}
                        <details style={{ marginTop:'16px', display:'none' }}>
                          <summary style={{ cursor:'pointer', fontWeight:'800', fontSize:'12px', color:'#7c3aed', padding:'8px 0', listStyle:'none' }}>⚙ Advanced · manual grading, save &amp; approve, adult-height</summary>

                        {/* Manual grading: original TW3 letters A–I (RUS + carpals) */}
                        <div style={{ marginTop:'16px', background:'#faf5ff', border:'1px solid #e9d5ff', borderRadius:'12px', padding:'16px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'12px', flexWrap:'wrap', gap:'8px' }}>
                            <span style={{ fontSize:'11px', fontWeight:'800', color:'#6b21a8', textTransform:'uppercase', letterSpacing:'0.05em' }}>Manual TW3 grading · left hand–wrist · stages A–I</span>
                            <button onClick={() => { setRusStages({}); setCarpalStages({}); }} style={{ padding:'5px 12px', background:'white', color:'#7c3aed', border:'1.5px solid #ddd6fe', borderRadius:'8px', fontSize:'11px', fontWeight:'700', cursor:'pointer' }}>Clear grades</button>
                          </div>
                          <div style={{ fontSize:'10px', fontWeight:'800', color:'#7c3aed', marginBottom:'6px', textTransform:'uppercase', letterSpacing:'.04em' }}>RUS bones (13)</div>
                          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(150px, 1fr))', gap:'8px' }}>
                            {REPORT_RUS.map(([code, label]) => (
                              <div key={code}>
                                <label style={{ fontSize:'10px', fontWeight:'700', color:'#7c3aed', display:'block', marginBottom:'3px' }}>{label}</label>
                                <select value={rusStages[code] || ''} onChange={e => setRusStages(s => { const n = { ...s }; if (e.target.value) n[code] = e.target.value; else delete n[code]; return n; })} className="input-field" style={{ padding:'7px 8px', width:'100%' }}>
                                  <option value="">— stage —</option>
                                  {LETTER_STAGES.map(st => <option key={st} value={st}>{st}</option>)}
                                </select>
                              </div>
                            ))}
                          </div>
                          <div style={{ fontSize:'10px', fontWeight:'800', color:'#7c3aed', margin:'14px 0 6px', textTransform:'uppercase', letterSpacing:'.04em' }}>Carpal bones (7)</div>
                          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(150px, 1fr))', gap:'8px' }}>
                            {REPORT_CARPALS.map(name => (
                              <div key={name}>
                                <label style={{ fontSize:'10px', fontWeight:'700', color:'#7c3aed', display:'block', marginBottom:'3px' }}>{name}</label>
                                <select value={carpalStages[name] || ''} onChange={e => setCarpalStages(s => { const n = { ...s }; if (e.target.value) n[name] = e.target.value; else delete n[name]; return n; })} className="input-field" style={{ padding:'7px 8px', width:'100%' }}>
                                  <option value="">— stage —</option>
                                  {LETTER_STAGES.map(st => <option key={st} value={st}>{st}</option>)}
                                </select>
                              </div>
                            ))}
                          </div>
                          <div style={{ marginTop:'12px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>These letter grades appear in the report above. The RUS/carpal scores and the TWII / TWIII / TWII'20 bone ages compute once the clinic's licensed TW3 tables are supplied — no values are guessed.</div>
                        </div>

                        {/* Annotation record — persists the 20-bone letter staging (directive §7, §11).
                            Scoring/approval unlock only when the licensed TW3 tables arrive. */}
                        <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
                          <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:'4px' }}>Annotation record</div>
                          <div style={{ fontSize:'10px', color:'#94a3b8', marginBottom:'10px', lineHeight:'1.5' }}>Saves the doctor-confirmed 20-bone letter staging to the local database (for review and to build the training dataset). Sex and age come from Demographics.</div>
                          <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'flex-end' }}>
                            <div style={{ flex:'1 1 180px' }}>
                              <label style={{ fontSize:'10px', fontWeight:'700', color:'#64748b', display:'block', marginBottom:'3px' }}>Patient code</label>
                              <input value={patientCode} onChange={e => setPatientCode(e.target.value)} placeholder="e.g. CASE-001"
                                     className="input-field" style={{ padding:'7px 8px', width:'100%' }} disabled={lcLocked} />
                            </div>
                            <button onClick={saveDraft} disabled={lcBusy} style={lcBtn('#7c3aed', lcBusy)}>{lcBusy ? 'Saving…' : (assessment && !lcLocked ? 'Update annotation' : 'Save annotation')}</button>
                            <button onClick={async () => {
                              if (!patientCode.trim()) { setLcMsg({ type:'err', text:'Enter a patient code to load.' }); return; }
                              setLcBusy(true); setLcMsg(null);
                              try {
                                const r = await fetch(`${LC_API}?patient_code=${encodeURIComponent(patientCode.trim())}`);
                                const list = await r.json();
                                if (!r.ok || !Array.isArray(list) || list.length === 0) { setLcMsg({ type:'err', text:'No saved annotation for that code.' }); return; }
                                const d = list[0];
                                bonesIntoGrids(d.bones); setAssessment(d); setShowAudit(false);
                                setLcMsg({ type:'ok', text:`Loaded #${d.id} rev ${d.revision} · ${d.assessment_status}` });
                              } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
                              finally { setLcBusy(false); }
                            }} disabled={lcBusy} style={lcBtn('#475569', lcBusy)}>Load saved</button>
                            {assessment && lcLocked && (
                              <button onClick={reviseAssessment} disabled={lcBusy} style={lcBtn('#0891b2', lcBusy)}>Open revision</button>
                            )}
                            {assessment && (
                              <button onClick={toggleAudit} disabled={lcBusy} style={lcBtn('#64748b', lcBusy)}>{showAudit ? 'Hide audit' : 'Audit'}</button>
                            )}
                          </div>
                          {assessment && (
                            <div style={{ marginTop:'10px', fontSize:'11px', color:'#475569' }}>
                              Record #{assessment.id} · rev {assessment.revision} · <strong style={{ textTransform:'uppercase' }}>{assessment.assessment_status}</strong>
                              {' '}· {assessment.rus_staged_count}/13 RUS + {assessment.carpal_staged_count}/7 carpal staged
                            </div>
                          )}
                          {lcMsg && (
                            <div style={{ marginTop:'8px', fontSize:'11px', fontWeight:'700', color: lcMsg.type === 'ok' ? '#059669' : '#dc2626' }}>{lcMsg.text}</div>
                          )}
                          {showAudit && assessment && assessment.audit && (
                            <div style={{ marginTop:'10px', maxHeight:'160px', overflowY:'auto', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'8px', fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:'10px', color:'#475569' }}>
                              {assessment.audit.map((e, i) => (
                                <div key={i}>{e.timestamp ? e.timestamp.slice(0,19).replace('T',' ') : ''} · {e.event_type} · {e.actor}{e.reason ? ' · ' + e.reason : ''}</div>
                              ))}
                            </div>
                          )}
                          {/* Attach film + doctor-confirmed acquisition domain (directive §16) */}
                          {assessment && (
                            <div style={{ marginTop:'12px', paddingTop:'12px', borderTop:'1px solid #f1f5f9' }}>
                              <div style={{ display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'flex-end' }}>
                                <label style={{ ...lcBtn('#0f766e', lcBusy || lcLocked), display:'inline-block' }}>
                                  {radiograph ? 'Replace film' : 'Attach film'}
                                  <input type="file" accept=".dcm,image/*" style={{ display:'none' }} disabled={lcBusy || lcLocked}
                                         onChange={e => { const f = e.target.files && e.target.files[0]; if (f) attachImage(f); e.target.value=''; }} />
                                </label>
                                {radiograph && (
                                  <div style={{ flex:'1 1 200px' }}>
                                    <label style={{ fontSize:'10px', fontWeight:'700', color:'#64748b', display:'block', marginBottom:'3px' }}>Image source (confirm)</label>
                                    <select value={radiograph.source_domain || 'unknown'} onChange={e => setImageDomain(e.target.value)}
                                            className="input-field" style={{ padding:'7px 8px', width:'100%' }} disabled={lcLocked}>
                                      {IMAGE_DOMAINS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
                                    </select>
                                  </div>
                                )}
                              </div>
                              {radiograph && (
                                <div style={{ marginTop:'8px', fontSize:'11px', color:'#475569' }}>
                                  Film #{radiograph.radiograph_id} · {radiograph.source_format} · quality {String(radiograph.quality_status||'').replace(/_/g,' ')}
                                  {radiograph.duplicate_of ? ` · duplicate of #${radiograph.duplicate_of}` : ''}
                                </div>
                              )}
                              {radiograph && LOW_TRUST_DOMAINS.includes(radiograph.source_domain) && (
                                <div style={{ marginTop:'8px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'8px 10px', fontSize:'10.5px', color:'#92400e', lineHeight:'1.5' }}>
                                  ⚠ {radiograph.source_domain === 'film_photo' ? 'Photograph of a film' : 'Compressed image'}: reduced reliability. Any future AI suggestion must be treated with lower confidence and every bone confirmed manually — this domain is evaluated separately from digital images.
                                </div>
                              )}
                            </div>
                          )}
                          <div style={{ marginTop:'10px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>Scoring, bone-age calculation and doctor approval unlock automatically once the clinic's licensed TW3 point/age tables are installed. Until then this record captures verified staging only.</div>
                        </div>

                        {/* Bone localization — PEA auto-boxes the doctor confirms (feeds crops) */}
                        {radiograph && (
                          <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
                              <div>
                                <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em' }}>Bone localization</div>
                                <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>Auto-box the bones (or draw them), drag to correct, save. Confirmed boxes become training crops.</div>
                              </div>
                              <div style={{ display:'flex', gap:'8px' }}>
                                <button onClick={localizeBones} disabled={locBusy || lcLocked} style={lcBtn('#0f766e', locBusy || lcLocked)}>{locBusy ? '…' : 'Auto-locate'}</button>
                                <button onClick={saveBoxes} disabled={locBusy || lcLocked || Object.keys(boxes).length===0} style={lcBtn('#7c3aed', locBusy || lcLocked || Object.keys(boxes).length===0)}>Save boxes</button>
                              </div>
                            </div>
                            {analysisUrl && (
                              <div ref={locRef} onMouseMove={onLocMove} onMouseUp={endLocDrag} onMouseLeave={endLocDrag}
                                   style={{ position:'relative', width:'100%', maxWidth:'420px', margin:'12px auto 0', userSelect:'none' }}>
                                <img src={analysisUrl} alt="radiograph" draggable={false}
                                     onLoad={e => { if (!locImg) setLocImg({ width:e.target.naturalWidth, height:e.target.naturalHeight }); }}
                                     style={{ width:'100%', display:'block', borderRadius:'8px', border:'1px solid #e2e8f0' }} />
                                {locImg && Object.entries(boxes).map(([bone, b]) => {
                                  const sel = selBone === bone;
                                  const st = { position:'absolute', left:`${b[0]/locImg.width*100}%`, top:`${b[1]/locImg.height*100}%`,
                                    width:`${(b[2]-b[0])/locImg.width*100}%`, height:`${(b[3]-b[1])/locImg.height*100}%`,
                                    border:`2px solid ${sel ? '#f59e0b' : '#0ea5e9'}`, background: sel ? 'rgba(245,158,11,0.12)' : 'rgba(14,165,233,0.08)',
                                    cursor:'move', boxSizing:'border-box' };
                                  return (
                                    <div key={bone} onMouseDown={e => startBoxDrag(bone, 'move', e)} style={st}>
                                      <span style={{ position:'absolute', top:'-14px', left:'-1px', fontSize:'8px', fontWeight:'700', color: sel?'#b45309':'#0369a1', background:'white', padding:'0 2px', borderRadius:'2px', whiteSpace:'nowrap' }}>{bone}</span>
                                      <div onMouseDown={e => startBoxDrag(bone, 'resize', e)}
                                           style={{ position:'absolute', right:'-5px', bottom:'-5px', width:'10px', height:'10px', background:'white', border:`2px solid ${sel?'#f59e0b':'#0ea5e9'}`, borderRadius:'2px', cursor:'nwse-resize' }} />
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                            <div style={{ marginTop:'10px', fontSize:'10px', fontWeight:'700', color:'#64748b' }}>Bones — click to add/select a box (× to remove):</div>
                            <div style={{ display:'flex', flexWrap:'wrap', gap:'4px', marginTop:'4px' }}>
                              {[...REPORT_RUS.map(([c])=>c), ...REPORT_CARPALS.map(carpalCode)].map(code => {
                                const has = !!boxes[code]; const sel = selBone === code;
                                return (
                                  <span key={code} style={{ display:'inline-flex', alignItems:'center', gap:'2px', padding:'3px 6px', borderRadius:'6px', fontSize:'10px', fontWeight:'700', cursor:'pointer',
                                    border:`1px solid ${has?'#0ea5e9':'#e2e8f0'}`, background: sel?'#fef3c7':(has?'#e0f2fe':'white'), color: has?'#0369a1':'#94a3b8' }}
                                    onClick={() => addOrSelectBox(code)}>
                                    {code}{has && <span onClick={e=>{e.stopPropagation(); clearBox(code);}} style={{ color:'#ef4444', fontWeight:'800' }}>×</span>}
                                  </span>
                                );
                              })}
                            </div>
                            {locMsg && <div style={{ marginTop:'8px', fontSize:'11px', fontWeight:'700', color: locMsg.type==='ok'?'#059669':'#dc2626' }}>{locMsg.text}</div>}
                            <div style={{ marginTop:'8px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>Auto-locate needs a trained localizer model (see backend/ai/LOCALIZE.md); until then you can draw boxes manually and they still save + export as crops.</div>
                          </div>
                        )}

                        {/* Dataset coverage (directive §13) — how many patients per bone×stage exist */}
                        <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
                            <div>
                              <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em' }}>Dataset coverage</div>
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>Unique patients per bone × stage across all saved annotations. Drives when AI suggestions could be trained.</div>
                            </div>
                            <button onClick={loadCoverage} disabled={covBusy} style={lcBtn('#475569', covBusy)}>{covBusy ? 'Loading…' : (coverage ? 'Refresh' : 'Load coverage')}</button>
                          </div>
                          {coverage && (
                            <div style={{ marginTop:'10px' }}>
                              <div style={{ fontSize:'11px', color:'#475569', marginBottom:'8px' }}>
                                {coverage.n_patients} patients · {coverage.n_assessments} assessments.
                                {Object.entries(coverage.summary).map(([sys, s]) => (
                                  <span key={sys} style={{ marginLeft:'8px' }}>· <strong>{sys}</strong>: {s.unique_patients} pt / {s.cells_covered} cells / {s.annotations} anno</span>
                                ))}
                              </div>
                              {coverage.cells.length === 0 ? (
                                <div style={{ fontSize:'11px', color:'#94a3b8' }}>No confirmed staging yet — save an annotation above.</div>
                              ) : (
                                <div style={{ maxHeight:'220px', overflowY:'auto', border:'1px solid #e2e8f0', borderRadius:'8px' }}>
                                  <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'11px' }}>
                                    <thead>
                                      <tr style={{ background:'#f8fafc', color:'#64748b', textAlign:'left' }}>
                                        <th style={{ padding:'5px 8px' }}>Bone</th><th style={{ padding:'5px 8px' }}>Stage</th>
                                        <th style={{ padding:'5px 8px' }}>♂</th><th style={{ padding:'5px 8px' }}>♀</th>
                                        <th style={{ padding:'5px 8px' }}>w/img</th><th style={{ padding:'5px 8px' }}>Support</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {[...coverage.cells].sort((a,b) => a.unique_total - b.unique_total).map((c, i) => {
                                        const col = { empty:'#dc2626', minimal:'#d97706', experimental:'#d97706', limited:'#2563eb', candidate:'#059669' }[c.support] || '#64748b';
                                        return (
                                          <tr key={i} style={{ borderTop:'1px solid #f1f5f9' }}>
                                            <td style={{ padding:'5px 8px', color:'#334155' }}>{c.bone_code}<span style={{ color:'#cbd5e1' }}> · {c.stage_system.replace('tw3','')}</span></td>
                                            <td style={{ padding:'5px 8px', fontWeight:'700' }}>{c.stage}</td>
                                            <td style={{ padding:'5px 8px' }}>{c.unique_boys}</td>
                                            <td style={{ padding:'5px 8px' }}>{c.unique_girls}</td>
                                            <td style={{ padding:'5px 8px' }}>{c.n_with_image}</td>
                                            <td style={{ padding:'5px 8px', color:col, fontWeight:'700' }}>{c.support}</td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                              <div style={{ marginTop:'8px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>Bands (unique patients): minimal 1–9 · experimental 10–24 · limited 25–49 · candidate ≥50. Engineering thresholds only — not proof of clinical validity.</div>
                            </div>
                          )}
                        </div>

                        {/* Monitoring & drift (Plan 2 WI-6) — watch the AI-vs-human gap; never mutate the model */}
                        <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
                            <div>
                              <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em' }}>Monitoring &amp; drift</div>
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>AI-vs-clinician error over time, input-quality drift, and a soft external plausibility check. Watch-the-gap only — this never changes a model or a reported age.</div>
                            </div>
                            <button onClick={loadMonitoring} disabled={monBusy} style={lcBtn('#475569', monBusy)}>{monBusy ? 'Loading…' : (monitoring ? 'Refresh' : 'Load monitoring')}</button>
                          </div>
                          {monitoring && (() => {
                            const st = monitoring.stats || {}; const tr = st.trend || {};
                            const dr = monitoring.input_drift || {}; const pl = monitoring.plausibility || {};
                            const pct = v => v == null ? '—' : `${Math.round(v * 100)}%`;
                            const yr = v => v == null ? '—' : `${v} yr`;
                            return (
                              <div style={{ marginTop:'10px' }}>
                                <div style={{ display:'flex', flexWrap:'wrap', gap:'10px', marginBottom:'10px' }}>
                                  <div style={{ flex:'1 1 150px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'10px' }}>
                                    <div style={{ fontSize:'10px', color:'#64748b' }}>AI vs clinician MAE</div>
                                    <div style={{ fontSize:'18px', fontWeight:'800', color:'#334155' }}>{yr(st.ai_vs_human_mae_years)}</div>
                                    <div style={{ fontSize:'10px', color:'#94a3b8' }}>{st.paired_with_ai || 0} paired · {st.total_feedback || 0} total</div>
                                  </div>
                                  <div style={{ flex:'1 1 150px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'10px' }}>
                                    <div style={{ fontSize:'10px', color:'#64748b' }}>Trend (recent vs older)</div>
                                    <div style={{ fontSize:'18px', fontWeight:'800', color: tr.improving ? '#059669' : '#334155' }}>{yr(tr.recent_mae_years)} {tr.improving ? '↓' : ''}</div>
                                    <div style={{ fontSize:'10px', color:'#94a3b8' }}>was {yr(tr.older_mae_years)}</div>
                                  </div>
                                  <div style={{ flex:'1 1 150px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'10px' }}>
                                    <div style={{ fontSize:'10px', color:'#64748b' }}>Low-trust input share</div>
                                    <div style={{ fontSize:'18px', fontWeight:'800', color: dr.worsening ? '#d97706' : '#334155' }}>{pct(dr.recent_low_trust_share)} {dr.worsening ? '↑' : ''}</div>
                                    <div style={{ fontSize:'10px', color:'#94a3b8' }}>was {pct(dr.older_low_trust_share)} · compressed/photo</div>
                                  </div>
                                </div>
                                {pl.vs_cpp && (
                                  <div style={{ background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'10px' }}>
                                    <div style={{ fontSize:'11px', fontWeight:'800', color:'#92400e' }}>External plausibility (soft · non-gating)</div>
                                    <div style={{ fontSize:'11px', color:'#334155', marginTop:'4px' }}>
                                      Observed bone-age distribution vs published cohorts — TV distance: CPP {pl.vs_cpp.tv_distance ?? '—'} · control {pl.vs_control?.tv_distance ?? '—'}.
                                    </div>
                                    <div style={{ fontSize:'10px', color:'#b45309', marginTop:'6px', lineHeight:'1.5' }}>⚠ {pl.vs_cpp.caveat}</div>
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                        </div>

                        {/* Adjudication queue (Plan 2 WI-4) — disputed bones a senior reads, never averaged */}
                        <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
                            <div>
                              <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em' }}>Adjudication queue</div>
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>Bones where independent reads disagree are queued for a senior read — resolved to one stage, never silently averaged.</div>
                            </div>
                            <button onClick={loadAdjudication} disabled={adjBusy} style={lcBtn('#475569', adjBusy)}>{adjBusy ? 'Loading…' : (adjItems ? 'Refresh' : 'Load queue')}</button>
                          </div>
                          {adjItems && (
                            <div style={{ marginTop:'10px' }}>
                              <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'10px', flexWrap:'wrap' }}>
                                <label style={{ fontSize:'11px', color:'#475569' }}>Reviewing clinician</label>
                                <input value={adjReviewer} onChange={e => setAdjReviewer(e.target.value)} placeholder="e.g. Dr Rao"
                                       style={{ fontSize:'11px', padding:'4px 8px', border:'1px solid #cbd5e1', borderRadius:'6px' }} />
                              </div>
                              {adjItems.length === 0 ? (
                                <div style={{ fontSize:'11px', color:'#94a3b8' }}>No disputed bones open. Multi-reader disagreements appear here for resolution.</div>
                              ) : (
                                <div style={{ maxHeight:'240px', overflowY:'auto', border:'1px solid #e2e8f0', borderRadius:'8px' }}>
                                  {adjItems.map(it => (
                                    <div key={it.id} style={{ padding:'8px 10px', borderTop:'1px solid #f1f5f9', display:'flex', justifyContent:'space-between', alignItems:'center', gap:'10px', flexWrap:'wrap' }}>
                                      <div style={{ fontSize:'11px', color:'#334155' }}>
                                        <strong>{it.bone_code}</strong> <span style={{ color:'#cbd5e1' }}>· {it.film_key}</span>
                                        <div style={{ fontSize:'10px', color:'#64748b', marginTop:'2px' }}>
                                          {it.n_readers} readers · votes {Object.entries(it.votes).map(([s,n]) => `${s}:${n}`).join('  ')}
                                        </div>
                                      </div>
                                      <div style={{ display:'flex', gap:'4px', flexWrap:'wrap' }}>
                                        {Object.keys(it.votes).sort().map(stage => (
                                          <button key={stage} onClick={() => resolveAdjudication(it.id, stage)} disabled={adjBusy}
                                                  style={{ fontSize:'11px', fontWeight:'700', padding:'3px 9px', border:'1px solid #cbd5e1', borderRadius:'6px', background:'#f8fafc', color:'#334155', cursor: adjBusy?'default':'pointer' }}>
                                            {stage}
                                          </button>
                                        ))}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                              {adjMsg && <div style={{ marginTop:'8px', fontSize:'11px', fontWeight:'700', color: adjMsg.type==='ok'?'#059669':'#dc2626' }}>{adjMsg.text}</div>}
                            </div>
                          )}
                        </div>

                        {/* Licensed TW3 tables — doctor enters her own reference values here (§18) */}
                        <details style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}
                                 onToggle={e => { if (e.target.open && !ltTables) loadLetterTables(); }}>
                          <summary style={{ cursor:'pointer', fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em', listStyle:'none' }}>
                            🔢 Licensed TW3 tables — enter once to turn scoring ON
                          </summary>
                          <div style={{ fontSize:'10px', color:'#94a3b8', margin:'8px 0 12px', lineHeight:'1.5' }}>
                            Enter the point values and score→age curves from your own licensed TW3 reference. Nothing is shipped or guessed. Scoring switches on only after a reference case from one of your reported films is reproduced (accuracy gate).
                          </div>
                          {ltStatus && (
                            <div style={{ marginBottom:'10px', fontSize:'11px', fontWeight:'700', color: ltStatus.scoring_ready ? '#059669' : '#b45309' }}>
                              {ltStatus.scoring_ready ? '✓ Scoring is ON — report fills with real numbers.'
                                : ltStatus.provenance_complete === false ? '○ Scoring OFF — document the licensed source (Provenance tab).'
                                : '○ Scoring OFF — table incomplete or reference not reproduced.'}
                            </div>
                          )}
                          {!ltTables ? (
                            <button onClick={loadLetterTables} disabled={ltBusy} style={lcBtn('#7c3aed', ltBusy)}>{ltBusy ? 'Loading…' : 'Open table editor'}</button>
                          ) : (
                            <div>
                              <div style={{ display:'flex', gap:'6px', flexWrap:'wrap', marginBottom:'10px' }}>
                                {[['rus','RUS points'],['carpal','Carpal points'],['tw20',"TWII'20 points"],['curves','Score→age curves'],['ref','Reference case'],['prov','Provenance']].map(([k,label]) => (
                                  <button key={k} onClick={() => setLtSection(k)} style={{ padding:'5px 10px', borderRadius:'8px', fontSize:'11px', fontWeight:'700', cursor:'pointer', border:'1px solid #ddd6fe', background: ltSection===k ? '#7c3aed' : 'white', color: ltSection===k ? 'white' : '#7c3aed' }}>{label}</button>
                                ))}
                                {ltSection !== 'ref' && (
                                  <span style={{ marginLeft:'auto', display:'flex', gap:'4px' }}>
                                    {['boys','girls'].map(s => (
                                      <button key={s} onClick={() => setLtSex(s)} style={{ padding:'5px 10px', borderRadius:'8px', fontSize:'11px', fontWeight:'700', cursor:'pointer', border:'1px solid #cbd5e1', background: ltSex===s ? '#334155' : 'white', color: ltSex===s ? 'white' : '#334155' }}>{s==='boys'?'Boys':'Girls'}</button>
                                    ))}
                                  </span>
                                )}
                              </div>

                              {(ltSection === 'rus' || ltSection === 'carpal' || ltSection === 'tw20') && (() => {
                                const group = ltSection === 'rus' ? 'rus_stage_to_score' : ltSection === 'carpal' ? 'carpal_stage_to_score' : 'tw20_stage_to_score';
                                const carpalRows = REPORT_CARPALS.map(n => [carpalCode(n), n]);
                                const rows = ltSection === 'carpal' ? carpalRows : ltSection === 'tw20' ? [...REPORT_RUS, ...carpalRows] : REPORT_RUS;
                                const cell = (bone, L) => ((ltTables[group][ltSex]||{})[bone]||{})[L];
                                return (
                                  <div style={{ overflowX:'auto' }}>
                                    <table style={{ borderCollapse:'collapse', fontSize:'11px' }}>
                                      <thead><tr><th style={{ padding:'3px 6px', textAlign:'left', color:'#64748b' }}>{ltSex} · bone</th>{LETTER_STAGES.map(L => <th key={L} style={{ padding:'3px 4px', color:'#64748b' }}>{L}</th>)}</tr></thead>
                                      <tbody>
                                        {rows.map(([code, label]) => (
                                          <tr key={code}>
                                            <td style={{ padding:'3px 6px', whiteSpace:'nowrap', color:'#334155' }}>{label}</td>
                                            {LETTER_STAGES.map(L => (
                                              <td key={L} style={{ padding:'1px' }}>
                                                <input type="number" value={cell(code, L) ?? ''} onChange={e => setLtPoint(group, ltSex, code, L, e.target.value)}
                                                       style={{ width:'42px', padding:'3px 2px', fontSize:'11px', textAlign:'center', border:'1px solid #e2e8f0', borderRadius:'4px' }} />
                                              </td>
                                            ))}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                    <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'6px' }}>Leave a cell blank if that letter is not defined for that bone. Enter both Boys and Girls.</div>
                                  </div>
                                );
                              })()}

                              {ltSection === 'curves' && (
                                <div style={{ display:'grid', gap:'12px', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))' }}>
                                  {[['rus_score_to_age','RUS'],['carpal_score_to_age','Carpal']].flatMap(([grp, gl]) =>
                                    ['twii','twiii'].map(cv => (
                                      <div key={grp+cv}>
                                        <label style={{ fontSize:'10px', fontWeight:'700', color:'#7c3aed', display:'block', marginBottom:'3px' }}>{gl} · {cv.toUpperCase()} · {ltSex}</label>
                                        <textarea value={curveToText((ltTables[grp][cv]||{})[ltSex])} onChange={e => setLtCurve(grp, cv, ltSex, e.target.value)}
                                                  placeholder={'score, age\n300, 8\n450, 10'} rows={4}
                                                  style={{ width:'100%', fontFamily:'ui-monospace, monospace', fontSize:'11px', padding:'6px', border:'1px solid #e2e8f0', borderRadius:'6px' }} />
                                      </div>
                                    ))
                                  )}
                                  <div>
                                    <label style={{ fontSize:'10px', fontWeight:'700', color:'#7c3aed', display:'block', marginBottom:'3px' }}>TWII'20 (20-bone) · {ltSex}</label>
                                    <textarea value={curveToText((ltTables.tw20_score_to_age||{})[ltSex])} onChange={e => setLtSexCurve('tw20_score_to_age', ltSex, e.target.value)}
                                              placeholder={'score, age\n300, 8\n450, 10'} rows={4}
                                              style={{ width:'100%', fontFamily:'ui-monospace, monospace', fontSize:'11px', padding:'6px', border:'1px solid #e2e8f0', borderRadius:'6px' }} />
                                  </div>
                                  <div style={{ gridColumn:'1/-1', fontSize:'10px', color:'#94a3b8' }}>One "score, age" pair per line (ascending score). ≥2 points per curve. Carpal / TWII'20 curves optional if you only report RUS.</div>
                                </div>
                              )}

                              {ltSection === 'prov' && (
                                <div style={{ display:'grid', gap:'8px', gridTemplateColumns:'repeat(auto-fit, minmax(180px, 1fr))' }}>
                                  {[['book_title','Book title *'],['edition','Edition / year *'],['isbn','ISBN'],['licensed_owner','Licensed owner *'],['pages','Pages'],['entered_by','Entered by *'],['verified_by','Verified by *'],['verification_date','Verification date *']].map(([k, label]) => (
                                    <div key={k}>
                                      <label style={{ fontSize:'10px', fontWeight:'700', color:'#64748b', display:'block', marginBottom:'2px' }}>{label}</label>
                                      <input type={k === 'verification_date' ? 'date' : 'text'} value={(ltTables.provenance || {})[k] || ''}
                                        onChange={e => setLtTables(t => ({ ...t, provenance: { ...(t.provenance || {}), [k]: e.target.value } }))}
                                        style={{ width:'100%', padding:'5px 7px', fontSize:'11px', border:'1px solid #e2e8f0', borderRadius:'6px' }} />
                                    </div>
                                  ))}
                                  <div style={{ gridColumn:'1/-1', fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>* required. Licensed TW3 values may not drive scoring without a documented, legally-owned source.{ltStatus && ltStatus.missing_provenance && ltStatus.missing_provenance.length > 0 ? ` Still missing: ${ltStatus.missing_provenance.join(', ')}.` : ''}</div>
                                </div>
                              )}

                              {ltSection === 'ref' && (() => {
                                const ref = (ltTables.reference_cases && ltTables.reference_cases[0]) || null;
                                const nRus = ref ? Object.keys(ref.rus_stages||{}).length : 0;
                                const nCar = ref ? Object.keys(ref.carpal_stages||{}).length : 0;
                                return (
                                  <div>
                                    <div style={{ fontSize:'11px', color:'#475569', marginBottom:'8px', lineHeight:'1.5' }}>Pick one of your own previously-reported films: grade its bones in the grid above, then capture them here and type the score/age you reported. Scoring turns on only when these values reproduce.</div>
                                    <button onClick={useGridAsReference} style={{ ...lcBtn('#0891b2', false), marginBottom:'8px' }}>Capture reference stages from grid</button>
                                    <div style={{ fontSize:'11px', color:'#475569', marginBottom:'8px' }}>Captured: {nRus}/13 RUS + {nCar}/7 carpal · sex {ref ? ref.sex : '—'}</div>
                                    <div style={{ display:'grid', gap:'8px', gridTemplateColumns:'repeat(auto-fit, minmax(150px, 1fr))' }}>
                                      <div><label style={{ fontSize:'10px', fontWeight:'700', color:'#64748b' }}>Reported RUS score</label>
                                        <input type="number" value={(ref && ref.expected && ref.expected.rus_score) ?? ''} onChange={e => setRefExpected('rus_score', e.target.value)} className="input-field" style={{ padding:'6px 8px', width:'100%' }} /></div>
                                      <div><label style={{ fontSize:'10px', fontWeight:'700', color:'#64748b' }}>Reported TWIII-RUS age (yr)</label>
                                        <input type="number" step="0.1" value={(ref && ref.expected && ref.expected.twiii_rus_age_years) ?? ''} onChange={e => setRefExpected('twiii_rus_age_years', e.target.value)} className="input-field" style={{ padding:'6px 8px', width:'100%' }} /></div>
                                    </div>
                                  </div>
                                );
                              })()}

                              <div style={{ marginTop:'12px', display:'flex', gap:'8px', alignItems:'center', flexWrap:'wrap' }}>
                                <button onClick={saveLetterTables} disabled={ltBusy} style={lcBtn('#7c3aed', ltBusy)}>{ltBusy ? 'Saving…' : 'Validate & save tables'}</button>
                                {ltMsg && <span style={{ fontSize:'11px', fontWeight:'700', color: ltMsg.type==='ok' ? '#059669' : '#dc2626' }}>{ltMsg.text}</span>}
                              </div>
                            </div>
                          )}
                        </details>

                        {/* Bone age used for prediction */}
                        <div className="split-grid" style={{ marginTop:'12px' }}>
                          <InputWithUnit
                            label="TW3 Bone Age (used for prediction)"
                            value={boneAge}
                            onChange={e => { setBoneAge(e.target.value === "" ? "" : parseFloat(e.target.value)); setBoneAgeSource('manual'); }}
                            placeholder="e.g. 10.5"
                            step="0.1"
                            unit="yrs"
                            accent="#7c3aed"
                          />
                          <div>
                            <label className="field-label">Source</label>
                            <div style={{ padding:'10px 12px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'9px', fontSize:'12px', fontWeight:'700', color:'#475569' }}>
                              {boneAge === "" ? 'Not set' : boneAgeSource === 'rus' ? 'From RUS staging' : 'Manual entry'}
                            </div>
                          </div>
                        </div>

                        {/* Parental heights */}
                        <div className="split-grid" style={{ marginTop:'12px' }}>
                          <InputWithUnit label="Father's Height" value={fatherHeight} onChange={e => setFatherHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm (optional)" unit="cm" />
                          <InputWithUnit label="Mother's Height" value={motherHeight} onChange={e => setMotherHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm (optional)" unit="cm" />
                        </div>

                        <div style={{ marginTop:'12px', background:'#f8fafc', border:'1px dashed #cbd5e1', borderRadius:'10px', padding:'12px 14px', fontSize:'11px', color:'#64748b', lineHeight:'1.6' }}>
                          The TW3 bone age is derived only from the 20 doctor-confirmed bone stages above
                          (RUS + carpal) via the licensed TW3 tables — never from the whole-image AI, which
                          is a rough screening triage only. Automatic per-bone staging from the X-ray is not
                          yet available (it needs stage-labelled training data the clinic is now collecting).
                        </div>

                        {!boneMetrics ? (
                          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', flex:1, gap:'12px', padding:'36px 0', textAlign:'center' }}>
                            <div style={{ width:'52px', height:'52px', borderRadius:'50%', background:'#f5f3ff', display:'flex', alignItems:'center', justifyContent:'center' }}>
                              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round"><path d="M18 8a6 6 0 0 0-9.33-5"/><path d="M6 16a6 6 0 0 0 9.33 5"/><line x1="12" y1="2" x2="12" y2="22"/></svg>
                            </div>
                            <div style={{ fontSize:'13px', fontWeight:'700', color:'#64748b' }}>Set a TW3 bone age or both parents' heights</div>
                            <div style={{ fontSize:'12px', color:'#94a3b8', maxWidth:'320px', lineHeight:'1.6' }}>Stage the left hand–wrist film above (TW3 RUS), or enter a TW3 bone age manually. Add parents' heights for the genetic target. Current height is taken from Demographics.</div>
                          </div>
                        ) : (
                          <div>
                            {/* ── Mid-parental genetic TARGET (open Tanner method; the quantity we actually have) ── */}
                            {boneMetrics.mph !== null ? (
                              <div className="hero-result" style={{ background:'linear-gradient(135deg,#f5f3ff,#eef2ff)', border:'1.5px solid #ddd6fe', borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
                                <div>
                                  <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#7c3aed', marginBottom:'8px' }}>Mid-Parental Target Height</div>
                                  <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
                                    <span className="hero-value" style={{ fontWeight:'900', color:'#5b21b6', lineHeight:1 }}>{boneMetrics.mph.toFixed(1)}</span>
                                    <span style={{ fontSize:'13px', color:'#7c3aed', fontWeight:'600' }}>cm</span>
                                  </div>
                                  <div style={{ fontSize:'11px', color:'#8b5cf6', marginTop:'4px' }}>
                                    ≈ {Math.floor(boneMetrics.mph/30.48)}′{Math.round((boneMetrics.mph/2.54)%12)}″ · genetic target from parents (Tanner) · range {boneMetrics.mphLow.toFixed(0)}–{boneMetrics.mphHigh.toFixed(0)} cm
                                  </div>
                                </div>
                                <div style={{ textAlign:'right' }}>
                                  <StatusBadge text="Genetic target — not a prediction" variant="info" />
                                  {boneMetrics.mphPct !== null && <div style={{ marginTop:'10px', fontSize:'12px', color:'#7c3aed', fontWeight:'700' }}>{boneMetrics.mphPct.toFixed(1)}th centile (Khadilkar)</div>}
                                </div>
                              </div>
                            ) : (
                              <div style={{ marginTop:'16px', background:'#f8fafc', border:'1px dashed #cbd5e1', borderRadius:'12px', padding:'16px', fontSize:'13px', fontWeight:'700', color:'#7c3aed', lineHeight:'1.6' }}>
                                Add both parents' heights for the mid-parental (genetic target) height and its ±8.5 cm range.
                              </div>
                            )}

                            {/* target channel bar — marker = skeletal prediction if calibrated, else the target itself */}
                            {boneMetrics.mph !== null && (() => {
                              const lo = boneMetrics.mphLow, hi = boneMetrics.mphHigh, span = hi - lo;
                              const marker = boneMetrics.predictedPah !== null ? boneMetrics.predictedPah : boneMetrics.mph;
                              const pos = Math.min(Math.max(((marker - lo) / span) * 100, 1), 99);
                              return (
                                <div style={{ marginTop:'14px', background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e2e8f0' }}>
                                  <div style={{ position:'relative', height:'10px', borderRadius:'99px', background:'#e9d5ff' }}>
                                    <div style={{ position:'absolute', top:'-3px', left:`${pos}%`, width:'16px', height:'16px', borderRadius:'50%', background:'white', border:'3px solid #7c3aed', transform:'translateX(-50%)', boxShadow:'0 1px 4px rgba(0,0,0,0.2)' }}></div>
                                  </div>
                                  <div style={{ display:'flex', justifyContent:'space-between', marginTop:'8px', fontSize:'10px', fontWeight:'700', color:'#94a3b8' }}>
                                    <span>{lo.toFixed(0)} cm</span>
                                    <span style={{ color:'#7c3aed' }}>target range ±8.5 cm{boneMetrics.predictedPah !== null ? ' · marker = skeletal prediction' : ''}</span>
                                    <span>{hi.toFixed(0)} cm</span>
                                  </div>
                                </div>
                              );
                            })()}

                            {/* ── Skeletal PREDICTED adult height — child-specific, calibration-gated, never the target ── */}
                            <div style={{ marginTop:'16px', background: (boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null) ? '#f8fafc' : '#fffbeb', border: (boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null) ? '1px solid #e2e8f0' : '1px solid #fde68a', borderRadius:'12px', padding:'16px' }}>
                              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline' }}>
                                <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b' }}>Predicted Adult Height · TW3 skeletal</span>
                                {(boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null) && (
                                  <div><span style={{ fontSize:'24px', fontWeight:'900', color:'#1e293b' }}>{boneMetrics.predictedPah.toFixed(1)}</span><span style={{ fontSize:'11px', color:'#94a3b8', marginLeft:'5px' }}>cm</span></div>
                                )}
                              </div>
                              {(boneMetrics.skeletalCalibrated && boneMetrics.predictedPah !== null) ? (
                                <>
                                  <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>
                                    {boneMetrics.predPct !== null ? `${boneMetrics.predPct.toFixed(1)}th centile · ` : ''}{boneMetrics.pct.toFixed(1)}% of adult height attained at bone age {boneMetrics.ba.toFixed(1)} yr{boneMetrics.remaining !== null ? ` · ${boneMetrics.remaining.toFixed(1)} cm left to grow` : ''}
                                  </div>
                                  {boneMetrics.predVsTarget !== null && (
                                    <div style={{ fontSize:'11px', fontWeight:'700', marginTop:'8px', color: boneMetrics.withinTarget ? '#059669' : '#d97706' }}>
                                      {boneMetrics.predVsTarget >= 0 ? '+' : ''}{boneMetrics.predVsTarget.toFixed(1)} cm vs genetic target · {boneMetrics.withinTarget ? 'within' : 'outside'} mid-parental channel
                                    </div>
                                  )}
                                </>
                              ) : (
                                <div style={{ fontSize:'11px', color:'#92400e', lineHeight:'1.7', marginTop:'4px' }}>
                                  <strong>Calibration required — no value shown by design.</strong> A skeletal prediction needs the licensed TW3 “% of adult height attained by bone age” reference (or another validated method) in <code>TW3_CONFIG.pctAdultHeight</code>. The mid-parental target above is a <em>genetic target</em>, not a prediction, and is never substituted here.
                                </div>
                              )}
                            </div>

                            {/* Bone age vs chronological + target on the population reference */}
                            <div className="secondary-grid" style={{ marginTop:'16px' }}>
                              <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e8ecf0' }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'6px' }}>Bone Age vs Chronological</div>
                                {boneMetrics.hasBone ? (
                                  <>
                                    <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                                      <span style={{ fontSize:'26px', fontWeight:'900', color: Math.abs(boneMetrics.diff) > 2 ? '#d97706' : '#1e293b', lineHeight:1 }}>{boneMetrics.diff >= 0 ? '+' : ''}{boneMetrics.diff.toFixed(1)}</span>
                                      <span style={{ fontSize:'12px', color:'#94a3b8' }}>yr</span>
                                    </div>
                                    <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>{boneMetrics.diff > 1 ? 'Advanced maturation' : boneMetrics.diff < -1 ? 'Delayed maturation' : 'Concordant with age'}</div>
                                  </>
                                ) : <div style={{ fontSize:'12px', color:'#94a3b8' }}>No bone age set</div>}
                              </div>
                              <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e8ecf0' }}>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'6px' }}>Genetic Target on Khadilkar</div>
                                {(boneMetrics.mph !== null && boneMetrics.mphZ !== null) ? (
                                  <>
                                    <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                                      <span style={{ fontSize:'26px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{boneMetrics.mphZ >= 0 ? '+' : ''}{boneMetrics.mphZ.toFixed(2)}</span>
                                      <span style={{ fontSize:'12px', color:'#94a3b8' }}>SDS</span>
                                    </div>
                                    <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>{boneMetrics.mphPct.toFixed(1)}th percentile · target vs {evalGender === 'boys' ? 'male' : 'female'} adult ({boneMetrics.adult[0]} cm)</div>
                                  </>
                                ) : <div style={{ fontSize:'12px', color:'#94a3b8' }}>Add parents' heights for target SDS</div>}
                              </div>
                            </div>

                            {/* Detail rows */}
                            <MetricRow label="Current Height" value={evalHeight.toFixed(1)} unit="cm" sub={`Chronological age ${evalAge.toFixed(1)} yr`} />
                          </div>
                        )}

                        {/* Method + population caveats — consolidated into one
                            collapsed accordion so they no longer push results down. */}
                        <details className="clinical-notes">
                          <summary>Clinical notes · TW3 workflow &amp; Indian-population context</summary>
                          <div className="clinical-notes-body">
                            <div style={{ fontSize:'12px', color:'#4338ca', lineHeight:'1.7', marginBottom:'10px' }}>
                              <strong>TW3 workflow:</strong> use a <strong>left</strong> hand–wrist PA radiograph. Stage all <strong>20 bones</strong> — 13 RUS (radius, ulna, metacarpals 1·3·5, proximal/middle/distal phalanges 1·3·5) and 7 carpals — with the original TW3 letters A→I. RUS and carpal maturity scores convert to <strong>separate</strong> bone ages (never averaged). Two independent reads within ±0.5 yr is acceptable. Bayley–Pinneau and Greulich–Pyle are <strong>not</strong> used.
                            </div>
                            <div style={{ fontSize:'12px', color:'#92400e', lineHeight:'1.7' }}>
                              <strong>Indian-population note:</strong> No India-specific TW3 reference exists. In validation on Indian children, <strong>TW3 was the most accurate</strong> of the common methods (Shah et al., 2021, 851 children), which is why it is used here. However, skeletal maturation in Indian children differs from Western standards: boys run roughly <strong>~6 months behind</strong> and girls vary (delayed pre-puberty, sometimes advanced in early puberty) (Patel 2012; Khadilkar 2022). Scoring uses <strong>TW3-C (Chinese)</strong> tables as the closest freely-available reference — <strong>no numeric correction is applied automatically</strong>. Interpret borderline results, and <strong>pubertal boys especially</strong>, with clinical correlation.
                            </div>
                          </div>
                        </details>

                        <div style={{ marginTop:'auto', paddingTop:'18px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
                          TW3: Tanner, Healy, Goldstein &amp; Cameron (2001) — licensed reference values required for scoring &amp; skeletal height prediction. Mid-parental target: Tanner (open). Adult-height SDS/centile vs Khadilkar (WHO–IAP) 18-yr reference. Clinician must verify — not a diagnostic device.
                        </div>
                        </details>
                      </div>
                    )}

                    {/* ══ RENAL TAB ══ */}
                    {activeTab === 'renal' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
                        <SectionHeader
                          title="Renal Workspace · eGFR"
                          subtitle={`Multi-equation clearance monitoring · ${renalMetrics.formulaName}`}
                          badge={hasManualRenal ? `Stage ${renalMetrics.ckdStage}` : null}
                          badgeVariant={hasManualRenal ? renalMetrics.stageVariant : 'info'}
                        />

                        {!hasManualRenal ? (
                          <EmptyState title="Enter serum creatinine"
                            hint="Serum creatinine — plus age, sex and height — is required to estimate GFR. No value is shown until it is entered." />
                        ) : (<React.Fragment>
                        {/* eGFR hero */}
                        <div className="hero-result" style={{ ...heroTone(renalMetrics.stageVariant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
                          <div>
                            <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>Estimated GFR</div>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
                              <span className="hero-value" style={{ fontWeight:'900', color: renalMetrics.stageVariant === 'high' ? '#b91c1c' : renalMetrics.stageVariant === 'mid' ? '#b45309' : '#15803d', lineHeight:1 }}>{renalMetrics.egfr.toFixed(1)}</span>
                              <span style={{ fontSize:'13px', color:'#6366f1', fontWeight:'600' }}>mL/min/1.73 m²</span>
                            </div>
                            <div style={{ fontSize:'11px', color:'#818cf8', marginTop:'4px' }}>via {renalMetrics.formulaName}</div>
                          </div>
                          <div style={{ textAlign:'right' }}>
                            <StatusBadge text={`Stage ${renalMetrics.ckdStage} · ${renalMetrics.ckdStageDesc}`} variant={renalMetrics.stageVariant} />
                            <div style={{ marginTop:'10px', fontSize:'11px', color:'#6366f1', fontWeight:'600' }}>
                              {renalMetrics.isPediatric ? '▸ Pediatric Mode' : '▸ Adult Mode'}
                            </div>
                          </div>
                        </div>

                        {/* CKD Stage chips */}
                        <div style={{ marginTop:'16px' }}>
                          <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'8px' }}>KDIGO CKD Stage Map</div>
                          <div className="ckd-stage">
                            {[
                              ['G1','≥ 90','Normal'],
                              ['G2','60–89','Mild ↓'],
                              ['G3','30–59','Mod ↓'],
                              ['G4','15–29','Severe ↓'],
                              ['G5','< 15','Failure'],
                            ].map(([stage, range, desc]) => (
                              <div key={stage} className={`ckd-chip ${renalMetrics.ckdStage === stage ? `ckd-active-${stage.toLowerCase()}` : 'ckd-inactive'}`}>
                                <div style={{ fontWeight:'900', fontSize:'11px' }}>{stage}</div>
                                <div style={{ fontSize:'9px', marginTop:'2px', fontWeight:'600', opacity:0.85 }}>{range}</div>
                                <div style={{ fontSize:'9px', marginTop:'1px', opacity:0.7 }}>{desc}</div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Alternate equations */}
                        {!renalMetrics.isPediatric && (
                          <div className="secondary-grid" style={{ marginTop:'16px' }}>
                            <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px', border:'1px solid #e2e8f0' }}>
                              <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:'6px' }}>Cockcroft-Gault CrCl</div>
                              <div style={{ fontSize:'22px', fontWeight:'900', color:'#334155' }}>{renalMetrics.cg ? renalMetrics.cg.toFixed(1) : '—'}</div>
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>mL/min</div>
                            </div>
                            <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px', border:'1px solid #e2e8f0' }}>
                              <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:'6px' }}>MDRD Clearance</div>
                              <div style={{ fontSize:'22px', fontWeight:'900', color:'#334155' }}>{renalMetrics.mdrd ? renalMetrics.mdrd.toFixed(1) : '—'}</div>
                              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>mL/min/1.73 m²</div>
                            </div>
                          </div>
                        )}

                        </React.Fragment>)}

                        <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
                          KDIGO G1 ≥ 90 · G2 60–89 · G3 30–59 · G4 15–29 · G5 &lt; 15 mL/min/1.73 m²
                        </div>
                      </div>
                    )}

                    {/* ══ LIVER TAB ══ */}
                    {activeTab === 'liver' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
                        <SectionHeader
                          title="Liver Fibrosis · FIB-4 Index"
                          subtitle="Non-invasive hepatic fibrosis staging — Age · AST · ALT · Platelets"
                          badge={hasManualLiver ? liverMetrics.interpretation : null}
                          badgeVariant={hasManualLiver ? liverMetrics.variant : 'info'}
                        />

                        {!hasManualLiver ? (
                          <EmptyState title="Enter AST, ALT & platelets"
                            hint="FIB-4 needs AST, ALT and platelet count (plus age). No score is shown until all three are entered." />
                        ) : (<React.Fragment>
                        {/* FIB-4 hero */}
                        <div className="hero-result" style={{ ...heroTone(liverMetrics.variant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
                          <div>
                            <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>FIB-4 Score</div>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
                              <span className="hero-value" style={{ fontWeight:'900', color: liverMetrics.variant === 'high' ? '#b91c1c' : liverMetrics.variant === 'mid' ? '#b45309' : '#15803d', lineHeight:1 }}>{liverMetrics.fib4.toFixed(2)}</span>
                              <span style={{ fontSize:'13px', color:'#64748b', fontWeight:'600' }}>index</span>
                            </div>
                            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>Formula: (Age × AST) / (Platelets × √ALT)</div>
                          </div>
                          <div>
                            <StatusBadge text={liverMetrics.interpretation} variant={liverMetrics.variant} />
                            <div style={{ fontSize:'12px', color:'#64748b', marginTop:'10px', maxWidth:'200px', lineHeight:'1.5' }}>{liverMetrics.details}</div>
                          </div>
                        </div>

                        {/* FIB-4 scale bar */}
                        <div style={{ marginTop:'20px', background:'#f8fafc', borderRadius:'12px', padding:'16px', border:'1px solid #e2e8f0' }}>
                          <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'12px' }}>Risk Scale</div>
                          <div style={{ position:'relative', height:'10px', borderRadius:'99px', background:'linear-gradient(to right, #22c55e 0%, #22c55e 48%, #eab308 48%, #eab308 74%, #ef4444 74%, #ef4444 100%)' }}>
                            {/* marker at FIB-4 value (max ~5) */}
                            <div style={{ position:'absolute', top:'-4px', left:`${Math.min(Math.max((liverMetrics.fib4/5)*100,1),99)}%`, width:'18px', height:'18px', borderRadius:'50%', background:'white', border:'3px solid #334155', transform:'translateX(-50%)', boxShadow:'0 1px 4px rgba(0,0,0,0.2)' }}></div>
                          </div>
                          <div style={{ display:'flex', justifyContent:'space-between', marginTop:'8px', fontSize:'10px', fontWeight:'700', color:'#94a3b8' }}>
                            <span>0</span>
                            <span style={{ color:'#16a34a' }}>Low &lt; 1.30</span>
                            <span style={{ color:'#d97706' }}>Indeterminate 1.30–2.67</span>
                            <span style={{ color:'#dc2626' }}>High &gt; 2.67</span>
                          </div>
                        </div>

                        {evalAge < 18 && (
                          <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
                            ⚠ FIB-4 is not validated in pediatric cohorts (age &lt; 18). Interpret with caution.
                          </div>
                        )}

                        </React.Fragment>)}

                        <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
                          FIB-4 ranges — Low: &lt; 1.30 · Indeterminate: 1.30–2.67 · High: ≥ 2.67
                          {evalAge > 65 ? '  (Age > 65 — indeterminate threshold adjusted to 2.0)' : ''}
                        </div>
                      </div>
                    )}

                    {/* ══ FRAX TAB ══ */}
                    {activeTab === 'frax' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
                        <SectionHeader
                          title="FRAX Plus · 10-Year Fracture Risk"
                          subtitle="India (Asian) · No femoral neck BMD · Sheffield intervention thresholds"
                          badge={hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'High Risk' : 'Low Risk') : null}
                          badgeVariant={hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'high' : 'low') : 'info'}
                        />

                        {!hasManualFrax ? (
                          <EmptyState title="Enter age, sex, height & weight"
                            hint="FRAX estimates 10-year fracture risk from demographics plus the risk factors on the left. No probability is shown until the core measurements are entered." />
                        ) : (<React.Fragment>
                        {evalAge < 40 && (
                          <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
                            ⚠ FRAX is calibrated for ages 40–90. Current age adjusted to the age-40 baseline model.
                          </div>
                        )}

                        {/* MOF card */}
                        <div style={{ ...heroTone(fraxMetrics.isHighMof ? 'high' : 'low'), borderRadius:'16px', padding:'22px', marginTop:'16px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
                            <div>
                              <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>Major Osteoporotic Fracture</div>
                              <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                                <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: fraxMetrics.isHighMof ? '#dc2626' : '#16a34a', lineHeight:1 }}>{fraxMetrics.mofProb.toFixed(1)}</span>
                                <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
                              </div>
                              <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability — spine, hip, forearm, shoulder</div>
                            </div>
                            <StatusBadge text={fraxMetrics.isHighMof ? 'High Risk ≥ 20%' : 'Low Risk < 20%'} variant={fraxMetrics.isHighMof ? 'high' : 'low'} />
                          </div>
                          <ProbBar prob={fraxMetrics.mofProb} maxProb={40} threshold={20} />
                        </div>

                        {/* HF card */}
                        <div style={{ ...heroTone(fraxMetrics.isHighHf ? 'high' : 'low'), borderRadius:'16px', padding:'22px', marginTop:'12px' }}>
                          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
                            <div>
                              <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>Hip Fracture</div>
                              <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                                <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: fraxMetrics.isHighHf ? '#dc2626' : '#16a34a', lineHeight:1 }}>{fraxMetrics.hfProb.toFixed(1)}</span>
                                <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
                              </div>
                              <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability of hip fracture</div>
                            </div>
                            <StatusBadge text={fraxMetrics.isHighHf ? 'High Risk ≥ 3%' : 'Low Risk < 3%'} variant={fraxMetrics.isHighHf ? 'high' : 'low'} />
                          </div>
                          <ProbBar prob={fraxMetrics.hfProb} maxProb={15} threshold={3} />
                        </div>

                        </React.Fragment>)}

                        <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
                          Sheffield thresholds: Treatment recommended when MOF ≥ 20% or Hip Fracture ≥ 3% (10-year absolute risk).
                        </div>
                      </div>
                    )}

                    {/* ══ QRISK3 CVD TAB ══ */}
                    {activeTab === 'qrisk' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
                        <SectionHeader
                          title="QRISK3 · 10-Year Cardiovascular Risk"
                          subtitle="Hippisley-Cox 2017 (ClinRisk open source) · South-Asian ethnicity aware"
                          badge={qriskMetrics.risk !== null ? qriskMetrics.band : "Age 25–84"}
                          badgeVariant={qriskMetrics.risk !== null ? qriskMetrics.variant : 'neutral'}
                        />

                        {!qriskMetrics.inAgeRange && (
                          <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
                            ⚠ QRISK3 is validated for ages 25–84. Set the patient's age in that range (Demographics) to compute risk.
                          </div>
                        )}

                        {/* Cardio inputs */}
                        <div style={{ marginTop:'16px', display:'flex', flexDirection:'column', gap:'12px' }}>
                          <div>
                            <label className="field-label">Ethnicity</label>
                            <select value={ethnicity} onChange={e => setEthnicity(parseInt(e.target.value))} className="input-field" style={{ width:'100%' }}>
                              <option value={1}>White / not stated</option>
                              <option value={2}>Indian</option>
                              <option value={3}>Pakistani</option>
                              <option value={4}>Bangladeshi</option>
                              <option value={5}>Other Asian</option>
                              <option value={6}>Black Caribbean</option>
                              <option value={7}>Black African</option>
                              <option value={8}>Chinese</option>
                              <option value={9}>Other</option>
                            </select>
                          </div>
                          <div className="split-grid">
                            <div>
                              <label className="field-label">Smoking</label>
                              <select value={smokeCat} onChange={e => setSmokeCat(parseInt(e.target.value))} className="input-field" style={{ width:'100%' }}>
                                <option value={0}>Non-smoker</option>
                                <option value={1}>Ex-smoker</option>
                                <option value={2}>Light (&lt; 10/day)</option>
                                <option value={3}>Moderate (10–19/day)</option>
                                <option value={4}>Heavy (20+/day)</option>
                              </select>
                            </div>
                            <div>
                              <label className="field-label">Diabetes</label>
                              <select value={diabetes} onChange={e => setDiabetes(parseInt(e.target.value))} className="input-field" style={{ width:'100%' }}>
                                <option value={0}>None</option>
                                <option value={1}>Type 1</option>
                                <option value={2}>Type 2</option>
                              </select>
                            </div>
                          </div>
                          <div className="split-grid">
                            <InputWithUnit label="Total : HDL Cholesterol ratio" value={cholRatio} onChange={e => setCholRatio(e.target.value)} placeholder="e.g. 4.0" step="0.1" unit="ratio" />
                            <InputWithUnit label="SBP variability (SD, optional)" value={sbpSD} onChange={e => setSbpSD(e.target.value)} placeholder="mmHg SD" step="0.1" unit="SD" />
                          </div>
                          <div style={{ fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>
                            Uses BMI (from height/weight) and systolic BP from the left panel. Blank cholesterol ratio / SBP-SD contribute neutrally (QRISK3 convention). Townsend deprivation is set to 0 (UK-only index).
                          </div>
                          <div style={{ background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'6px 14px' }}>
                            <FraxToggleRow label="Atrial fibrillation" value={qAF} setter={setQAF} />
                            <FraxToggleRow label="On BP treatment" value={qTreatedHtn} setter={setQTreatedHtn} />
                            <FraxToggleRow label="CKD stage 3–5" value={qCKD} setter={setQCKD} />
                            <FraxToggleRow label="Rheumatoid arthritis" value={qRA} setter={setQRA} />
                            <FraxToggleRow label="Migraine" value={qMigraine} setter={setQMigraine} />
                            <FraxToggleRow label="SLE (lupus)" value={qSLE} setter={setQSLE} />
                            <FraxToggleRow label="Severe mental illness" value={qSMI} setter={setQSMI} />
                            <FraxToggleRow label="Atypical antipsychotics" value={qAtypAntipsy} setter={setQAtypAntipsy} />
                            <FraxToggleRow label="Regular corticosteroids" value={qCortico} setter={setQCortico} />
                            {evalGender === 'boys' && <FraxToggleRow label="Erectile dysfunction" value={qED} setter={setQED} />}
                            <FraxToggleRow label="Family history of CVD" value={qFhCvd} setter={setQFhCvd} />
                          </div>
                        </div>

                        {/* Risk hero */}
                        {qriskMetrics.risk !== null && (
                          <div style={{ ...heroTone(qriskMetrics.variant), borderRadius:'16px', padding:'22px', marginTop:'16px' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
                              <div>
                                <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>10-Year CVD Risk</div>
                                <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                                  <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: qriskMetrics.variant === 'high' ? '#dc2626' : qriskMetrics.variant === 'mid' ? '#d97706' : '#16a34a', lineHeight:1 }}>{qriskMetrics.risk.toFixed(1)}</span>
                                  <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
                                </div>
                                {qriskMetrics.typical !== null && <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>Healthy baseline (same age/sex/ethnicity): {qriskMetrics.typical.toFixed(1)}%</div>}
                              </div>
                              <StatusBadge text={qriskMetrics.band} variant={qriskMetrics.variant} />
                            </div>
                            <ProbBar prob={qriskMetrics.risk} maxProb={40} threshold={10} />
                          </div>
                        )}

                        {/* Imputed-input disclosure — never a precise-looking score from incomplete data (audit F-3) */}
                        {qriskMetrics.risk !== null && (() => {
                          const imp = [];
                          if (qriskMetrics.missingRatio) imp.push('cholesterol ratio');
                          if (systolic === '') imp.push('systolic BP');
                          if (sbpSD === '') imp.push('SBP variability (SD)');
                          return imp.length ? (
                            <div style={{ marginTop:'10px', fontSize:'10.5px', color:'#92400e', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'7px 10px', lineHeight:'1.5' }}>
                              ⚠ Estimated with defaulted inputs: <strong>{imp.join(', ')}</strong>. Enter these for a patient-specific score.
                            </div>
                          ) : null;
                        })()}

                        {/* Eligibility gate — QRISK3 is validated only for adults 25–84 (audit F-3) */}
                        {qriskMetrics.risk === null && (
                          <div style={{ marginTop:'16px', background:'#fef2f2', border:'1.5px solid #fecaca', borderRadius:'12px', padding:'14px 16px' }}>
                            <div style={{ fontSize:'12px', fontWeight:'800', color:'#991b1b' }}>QRISK3 not applicable</div>
                            <div style={{ fontSize:'11px', color:'#b91c1c', marginTop:'4px', lineHeight:'1.5' }}>
                              {!qriskMetrics.inAgeRange ? 'QRISK3 is validated only for adults aged 25–84. This patient is outside that range — no score is shown.' : 'Enter height and weight (BMI) to compute the score.'}
                            </div>
                          </div>
                        )}

                        <div style={{ marginTop:'16px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'10px', padding:'12px 14px', fontSize:'11px', color:'#4338ca', lineHeight:'1.7' }}>
                          <strong>India note:</strong> QRISK3 is derived on a UK cohort. Its Indian/South-Asian ethnicity term raises risk relative to White, but studies suggest it may still under-estimate true risk in Indians. Treat ≥ 10% as the usual statin-consideration threshold, and interpret alongside the <strong>Lipid Association of India</strong> risk stratification and ICMR guidance. QRISK3 does not apply to established CVD, familial hypercholesterolaemia, or type-appropriate secondary prevention.
                        </div>

                        <div style={{ marginTop:'auto', paddingTop:'18px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
                          QRISK3-2017 · Hippisley-Cox J et al., BMJ 2017;357:j2099 · ClinRisk open-source coefficients (GNU LGPL), verified against the CRAN QRISK3 reference. Clinician must verify — decision support only, not a diagnostic device.
                        </div>
                      </div>
                    )}

                    {/* ══ TIMELINE TAB ══ */}
                    {activeTab === 'timeline' && (
                      <div style={{ flex:1, display:'flex', flexDirection:'column', gap:'16px' }}>
                        <div className="timeline-header">
                          <div>
                            <h3 style={{ fontSize:'13px', fontWeight:'800', color:'#334155' }}>CKD Progression Ledger</h3>
                            <p style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>Session snapshots — chronicity assessment over ≥ 90 days</p>
                          </div>
                          <div className="timeline-actions">
                            <button onClick={logCurrentData} style={{ padding:'7px 16px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'12px', fontWeight:'700', cursor:'pointer', boxShadow:'0 1px 4px rgba(79,70,229,0.3)', transition:'background 0.15s' }}
                              onMouseEnter={e=>e.target.style.background='#4338ca'} onMouseLeave={e=>e.target.style.background='#4f46e5'}>
                              + Log Snapshot
                            </button>
                            {timeline.length > 0 && (
                              <button onClick={() => { if (window.confirm('Clear all logged snapshots from the ledger?')) setTimeline([]); }} style={{ padding:'7px 14px', background:'white', color:'#64748b', border:'1.5px solid #e2e8f0', borderRadius:'9px', fontSize:'12px', fontWeight:'600', cursor:'pointer', transition:'all 0.15s' }}
                                onMouseEnter={e=>e.target.style.background='#f8fafc'} onMouseLeave={e=>e.target.style.background='white'}>
                                Reset
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Chronicity status */}
                        <div style={{ padding:'14px 16px', borderRadius:'12px', fontSize:'12px', lineHeight:'1.6' }} className={chronicityStatus.bgClass}>
                          <span style={{ fontWeight:'800', fontSize:'10px', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:'3px' }}>Chronicity Assessment</span>
                          {chronicityStatus.status}
                        </div>

                        {/* GFR sparkline */}
                        {timeline.length > 0 && (
                          <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'16px', border:'1px solid #e2e8f0' }}>
                            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'10px' }}>eGFR Timeline</div>
                            <svg width="100%" height="100" viewBox="0 0 500 100" preserveAspectRatio="none" style={{ borderRadius:'8px', background:'white', border:'1px solid #f1f5f9' }}>
                              <line x1="0" y1="22" x2="500" y2="22" stroke="#f1f5f9" strokeWidth="1.5"/>
                              <line x1="0" y1="50" x2="500" y2="50" stroke="#f1f5f9" strokeWidth="1.5"/>
                              <line x1="0" y1="78" x2="500" y2="78" stroke="#f1f5f9" strokeWidth="1.5"/>
                              {(() => {
                                const sorted = [...timeline].sort((a,b) => new Date(a.date)-new Date(b.date));
                                const pts = sorted.map((e,i) => ({
                                  x: sorted.length > 1 ? (i/(sorted.length-1))*440+30 : 250,
                                  y: 90 - ((Math.min(e.egfr,150)/150)*70),
                                  e
                                }));
                                return (
                                  <g>
                                    {pts.length > 1 && <polyline fill="none" stroke="#4f46e5" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={pts.map(p=>`${p.x},${p.y}`).join(' ')} />}
                                    {pts.map((p,i) => (
                                      <g key={p.e.id}>
                                        <circle cx={p.x} cy={p.y} r="4" fill="#4f46e5" />
                                        <text x={p.x} y={p.y-9} textAnchor="middle" fill="#4338ca" fontSize="9" fontWeight="bold">{p.e.egfr}</text>
                                        <text x={p.x} y="96" textAnchor="middle" fill="#94a3b8" fontSize="8">{p.e.date.slice(5)}</text>
                                      </g>
                                    ))}
                                  </g>
                                );
                              })()}
                            </svg>
                          </div>
                        )}

                        {/* Table */}
                        {timeline.length === 0 ? (
                          <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'40px 0', gap:'12px', textAlign:'center' }}>
                            <div style={{ width:'52px', height:'52px', borderRadius:'50%', background:'#f1f5f9', display:'flex', alignItems:'center', justifyContent:'center' }}>
                              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
                            </div>
                            <div style={{ fontSize:'13px', fontWeight:'700', color:'#64748b' }}>No snapshots logged yet</div>
                            <div style={{ fontSize:'12px', color:'#94a3b8' }}>Enter patient data and click "Log Snapshot" to begin tracking.</div>
                          </div>
                        ) : (
                          <div style={{ overflowX:'auto', borderRadius:'12px', border:'1px solid #e2e8f0' }} className="custom-scrollbar">
                            <table style={{ width:'100%', borderCollapse:'collapse', minWidth:'580px', fontSize:'12px' }}>
                              <thead>
                                <tr style={{ background:'#f8fafc', borderBottom:'1px solid #e2e8f0' }}>
                                  {['Date','Age','Ht / Wt','SCr','eGFR','ACR','FIB-4'].map(h => (
                                    <th key={h} style={{ padding:'10px 12px', textAlign:'left', fontWeight:'800', color:'#64748b', fontSize:'10px', textTransform:'uppercase', letterSpacing:'0.05em', whiteSpace:'nowrap' }}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {timeline.map((item, idx) => (
                                  <tr key={item.id} style={{ borderBottom:'1px solid #f1f5f9', background: idx % 2 === 0 ? 'white' : '#fafbfc' }}>
                                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#1e293b' }}>{item.date}</td>
                                    <td style={{ padding:'10px 12px', color:'#475569' }}>{item.age.toFixed(1)} y</td>
                                    <td style={{ padding:'10px 12px', color:'#64748b' }}>{item.height} / {item.weight}</td>
                                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#475569' }}>{item.creatinine}</td>
                                    <td style={{ padding:'10px 12px', fontWeight:'800', color:'#4f46e5' }}>{item.egfr}</td>
                                    <td style={{ padding:'10px 12px' }}>
                                      <span style={{ padding:'2px 8px', borderRadius:'99px', fontSize:'10px', fontWeight:'700', background:'#eef2ff', color:'#4338ca', border:'1px solid #c7d2fe' }}>{item.albuminuria}</span>
                                    </td>
                                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#059669' }}>{item.fib4 !== null ? item.fib4 : '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}

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
                        {height !== "" && weight !== "" ? (
                          <>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                              <span style={{ fontSize:'28px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{generalMetrics.bmi.toFixed(1)}</span>
                              <span style={{ fontSize:'12px', color:'#94a3b8' }}>kg/m²</span>
                            </div>
                            <div style={{ marginTop:'6px' }}>
                              <StatusBadge text={generalMetrics.bmiCat} variant={generalMetrics.bmiVariant} />
                            </div>
                            <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'4px' }}>Asian cutoffs: Normal &lt; 23, OW ≥ 23, Obese ≥ 27.5</div>
                          </>
                        ) : <div style={{ fontSize:'12px', color:'#94a3b8', padding:'6px 0' }}>Enter height &amp; weight</div>}
                      </div>
                      <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px 16px', border:'1px solid #e8ecf0' }}>
                        <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'6px' }}>Mean Arterial Pressure</div>
                        {systolic !== "" && diastolic !== "" ? (
                          <>
                            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
                              <span style={{ fontSize:'28px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{generalMetrics.map.toFixed(1)}</span>
                              <span style={{ fontSize:'12px', color:'#94a3b8' }}>mmHg</span>
                            </div>
                            <div style={{ marginTop:'6px' }}>
                              <StatusBadge text={generalMetrics.mapCat} variant={generalMetrics.mapVariant} />
                            </div>
                            <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'4px' }}>Normal range: 70–100 mmHg</div>
                          </>
                        ) : <div style={{ fontSize:'12px', color:'#94a3b8', padding:'6px 0' }}>Enter systolic &amp; diastolic BP</div>}
                      </div>
                    </div>
                  </div>

                </div>
              </main>

              {/* ── FOOTER ── */}
              <footer className="clinical-footer">
                Reference: Khadilkar V et al. (2015) Indian Pediatrics · TW3 (Tanner-Whitehouse 3, 2001) · QRISK3-2017 (Hippisley-Cox, BMJ 2017; ClinRisk LGPL) · CKD-EPI 2021 · Modified Bedside Schwartz (2009) · FRAX India Asian · FIB-4 (Sterling et al.) · For clinical decision support only.
              </footer>

            </div>
          );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
