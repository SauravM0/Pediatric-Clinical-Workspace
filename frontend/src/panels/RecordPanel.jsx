/**
 * Patient Record panel (step 3).
 *
 * The persisted longitudinal record, and the reasoning built on it, surfaced for
 * the first time. Until now the backend could store visits, compute growth
 * velocity, run twelve clinical rules and triage a referral -- and none of it
 * was reachable from the workspace, because nothing could even create a patient.
 *
 * Safety behaviour, deliberately in this file:
 *
 *  * The record is opened by the MRN in the identity bar -- exact match, no
 *    name search.
 *  * WRITES ARE BLOCKED when the open record disagrees with the screen on sex or
 *    date of birth. That is the signature of the wrong record being open, and
 *    writing a height into another child's record is not recoverable by anyone
 *    who does not know it happened.
 *  * Measurements are saved as one visit, all-or-nothing, dated by the exam
 *    date; BMI is derived by the server. Only entered, plausible values are sent.
 *  * An implausible drop in height is refused by the server; overriding it needs
 *    an explicit confirmation that quotes the server's reason.
 *  * Findings are shown with their source and confidence, "not assessed" checks
 *    are listed (silence is not "normal"), and no triage level is reassuring.
 *  * The parent-facing summary needs a clinician to release it explicitly.
 */
import { useRecord } from "../state.jsx";
import { SectionHeader, StatusBadge, EmptyState, InputWithUnit } from "../ui.jsx";
import { rangeProblem } from "../clinicalRanges.js";

const { useState, useEffect, useCallback, useRef } = React;

async function api(url, init) {
  const r = await fetch(url, init);
  const data = await r.json().catch(() => null);
  const detail = data && data.detail;
  return { ok: r.ok, status: r.status, data,
           error: r.ok ? null : (typeof detail === 'string' ? detail : `HTTP ${r.status}`) };
}
const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

const TRIAGE = {
  routine_monitoring: { label: 'Routine monitoring', variant: 'mid' },
  discuss_with_paediatrician: { label: 'Discuss with paediatrician', variant: 'mid' },
  specialist_soon: { label: 'Specialist review soon', variant: 'high' },
};
const SEVERITY = {
  urgent: { label: 'Urgent', variant: 'high' },
  attention: { label: 'Attention', variant: 'mid' },
  info: { label: 'Info', variant: 'info' },
  insufficient_data: { label: 'Not assessed', variant: 'neutral' },
};
const OBS_LABEL = { height: 'Height', weight: 'Weight', bmi: 'BMI', head_circumference: 'Head circ.',
  sitting_height: 'Sitting height', arm_span: 'Arm span', systolic_bp: 'Systolic BP', diastolic_bp: 'Diastolic BP' };

const card = { background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'14px 16px', marginTop:'14px' };
const h4 = { fontSize:'10px', fontWeight:800, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'8px' };
const btn = (bg, disabled) => ({ padding:'7px 14px', background: disabled ? '#cbd5e1' : bg, color:'white', border:'none',
  borderRadius:'9px', fontSize:'12px', fontWeight:700, cursor: disabled ? 'not-allowed' : 'pointer' });
const numOrBlank = (e) => e.target.value === "" ? "" : parseFloat(e.target.value);
// Server messages carry a hint meant for API callers ("resubmit with
// allow_implausible_change=true"); a clinician needs only the clinical sentence.
const plain = (text) => String(text || '')
  .replace(/^implausible_decrease:\s*/, '')
  .replace(/\s*Re-check, or resubmit with allow_implausible_change=true\.?/, ' Re-check the measurement.');

