/**
 * Qrisk panel.
 *
 * QRISK3-2017. Unusual among the panels in owning its OWN inputs (the
 * sixteen risk-factor toggles are not shared), so most of its slice is
 * setters rather than derived values. The score itself comes from the backend
 * (backend/cvd/qrisk3.py), which also reports every defaulted input.
 */
import { useQrisk } from "../state.jsx";
import { ProbBar, StatusBadge, SectionHeader, YesNoToggleRow, InputWithUnit, heroTone } from "../ui.jsx";
import { rangeProblem } from "../clinicalRanges.js";

function QriskPanel() {
  const { cholRatio, diabetes, ethnicity, evalGender, qAF, qAtypAntipsy, qCKD, qCortico, qED, qFhCvd, qMigraine, qRA, qSLE, qSMI, qTreatedHtn, qriskMetrics, sbpSD, setCholRatio, setDiabetes, setEthnicity, setQAF, setQAtypAntipsy, setQCKD, setQCortico, setQED, setQFhCvd, setQMigraine, setQRA, setQSLE, setQSMI, setQTreatedHtn, setSbpSD, setSmokeCat, smokeCat } = useQrisk();
  return (
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
            <InputWithUnit label="Total : HDL Cholesterol ratio" value={cholRatio} onChange={e => setCholRatio(e.target.value)} placeholder="e.g. 4.0" step="0.1" unit="ratio" problem={rangeProblem('cholRatio', cholRatio)} />
            <InputWithUnit label="SBP variability (SD, optional)" value={sbpSD} onChange={e => setSbpSD(e.target.value)} placeholder="mmHg SD" step="0.1" unit="SD" problem={rangeProblem('sbpSD', sbpSD)} />
          </div>
          <div style={{ fontSize:'10px', color:'#94a3b8', lineHeight:'1.5' }}>
            Uses BMI (from height/weight) and systolic BP from the left panel. Blank cholesterol ratio / SBP-SD contribute neutrally (QRISK3 convention). Townsend deprivation is set to 0 (UK-only index).
          </div>
          <div style={{ background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'6px 14px' }}>
            <YesNoToggleRow label="Atrial fibrillation" value={qAF} setter={setQAF} />
            <YesNoToggleRow label="On BP treatment" value={qTreatedHtn} setter={setQTreatedHtn} />
            <YesNoToggleRow label="CKD stage 3–5" value={qCKD} setter={setQCKD} />
            <YesNoToggleRow label="Rheumatoid arthritis" value={qRA} setter={setQRA} />
            <YesNoToggleRow label="Migraine" value={qMigraine} setter={setQMigraine} />
            <YesNoToggleRow label="SLE (lupus)" value={qSLE} setter={setQSLE} />
            <YesNoToggleRow label="Severe mental illness" value={qSMI} setter={setQSMI} />
            <YesNoToggleRow label="Atypical antipsychotics" value={qAtypAntipsy} setter={setQAtypAntipsy} />
            <YesNoToggleRow label="Regular corticosteroids" value={qCortico} setter={setQCortico} />
            {evalGender === 'boys' && <YesNoToggleRow label="Erectile dysfunction" value={qED} setter={setQED} />}
            <YesNoToggleRow label="Family history of CVD" value={qFhCvd} setter={setQFhCvd} />
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

        {/* Imputed-input disclosure — the BACKEND lists every defaulted input,
            so a precise-looking score is never produced silently (audit F-3). */}
        {qriskMetrics.risk !== null && qriskMetrics.imputed.length > 0 && (
          <div style={{ marginTop:'10px', fontSize:'10.5px', color:'#92400e', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'7px 10px', lineHeight:'1.5' }}>
            ⚠ Estimated with defaulted inputs: <strong>{qriskMetrics.imputed.join(', ')}</strong>. Enter these for a patient-specific score.
          </div>
        )}
        {qriskMetrics.risk !== null && qriskMetrics.bmiClamped && (
          <div style={{ marginTop:'8px', fontSize:'10.5px', color:'#92400e', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'7px 10px', lineHeight:'1.5' }}>
            ⚠ BMI is outside QRISK3's 20–40 kg/m² range; the model scores it as if at the nearest limit.
          </div>
        )}

        {/* Eligibility gate — QRISK3 is validated only for adults 25–84 (audit F-3) */}
        {qriskMetrics.risk === null && (
          <div style={{ marginTop:'16px', background:'#fef2f2', border:'1.5px solid #fecaca', borderRadius:'12px', padding:'14px 16px' }}>
            <div style={{ fontSize:'12px', fontWeight:'800', color:'#991b1b' }}>
              {qriskMetrics.inAgeRange && qriskMetrics.bodySizeOk && qriskMetrics.loading ? 'Calculating…' : 'QRISK3 not applicable'}
            </div>
            <div style={{ fontSize:'11px', color:'#b91c1c', marginTop:'4px', lineHeight:'1.5' }}>
              {!qriskMetrics.inAgeRange ? 'QRISK3 is validated only for adults aged 25–84 (age and sex must be entered). No score is shown.'
                : !qriskMetrics.bodySizeOk ? 'Enter height and weight (BMI) to compute the score.'
                : qriskMetrics.error ? `Calculation failed: ${qriskMetrics.error}`
                : qriskMetrics.reason || ''}
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
  );
}

export { QriskPanel };
