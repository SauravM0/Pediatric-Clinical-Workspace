/**
 * Liver panel (FIB-4 fibrosis index).
 *
 * Presentational. The score, its category, the age-dependent cut-offs and the
 * caveats all come from backend/hepatic via liverMetrics. Under 18 the backend
 * returns the number with NO category -- FIB-4 is not validated in children and
 * its age numerator makes a child's score low by construction.
 */
import { useLiver } from "../state.jsx";
import { StatusBadge, SectionHeader, EmptyState, heroTone } from "../ui.jsx";

function LiverPanel() {
  const { metrics, hasManual } = useLiver();
  const m = metrics;
  const r = m.ready ? m.result : null;
  const scaleMax = 5;
  const pos = (v) => Math.min(Math.max((v / scaleMax) * 100, 1), 99);
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="Liver Fibrosis · FIB-4 Index"
        subtitle="Non-invasive fibrosis risk — Age · AST · ALT · Platelets"
        badge={r ? m.interpretation : null}
        badgeVariant={r ? (m.variant === 'info' ? 'neutral' : m.variant) : 'info'}
      />

      {!hasManual ? (
        <EmptyState title="Enter age, AST, ALT & platelets"
          hint="FIB-4 needs all four. No score is shown until they are entered." />
      ) : !m.ready ? (
        <EmptyState title={m.reason ? 'Not calculated' : m.error ? 'Calculation failed' : 'Calculating…'}
          hint={m.reason || m.error || ''} />
      ) : (<React.Fragment>
      <div className="hero-result" style={{ ...heroTone(m.variant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
        <div>
          <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>FIB-4 Score</div>
          <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
            <span className="hero-value" style={{ fontWeight:'900', color: m.variant === 'high' ? '#b91c1c' : m.variant === 'mid' ? '#b45309' : m.variant === 'low' ? '#15803d' : '#334155', lineHeight:1 }}>{r.fib4.toFixed(2)}</span>
            <span style={{ fontSize:'13px', color:'#64748b', fontWeight:'600' }}>index</span>
          </div>
          <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>(Age × AST) / (Platelets × √ALT) · {r.citation}</div>
        </div>
        <div>
          <StatusBadge text={r.category_label} variant={m.variant === 'info' ? 'neutral' : m.variant} />
        </div>
      </div>

      {r.category && (
        <div style={{ marginTop:'20px', background:'#f8fafc', borderRadius:'12px', padding:'16px', border:'1px solid #e2e8f0' }}>
          <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'12px' }}>Risk Scale</div>
          <div style={{ position:'relative', height:'10px', borderRadius:'99px',
            background:`linear-gradient(to right, #22c55e 0%, #22c55e ${pos(r.cutoffs.low_below)}%, #eab308 ${pos(r.cutoffs.low_below)}%, #eab308 ${pos(r.cutoffs.high_at_or_above)}%, #ef4444 ${pos(r.cutoffs.high_at_or_above)}%, #ef4444 100%)` }}>
            <div style={{ position:'absolute', top:'-4px', left:`${pos(r.fib4)}%`, width:'18px', height:'18px', borderRadius:'50%', background:'white', border:'3px solid #334155', transform:'translateX(-50%)', boxShadow:'0 1px 4px rgba(0,0,0,0.2)' }}></div>
          </div>
          <div style={{ display:'flex', justifyContent:'space-between', marginTop:'8px', fontSize:'10px', fontWeight:'700', color:'#94a3b8', flexWrap:'wrap', gap:'4px' }}>
            <span style={{ color:'#16a34a' }}>Low &lt; {r.cutoffs.low_below.toFixed(2)}</span>
            <span style={{ color:'#d97706' }}>Indeterminate {r.cutoffs.low_below.toFixed(2)}–{r.cutoffs.high_at_or_above.toFixed(2)}</span>
            <span style={{ color:'#dc2626' }}>High ≥ {r.cutoffs.high_at_or_above.toFixed(2)}</span>
          </div>
        </div>
      )}

      <ul style={{ marginTop:'14px', paddingLeft:'18px', fontSize:'11px', color:'#92400e', lineHeight:'1.6' }}>
        {r.caveats.map(c => <li key={c}>{c}</li>)}
      </ul>
      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        Cut-offs: low &lt; 1.30 (&lt; 2.0 from age 65), high ≥ 2.67 (AASLD 2023; McPherson 2017). No category under 18.
      </div>
    </div>
  );
}

export { LiverPanel };
