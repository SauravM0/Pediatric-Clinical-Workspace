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
import { BoneAgeAdvanced } from "./BoneAgeAdvanced.jsx";

import { IMAGE_DOMAINS } from "../domain.js";
import { SectionHeader } from "../ui.jsx";

function BoneAgePanel() {
  const {
    DECLARABLE_FLAGS, age, aiBusy, aiEstimate, assessment, boneAge,
    boneMetrics, boneReport, boxes, declaredFlags, estimateDomain, fbAge,
    fbBusy, fbConfidence, fbMethod, fbMsg, fbNote, fbRater, height, lcBtn,
    letterResult, loadLocalCohort, localCohort, lcohBusy, monitoring,
    radiograph, runEstimate, setEstimateDomain, setFbAge, setFbConfidence,
    setFbMethod, setFbNote, setFbRater, submitFeedback, toggleDeclaredFlag,
    tw3Config,
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
                <div style={{ fontSize:'11px', color:'#6b21a8', fontWeight:'700' }}>AI screening estimate (Greulich–Pyle, not TW3)</div>
                <div style={{ fontWeight:'900', color:'#5b21b6', lineHeight:1 }}><span style={{ fontSize:'34px' }}>{aiEstimate.bone_age_years}</span> <span style={{ fontSize:'14px' }}>yr</span></div>
                {aiEstimate.ci_low_years != null && aiEstimate.ci_high_years != null && (
                  <div style={{ fontSize:'11px', color:'#7c3aed', fontWeight:'700', marginTop:'3px' }}>
                    {/* 'conformal' and 'conformal_grouped' are both calibrated intervals;
                        checking only the first labelled a grouped one "not calibrated". */}
                    {String(aiEstimate.interval_kind).startsWith('conformal') ? `${Math.round(parseFloat(aiEstimate.interval_coverage)*100)}% interval` : 'Likely range'} {aiEstimate.ci_low_years}–{aiEstimate.ci_high_years} yr
                    <span style={{ fontWeight:'500', color:'#a78bfa' }}> {String(aiEstimate.interval_kind).startsWith('conformal') ? `(conformal · ±${aiEstimate.uncertainty_months} mo${aiEstimate.interval_group ? ` · ${aiEstimate.interval_group}` : ''}, held-out RSNA)` : `(±${aiEstimate.uncertainty_months} mo MAE — approx, not calibrated)`}</span>
                  </div>
                )}
                <div style={{ fontSize:'10px', color:'#7c3aed', marginTop:'2px' }}>Greulich–Pyle whole-image · NOT TW3{aiEstimate.model_version ? ` · ${aiEstimate.model_version}` : ''}</div>
                {aiEstimate.range_warning && (
                  <div role="alert" style={{ fontSize:'10px', color:'#991b1b', background:'#fef2f2', border:'1px solid #fecaca', borderRadius:'7px', padding:'6px 8px', marginTop:'6px', lineHeight:'1.5' }}>⚠ {aiEstimate.range_warning}</div>
                )}
                {aiEstimate.quality_warning && (
                  <div style={{ fontSize:'10px', color:'#b45309', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'7px', padding:'6px 8px', marginTop:'6px', lineHeight:'1.5' }}>⚠ {aiEstimate.quality_warning}</div>
                )}

                {/* How the image source was decided, and on what evidence.
                    Shown because the alternative — a bone age that looks the
                    same whether it came off a scanner or off a phone — is the
                    gap this detection exists to close. */}
                {(aiEstimate.image_domain_conflict
                  || aiEstimate.image_domain_source === 'auto-detected') && (() => {
                  const conflict = aiEstimate.image_domain_conflict;
                  const label = { film_photo: 'photo of a film',
                                  compressed: 'compressed export',
                                  digital_diagnostic: 'digital radiograph',
                                  unknown: 'undetermined' };
                  const tone = conflict
                    ? { bg:'#fef2f2', border:'#fecaca', head:'#991b1b', body:'#b91c1c' }
                    : { bg:'#f8fafc', border:'#e2e8f0', head:'#334155', body:'#64748b' };
                  return (
                    <div style={{ marginTop:'6px', background:tone.bg, border:`1px solid ${tone.border}`, borderRadius:'7px', padding:'7px 9px' }}>
                      <div style={{ fontSize:'10px', fontWeight:'800', color:tone.head }}>
                        {conflict
                          ? '⚠ Declared source disagrees with the image'
                          : `Image source detected: ${label[aiEstimate.image_domain] || aiEstimate.image_domain}`}
                        {!conflict && aiEstimate.image_domain_confidence && (
                          <span style={{ fontWeight:'600', color:tone.body }}> · {aiEstimate.image_domain_confidence} confidence</span>
                        )}
                      </div>
                      {conflict && (
                        <div style={{ fontSize:'10px', color:tone.body, marginTop:'3px', lineHeight:'1.5' }}>
                          You marked this a digital radiograph; the file looks like a
                          {' '}{label[aiEstimate.image_domain_detected] || aiEstimate.image_domain_detected}.
                          Your declaration stands — the estimate is being treated as you marked it.
                        </div>
                      )}
                      {(aiEstimate.image_domain_evidence || []).length > 0 && (
                        <ul style={{ margin:'4px 0 0 14px', padding:0, fontSize:'9.5px', color:tone.body, lineHeight:'1.55' }}>
                          {aiEstimate.image_domain_evidence.map((e, i) => <li key={i}>{e}</li>)}
                        </ul>
                      )}
                      {!conflict && (
                        <div style={{ fontSize:'9.5px', color:tone.body, marginTop:'4px' }}>
                          Not what this is? Change <strong>Image source</strong> above — your
                          choice always overrides the detection.
                        </div>
                      )}
                    </div>
                  );
                })()}
                {aiEstimate.population_note && (
                  <div style={{ fontSize:'10px', color:'#64748b', marginTop:'6px', lineHeight:'1.5' }}>{aiEstimate.population_note}</div>
                )}
                {/* No "use as bone age" button. It copied this Greulich–Pyle screening
                    estimate into the TW3 bone-age field and marked it a manual entry,
                    so a machine estimate on a different method then drove the TW3
                    comparison and adult-height prediction as if a clinician had
                    staged the film (the API marks it is_tw3_scale: false). */}
                <div style={{ fontSize:'10px', color:'#64748b', marginTop:'8px', lineHeight:'1.5' }}>
                  A screening cross-check only — it is not entered as the TW3 bone age. Grade the bones for the clinical result.
                </div>
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

      {/* Local validation cohort — the only number that describes THIS clinic's
          films. Deliberately OUTSIDE the hidden Advanced block below: the
          monitoring and adjudication views live in there and are switched off,
          but "how accurate is this on my patients" is the question a clinician
          should not have to go looking for. */}
      <div style={{ marginTop:'16px', background:'white', border:'1px solid #e2e8f0', borderRadius:'12px', padding:'16px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'8px' }}>
          <div>
            <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155', textTransform:'uppercase', letterSpacing:'.05em' }}>Local validation cohort</div>
            <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>Films read independently by two clinicians, frozen and never used for training. This is the only measurement that describes accuracy on <em>your</em> patients — published figures describe someone else's.</div>
          </div>
          <button onClick={loadLocalCohort} disabled={lcohBusy} style={lcBtn('#475569', lcohBusy)}>{lcohBusy ? 'Loading…' : (localCohort ? 'Refresh' : 'Load cohort')}</button>
        </div>

        {localCohort && (() => {
          const sv = localCohort.survey || {};
          const ev = localCohort.evaluation || {};
          const strata = sv.strata || {};
          const target = localCohort.target_size || 0;
          const perStratum = localCohort.min_per_stratum || 0;
          const eligible = sv.n_eligible || 0;
          const pct = target ? Math.min(100, Math.round((eligible / target) * 100)) : 0;
          const mo = v => (v == null ? '—' : `${v} mo`);

          return (
            <div style={{ marginTop:'12px' }}>
              {/* Progress toward a cohort that can support a claim at all */}
              <div style={{ background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'12px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', flexWrap:'wrap', gap:'6px' }}>
                  <div style={{ fontSize:'11px', fontWeight:'800', color:'#334155' }}>Eligible films</div>
                  <div style={{ fontSize:'11px', color:'#64748b' }}>{eligible} of {target} · at least {sv.min_readers || 2} independent reads each</div>
                </div>
                <div style={{ marginTop:'6px', height:'8px', background:'#e2e8f0', borderRadius:'999px', overflow:'hidden' }}>
                  <div style={{ width:`${pct}%`, height:'100%', background: pct >= 100 ? '#059669' : '#6366f1' }} />
                </div>

                <div style={{ display:'flex', flexWrap:'wrap', gap:'8px', marginTop:'10px' }}>
                  {(localCohort.strata || []).map(name => {
                    const have = strata[name] || 0;
                    const ok = have >= perStratum;
                    return (
                      <div key={name} style={{ flex:'1 1 120px', background:'white', border:`1px solid ${ok ? '#a7f3d0' : '#fecaca'}`, borderRadius:'8px', padding:'8px' }}>
                        <div style={{ fontSize:'10px', color:'#64748b' }}>{name.replace(':', ' · ')}</div>
                        <div style={{ fontSize:'16px', fontWeight:'800', color: ok ? '#059669' : '#b91c1c' }}>{have}<span style={{ fontSize:'11px', fontWeight:'600', color:'#94a3b8' }}> / {perStratum}</span></div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'8px', lineHeight:'1.5' }}>
                  Every stratum needs its minimum before the cohort can be frozen. Published Indian data show TW3 is <strong>worst of three methods in pubertal boys</strong>, so a cohort thin in any stratum hides the subgroup that matters most.
                </div>
              </div>

              {/* Why it cannot be frozen yet */}
              {!sv.ready_to_freeze && (sv.reasons || []).length > 0 && (
                <div style={{ marginTop:'10px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'10px' }}>
                  <div style={{ fontSize:'11px', fontWeight:'800', color:'#92400e' }}>Not ready to freeze</div>
                  <ul style={{ margin:'6px 0 0 16px', padding:0, fontSize:'10px', color:'#78350f', lineHeight:'1.6' }}>
                    {sv.reasons.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}

              {/* Films that did not qualify, and why — never silently dropped */}
              {sv.rejected && Object.values(sv.rejected).some(n => n > 0) && (
                <div style={{ marginTop:'10px', fontSize:'10px', color:'#64748b' }}>
                  Excluded: {Object.entries(sv.rejected).filter(([, n]) => n > 0)
                    .map(([k, n]) => `${k.replace(/_/g, ' ')} ${n}`).join(' · ')}
                </div>
              )}

              {/* The result, if one can honestly be produced */}
              {ev.available ? (
                <div style={{ marginTop:'12px' }}>
                  <div style={{ display:'flex', flexWrap:'wrap', gap:'10px' }}>
                    <div style={{ flex:'1 1 160px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'8px', padding:'10px' }}>
                      <div style={{ fontSize:'10px', color:'#4338ca' }}>Model error on your films</div>
                      <div style={{ fontSize:'20px', fontWeight:'800', color:'#3730a3' }}>{mo((ev.headline || {}).mae_months)}</div>
                      <div style={{ fontSize:'10px', color:'#6366f1' }}>{(ev.provenance || {}).n_evaluated || 0} films evaluated</div>
                    </div>
                    {/* Deliberately adjacent and the same size: a model error shown
                        without the readers' own spread invites the consensus to be
                        read as truth. Bone age has no ground truth. */}
                    <div style={{ flex:'1 1 160px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'8px', padding:'10px' }}>
                      <div style={{ fontSize:'10px', color:'#64748b' }}>Disagreement between your readers</div>
                      <div style={{ fontSize:'20px', fontWeight:'800', color:'#334155' }}>{mo((ev.reader_disagreement || {}).mean_spread_months)}</div>
                      <div style={{ fontSize:'10px', color:'#94a3b8' }}>the floor this should be read against</div>
                    </div>
                  </div>

                  {(ev.interpretation || []).length > 0 && (
                    <div style={{ marginTop:'10px', background:'#f0fdf4', border:'1px solid #bbf7d0', borderRadius:'8px', padding:'10px' }}>
                      {ev.interpretation.map((line, i) => (
                        <div key={i} style={{ fontSize:'11px', color:'#14532d', lineHeight:'1.6', marginTop: i ? '6px' : 0 }}>{line}</div>
                      ))}
                    </div>
                  )}

                  {((ev.by_stratum || {}).subgroups || []).length > 0 && (
                    <div style={{ marginTop:'10px', overflowX:'auto' }}>
                      <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'11px' }}>
                        <thead>
                          <tr style={{ background:'#f8fafc' }}>
                            <th style={{ textAlign:'left', padding:'6px 8px', color:'#64748b', fontWeight:'700' }}>Stratum</th>
                            <th style={{ textAlign:'right', padding:'6px 8px', color:'#64748b', fontWeight:'700' }}>Films</th>
                            <th style={{ textAlign:'right', padding:'6px 8px', color:'#64748b', fontWeight:'700' }}>MAE</th>
                            <th style={{ textAlign:'right', padding:'6px 8px', color:'#64748b', fontWeight:'700' }}>Bias</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ev.by_stratum.subgroups.map((row, i) => {
                            const name = (row.group || {}).stratum || '—';
                            const thin = (row.n || 0) < perStratum;
                            return (
                              <tr key={i} style={{ borderTop:'1px solid #e2e8f0' }}>
                                <td style={{ padding:'6px 8px', color:'#334155' }}>{name.replace(':', ' · ')}</td>
                                <td style={{ padding:'6px 8px', textAlign:'right', color: thin ? '#b91c1c' : '#64748b' }}>{row.n}{thin ? ' ⚠' : ''}</td>
                                <td style={{ padding:'6px 8px', textAlign:'right', fontWeight:'700', color:'#334155' }}>{mo(row.mae_months)}</td>
                                <td style={{ padding:'6px 8px', textAlign:'right', color:'#64748b' }}>{row.signed_bias_months == null ? '—' : `${row.signed_bias_months > 0 ? '+' : ''}${row.signed_bias_months} mo`}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'6px', lineHeight:'1.5' }}>
                        ⚠ marks a stratum below the minimum count — its figure is too imprecise to support a claim. The reference standard is a consensus of independent expert reads, <strong>not ground truth</strong>; a model inside the readers' own spread is within the band where the reference is uncertain, not better than the readers.
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ marginTop:'10px', background:'#f8fafc', border:'1px dashed #cbd5e1', borderRadius:'8px', padding:'10px' }}>
                  <div style={{ fontSize:'11px', fontWeight:'700', color:'#475569' }}>No local accuracy figure yet</div>
                  <div style={{ fontSize:'10px', color:'#64748b', marginTop:'4px', lineHeight:'1.5' }}>
                    {ev.reason || 'Freeze the cohort once every stratum is complete.'}
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>

      {/* Advanced TW3 workflow: hidden by request, kept intact in BoneAgeAdvanced.jsx */}
      <BoneAgeAdvanced />
    </div>
  );
}

export { BoneAgePanel };
