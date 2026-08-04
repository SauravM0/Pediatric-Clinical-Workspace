/**
 * Overview panel.
 *
 * The at-a-glance card grid. Reads every module's derived status, which is
 * exactly why those metrics live in context rather than in each panel.
 */
import { useOverview } from "../state.jsx";
import { SectionHeader } from "../ui.jsx";

function OverviewPanel() {
  const { moduleStatus, setActiveTab } = useOverview();
  return (
      <div style={{ flex:1 }}>
        <SectionHeader
          title="Patient Overview"
          subtitle="Every module's headline at a glance — click any card to open its full workspace."
        />
        <div className="overview-grid" style={{ marginTop:'16px' }}>
          {['growth','boneage','renal','liver','frax','qrisk'].map(key => {
            const m = moduleStatus[key];
            const accent = m.state === 'high' ? '#dc2626' : m.state === 'borderline' ? '#d97706' : m.state === 'normal' ? '#16a34a' : '#94a3b8';
            return (
              <button key={key} className="overview-card" onClick={() => setActiveTab(key)}>
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:'8px', marginBottom:'10px' }}>
                  <span style={{ fontSize:'11px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.05em', color:'#64748b' }}>{m.title}</span>
                  <span className={`status-dot status-dot-${m.state}`} style={{ marginLeft:0 }}></span>
                </div>
                <div style={{ display:'flex', alignItems:'baseline', gap:'6px' }}>
                  <span style={{ fontSize:'30px', fontWeight:'900', color:accent, lineHeight:1 }}>{m.value}</span>
                  <span style={{ fontSize:'11px', fontWeight:'600', color:'#94a3b8' }}>{m.unit}</span>
                </div>
                <div style={{ fontSize:'11px', color:'#64748b', marginTop:'6px', lineHeight:'1.5' }}>{m.label}</div>
              </button>
            );
          })}
        </div>
        <div style={{ marginTop:'16px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#4338ca', lineHeight:'1.7' }}>
          Enter patient data in the left panel — every module recalculates automatically. A grey dot means that module still needs input; green / amber / red reflect the result. Decision support only — a clinician must verify every value.
        </div>
      </div>
  );
}

export { OverviewPanel };
