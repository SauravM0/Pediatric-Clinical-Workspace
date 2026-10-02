/**
 * Physiologically plausible input ranges.
 *
 * Not reference ranges and not clinical thresholds: these only separate a real
 * measurement from a typo or a wrong unit (creatinine in µmol/L typed into a
 * mg/dL field, platelets as a raw count instead of ×10³/µL, a height of 0). A
 * value outside its range does not produce a result -- it produces a message
 * naming the range, so the clinician fixes the entry instead of acting on a
 * number computed from it.
 *
 * Bounds are deliberately wide so no genuine patient value is refused.
 */

const RANGES = {
  age:        { min: 0,    max: 120,   unit: 'yrs' },
  // Lower bounds admit extremely preterm infants (~22-24 weeks: ~0.4 kg, ~28 cm).
  height:     { min: 20,   max: 250,   unit: 'cm' },
  weight:     { min: 0.3,  max: 350,   unit: 'kg' },
  creatinine: { min: 0.05, max: 25,    unit: 'mg/dL' },
  systolic:   { min: 40,   max: 300,   unit: 'mmHg' },
  diastolic:  { min: 20,   max: 200,   unit: 'mmHg' },
  // Acute liver failure can exceed 10,000 U/L; extreme thrombocytosis 2,000.
  ast:        { min: 1,    max: 50000, unit: 'U/L' },
  alt:        { min: 1,    max: 50000, unit: 'U/L' },
  platelets:  { min: 1,    max: 5000,  unit: '×10³/µL' },
  // Parents are adults (100 cm admits skeletal dysplasias); outside this is a
  // typo, or inches rather than cm.
  parentHeight: { min: 100, max: 230, unit: 'cm' },
  boneAge:    { min: 0,    max: 20,    unit: 'yrs' },
  // QRISK3 inputs entered on its own tab.
  cholRatio:  { min: 1,    max: 20,    unit: 'ratio' },
  sbpSD:      { min: 0,    max: 50,    unit: 'mmHg' },
  // A percentage read off the official FRAX calculator.
  fraxPct:    { min: 0,    max: 100,   unit: '%' },
};

// True when `value` is an entered, finite number inside the named range.
// An empty field is NOT plausible -- callers treat it as "not entered".
function inRange(field, value) {
  if (value === "" || value === null || value === undefined) return false;
  const n = typeof value === 'number' ? value : parseFloat(value);
  const r = RANGES[field];
  return Number.isFinite(n) && n >= r.min && n <= r.max;
}

// Message for an entered-but-implausible value, or null when the field is empty
// or fine. Empty is not an error; the panels already say what is missing.
function rangeProblem(field, value) {
  if (value === "" || value === null || value === undefined) return null;
  if (inRange(field, value)) return null;
  const r = RANGES[field];
  return `Outside plausible range (${r.min}–${r.max} ${r.unit}) — check the value and unit`;
}

export { RANGES, inRange, rangeProblem };
