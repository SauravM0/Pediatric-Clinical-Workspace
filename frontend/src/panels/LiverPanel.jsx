/**
 * Liver panel (FIB-4 fibrosis index).
 *
 * Presentational, same contract as the other panels: derived metrics in, markup
 * out. The paediatric caveat below age 18 is part of the panel, not the maths --
 * FIB-4 is simply not validated in children.
 */
import { useLiver, usePatient } from "../state.jsx";
import { SectionHeader, StatusBadge, EmptyState, MetricRow, ProbBar,
         FraxToggleRow, heroTone } from "../ui.jsx";

function LiverPanel() {
  const { metrics, hasManual, platelets } = useLiver();
  const { evalAge, age, height } = usePatient();
  const liverMetrics = metrics;
  const hasManualLiver = hasManual;
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="Liver Fibrosis · FIB-4 Index"
        subtitle="Non-invasive hepatic fibrosis staging — Age · AST · ALT · Platelets"
        badge={hasManualLiver ? liverMetrics.interpretation : null}
        badgeVariant={hasManualLiver ? liverMetrics.variant : 'info'}
      />

      {!hasManualLiver ? (
        <EmptyState title="Enter AST, ALT & platelets"
          hint="FIB-4 needs AST, ALT and platelet count (plus age). No score is shown until all three are entered." />
      ) : (<React.Fragment>
      {/* FIB-4 hero */}
      <div className="hero-result" style={{ ...heroTone(liverMetrics.variant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
        <div>
          <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>FIB-4 Score</div>
          <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
            <span className="hero-value" style={{ fontWeight:'900', color: liverMetrics.variant === 'high' ? '#b91c1c' : liverMetrics.variant === 'mid' ? '#b45309' : '#15803d', lineHeight:1 }}>{liverMetrics.fib4.toFixed(2)}</span>
            <span style={{ fontSize:'13px', color:'#64748b', fontWeight:'600' }}>index</span>
          </div>
          <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'4px' }}>Formula: (Age × AST) / (Platelets × √ALT)</div>
        </div>
        <div>
          <StatusBadge text={liverMetrics.interpretation} variant={liverMetrics.variant} />
          <div style={{ fontSize:'12px', color:'#64748b', marginTop:'10px', maxWidth:'200px', lineHeight:'1.5' }}>{liverMetrics.details}</div>
        </div>
      </div>

      {/* FIB-4 scale bar */}
      <div style={{ marginTop:'20px', background:'#f8fafc', borderRadius:'12px', padding:'16px', border:'1px solid #e2e8f0' }}>
        <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'12px' }}>Risk Scale</div>
        <div style={{ position:'relative', height:'10px', borderRadius:'99px', background:'linear-gradient(to right, #22c55e 0%, #22c55e 48%, #eab308 48%, #eab308 74%, #ef4444 74%, #ef4444 100%)' }}>
          {/* marker at FIB-4 value (max ~5) */}
          <div style={{ position:'absolute', top:'-4px', left:`${Math.min(Math.max((liverMetrics.fib4/5)*100,1),99)}%`, width:'18px', height:'18px', borderRadius:'50%', background:'white', border:'3px solid #334155', transform:'translateX(-50%)', boxShadow:'0 1px 4px rgba(0,0,0,0.2)' }}></div>
        </div>
        <div style={{ display:'flex', justifyContent:'space-between', marginTop:'8px', fontSize:'10px', fontWeight:'700', color:'#94a3b8' }}>
          <span>0</span>
          <span style={{ color:'#16a34a' }}>Low &lt; 1.30</span>
          <span style={{ color:'#d97706' }}>Indeterminate 1.30–2.67</span>
          <span style={{ color:'#dc2626' }}>High &gt; 2.67</span>
        </div>
      </div>

      {evalAge < 18 && (
        <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
          ⚠ FIB-4 is not validated in pediatric cohorts (age &lt; 18). Interpret with caution.
        </div>
      )}

      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        FIB-4 ranges — Low: &lt; 1.30 · Indeterminate: 1.30–2.67 · High: ≥ 2.67
        {evalAge > 65 ? '  (Age > 65 — indeterminate threshold adjusted to 2.0)' : ''}
      </div>
    </div>
  );
}

export { LiverPanel };
