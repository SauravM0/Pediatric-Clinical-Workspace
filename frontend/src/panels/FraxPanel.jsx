/**
 * FRAX panel (10-year fracture probability).
 *
 * Presentational. Reads its metrics from context because the Overview summary
 * card renders the same numbers.
 */
import { useFrax, usePatient } from "../state.jsx";
import { SectionHeader, StatusBadge, EmptyState, MetricRow, ProbBar,
         FraxToggleRow, heroTone } from "../ui.jsx";

function FraxPanel() {
  const { metrics, hasManual } = useFrax();
  const { evalAge, age, height, weight } = usePatient();
  const fraxMetrics = metrics;
  const hasManualFrax = hasManual;
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="FRAX Plus · 10-Year Fracture Risk"
        subtitle="India (Asian) · No femoral neck BMD · Sheffield intervention thresholds"
        badge={hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'High Risk' : 'Low Risk') : null}
        badgeVariant={hasManualFrax ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'high' : 'low') : 'info'}
      />

      {!hasManualFrax ? (
        <EmptyState title="Enter age, sex, height & weight"
          hint="FRAX estimates 10-year fracture risk from demographics plus the risk factors on the left. No probability is shown until the core measurements are entered." />
      ) : (<React.Fragment>
      {evalAge < 40 && (
        <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
          ⚠ FRAX is calibrated for ages 40–90. Current age adjusted to the age-40 baseline model.
        </div>
      )}

      {/* MOF card */}
      <div style={{ ...heroTone(fraxMetrics.isHighMof ? 'high' : 'low'), borderRadius:'16px', padding:'22px', marginTop:'16px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
          <div>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>Major Osteoporotic Fracture</div>
            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
              <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: fraxMetrics.isHighMof ? '#dc2626' : '#16a34a', lineHeight:1 }}>{fraxMetrics.mofProb.toFixed(1)}</span>
              <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
            </div>
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability — spine, hip, forearm, shoulder</div>
          </div>
          <StatusBadge text={fraxMetrics.isHighMof ? 'High Risk ≥ 20%' : 'Low Risk < 20%'} variant={fraxMetrics.isHighMof ? 'high' : 'low'} />
        </div>
        <ProbBar prob={fraxMetrics.mofProb} maxProb={40} threshold={20} />
      </div>

      {/* HF card */}
      <div style={{ ...heroTone(fraxMetrics.isHighHf ? 'high' : 'low'), borderRadius:'16px', padding:'22px', marginTop:'12px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
          <div>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>Hip Fracture</div>
            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
              <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: fraxMetrics.isHighHf ? '#dc2626' : '#16a34a', lineHeight:1 }}>{fraxMetrics.hfProb.toFixed(1)}</span>
              <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
            </div>
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability of hip fracture</div>
          </div>
          <StatusBadge text={fraxMetrics.isHighHf ? 'High Risk ≥ 3%' : 'Low Risk < 3%'} variant={fraxMetrics.isHighHf ? 'high' : 'low'} />
        </div>
        <ProbBar prob={fraxMetrics.hfProb} maxProb={15} threshold={3} />
      </div>

      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        Sheffield thresholds: Treatment recommended when MOF ≥ 20% or Hip Fracture ≥ 3% (10-year absolute risk).
      </div>
    </div>
  );
}

export { FraxPanel };
