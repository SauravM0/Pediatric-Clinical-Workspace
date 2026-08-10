/**
 * The left-hand input column (M6 panel extraction).
 *
 * Three cards -- demographics, clinical labs, FRAX risk factors -- and the last
 * large markup block that was still inline in App.
 *
 * Not a panel in the tab sense: it is the EDITOR for the measurements every tab
 * reads, and it stays on screen whichever tab is open. That is why it is the
 * only consumer of `useInputs()`, the only slice carrying setters for the shared
 * demographics and labs. Everything else reads derived metrics.
 *
 * The cards de-emphasise rather than disable when the active tab does not use
 * them (`labsRelevant` / `fraxRelevant`): results still recalculate as you type,
 * so a clinician entering data out of order is never blocked -- the dimming is a
 * hint about relevance, not a gate.
 */
import { useInputs } from "../state.jsx";
import { FraxToggleRow, InputWithUnit } from "../ui.jsx";

function InputColumn() {
  const {
    age, handleAgeChange, dob, handleDobChange, ageParts,
    gender, setGender, height, setHeight, weight, setWeight,
    labsRelevant, fraxRelevant,
    creatinine, setCreatinine, albuminuria, setAlbuminuria,
    systolic, setSystolic, diastolic, setDiastolic,
    ast, setAst, alt, setAlt, platelets, setPlatelets,
    prevFracture, setPrevFracture, parentHipFracture, setParentHipFracture,
    smoking, setSmoking, glucocorticoids, setGlucocorticoids,
    rheumatoid, setRheumatoid, secondaryOsteo, setSecondaryOsteo,
    alcohol, setAlcohol,
  } = useInputs();

  return (
    <div className="input-column">

      {/* Card: Demographics */}
      <div className="card" style={{ padding:'20px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
          <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#4f46e5', flexShrink:0 }}></div>
          <span className="section-label">Demographics</span>
          <span style={{ marginLeft:'auto', fontSize:'9px', fontWeight:'700', color:'#cbd5e1', textTransform:'uppercase', letterSpacing:'0.05em' }}>Required</span>
        </div>

        <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
          {/* Age or Date of birth — enter either one */}
          <div>
            <div className="form-grid">
              <InputWithUnit
                label="Chronological Age"
                value={age}
                onChange={handleAgeChange}
                placeholder="e.g. 9.5"
                step="0.1"
                unit="yrs"
                unitPosition="right"
                accent="#4f46e5"
              />
              <div style={{ minWidth:0 }}>
                <label className="field-label">Date of Birth</label>
                <input
                  type="date"
                  value={dob}
                  onChange={handleDobChange}
                  max={new Date().toISOString().split('T')[0]}
                  className="input-field"
                  style={{ width:'100%', color: dob ? '#1e293b' : '#94a3b8' }}
                />
              </div>
            </div>
            {ageParts ? (
              <div style={{ marginTop:'8px', fontSize:'11px', color:'#4338ca', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'8px', padding:'7px 10px', lineHeight:'1.5' }}>
                Age <strong>{ageParts.years} yr {ageParts.months} mo {ageParts.days} d</strong>
                <span style={{ color:'#818cf8' }}> · used as {ageParts.decimal.toFixed(1)} yr in calculations</span>
              </div>
            ) : (
              <div style={{ marginTop:'6px', fontSize:'10px', color:'#94a3b8', lineHeight:'1.4' }}>
                Enter an age directly, or a date of birth to compute it automatically.
              </div>
            )}
          </div>

          {/* Gender */}
          <div>
            <label className="field-label">Biological Sex</label>
            <div style={{ display:'flex', gap:'8px' }}>
              <button className={`gender-btn ${gender === 'boys' ? 'gender-active' : 'gender-inactive'}`} onClick={() => setGender('boys')}>
                ♂ Male
              </button>
              <button className={`gender-btn ${gender === 'girls' ? 'gender-active' : 'gender-inactive'}`} onClick={() => setGender('girls')}>
                ♀ Female
              </button>
            </div>
          </div>

          {/* Height + Weight */}
          <div className="form-grid">
            <InputWithUnit label="Height" value={height} onChange={e => setHeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="cm" unit="cm" />
            <InputWithUnit label="Weight" value={weight} onChange={e => setWeight(e.target.value === "" ? "" : parseFloat(e.target.value))} placeholder="kg" unit="kg" />
          </div>
        </div>
      </div>

      {/* Card: Labs */}
      <div className={`card${labsRelevant ? '' : ' section-dim'}`} style={{ padding:'20px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'16px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
          <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#0891b2', flexShrink:0 }}></div>
          <span className="section-label">Clinical Labs & Parameters</span>
        </div>

        <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
          {/* Creatinine */}
          <InputWithUnit
            label="Serum Creatinine"
            value={creatinine}
            onChange={e => setCreatinine(e.target.value === "" ? "" : parseFloat(e.target.value))}
            placeholder="mg/dL"
            step="0.01"
            unit="mg/dL"
            accent="#0891b2"
          />

          {/* Albuminuria */}
          <div>
            <label className="field-label">Albuminuria / ACR Stage</label>
            <div style={{ display:'flex', gap:'8px' }}>
              {[['A1','< 30 mg/g'],['A2','30–300 mg/g'],['A3','> 300 mg/g']].map(([lv, desc]) => (
                <button key={lv} className={`alb-btn ${albuminuria === lv ? 'alb-active' : 'alb-inactive'}`} onClick={() => setAlbuminuria(lv)}>
                  <div style={{ fontSize:'12px', fontWeight:'800', color: albuminuria === lv ? '#4338ca' : '#334155' }}>{lv}</div>
                  <div style={{ fontSize:'9px', color:'#94a3b8', marginTop:'2px' }}>{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* BP */}
          <div className="form-grid">
            <InputWithUnit label="Systolic BP" value={systolic} onChange={e => setSystolic(e.target.value === "" ? "" : parseInt(e.target.value))} placeholder="mmHg" unit="mmHg" />
            <InputWithUnit label="Diastolic BP" value={diastolic} onChange={e => setDiastolic(e.target.value === "" ? "" : parseInt(e.target.value))} placeholder="mmHg" unit="mmHg" />
          </div>

          {/* Liver enzymes */}
          <div style={{ paddingTop:'12px', borderTop:'1px solid #f1f5f9' }}>
            <label className="field-label" style={{ marginBottom:'10px' }}>Hepatic Enzymes & Platelets</label>
            <div className="liver-grid">
              {[
                ['AST', 'SGOT · U/L', ast, e => setAst(e.target.value === "" ? "" : parseFloat(e.target.value))],
                ['ALT', 'SGPT · U/L', alt, e => setAlt(e.target.value === "" ? "" : parseFloat(e.target.value))],
                ['PLT', '×10³ / µL', platelets, e => setPlatelets(e.target.value === "" ? "" : parseFloat(e.target.value))],
              ].map(([lbl, sub, val, fn]) => (
                <div key={lbl} style={{ display:'flex', flexDirection:'column', alignItems:'stretch' }}>
                  <span style={{ fontSize:'12px', fontWeight:'800', color:'#334155', textAlign:'center', display:'block', marginBottom:'2px' }}>{lbl}</span>
                  <span style={{ fontSize:'9px', fontWeight:'600', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', textAlign:'center', display:'block', marginBottom:'6px' }}>{sub}</span>
                  <input
                    type="number"
                    placeholder="—"
                    value={val}
                    onChange={fn}
                    className="input-field"
                    style={{ textAlign:'center', padding:'9px 8px', width:'100%', boxSizing:'border-box' }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Card: FRAX */}
      <div className={`card${fraxRelevant ? '' : ' section-dim'}`} style={{ padding:'20px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'14px', paddingBottom:'12px', borderBottom:'1px solid #f1f5f9' }}>
          <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#d97706', flexShrink:0 }}></div>
          <span className="section-label">FRAX Risk Factors</span>
          <span style={{ marginLeft:'auto', fontSize:'9px', fontWeight:'700', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em' }}>India · No BMD</span>
        </div>
        <div>
          <FraxToggleRow label="Previous Fracture" value={prevFracture} setter={setPrevFracture} />
          <FraxToggleRow label="Parent Hip Fracture" value={parentHipFracture} setter={setParentHipFracture} />
          <FraxToggleRow label="Current Smoking" value={smoking} setter={setSmoking} />
          <FraxToggleRow label="Glucocorticoids" value={glucocorticoids} setter={setGlucocorticoids} />
          <FraxToggleRow label="Rheumatoid Arthritis" value={rheumatoid} setter={setRheumatoid} />
          <FraxToggleRow label="Secondary Osteoporosis" value={secondaryOsteo} setter={setSecondaryOsteo} />
          <FraxToggleRow label="Alcohol ≥ 3 units/day" value={alcohol} setter={setAlcohol} />
        </div>
      </div>

    </div>
  );
}

export { InputColumn };