function RecordPanel() {
  const { patientMrn, patientName, examDate, sexEntered, dob,
          height, weight, systolic, diastolic, heightOk, weightOk, bpOk } = useRecord();

  const [record, setRecord] = useState(null);        // patient summary
  const [notFound, setNotFound] = useState(false);
  const [timeline, setTimeline] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [msg, setMsg] = useState(null);              // {type, text}
  const [busy, setBusy] = useState(false);
  const [ctx, setCtx] = useState({ mother_height_cm:"", father_height_cm:"", parental_height_source:"",
                                   gestational_age_weeks:"", birth_weight_g:"" });
  const [pub, setPub] = useState({ breast_stage:"", genital_stage:"", pubic_hair_stage:"",
                                   testicular_volume_ml:"", menarche_date:"" });
  const [extra, setExtra] = useState({ head_circumference:"", sitting_height:"", arm_span:"" });
  const [parentSummary, setParentSummary] = useState(null);

  // Responses are checked against the CURRENT MRN / record before being used:
  // a slow reply for the previous patient must not open under the next one.
  const mrnRef = useRef(patientMrn);
  mrnRef.current = patientMrn;
  const recordIdRef = useRef(null);

  // A different MRN is a different patient: drop everything shown for the last one.
  useEffect(() => {
    recordIdRef.current = null;
    setRecord(null); setNotFound(false); setTimeline(null); setAssessment(null);
    setMsg(null); setParentSummary(null);
  }, [patientMrn]);

  const loadDetails = useCallback(async (id) => {
    const [t, a] = await Promise.all([api(`/api/patients/${id}/timeline`),
                                      api(`/api/clinical/patients/${id}/assessment`)]);
    if (recordIdRef.current !== id) return;   // another record was opened meanwhile
    if (t.ok) setTimeline(t.data);
    if (a.ok) setAssessment(a.data);
    if (!t.ok || !a.ok) setMsg({ type:'err', text: t.error || a.error });
  }, []);

  const adopt = (p) => {
    recordIdRef.current = p.id;
    setRecord(p); setNotFound(false); setParentSummary(null);
    setCtx({
      mother_height_cm: p.mother_height_cm ?? "", father_height_cm: p.father_height_cm ?? "",
      parental_height_source: p.parental_height_source ?? "",
      gestational_age_weeks: p.gestational_age_weeks ?? "", birth_weight_g: p.birth_weight_g ?? "",
    });
    loadDetails(p.id);
  };

  const openRecord = async () => {
    if (!patientMrn.trim()) { setMsg({ type:'err', text:'Enter the MRN in the patient bar first.' }); return; }
    setBusy(true); setMsg(null);
    const code = patientMrn.trim();
    // POST: the MRN goes in the body, never in a URL (logs, history).
    const r = await api('/api/patients/lookup', json('POST', { code }));
    setBusy(false);
    if (mrnRef.current.trim() !== code) return;   // MRN changed while waiting
    if (r.status === 404) { setRecord(null); setNotFound(true); return; }
    if (!r.ok) { setMsg({ type:'err', text: r.error }); return; }
    adopt(r.data);
  };

  const createRecord = async () => {
    if (!sexEntered || !dob) { setMsg({ type:'err', text:'Creating a record needs biological sex and date of birth (not just age) in Demographics.' }); return; }
    if (!window.confirm(`Create a new record for MRN ${patientMrn.trim()} (${sexEntered === 'boys' ? 'male' : 'female'}, born ${dob})?`)) return;
    setBusy(true); setMsg(null);
    const r = await api('/api/patients', json('POST', {
      patient_code: patientMrn.trim(), sex: sexEntered, date_of_birth: `${dob}T00:00:00`,
      name: patientName.trim() || null }));
    setBusy(false);
    if (!r.ok) { setMsg({ type:'err', text: r.error }); return; }
    adopt(r.data); setMsg({ type:'ok', text:'Record created.' });
  };

  // The wrong-record guard. Only compares what the screen actually has.
  const mismatches = [];
  if (record) {
    // The screen must CONFIRM the record, not merely fail to contradict it: with
    // no sex selected there is nothing to compare, and that is not a match.
    if (!sexEntered)
      mismatches.push('select biological sex in Demographics to confirm this is the right child');
    else if (record.sex_at_birth !== sexEntered)
      mismatches.push(`sex: record ${record.sex_at_birth === 'boys' ? 'male' : 'female'}, screen ${sexEntered === 'boys' ? 'male' : 'female'}`);
    if (dob && record.date_of_birth && record.date_of_birth !== dob)
      mismatches.push(`date of birth: record ${record.date_of_birth}, screen ${dob}`);
  }
  const writable = !!record && mismatches.length === 0 && !busy;

  const visitValues = {
    height: heightOk ? height : null, weight: weightOk ? weight : null,
    systolic_bp: bpOk ? systolic : null, diastolic_bp: bpOk ? diastolic : null,
    head_circumference: extra.head_circumference === "" ? null : extra.head_circumference,
    sitting_height: extra.sitting_height === "" ? null : extra.sitting_height,
    arm_span: extra.arm_span === "" ? null : extra.arm_span,
  };
  const visitEntries = Object.entries(visitValues).filter(([, v]) => v !== null);

  const saveVisit = async (allowDrop = false) => {
    if (!writable || !examDate) return;
    setBusy(true); setMsg(null);
    const r = await api(`/api/patients/${record.id}/visits`, json('POST', {
      observed_at: `${examDate}T00:00:00`, allow_implausible_change: allowDrop, ...visitValues }));
    setBusy(false);
    if (!r.ok) {
      if (!allowDrop && /implausible_decrease/.test(r.error || '')
          && window.confirm(`${plain(r.error)}\n\nSave anyway? Only if you have re-measured and the value is correct.`)) {
        return saveVisit(true);
      }
      setMsg({ type:'err', text: plain(r.error) }); return;
    }
    const warn = r.data.warnings.length ? ` Warnings: ${r.data.warnings.join('; ')}` : '';
    setMsg({ type: warn ? 'warn' : 'ok', text: `Visit of ${examDate} saved (${r.data.saved.map(s => s.obs_type).join(', ')}).${warn}` });
    setExtra({ head_circumference:"", sitting_height:"", arm_span:"" });
    loadDetails(record.id);
  };

  const saveContext = async () => {
    if (!writable) return;
    const body = {};
    Object.entries(ctx).forEach(([k, v]) => { body[k] = v === "" ? null : v; });
    setBusy(true); setMsg(null);
    const r = await api(`/api/patients/${record.id}`, json('PATCH', body));
    setBusy(false);
    if (!r.ok) { setMsg({ type:'err', text: r.error }); return; }
    adopt(r.data); setMsg({ type:'ok', text:'Clinical context saved.' });
  };

  const savePuberty = async () => {
    if (!writable || !examDate) return;
    const body = { assessed_at: `${examDate}T00:00:00` };
    Object.entries(pub).forEach(([k, v]) => {
      if (v === "") return;
      body[k] = k === 'menarche_date' ? `${v}T00:00:00` : Number(v);
    });
    if (Object.keys(body).length === 1) { setMsg({ type:'err', text:'Enter at least one Tanner stage.' }); return; }
    setBusy(true); setMsg(null);
    const r = await api(`/api/patients/${record.id}/puberty`, json('POST', body));
    setBusy(false);
    if (!r.ok) { setMsg({ type:'err', text: r.error }); return; }
    setPub({ breast_stage:"", genital_stage:"", pubic_hair_stage:"", testicular_volume_ml:"", menarche_date:"" });
    setMsg({ type:'ok', text:`Puberty assessment of ${examDate} saved.` });
    loadDetails(record.id);
  };

  const releaseParentSummary = async () => {
    if (!record) return;
    if (!window.confirm('Generate the plain-language summary for the parent? Release it only after you have reviewed the findings yourself.')) return;
    const r = await api(`/api/clinical/patients/${record.id}/parent-summary?release=true`);
    if (!r.ok) { setMsg({ type:'err', text: r.error }); return; }
    setParentSummary(r.data);
  };

  const isGirl = record ? record.sex_at_birth === 'girls' : sexEntered === 'girls';
  const stageSelect = (key, label) => (
    <div style={{ minWidth:0 }}>
      <label className="field-label">{label}</label>
      <select className="input-field" style={{ width:'100%' }} value={pub[key]}
        onChange={e => setPub(p => ({ ...p, [key]: e.target.value }))}>
        <option value="">—</option>{[1,2,3,4,5].map(n => <option key={n} value={n}>Tanner {n}</option>)}
      </select>
    </div>
  );

  const triage = assessment && TRIAGE[assessment.triage.level];
  const findings = assessment ? assessment.findings.filter(f => f.severity !== 'insufficient_data') : [];
  const notAssessed = assessment ? assessment.findings.filter(f => f.severity === 'insufficient_data') : [];
  const ah = assessment && assessment.adult_height;

  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader title="Patient Record · Growth history, findings & triage"
        subtitle="Saved visits, growth velocity, Tanner staging and the clinical rules engine"
        badge={triage ? triage.label : null} badgeVariant={triage ? triage.variant : 'info'} />

      {/* ── open / create ── */}
      <div style={{ ...card, display:'flex', alignItems:'center', gap:'10px', flexWrap:'wrap' }}>
        <div style={{ fontSize:'12px', color:'#334155', flex:'1 1 200px' }}>
          {record ? <>Record <strong>{record.patient_code}</strong> · {record.sex_at_birth === 'boys' ? 'Male' : 'Female'} · born {record.date_of_birth || 'unknown'}</>
            : <>MRN in patient bar: <strong>{patientMrn.trim() || '—'}</strong></>}
        </div>
        <button onClick={openRecord} disabled={busy || !patientMrn.trim()} style={btn('#4f46e5', busy || !patientMrn.trim())}>
          {record ? 'Reload' : 'Open record'}
        </button>
        {notFound && <button onClick={createRecord} disabled={busy} style={btn('#0f766e', busy)}>Create record</button>}
      </div>
      {notFound && <div style={{ fontSize:'11px', color:'#64748b', marginTop:'6px' }}>No record with this MRN. Check the MRN before creating a new one.</div>}

      {msg && (
        <div role="status" style={{ marginTop:'10px', fontSize:'12px', lineHeight:1.5, borderRadius:'8px', padding:'8px 12px',
          background: msg.type === 'err' ? '#fef2f2' : msg.type === 'warn' ? '#fffbeb' : '#f0fdf4',
          color: msg.type === 'err' ? '#991b1b' : msg.type === 'warn' ? '#92400e' : '#166534' }}>{msg.text}</div>
      )}

      {mismatches.length > 0 && (
        <div role="alert" style={{ marginTop:'10px', background:'#fef2f2', border:'1.5px solid #fca5a5', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#991b1b', lineHeight:1.6 }}>
          <strong>Nothing can be saved until the record is confirmed</strong> ({mismatches.join('; ')}).
          If the details genuinely differ, check the MRN — the wrong record may be open.
        </div>
      )}

      {!record ? (
        <EmptyState title="Open a patient record"
          hint="Enter the MRN in the patient bar and open the record — or create one (needs sex and date of birth). Visits, velocity, Tanner staging, findings and triage then appear here." />
      ) : (<React.Fragment>

      {/* ── clinical assessment ── */}
      {assessment && (
        <div style={{ ...card, background: triage && triage.variant === 'high' ? '#fff1f2' : '#fffbeb', borderColor: triage && triage.variant === 'high' ? '#fecaca' : '#fde68a' }}>
          <div style={h4}>Triage</div>
          <div style={{ display:'flex', alignItems:'center', gap:'8px', flexWrap:'wrap' }}>
            <StatusBadge text={triage.label} variant={triage.variant} />
            {assessment.triage.specialties.length > 0 && <span style={{ fontSize:'11px', color:'#475569' }}>→ {assessment.triage.specialties.join(', ')}</span>}
          </div>
          <div style={{ fontSize:'12px', color:'#334155', marginTop:'8px', lineHeight:1.6 }}>{assessment.triage.guidance}</div>
          <div style={{ fontSize:'10.5px', color:'#64748b', marginTop:'6px' }}>{assessment.disclaimer}</div>
        </div>
      )}

      {assessment && (
        <div style={card}>
          <div style={h4}>Findings {assessment.as_of_age_years != null && `· as of ${assessment.as_of_age_years} y`}</div>
          {findings.length === 0 ? <div style={{ fontSize:'12px', color:'#475569' }}>No rule fired on the recorded data. This is not an all-clear: see what could not be assessed below.</div>
            : findings.map(f => (
              <div key={f.rule_id} style={{ padding:'8px 0', borderBottom:'1px solid #eef2f7' }}>
                <div style={{ display:'flex', gap:'8px', alignItems:'center', flexWrap:'wrap' }}>
                  <StatusBadge text={SEVERITY[f.severity].label} variant={SEVERITY[f.severity].variant} />
                  <strong style={{ fontSize:'12.5px', color:'#1e293b' }}>{f.title}</strong>
                  <span style={{ fontSize:'10px', color:'#94a3b8' }}>confidence: {f.confidence}</span>
                </div>
                <div style={{ fontSize:'11.5px', color:'#475569', marginTop:'4px', lineHeight:1.55 }}>{f.rationale}</div>
                <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'3px' }}>Source: {f.source}</div>
              </div>
            ))}
          {notAssessed.length > 0 && (
            <details style={{ marginTop:'8px' }}>
              <summary style={{ fontSize:'11px', fontWeight:700, color:'#64748b', cursor:'pointer' }}>Not assessed — missing data ({notAssessed.length})</summary>
              <ul style={{ margin:'6px 0 0', paddingLeft:'18px', fontSize:'11px', color:'#64748b', lineHeight:1.6 }}>
                {notAssessed.map(f => <li key={f.rule_id}>{f.title}{f.rationale ? ` — ${f.rationale}` : ''}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}

      {/* ── adult height: three separately labelled quantities ── */}
      {ah && (
        <div style={card}>
          <div style={h4}>Adult height — three different quantities</div>
          <div style={{ fontSize:'12px', color:'#334155', lineHeight:1.7 }}>
            <div><strong>{ah.genetic_target ? ah.genetic_target.label : 'Mid-parental target'}:</strong>{' '}
              {ah.genetic_target ? `${ah.genetic_target.target_cm.toFixed(1)} cm (range ${ah.genetic_target.range_cm[0].toFixed(0)}–${ah.genetic_target.range_cm[1].toFixed(0)}; parental heights ${ah.genetic_target.parental_height_source})` : 'needs both parents’ heights'}</div>
            <div><strong>{ah.predicted_adult_height.label}:</strong>{' '}
              {ah.predicted_adult_height.available ? `${ah.predicted_adult_height.predicted_cm.toFixed(1)} ± ${ah.predicted_adult_height.interval_cm} cm` : ah.predicted_adult_height.status}</div>
            <div><strong>{ah.from_bone_age.label}:</strong>{' '}
              {ah.from_bone_age.available ? `${ah.from_bone_age.predicted_cm} cm` : (ah.from_bone_age.status || ah.from_bone_age.reason || 'not available')}</div>
          </div>
          <div style={{ fontSize:'10.5px', color:'#94a3b8', marginTop:'6px', lineHeight:1.5 }}>{ah.note}</div>
        </div>
      )}

      {/* ── record a visit ── */}
      <div style={card}>
        <div style={h4}>Record this visit · exam date {examDate || '—'}</div>
        <div style={{ fontSize:'11.5px', color:'#475569', marginBottom:'8px' }}>
          From Demographics / Labs: {visitEntries.filter(([k]) => ['height','weight','systolic_bp','diastolic_bp'].includes(k)).map(([k, v]) => `${OBS_LABEL[k]} ${v}`).join(' · ') || 'nothing entered yet'}
          {(height !== "" && !heightOk) || (weight !== "" && !weightOk) || ((systolic !== "" || diastolic !== "") && !bpOk) ? ' · implausible values are not sent' : ''}
        </div>
        <div className="form-grid">
          <InputWithUnit label="Head circumference" value={extra.head_circumference} unit="cm" step="0.1"
            onChange={e => setExtra(x => ({ ...x, head_circumference: numOrBlank(e) }))} />
          <InputWithUnit label="Sitting height" value={extra.sitting_height} unit="cm" step="0.1"
            onChange={e => setExtra(x => ({ ...x, sitting_height: numOrBlank(e) }))} />
          <InputWithUnit label="Arm span" value={extra.arm_span} unit="cm" step="0.1"
            onChange={e => setExtra(x => ({ ...x, arm_span: numOrBlank(e) }))} />
        </div>
        <div style={{ marginTop:'10px' }}>
          <button onClick={() => saveVisit(false)} disabled={!writable || !examDate || visitEntries.length === 0}
            style={btn('#4f46e5', !writable || !examDate || visitEntries.length === 0)}>Save visit</button>
          <span style={{ fontSize:'10.5px', color:'#94a3b8', marginLeft:'8px' }}>Saved together or not at all · BMI is derived by the server</span>
        </div>
      </div>

      {/* ── puberty ── */}
      <div style={card}>
        <div style={h4}>Tanner staging · exam date {examDate || '—'}</div>
        <div className="form-grid">
          {isGirl ? stageSelect('breast_stage', 'Breast (B)') : stageSelect('genital_stage', 'Genital (G)')}
          {stageSelect('pubic_hair_stage', 'Pubic hair (PH)')}
          {isGirl ? (
            <div style={{ minWidth:0 }}>
              <label className="field-label">Menarche date (if reached)</label>
              <input type="date" className="input-field" style={{ width:'100%' }} value={pub.menarche_date}
                max={new Date().toISOString().split('T')[0]} onChange={e => setPub(p => ({ ...p, menarche_date: e.target.value }))} />
            </div>
          ) : (
            <InputWithUnit label="Testicular volume" value={pub.testicular_volume_ml} unit="mL" step="1"
              onChange={e => setPub(p => ({ ...p, testicular_volume_ml: e.target.value }))} />
          )}
        </div>
        <button onClick={savePuberty} disabled={!writable || !examDate} style={{ ...btn('#7c3aed', !writable || !examDate), marginTop:'10px' }}>Save Tanner staging</button>
      </div>

      {/* ── clinical context ── */}
      <div style={card}>
        <div style={h4}>Clinical context (used by the target-height, SGA and puberty rules)</div>
        <div className="form-grid">
          <InputWithUnit label="Mother's height" value={ctx.mother_height_cm} unit="cm" step="0.1"
            onChange={e => setCtx(c => ({ ...c, mother_height_cm: numOrBlank(e) }))} problem={rangeProblem('parentHeight', ctx.mother_height_cm)} />
          <InputWithUnit label="Father's height" value={ctx.father_height_cm} unit="cm" step="0.1"
            onChange={e => setCtx(c => ({ ...c, father_height_cm: numOrBlank(e) }))} problem={rangeProblem('parentHeight', ctx.father_height_cm)} />
          <div style={{ minWidth:0 }}>
            <label className="field-label">Parental heights were</label>
            <select className="input-field" style={{ width:'100%' }} value={ctx.parental_height_source}
              onChange={e => setCtx(c => ({ ...c, parental_height_source: e.target.value }))}>
              <option value="">—</option><option value="measured">Measured</option><option value="reported">Reported (less reliable)</option>
            </select>
          </div>
          <InputWithUnit label="Gestational age at birth" value={ctx.gestational_age_weeks} unit="wk" step="0.1"
            onChange={e => setCtx(c => ({ ...c, gestational_age_weeks: numOrBlank(e) }))} />
          <InputWithUnit label="Birth weight" value={ctx.birth_weight_g} unit="g" step="10"
            onChange={e => setCtx(c => ({ ...c, birth_weight_g: numOrBlank(e) }))} />
        </div>
        <button onClick={saveContext} disabled={!writable} style={{ ...btn('#0f766e', !writable), marginTop:'10px' }}>Save clinical context</button>
      </div>

      {/* ── history ── */}
      {timeline && (
        <div style={card}>
          <div style={h4}>Measurement history</div>
          {Object.keys(timeline.observations).length === 0 ? <div style={{ fontSize:'12px', color:'#64748b' }}>No measurements recorded yet.</div> : (
            <div style={{ overflowX:'auto' }}>
              <table style={{ borderCollapse:'collapse', fontSize:'11.5px', width:'100%' }}>
                <thead><tr style={{ color:'#64748b', textAlign:'left' }}><th style={{ padding:'4px 8px' }}>Measure</th><th style={{ padding:'4px 8px' }}>Date</th><th style={{ padding:'4px 8px' }}>Age</th><th style={{ padding:'4px 8px' }}>Value</th></tr></thead>
                <tbody>
                  {Object.entries(timeline.observations).flatMap(([k, rows]) => rows.map(r => (
                    <tr key={r.id} style={{ borderTop:'1px solid #eef2f7' }}>
                      <td style={{ padding:'4px 8px' }}>{OBS_LABEL[k] || k}{r.method === 'derived' ? ' (derived)' : ''}</td>
                      <td style={{ padding:'4px 8px' }}>{r.observed_at.slice(0, 10)}</td>
                      <td style={{ padding:'4px 8px' }}>{r.age_years != null ? `${r.age_years.toFixed(2)} y` : '—'}</td>
                      <td style={{ padding:'4px 8px', fontWeight:700 }}>{r.value} {r.unit}</td>
                    </tr>
                  )))}
                </tbody>
              </table>
            </div>
          )}
          {timeline.velocities && timeline.velocities.height && timeline.velocities.height.length > 0 && (
            <div style={{ marginTop:'12px' }}>
              <div style={h4}>Height velocity</div>
              {timeline.velocities.height.map((v, i) => (
                <div key={i} style={{ fontSize:'11.5px', color:'#334155', padding:'2px 0' }}>
                  {v.from_age_years != null ? `${v.from_age_years.toFixed(2)}–${v.to_age_years.toFixed(2)} y: ` : ''}
                  {v.available && v.velocity_per_year != null ? <strong>{v.velocity_per_year.toFixed(1)} cm/yr</strong> : (v.status || 'not computable')}
                  {v.velocity_sds != null ? ` · SDS ${v.velocity_sds.toFixed(2)}` : ''}
                  {v.flags && v.flags.length ? ` · ${v.flags.join(', ')}` : ''}
                </div>
              ))}
              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'4px' }}>Velocity centiles need the Indian velocity reference, not yet installed; rates are shown without a centile rather than against an invented one.</div>
            </div>
          )}
          {timeline.puberty.length > 0 && (
            <div style={{ marginTop:'12px' }}>
              <div style={h4}>Tanner history</div>
              {timeline.puberty.map((p, i) => (
                <div key={i} style={{ fontSize:'11.5px', color:'#334155', padding:'2px 0' }}>
                  {p.assessed_at.slice(0, 10)}: {[p.breast_stage && `B${p.breast_stage}`, p.genital_stage && `G${p.genital_stage}`,
                    p.pubic_hair_stage && `PH${p.pubic_hair_stage}`, p.testicular_volume_ml && `${p.testicular_volume_ml} mL`,
                    p.menarche_date && `menarche ${p.menarche_date.slice(0, 10)}`].filter(Boolean).join(' · ')}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── parent summary: clinician release only ── */}
      <div style={card}>
        <div style={h4}>Parent summary (clinician release)</div>
        {!parentSummary ? (
          <button onClick={releaseParentSummary} style={btn('#475569', false)}>Review &amp; release summary…</button>
        ) : (
          <div style={{ fontSize:'12px', color:'#334155', lineHeight:1.7 }}>
            <div><strong>What was looked at:</strong> {parentSummary.what_was_looked_at}</div>
            <div><strong>What was noticed:</strong> {parentSummary.what_was_noticed.join(' ')}</div>
            <div><strong>What to do:</strong> {parentSummary.what_to_do}</div>
            <div><strong>Questions to ask:</strong> {parentSummary.questions_to_ask.join(' ')}</div>
            <div style={{ fontSize:'11px', color:'#92400e', marginTop:'4px' }}>{parentSummary.important}</div>
          </div>
        )}
      </div>
      </React.Fragment>)}
    </div>
  );
}

export { RecordPanel };
