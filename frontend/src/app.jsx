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
import { ClinicalStateProvider } from "./state.jsx";
import { useBoneAgeHandlers } from "./boneAgeHandlers.js";
import { RenalPanel } from "./panels/RenalPanel.jsx";
import { LiverPanel } from "./panels/LiverPanel.jsx";
import { FraxPanel } from "./panels/FraxPanel.jsx";
import { OverviewPanel } from "./panels/OverviewPanel.jsx";
import { GrowthPanel } from "./panels/GrowthPanel.jsx";
import { QriskPanel } from "./panels/QriskPanel.jsx";
import { LedgerPanel } from "./panels/LedgerPanel.jsx";
import { BoneAgePanel } from "./panels/BoneAgePanel.jsx";

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
          const [localCohort, setLocalCohort] = useState(null); // /api/bone-age/local-cohort
          const [lcohBusy, setLcohBusy] = useState(false);
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
          // Bone-age workflow handlers, lifted out of App. See
          // boneAgeHandlers.js for why the handlers move but the state stays.
          const {
            LC_API, lcLocked, saveDraft, bonesIntoGrids,
            calculateAssessment, approveAssessment, reviseAssessment,
            toggleAudit, submitFeedback, runEstimate, toggleDeclaredFlag,
            attachImage, loadCoverage, loadMonitoring, loadAdjudication,
            resolveAdjudication, _emptyLt, loadLetterTables, setLtPoint,
            curveToText, parseCurve, setLtCurve, setLtSexCurve,
            useGridAsReference, setRefExpected, saveLetterTables,
            setImageDomain, analysisUrl, localizeBones, addOrSelectBox,
            clearBox, saveBoxes, startBoxDrag, onLocMove, endLocDrag,
            lcBtn, loadLocalCohort,
          } = useBoneAgeHandlers({
            adjReviewer, age, aiEstimate, approverName, assessment, boxes,
            boxesRef, carpalStages, coverage, declaredFlags,
            estimateDomain, evalAge, evalGender, fbAge, fbConfidence,
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
            age, dob, gender, height, weight,
            evalAge, evalHeight, evalWeight,
            patientName, patientMrn, examDate,
            liverMetrics, hasManualLiver, platelets,
            renalMetrics, hasManualRenal, creatinine, monitoring,
            fraxMetrics, hasManualFrax,
            DECLARABLE_FLAGS,
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
            timeline,
          };

          return (
            <ClinicalStateProvider value={clinicalState}>
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
                    {activeTab === 'overview' && <OverviewPanel />}
                    {activeTab === 'growth' && <GrowthPanel />}
                    {activeTab === 'boneage' && <BoneAgePanel />}
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
            </ClinicalStateProvider>
          );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
