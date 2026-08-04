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
 * State ownership deliberately stays in App
 * -----------------------------------------
 * The provider transports state; it does not own it. Moving ~400 bindings out
 * of App would have been a large mechanical edit with a defect opportunity per
 * line, for no behavioural gain -- what blocked panel extraction was the
 * *plumbing*, not where useState lived. Panels can now be lifted one at a time;
 * relocating ownership can follow if it ever pays for itself.
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

function useLiver() {
  const s = useClinicalState();
  return { metrics: s.liverMetrics, hasManual: s.hasManualLiver, platelets: s.platelets };
}

function useRenal() {
  const s = useClinicalState();
  return {
    metrics: s.renalMetrics, hasManual: s.hasManualRenal,
    creatinine: s.creatinine, monitoring: s.monitoring,
  };
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
    printGrowthReport: s.printGrowthReport,
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

export {
  ClinicalStateContext, ClinicalStateProvider, useClinicalState,
  usePatient, useLiver, useRenal, useFrax,
  useOverview, useGrowth, useQrisk, useLedger,
};
