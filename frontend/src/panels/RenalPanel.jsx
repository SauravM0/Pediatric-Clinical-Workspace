/**
 * Renal panel (eGFR / CKD staging).
 *
 * Presentational. Its inputs live in the shared left-hand column; this renders
 * the derived metrics, which the Overview cards and the visit ledger also read --
 * hence context rather than props.
 */
import { useRenal, usePatient } from "../state.jsx";
import { StatusBadge, SectionHeader, EmptyState, heroTone } from "../ui.jsx";

function RenalPanel() {
  const { metrics, hasManual } = useRenal();
  const { evalAge, age, height } = usePatient();
  const renalMetrics = metrics;
  const hasManualRenal = hasManual;
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="Renal Workspace · eGFR"
        subtitle={`Multi-equation clearance monitoring · ${renalMetrics.formulaName}`}
        badge={hasManualRenal ? `Stage ${renalMetrics.ckdStage}` : null}
        badgeVariant={hasManualRenal ? renalMetrics.stageVariant : 'info'}
      />

      {!hasManualRenal ? (
        <EmptyState title="Enter serum creatinine"
          hint="Serum creatinine — plus age, sex and height — is required to estimate GFR. No value is shown until it is entered." />
      ) : (<React.Fragment>
      {/* eGFR hero */}
      <div className="hero-result" style={{ ...heroTone(renalMetrics.stageVariant), borderRadius:'16px', padding:'24px', marginTop:'16px' }}>
        <div>
          <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.08em', color:'#64748b', marginBottom:'8px' }}>Estimated GFR</div>
          <div style={{ display:'flex', alignItems:'baseline', gap:'10px' }}>
            <span className="hero-value" style={{ fontWeight:'900', color: renalMetrics.stageVariant === 'high' ? '#b91c1c' : renalMetrics.stageVariant === 'mid' ? '#b45309' : '#15803d', lineHeight:1 }}>{renalMetrics.egfr.toFixed(1)}</span>
            <span style={{ fontSize:'13px', color:'#6366f1', fontWeight:'600' }}>mL/min/1.73 m²</span>
          </div>
          <div style={{ fontSize:'11px', color:'#818cf8', marginTop:'4px' }}>via {renalMetrics.formulaName}</div>
        </div>
        <div style={{ textAlign:'right' }}>
          <StatusBadge text={`Stage ${renalMetrics.ckdStage} · ${renalMetrics.ckdStageDesc}`} variant={renalMetrics.stageVariant} />
          <div style={{ marginTop:'10px', fontSize:'11px', color:'#6366f1', fontWeight:'600' }}>
            {renalMetrics.isPediatric ? '▸ Pediatric Mode' : '▸ Adult Mode'}
          </div>
        </div>
      </div>

      {/* CKD Stage chips */}
      <div style={{ marginTop:'16px' }}>
        <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'8px' }}>KDIGO CKD Stage Map</div>
        <div className="ckd-stage">
          {[
            ['G1','≥ 90','Normal'],
            ['G2','60–89','Mild ↓'],
            ['G3','30–59','Mod ↓'],
            ['G4','15–29','Severe ↓'],
            ['G5','< 15','Failure'],
          ].map(([stage, range, desc]) => (
            <div key={stage} className={`ckd-chip ${renalMetrics.ckdStage === stage ? `ckd-active-${stage.toLowerCase()}` : 'ckd-inactive'}`}>
              <div style={{ fontWeight:'900', fontSize:'11px' }}>{stage}</div>
              <div style={{ fontSize:'9px', marginTop:'2px', fontWeight:'600', opacity:0.85 }}>{range}</div>
              <div style={{ fontSize:'9px', marginTop:'1px', opacity:0.7 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Alternate equations */}
      {!renalMetrics.isPediatric && (
        <div className="secondary-grid" style={{ marginTop:'16px' }}>
          <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px', border:'1px solid #e2e8f0' }}>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:'6px' }}>Cockcroft-Gault CrCl</div>
            <div style={{ fontSize:'22px', fontWeight:'900', color:'#334155' }}>{renalMetrics.cg ? renalMetrics.cg.toFixed(1) : '—'}</div>
            <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>mL/min</div>
          </div>
          <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'14px', border:'1px solid #e2e8f0' }}>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:'6px' }}>MDRD Clearance</div>
            <div style={{ fontSize:'22px', fontWeight:'900', color:'#334155' }}>{renalMetrics.mdrd ? renalMetrics.mdrd.toFixed(1) : '—'}</div>
            <div style={{ fontSize:'10px', color:'#94a3b8', marginTop:'2px' }}>mL/min/1.73 m²</div>
          </div>
        </div>
      )}

      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        KDIGO G1 ≥ 90 · G2 60–89 · G3 30–59 · G4 15–29 · G5 &lt; 15 mL/min/1.73 m²
      </div>
    </div>
  );
}

export { RenalPanel };
