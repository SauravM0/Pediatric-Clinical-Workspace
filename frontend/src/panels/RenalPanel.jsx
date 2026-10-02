/**
 * Renal panel (eGFR / KDIGO staging).
 *
 * Presentational. Every number comes from backend/renal (via renalMetrics in
 * context): the age-appropriate equation, KDIGO G1-G5 with G3a/G3b, the G x A
 * prognosis heat map, comparison equations and their caveats. This file does
 * no arithmetic -- that is what makes the backend tests the tests of what is
 * shown here.
 */
import { useRenal } from "../state.jsx";
import { StatusBadge, SectionHeader, EmptyState, heroTone } from "../ui.jsx";

const G_CODES = [
  ['G1', '≥ 90', 'Normal/high'], ['G2', '60–89', 'Mild ↓'], ['G3a', '45–59', 'Mild–mod ↓'],
  ['G3b', '30–44', 'Mod–severe ↓'], ['G4', '15–29', 'Severe ↓'], ['G5', '< 15', 'Failure'],
];
const A_CODES = ['A1', 'A2', 'A3'];
// KDIGO heat map colours (same grid as backend/renal/egfr.py _HEAT_MAP).
const HEAT = {
  G1: ['low', 'moderate', 'high'], G2: ['low', 'moderate', 'high'],
  G3a: ['moderate', 'high', 'very_high'], G3b: ['high', 'very_high', 'very_high'],
  G4: ['very_high', 'very_high', 'very_high'], G5: ['very_high', 'very_high', 'very_high'],
};
const HEAT_BG = { low: '#dcfce7', moderate: '#fef9c3', high: '#fed7aa', very_high: '#fecaca' };

function RenalPanel() {
  const { metrics, hasManual } = useRenal();
  const m = metrics;
  const r = m.ready ? m.result : null;
  const g = r && r.gfr_category ? r.gfr_category.code : null;
  const a = r && r.albuminuria_category ? r.albuminuria_category.code : null;
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="Renal Workspace · eGFR & KDIGO"
        subtitle={r ? `${r.primary.equation} · ${r.paediatric ? 'paediatric' : 'adult'} equation` : 'Age-appropriate creatinine equation, KDIGO G × A staging'}
        badge={r && g ? `${g}${a || ''}` : null}
        badgeVariant={r ? m.stageVariant : 'info'}
      />

      {!hasManual ? (
        <EmptyState title="Enter age, sex, height & serum creatinine"
          hint="All four are required (height for the paediatric equation). Add the urine albumin-to-creatinine stage for a KDIGO risk category." />
      ) : !m.ready ? (
        <EmptyState title={m.reason ? 'Not calculated' : m.error ? 'Calculation failed' : 'Calculating…'}
          hint={m.reason || m.error || ''} />
      ) : (<React.Fragment>
      {/* eGFR hero */}
      <div className="hero-result" style={{ ...heroTone(m.stageVariant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
        <div>
          <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>Estimated GFR</div>
          <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
            <span className="hero-value" style={{ fontWeight:'900', color: m.stageVariant === 'high' ? '#b91c1c' : m.stageVariant === 'mid' ? '#b45309' : '#1e293b', lineHeight:1 }}>{r.primary.value.toFixed(1)}</span>
            <span style={{ fontSize:'13px', color:'#6366f1', fontWeight:'600' }}>{r.primary.unit}</span>
          </div>
          <div style={{ fontSize:'11px', color:'#818cf8', marginTop:'4px' }}>{r.primary.equation} · {r.primary.citation}</div>
        </div>
        <div style={{ textAlign:'right', maxWidth:'260px' }}>
          {g && <StatusBadge text={`${g} · ${r.gfr_category.label}`} variant={m.stageVariant === 'info' ? 'neutral' : m.stageVariant} />}
          {r.kdigo_risk && <div style={{ marginTop:'8px' }}><StatusBadge text={r.kdigo_risk.label} variant={m.stageVariant} /></div>}
        </div>
      </div>

      <div style={{ marginTop:'12px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#334155', lineHeight:'1.6' }}>
        {r.interpretation}
      </div>

      {/* GFR categories */}
      {g && (
        <div style={{ marginTop:'16px' }}>
          <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'8px' }}>KDIGO GFR category</div>
          <div className="ckd-stage">
            {G_CODES.map(([code, range, desc]) => (
              <div key={code} className={`ckd-chip ${g === code ? `ckd-active-${code.toLowerCase()}` : 'ckd-inactive'}`}>
                <div style={{ fontWeight:'900', fontSize:'11px' }}>{code}</div>
                <div style={{ fontSize:'9px', marginTop:'2px', fontWeight:'600', opacity:0.85 }}>{range}</div>
                <div style={{ fontSize:'9px', marginTop:'1px', opacity:0.7 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KDIGO G x A heat map, the patient's cell outlined */}
      {g && (
        <div style={{ marginTop:'16px', overflowX:'auto' }}>
          <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'8px' }}>
            KDIGO prognosis (G × albuminuria){!a && ' — record ACR stage to place the patient'}
          </div>
          <table style={{ borderCollapse:'separate', borderSpacing:'3px', fontSize:'10px', width:'100%' }}>
            <thead><tr><th></th>{A_CODES.map(x => <th key={x} style={{ color:'#64748b', fontWeight:800 }}>{x}</th>)}</tr></thead>
            <tbody>
              {G_CODES.map(([code]) => (
                <tr key={code}>
                  <td style={{ fontWeight:800, color:'#64748b', paddingRight:'6px' }}>{code}</td>
                  {A_CODES.map((ac, i) => {
                    const here = code === g && ac === a;
                    return <td key={ac} aria-label={here ? 'this patient' : undefined}
                      style={{ background: HEAT_BG[HEAT[code][i]], textAlign:'center', padding:'5px 2px', borderRadius:'4px',
                               outline: here ? '3px solid #1e293b' : (code === g && !a ? '1px dashed #64748b' : 'none'),
                               fontWeight: here ? 900 : 500 }}>
                      {here ? '●' : ''}
                    </td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ fontSize:'9px', color:'#94a3b8', marginTop:'4px' }}>Green low · yellow moderately increased · orange high · red very high risk</div>
        </div>
      )}

      {/* Comparison equations */}
      {r.alternatives.length > 0 && (
        <div className="secondary-grid" style={{ marginTop:'16px' }}>
          {r.alternatives.map(alt => (
            <div key={alt.equation} style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px', border:'1px solid #e2e8f0' }}>
              <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:'6px' }}>{alt.equation}</div>
              <div style={{ fontSize:'22px', fontWeight:'900', color:'#334155' }}>{alt.value.toFixed(1)}</div>
              <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>{alt.unit}</div>
            </div>
          ))}
        </div>
      )}

      <ul style={{ marginTop:'14px', paddingLeft:'18px', fontSize:'11px', color:'#64748b', lineHeight:'1.6' }}>
        {r.caveats.map(c => <li key={c}>{c}</li>)}
      </ul>
      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        Bedside Schwartz under 18 · CKD-EPI 2021 (race-free) from 18 · CKiD U25 shown to 25 y · none under 1 y · KDIGO G categories from 2 y.
        CKD requires a marker persisting &gt; 3 months.
      </div>
    </div>
  );
}

export { RenalPanel };
