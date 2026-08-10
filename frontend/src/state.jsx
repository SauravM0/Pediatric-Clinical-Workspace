/**
 * Clinical state context (M6 state refactor).
 *
 * App holds ~95 useState hooks. The panels that render from them were therefore
 * un-extractable: pulling one out meant threading its inputs, its derived
 * metrics and the shared demographics through as props, and every panel would
 * have needed a different subset.
 *
 * Why context rather than props here, specifically
 * ------------------------------------------------
 * The derived metrics are NOT panel-local. `liverMetrics` is read by the Liver
 * panel, by the Overview summary cards, and by the visit ledger; the same is
 * true of renal, FRAX and QRISK. So the values are genuinely app-wide shared
 * state with several unrelated consumers, which is the case context exists for.
 * Passing them down as props would mean App re-declaring the same eight values
 * on every panel element it renders.
 *
 * Why ONE provider rather than one per domain
 * -------------------------------------------
 * Six nested providers would be tidier on paper. But this is a single-page tool
 * showing one patient at a time, App already re-renders everything on any
 * change, and the nesting would buy no render savings while making the tree
 * harder to read. One provider with GROUPED SELECTORS (usePatient, useLiver,
 * ...) gives panels a narrow view of exactly their slice without the ceremony.
 *
 * State ownership stays in App -- audited, not assumed
 * -----------------------------------------------------
 * The provider transports state; it does not own it. That was deferred with the
 * condition that relocating ownership "follow if it ever pays for itself", and
 * the audit that settled it found:
 *
 *   - 97 useState bindings in App, 156 names on the context;
 *   - 109 of those names are read by exactly ONE panel -- which looks like the
 *     case for pushing them down;
 *   - but every one is ALSO read by App itself or by the handler hook App owns.
 *     boneMetrics feeds the Overview cards, resetAll clears them, the growth
 *     panel's adult-height projection needs the parental heights collected on
 *     the bone-age tab, and qriskMetrics feeds the Overview grid.
 *
 * So moving ownership OUT of App would thread the same values straight back in.
 * The sharing surface cannot shrink without either a second provider (weighed
 * and rejected above -- no render saving, a harder tree to read) or inverting
 * the data flow so panels report upward. Neither pays.
 *
 * What did pay was GROUPING. `boneAgeState.js` and `qriskState.js` hold those
 * two domains' declarations, defaults and explanatory comments; App calls them
 * during its own render, so ownership is unchanged and no consumer moved. That
 * took 64 useState declarations out of a 1,300-line component and put the
 * module boundary where a comment header used to be. The rest stay in App
 * because they are the shared demographics and derived metrics -- exactly the
 * values this context exists to transport.
 */
const ClinicalStateContext = React.createContext(null);

function ClinicalStateProvider({ value, children }) {
  return React.createElement(ClinicalStateContext.Provider, { value }, children);
}

function useClinicalState() {
  const ctx = React.useContext(ClinicalStateContext);
  if (!ctx) {
    // Fail loudly. A panel rendered outside the provider would otherwise crash
    // on an undefined field somewhere deeper, with a message pointing at the
    // wrong place entirely.
    throw new Error(
      'useClinicalState must be used inside <ClinicalStateProvider>. A panel was ' +
      'rendered outside the provider that supplies its data.'
    );
  }
  return ctx;
}

/** Demographics and the evaluated (coerced) measurements every panel shares. */
function usePatient() {
  const s = useClinicalState();
  return {
    age: s.age, dob: s.dob, gender: s.gender, height: s.height, weight: s.weight,
    evalAge: s.evalAge, evalHeight: s.evalHeight, evalWeight: s.evalWeight,
    patientName: s.patientName, patientMrn: s.patientMrn, examDate: s.examDate,
  };
}

// Each slice carries what its panel READS and nothing else. The panels take the
// raw inputs (creatinine, platelets) only through the derived `metrics`, so the
// raw values are not re-exposed here -- a field nobody reads is how a narrow
// slice drifts back into a shared store, one key at a time.
// test_selectors_expose_nothing_the_panel_does_not_use enforces it.

function useLiver() {
  const s = useClinicalState();
  return { metrics: s.liverMetrics, hasManual: s.hasManualLiver };
}

function useRenal() {
  const s = useClinicalState();
  // Notably NOT `monitoring`: that is the bone-age AI monitoring payload
  // (/api/bone-age/monitoring), which the renal slice offered and the renal
  // panel never used, purely because it sits beside the renal fields in
  // clinicalState.
  return { metrics: s.renalMetrics, hasManual: s.hasManualRenal };
}

function useFrax() {
  const s = useClinicalState();
  return { metrics: s.fraxMetrics, hasManual: s.hasManualFrax };
}



/** Every module's derived status, for the at-a-glance grid. */
function useOverview() {
  const s = useClinicalState();
  return {
    moduleStatus: s.moduleStatus,
    setActiveTab: s.setActiveTab,
  };
}

/** Charts, centiles and the printable report. */
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
    weight: s.weight,
  };
}

/** QRISK3 inputs and result. Mostly setters: unlike the other panels it owns its
 *  own risk-factor toggles rather than reading shared measurements. */
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
    weight: s.weight,
  };
}

/** The visit ledger -- the second consumer of the derived metrics, and the
 *  reason they are shared state rather than panel-local. */
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
    weight: s.weight,
  };
}

/** The bone-age workspace: its state AND its workflow handlers.
 *
 *  The largest slice by far, because the bone-age workflow is the largest
 *  thing in the product -- staging, lifecycle, upload, AI, localisation,
 *  adjudication, licensed tables and feedback. It is still an explicit list,
 *  so what the panel can reach stays reviewable. */
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
    useGridAsReference: s.useGridAsReference,
  };
}

export {
  ClinicalStateContext, ClinicalStateProvider, useClinicalState,
  usePatient, useLiver, useRenal, useFrax,
  useOverview, useGrowth, useQrisk, useLedger, useBoneAge,
};
