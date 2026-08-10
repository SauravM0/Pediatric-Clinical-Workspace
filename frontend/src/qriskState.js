/**
 * QRISK3 cardiovascular risk-factor inputs (M6 state ownership).
 *
 * The most self-contained state group in the product. Unlike the other panels,
 * QRISK does not read shared measurements for these: they are its own toggles,
 * entered on its own tab and used nowhere else in the app except the one
 * `qriskMetrics` calculation App runs from them.
 *
 * Note what is NOT here: `systolic`. It looks like a QRISK input and is one, but
 * it is also a general vital -- it feeds mean arterial pressure and the
 * general-indicators completeness check -- so it stays with the shared
 * demographics. Moving it here would have been the tidy-looking choice and the
 * wrong one.
 *
 * See `boneAgeState.js` for why this groups declarations rather than relocating
 * ownership: the hook runs during App's render, so App still owns the state and
 * every existing consumer is untouched.
 */
const { useState } = React;

function useQriskInputs() {
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

  return {
    ethnicity, setEthnicity, smokeCat, setSmokeCat, diabetes, setDiabetes,
    cholRatio, setCholRatio, sbpSD, setSbpSD,
    qAF, setQAF, qTreatedHtn, setQTreatedHtn, qRA, setQRA, qCKD, setQCKD,
    qMigraine, setQMigraine, qSLE, setQSLE, qSMI, setQSMI,
    qAtypAntipsy, setQAtypAntipsy, qCortico, setQCortico,
    qED, setQED, qFhCvd, setQFhCvd,
  };
}

export { useQriskInputs };
