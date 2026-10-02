/**
 * Overview panel.
 *
 * The at-a-glance card grid. Reads every module's derived status, which is
 * exactly why those metrics live in context rather than in each panel.
 */
import { useOverview } from "../state.jsx";
import { SectionHeader } from "../ui.jsx";

const { useState, useEffect } = React;

// What every number on this page rests on (step 5). Fetched here rather than
// through context: nothing else reads it, and it changes only when a clinic
// installs a reference, not as the patient's values change.
function ReferenceDataStatus() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch('/api/reference-data').then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(setData).catch(e => setError(String(e.message || e)));
  }, []);
  if (error) return <div style={{ marginTop:'16px', fontSize:'11px', color:'#b91c1c' }}>Reference-data status unavailable: {error}</div>;
  if (!data) return null;
  return (
    <details className="clinical-notes" style={{ marginTop:'16px' }}>
      <summary>Reference data behind these numbers · {data.active_count} of {data.total} installed</summary>
      <div className="clinical-notes-body">
        <div style={{ fontSize:'11px', color:'#64748b', marginBottom:'8px', lineHeight:1.6 }}>{data.note}</div>
        {data.items.map(i => (
          <div key={i.key} style={{ padding:'8px 0', borderTop:'1px solid #eef2f7' }}>
            <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
              <span className={`status-dot status-dot-${i.active ? 'normal' : 'borderline'}`} style={{ marginLeft:0 }}></span>
              <strong style={{ fontSize:'12px', color:'#1e293b' }}>{i.title}</strong>
              <span style={{ fontSize:'10.5px', color: i.active ? '#15803d' : '#b45309', fontWeight:700 }}>{i.active ? 'installed' : 'missing'}</span>
            </div>
            {!i.active && (
              <div style={{ fontSize:'11px', color:'#475569', margin:'3px 0 0 16px', lineHeight:1.55 }}>
                {i.effect_while_missing} <span style={{ color:'#64748b' }}>To obtain: {i.obtain} — see <code>{i.how_to}</code>.</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </details>
  );
}

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
        <ReferenceDataStatus />
      </div>
  );
}

export { OverviewPanel };
