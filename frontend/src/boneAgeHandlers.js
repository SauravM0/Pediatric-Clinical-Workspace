/**
 * Bone-age workflow handlers (M6 panel extraction).
 *
 * The handlers behind the bone-age tab: assessment lifecycle (draft ->
 * calculate -> approve/revise), film upload and the image-quality gate, AI
 * screening, per-bone localisation boxes, the adjudication queue, the licensed
 * TW3 table editor, and clinician feedback.
 *
 * Why a HOOK taking state, rather than a provider owning it
 * ---------------------------------------------------------
 * Bone age was the last and largest panel in App -- 908 lines, 109
 * dependencies. Measured before moving anything: App still needs 27 of the
 * bone-age STATE names (boneMetrics feeds the Overview cards, resetAll clears
 * them, and fatherHeight/motherHeight feed the growth panel's adult-height
 * projection) but ZERO of the handlers.
 *
 * So the handlers move and the state stays. Relocating state that four other
 * consumers already read would mean threading it straight back out -- more
 * plumbing than it removes. The split follows the real dependency direction
 * rather than a tidy-looking rule.
 *
 * `s` is the bone-age state bag App passes in: one object rather than sixty-odd
 * positional arguments, where order would be a hazard and a mistake silent.
 */
function useBoneAgeHandlers(s) {
  const {
    adjReviewer, age, aiEstimate, approverName, assessment, boxes,
    boxesRef, carpalStages, coverage, declaredFlags, estimateDomain,
    evalAge, evalGender, fbAge, fbConfidence, fbMethod, fbNote, fbRater,
    height, lastFilm, locDrag, locImg, locRef, ltTables, monitoring,
    patientCode, radiograph, rusStages, setAdjBusy, setAdjItems,
    setAdjMsg, setAiBusy, setAiEstimate, setAssessment, setBoneAge,
    setBoneAgeSource, setBoxes, setCarpalStages, setCovBusy, setCoverage,
    setDeclaredFlags, setFbAge, setFbBusy, setFbMsg, setFbNote,
    setLastFilm, setLcBusy, setLcMsg, setLocBusy, setLocImg, setLocMsg,
    setLcohBusy, setLocalCohort,
    setLtBusy, setLtMsg, setLtStatus, setLtTables, setMonBusy,
    setMonitoring, setRadiograph, setRusStages, setSelBone, setShowAudit,
    showAudit,
  } = s;

  const LC_API = '/api/bone-age/assessments';
  const lcLocked = assessment && (assessment.assessment_status === 'approved' || assessment.assessment_status === 'superseded');

  // Persist the doctor's 20-bone letter staging as a doctor-confirmed
  // annotation (stage_system 'tw3-letters'). Scoring stays disabled until
  // licensed tables exist, so this is the data-collection stream (directive §7, §11).
  const saveDraft = async () => {
    if (!patientCode.trim()) { setLcMsg({ type:'err', text:'Enter a patient code to save.' }); return; }
    if (evalGender !== 'boys' && evalGender !== 'girls') { setLcMsg({ type:'err', text:'Set biological sex first.' }); return; }
    const carpalEntries = Object.entries(carpalStages).map(([n, g]) => [carpalCode(n), g]);
    if (Object.keys(rusStages).length === 0 && carpalEntries.length === 0) {
      setLcMsg({ type:'err', text:'Grade at least one bone.' }); return;
    }
    setLcBusy(true); setLcMsg(null);
    try {
      let a = assessment;
      if (!a || a.assessment_status === 'approved' || a.assessment_status === 'superseded') {
        const res = await fetch(LC_API, { method:'POST', headers:{ 'Content-Type':'application/json' },
          body: JSON.stringify({ patient_code: patientCode.trim(), sex: evalGender,
            chronological_age_years: age !== "" ? Number(age) : null,
            stage_system: 'tw3-letters' }) });
        if (!res.ok) throw new Error((await res.json()).detail || 'create failed');
        a = await res.json();
      }
      for (const [bone, grade] of [...Object.entries(rusStages), ...carpalEntries]) {
        const r = await fetch(`${LC_API}/${a.id}/bones/${bone}`, { method:'PUT',
          headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ stage: grade }) });
        if (r.ok) { a = await r.json(); }
        else { throw new Error((await r.json()).detail || `could not save ${bone}`); }
      }
      setAssessment(a);
      setLcMsg({ type:'ok', text:`Saved annotation · #${a.id} rev ${a.revision} · ${a.rus_staged_count}/13 RUS + ${a.carpal_staged_count}/7 carpal` });
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
    finally { setLcBusy(false); }
  };

  // Load a saved annotation's bones back into the grids (RUS + carpals).
  const bonesIntoGrids = (bones) => {
    const rus = {}, carp = {}, bx = {};
    (bones || []).forEach(b => {
      if (b.localisation_box) bx[b.bone_code] = b.localisation_box;
      if (!b.confirmed_stage) return;
      if (b.bone_group === 'carpal') carp[carpalName(b.bone_code)] = b.confirmed_stage;
      else rus[b.bone_code] = b.confirmed_stage;
    });
    setRusStages(rus); setCarpalStages(carp); setBoxes(bx);
  };

  const calculateAssessment = async () => {
    if (!assessment) return; setLcBusy(true); setLcMsg(null);
    try {
      const res = await fetch(`${LC_API}/${assessment.id}/calculate`, { method:'POST' });
      const d = await res.json();
      if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'calculate failed' }); }
      else {
        setAssessment(d);
        if (d.bone_age_years != null) { setBoneAge(Number(d.bone_age_years.toFixed(1))); setBoneAgeSource('rus'); }
        setLcMsg({ type:'ok', text:`Calculated · RUS ${d.total_rus_score} → ${d.bone_age_years} yr` });
      }
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
    finally { setLcBusy(false); }
  };

  const approveAssessment = async () => {
    if (!assessment) return;
    if (!approverName.trim()) { setLcMsg({ type:'err', text:'Enter the approving doctor name.' }); return; }
    setLcBusy(true); setLcMsg(null);
    try {
      const res = await fetch(`${LC_API}/${assessment.id}/approve`, { method:'POST',
        headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ approved_by: approverName.trim() }) });
      const d = await res.json();
      if (!res.ok) setLcMsg({ type:'err', text: d.detail || 'approve failed' });
      else { setAssessment(d); setLcMsg({ type:'ok', text:`Approved by ${d.approved_by}` }); }
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
    finally { setLcBusy(false); }
  };

  const reviseAssessment = async () => {
    if (!assessment) return; setLcBusy(true); setLcMsg(null);
    try {
      const res = await fetch(`${LC_API}/${assessment.id}/revise`, { method:'POST',
        headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ reason:'re-read' }) });
      const d = await res.json();
      if (!res.ok) setLcMsg({ type:'err', text: d.detail || 'revise failed' });
      else {
        bonesIntoGrids(d.bones); setAssessment(d); setShowAudit(false);
        setLcMsg({ type:'ok', text:`Opened revision ${d.revision} (draft)` });
      }
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
    finally { setLcBusy(false); }
  };

  const toggleAudit = async () => {
    if (!assessment) return;
    const next = !showAudit; setShowAudit(next);
    if (next) {
      try { const r = await fetch(`${LC_API}/${assessment.id}?include_audit=true`); if (r.ok) setAssessment(await r.json()); } catch {}
    }
  };

  const submitFeedback = async () => {
    const yrs = parseFloat(fbAge);
    if (!(yrs > 0)) { setFbMsg({ type:'err', text:'Enter the correct bone age in years.' }); return; }
    setFbBusy(true); setFbMsg(null);
    try {
      const body = {
        corrected_age_years: yrs,
        method: fbMethod,
        confidence: fbConfidence,
        rater_id: fbRater || null,
        sex: (evalGender === 'boys' || evalGender === 'girls') ? evalGender : null,
        chronological_age_years: evalAge || null,
        ai_estimate_years: (aiEstimate && aiEstimate.bone_age_years != null) ? aiEstimate.bone_age_years : null,
        ai_model_version: (aiEstimate && aiEstimate.model_version) || null,
        radiograph_id: (radiograph && radiograph.id) || null,
        assessment_id: (assessment && assessment.id) || null,
        image_domain: (radiograph && radiograph.source_domain) || estimateDomain || null,
        note: fbNote || null,
      };
      const res = await fetch('/api/bone-age/feedback', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(body) });
      const d = await res.json();
      if (!res.ok) { setFbMsg({ type:'err', text: d.detail || 'could not save' }); }
      else { setFbMsg({ type:'ok', text: d.message || 'Thanks — logged.' }); setFbAge(''); setFbNote(''); }
    } catch (e) { setFbMsg({ type:'err', text: String(e.message || e) }); }
    finally { setFbBusy(false); }
  };

  const runEstimate = async (fileObj, flags) => {
    if (evalGender !== 'boys' && evalGender !== 'girls') { setAiEstimate({ error:'Set biological sex in Demographics first.' }); return; }
    const useFlags = flags || declaredFlags;
    setLastFilm(fileObj);
    setAiBusy(true); setAiEstimate(null);
    try {
      const fd = new FormData(); fd.append('file', fileObj); fd.append('sex', evalGender);
      fd.append('image_domain', estimateDomain); fd.append('declared_flags', useFlags.join(','));
      const res = await fetch('/api/bone-age/estimate', { method:'POST', body: fd });
      const d = await res.json();
      // Keep the full response: it may be an estimate, an acceptability
      // ABSTENTION (available:false, accepted:false), or a no-model notice.
      if (!res.ok) setAiEstimate({ error: d.detail || 'estimate failed' });
      else setAiEstimate(d);
    } catch (e) { setAiEstimate({ error: String(e.message || e) }); }
    finally { setAiBusy(false); }
  };

  // Toggle a declared image issue; re-gate the last film immediately so the
  // estimate abstains/returns without needing a re-attach.
  const toggleDeclaredFlag = (code) => {
    setDeclaredFlags(prev => {
      const next = prev.includes(code) ? prev.filter(f => f !== code) : [...prev, code];
      if (lastFilm) runEstimate(lastFilm, next);
      return next;
    });
  };

  const attachImage = async (fileObj) => {
    if (!assessment) { setLcMsg({ type:'err', text:'Save the draft first, then attach a film.' }); return; }
    if (lcLocked) { setLcMsg({ type:'err', text:'Assessment is locked; open a revision to change the image.' }); return; }
    setLcBusy(true); setLcMsg(null);
    try {
      const fd = new FormData(); fd.append('file', fileObj);
      const res = await fetch(`${LC_API}/${assessment.id}/image`, { method:'POST', body: fd });
      const d = await res.json();
      if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'upload failed' }); }
      else {
        setRadiograph(d);
        setLcMsg({ type:'ok', text:`Film attached · ${d.source_format} · ${d.quality_status.replace(/_/g, ' ')}` });
        // Auto-analyse the attached film so the report populates immediately.
        runEstimate(fileObj);   // AI whole-image bone age (screening)
        localizeBones();        // auto-locate bones (if a localizer model is installed)
      }
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
    finally { setLcBusy(false); }
  };

  const loadCoverage = async () => {
    setCovBusy(true);
    try {
      const r = await fetch('/api/bone-age/coverage');
      if (r.ok) setCoverage(await r.json());
    } catch {}
    finally { setCovBusy(false); }
  };

  const loadMonitoring = async () => {
    setMonBusy(true);
    try {
      const r = await fetch('/api/bone-age/monitoring');
      if (r.ok) setMonitoring(await r.json());
    } catch {}
    finally { setMonBusy(false); }
  };

  const loadLocalCohort = async () => {
    setLcohBusy(true);
    try {
      const r = await fetch('/api/bone-age/local-cohort');
      if (r.ok) setLocalCohort(await r.json());
    } catch {}
    finally { setLcohBusy(false); }
  };

  const loadAdjudication = async () => {
    setAdjBusy(true); setAdjMsg(null);
    try {
      const r = await fetch('/api/bone-age/adjudication?status=open');
      if (r.ok) setAdjItems((await r.json()).items || []);
    } catch (e) { setAdjMsg({ type:'err', text:String(e.message||e) }); }
    finally { setAdjBusy(false); }
  };

  const resolveAdjudication = async (id, stage) => {
    if (!adjReviewer.trim()) { setAdjMsg({ type:'err', text:'Enter the reviewing clinician first.' }); return; }
    setAdjBusy(true); setAdjMsg(null);
    try {
      const r = await fetch(`/api/bone-age/adjudication/${id}/resolve`, {
        method:'POST', headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ resolved_stage: stage, resolved_by: adjReviewer.trim() }),
      });
      if (r.ok) { setAdjMsg({ type:'ok', text:`Resolved to stage ${stage}.` }); await loadAdjudication(); }
      else { const e = await r.json(); setAdjMsg({ type:'err', text: e.detail || 'Resolve failed.' }); }
    } catch (e) { setAdjMsg({ type:'err', text:String(e.message||e) }); }
    finally { setAdjBusy(false); }
  };

  // ── Licensed TW3 table entry (original-TW3 letters) ──────────────────────
  const _emptyLt = () => ({
    method:'TW3-letters', version:'letters-clinic',
    rus_stage_to_score:{ boys:{}, girls:{} },
    carpal_stage_to_score:{ boys:{}, girls:{} },
    rus_score_to_age:{ twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} },
    carpal_score_to_age:{ twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} },
    tw20_stage_to_score:{ boys:{}, girls:{} },
    tw20_score_to_age:{ boys:[], girls:[] },
    reference_cases:[],
  });
  const loadLetterTables = async () => {
    setLtBusy(true); setLtMsg(null);
    try {
      const d = await (await fetch('/api/bone-age/letters-tables')).json();
      const t = (d.tables && d.tables.rus_stage_to_score) ? d.tables : _emptyLt();
      t.rus_stage_to_score = t.rus_stage_to_score || { boys:{}, girls:{} };
      t.carpal_stage_to_score = t.carpal_stage_to_score || { boys:{}, girls:{} };
      t.rus_score_to_age = t.rus_score_to_age || { twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} };
      t.carpal_score_to_age = t.carpal_score_to_age || { twii:{boys:[],girls:[]}, twiii:{boys:[],girls:[]} };
      t.tw20_stage_to_score = t.tw20_stage_to_score || { boys:{}, girls:{} };
      t.tw20_score_to_age = t.tw20_score_to_age || { boys:[], girls:[] };
      t.reference_cases = (t.reference_cases || []).filter(c => c && !c._fill && !String(c.id||'').startsWith('example'));
      setLtTables(t); setLtStatus(d.status);
    } catch (e) { setLtMsg({ type:'err', text:String(e.message||e) }); }
    finally { setLtBusy(false); }
  };
  const setLtPoint = (group, sex, bone, letter, val) => {
    setLtTables(prev => {
      const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
      t[group][sex] = t[group][sex] || {}; t[group][sex][bone] = t[group][sex][bone] || {};
      if (val === '' || val === null) delete t[group][sex][bone][letter];
      else t[group][sex][bone][letter] = Number(val);
      return t;
    });
  };
  const curveToText = (arr) => (arr||[]).map(p => p.join(', ')).join('\n');
  const parseCurve = (text) => text.split('\n').map(l => l.trim()).filter(Boolean)
    .map(l => l.split(/[\s,]+/).map(Number)).filter(p => p.length===2 && p.every(n => !isNaN(n)));
  const setLtCurve = (group, curve, sex, text) => {
    setLtTables(prev => {
      const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
      t[group][curve] = t[group][curve] || {}; t[group][curve][sex] = parseCurve(text);
      return t;
    });
  };
  const setLtSexCurve = (group, sex, text) => {  // single [sex]->anchors curve (TWII'20)
    setLtTables(prev => {
      const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
      t[group] = t[group] || {}; t[group][sex] = parseCurve(text);
      return t;
    });
  };
  const useGridAsReference = () => {
    const rus = { ...rusStages };
    const carp = {}; Object.entries(carpalStages).forEach(([n,g]) => carp[carpalCode(n)] = g);
    setLtTables(prev => {
      const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
      t.reference_cases = [{ id:'clinic-ref-1', sex: evalGender === 'girls' ? 'girls' : 'boys',
        rus_stages: rus, carpal_stages: carp,
        expected: (t.reference_cases[0] && t.reference_cases[0].expected) || { rus_score:null, twiii_rus_age_years:null },
        tolerance_years: 0.3 }];
      return t;
    });
    setLtMsg({ type:'ok', text:'Reference stages captured from the grading grid. Now enter the reported score/age below.' });
  };
  const setRefExpected = (field, val) => {
    setLtTables(prev => {
      const t = JSON.parse(JSON.stringify(prev || _emptyLt()));
      if (!t.reference_cases[0]) t.reference_cases[0] = { id:'clinic-ref-1', sex:'girls', rus_stages:{}, carpal_stages:{}, expected:{}, tolerance_years:0.3 };
      t.reference_cases[0].expected = t.reference_cases[0].expected || {};
      t.reference_cases[0].expected[field] = (val === '' ? null : Number(val));
      return t;
    });
  };
  const saveLetterTables = async () => {
    setLtBusy(true); setLtMsg(null);
    try {
      const r = await fetch('/api/bone-age/letters-tables', { method:'PUT',
        headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ tables: ltTables }) });
      const d = await r.json();
      if (!r.ok) { setLtMsg({ type:'err', text: d.detail || 'save failed' }); }
      else {
        setLtStatus(d.status);
        if (d.status.scoring_ready) setLtMsg({ type:'ok', text:'Saved — TW3 scoring is ON (accuracy gate passed). The report now fills with real numbers.' });
        else if (!d.status.reference_validation.all_passed && d.status.reference_validation.n_cases > 0)
          setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: the reference case is not reproduced by these values — recheck the points/curve or the reported numbers.' });
        else if (d.status.provenance_complete === false)
          setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: document the licensed source in the Provenance tab (book, edition, owner, who entered/verified, date).' });
        else setLtMsg({ type:'err', text:'Saved, but scoring stays OFF: fill every bone’s points, the score→age curves, and a reference case.' });
      }
    } catch (e) { setLtMsg({ type:'err', text:String(e.message||e) }); }
    finally { setLtBusy(false); }
  };

  const setImageDomain = async (domain) => {
    if (!assessment) return;
    try {
      const res = await fetch(`${LC_API}/${assessment.id}/image-domain`, { method:'PUT',
        headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ domain }) });
      const d = await res.json();
      if (!res.ok) { setLcMsg({ type:'err', text: d.detail || 'could not set domain' }); }
      else { setRadiograph(r => ({ ...(r||{}), source_domain: d.source_domain })); }
    } catch (e) { setLcMsg({ type:'err', text: String(e.message || e) }); }
  };

  // ── Bone localization (PEA auto-boxes + doctor correction) ──────────────────
  const analysisUrl = radiograph ? `/api/bone-age/radiographs/${radiograph.radiograph_id}/analysis` : null;
  const localizeBones = async () => {
    if (!assessment) { setLocMsg({ type:'err', text:'Save the annotation and attach a film first.' }); return; }
    setLocBusy(true); setLocMsg(null);
    try {
      const res = await fetch(`${LC_API}/${assessment.id}/localize`, { method:'POST' });
      const d = await res.json();
      if (!res.ok) { setLocMsg({ type:'err', text: d.detail || 'localize failed' }); return; }
      if (d.image_width) setLocImg({ width: d.image_width, height: d.image_height });
      if (!d.available) { setLocMsg({ type:'err', text: d.message || 'No localizer model installed.' }); return; }
      const nb = { ...boxes }; (d.boxes || []).forEach(b => { nb[b.bone_code] = b.box; });
      setBoxes(nb);
      setLocMsg({ type:'ok', text:`Auto-located ${(d.boxes||[]).length} bones — drag to correct, then Save boxes.` });
    } catch (e) { setLocMsg({ type:'err', text:String(e.message||e) }); }
    finally { setLocBusy(false); }
  };
  const addOrSelectBox = (bone) => {
    setSelBone(bone);
    setBoxes(prev => {
      if (prev[bone] || !locImg) return prev;
      const s = Math.min(locImg.width, locImg.height) * 0.16;
      const cx = locImg.width / 2, cy = locImg.height / 2;
      return { ...prev, [bone]: [cx - s/2, cy - s/2, cx + s/2, cy + s/2] };
    });
  };
  const clearBox = (bone) => setBoxes(prev => { const n = { ...prev }; delete n[bone]; return n; });
  const saveBoxes = async () => {
    if (!assessment) return; setLocBusy(true); setLocMsg(null);
    try {
      let a = assessment;
      const cur = boxesRef.current;            // read current boxes, not a stale closure
      const codes = new Set(Object.keys(cur));
      // save present boxes; clear any that were removed
      for (const [bone, box] of Object.entries(cur)) {
        const r = await fetch(`${LC_API}/${assessment.id}/bones/${bone}/box`, { method:'PUT',
          headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ box: box.map(v => Math.round(v*10)/10) }) });
        if (r.ok) a = await r.json(); else throw new Error((await r.json()).detail || `save ${bone}`);
      }
      (a.bones || []).forEach(async b => {
        if (b.localisation_box && !codes.has(b.bone_code)) {
          await fetch(`${LC_API}/${assessment.id}/bones/${b.bone_code}/box`, { method:'PUT',
            headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ box: null }) });
        }
      });
      setAssessment(a);
      setLocMsg({ type:'ok', text:`Saved ${codes.size} bone box${codes.size===1?'':'es'}.` });
    } catch (e) { setLocMsg({ type:'err', text:String(e.message||e) }); }
    finally { setLocBusy(false); }
  };
  const startBoxDrag = (bone, mode, e) => {
    e.preventDefault(); e.stopPropagation();
    if (!locRef.current || !locImg) return;
    const rect = locRef.current.getBoundingClientRect();
    const scale = rect.width / locImg.width;
    locDrag.current = { bone, mode, mx:(e.clientX-rect.left)/scale, my:(e.clientY-rect.top)/scale,
      orig:[...(boxesRef.current[bone] || [0,0,0,0])] };
    setSelBone(bone);
  };
  const onLocMove = (e) => {
    const d = locDrag.current; if (!d || !locRef.current || !locImg) return;
    const rect = locRef.current.getBoundingClientRect();
    const scale = rect.width / locImg.width;
    const mx = (e.clientX-rect.left)/scale, my = (e.clientY-rect.top)/scale;
    const W = locImg.width, H = locImg.height, clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
    setBoxes(prev => {
      let [x0,y0,x1,y1] = d.orig;
      if (d.mode === 'move') {
        let dx = mx-d.mx, dy = my-d.my;
        dx = clamp(dx, -x0, W-x1); dy = clamp(dy, -y0, H-y1);
        return { ...prev, [d.bone]:[x0+dx,y0+dy,x1+dx,y1+dy] };
      }
      return { ...prev, [d.bone]:[x0, y0, clamp(mx, x0+8, W), clamp(my, y0+8, H)] };
    });
  };
  const endLocDrag = () => { locDrag.current = null; };

  const lcBtn = (bg, disabled) => ({ padding:'7px 12px', background: disabled ? '#cbd5e1' : bg,
    color:'white', border:'none', borderRadius:'8px', fontSize:'11px', fontWeight:'700',
    cursor: disabled ? 'not-allowed' : 'pointer' });

  return {
    LC_API, lcLocked, saveDraft, bonesIntoGrids, calculateAssessment,
    approveAssessment, reviseAssessment, toggleAudit, submitFeedback,
    runEstimate, toggleDeclaredFlag, attachImage, loadCoverage,
    loadMonitoring, loadLocalCohort, loadAdjudication, resolveAdjudication, _emptyLt,
    loadLetterTables, setLtPoint, curveToText, parseCurve, setLtCurve,
    setLtSexCurve, useGridAsReference, setRefExpected, saveLetterTables,
    setImageDomain, analysisUrl, localizeBones, addOrSelectBox, clearBox,
    saveBoxes, startBoxDrag, onLocMove, endLocDrag, lcBtn,
  };
}

export { useBoneAgeHandlers };
