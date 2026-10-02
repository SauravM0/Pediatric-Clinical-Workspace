/**
 * The Advanced bone-age workflow, split out of BoneAgePanel (step 7).
 *
 * Collapsed by default under "Advanced" (it was hidden until step 8): manual TW3
 * letter grading, the annotation record with Save / Calculate / Approve,
 * localisation boxes, dataset coverage, monitoring, adjudication, the
 * licensed-table editor, the adult-height section and the clinical notes.
 *
 * Approve is the only way a bone age reaches the clinical rules
 * (clinical_service reads approved assessments only). The AI estimate on the
 * main panel can never be approved: it is not an assessment.
 */
import { useBoneAge } from "../state.jsx";
import { rangeProblem } from "../clinicalRanges.js";
import { TW3_CONFIG, REPORT_RUS, REPORT_CARPALS, LETTER_STAGES, carpalCode, IMAGE_DOMAINS, LOW_TRUST_DOMAINS } from "../domain.js";
import { StatusBadge, MetricRow, InputWithUnit } from "../ui.jsx";

function BoneAgeAdvanced() {
  const {
    LC_API, addOrSelectBox, adjBusy, adjItems, adjMsg, adjReviewer, age,
    analysisUrl, assessment, attachImage, boneAge, boneAgeSource,
    boneMetrics, bonesIntoGrids, boxes, carpalStages, clearBox, covBusy,
    coverage, curveToText, endLocDrag, evalAge, evalGender, evalHeight,
    fatherHeight, height, lcBtn, lcBusy, lcLocked, lcMsg, loadAdjudication,
    loadCoverage, loadLetterTables, loadMonitoring, locBusy, locImg, locMsg,
    locRef, localizeBones, ltBusy, ltMsg, ltSection, ltSex, ltStatus,
    ltTables, monBusy, monitoring, motherHeight, onLocMove, patientCode,
    radiograph, resolveAdjudication, reviseAssessment, rusStages, saveBoxes,
    saveDraft, saveLetterTables, selBone, setAdjReviewer, setAssessment,
    setBoneAge, setBoneAgeSource, setCarpalStages, setFatherHeight,
    setImageDomain, setLcBusy, setLcMsg, setLocImg, setLtCurve, setLtPoint,
    setLtSection, setLtSex, setLtSexCurve, setLtTables, setMotherHeight,
    setPatientCode, setRefExpected, setRusStages, setShowAudit, showAudit,
    startBoxDrag, toggleAudit, calculateAssessment, approveAssessment,
    unsavedStaging, useGridAsReference,
  } = useBoneAge();

  return (
    <React.Fragment>
      {/* Advanced TW3 workflow, collapsed by default. */}
      <details style={{ marginTop:'16px' }}>
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
          {assessment && !lcLocked && (
            <button onClick={calculateAssessment} disabled={lcBusy || unsavedStaging}
                    title={unsavedStaging ? 'Save the annotation first' : 'Score the saved staging'}
                    style={lcBtn('#0f766e', lcBusy || unsavedStaging)}>Calculate</button>
          )}
          {assessment && !lcLocked && (() => {
            const canApprove = assessment.assessment_status === 'ready_for_review'
              && assessment.bone_age_years != null && !unsavedStaging;
            return (
              <button onClick={approveAssessment} disabled={lcBusy || !canApprove}
                      title={canApprove ? 'Approve this bone age for clinical use' : 'Calculate a bone age first'}
                      style={lcBtn('#059669', lcBusy || !canApprove)}>Approve</button>
            );
          })()}
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
            {assessment.bone_age_years != null && <> · bone age <strong>{assessment.bone_age_years.toFixed(1)} yr</strong></>}
            {assessment.assessment_status === 'approved' && assessment.approved_by && <> · approved by {assessment.approved_by}</>}
            {unsavedStaging && !lcLocked && <span style={{ color:'#b45309', fontWeight:'700' }}> · unsaved grade changes</span>}
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
        <InputWithUnit label="Father's Height" value={fatherHeight} onChange={e => setFatherHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm (optional)" unit="cm" problem={rangeProblem('parentHeight', fatherHeight)} />
        <InputWithUnit label="Mother's Height" value={motherHeight} onChange={e => setMotherHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm (optional)" unit="cm" problem={rangeProblem('parentHeight', motherHeight)} />
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
          <MetricRow label="Current Height" value={height !== "" ? evalHeight.toFixed(1) : '—'} unit="cm"
            sub={age !== "" ? `Chronological age ${evalAge.toFixed(1)} yr` : 'Chronological age not entered'} />
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
    </React.Fragment>
  );
}

export { BoneAgeAdvanced };
