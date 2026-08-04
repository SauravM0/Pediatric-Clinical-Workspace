/**
 * Bone-age panel.
 *
 * The largest panel in the app (907 lines): staging the 13 RUS bones and 7
 * carpals, the assessment lifecycle, film upload with its quality gate, AI
 * screening, per-bone localisation, adjudication, the licensed-table editor
 * and clinician feedback.
 *
 * It reads one slice covering both its state and the workflow handlers (see
 * boneAgeHandlers.js). That slice is large because the bone-age workflow
 * genuinely is -- but it is still a declared list, so what this panel can
 * reach remains reviewable rather than being the whole application.
 */
import { useBoneAge } from "../state.jsx";
import { TW3_CONFIG, REPORT_RUS, REPORT_CARPALS, LETTER_STAGES, carpalCode, IMAGE_DOMAINS, LOW_TRUST_DOMAINS } from "../domain.js";
import { SectionHeader, StatusBadge, EmptyState, MetricRow, InputWithUnit,
         heroTone } from "../ui.jsx";

function BoneAgePanel() {
  const {
    DECLARABLE_FLAGS, LC_API, addOrSelectBox, adjBusy, adjItems, adjMsg,
    adjReviewer, age, aiBusy, aiEstimate, analysisUrl, assessment,
    attachImage, boneAge, boneAgeSource, boneMetrics, boneReport,
    bonesIntoGrids, boxes, carpalStages, clearBox, covBusy, coverage,
    curveToText, declaredFlags, endLocDrag, estimateDomain, evalAge,
    evalGender, evalHeight, fatherHeight, fbAge, fbBusy, fbConfidence,
    fbMethod, fbMsg, fbNote, fbRater, height, lcBtn, lcBusy, lcLocked,
    lcMsg, letterResult, loadAdjudication, loadCoverage, loadLetterTables,
    loadMonitoring, locBusy, locImg, locMsg, locRef, localizeBones,
    ltBusy, ltMsg, ltSection, ltSex, ltStatus, ltTables, monBusy,
    monitoring, motherHeight, onLocMove, patientCode, radiograph,
    resolveAdjudication, reviseAssessment, runEstimate, rusStages,
    saveBoxes, saveDraft, saveLetterTables, selBone, setAdjReviewer,
    setAssessment, setBoneAge, setBoneAgeSource, setCarpalStages,
    setEstimateDomain, setFatherHeight, setFbAge, setFbConfidence,
    setFbMethod, setFbNote, setFbRater, setImageDomain, setLcBusy,
    setLcMsg, setLocImg, setLtCurve, setLtPoint, setLtSection, setLtSex,
    setLtSexCurve, setLtTables, setMotherHeight, setPatientCode,
    setRefExpected, setRusStages, setShowAudit, showAudit, startBoxDrag,
    submitFeedback, toggleAudit, toggleDeclaredFlag, tw3Config,
    useGridAsReference,
  } = useBoneAge();

  return (
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
  );
}

export { BoneAgePanel };
