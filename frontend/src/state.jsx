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

export {
  ClinicalStateContext, ClinicalStateProvider, useClinicalState,
  usePatient, useLiver, useRenal, useFrax,
};
