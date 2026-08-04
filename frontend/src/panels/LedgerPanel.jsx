/**
 * Ledger panel.
 *
 * The visit ledger. Reads the same derived metrics the panels do, which is
 * the second consumer that makes them genuinely shared state.
 */
import { useLedger } from "../state.jsx";

function LedgerPanel() {
  const { age, albuminuria, assessment, chronicityStatus, creatinine, height, logCurrentData, setTimeline, timeline, weight } = useLedger();
  return (
      <div style={{ flex:1, display:'flex', flexDirection:'column', gap:'16px' }}>
        <div className="timeline-header">
          <div>
            <h3 style={{ fontSize:'13px', fontWeight:'800', color:'#334155' }}>CKD Progression Ledger</h3>
            <p style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>Session snapshots — chronicity assessment over ≥ 90 days</p>
          </div>
          <div className="timeline-actions">
            <button onClick={logCurrentData} style={{ padding:'7px 16px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'12px', fontWeight:'700', cursor:'pointer', boxShadow:'0 1px 4px rgba(79,70,229,0.3)', transition:'background 0.15s' }}
              onMouseEnter={e=>e.target.style.background='#4338ca'} onMouseLeave={e=>e.target.style.background='#4f46e5'}>
              + Log Snapshot
            </button>
            {timeline.length > 0 && (
              <button onClick={() => { if (window.confirm('Clear all logged snapshots from the ledger?')) setTimeline([]); }} style={{ padding:'7px 14px', background:'white', color:'#64748b', border:'1.5px solid #e2e8f0', borderRadius:'9px', fontSize:'12px', fontWeight:'600', cursor:'pointer', transition:'all 0.15s' }}
                onMouseEnter={e=>e.target.style.background='#f8fafc'} onMouseLeave={e=>e.target.style.background='white'}>
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Chronicity status */}
        <div style={{ padding:'14px 16px', borderRadius:'12px', fontSize:'12px', lineHeight:'1.6' }} className={chronicityStatus.bgClass}>
          <span style={{ fontWeight:'800', fontSize:'10px', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:'3px' }}>Chronicity Assessment</span>
          {chronicityStatus.status}
        </div>

        {/* GFR sparkline */}
        {timeline.length > 0 && (
          <div style={{ background:'#f8fafc', borderRadius:'12px', padding:'16px', border:'1px solid #e2e8f0' }}>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:'10px' }}>eGFR Timeline</div>
            <svg width="100%" height="100" viewBox="0 0 500 100" preserveAspectRatio="none" style={{ borderRadius:'8px', background:'white', border:'1px solid #f1f5f9' }}>
              <line x1="0" y1="22" x2="500" y2="22" stroke="#f1f5f9" strokeWidth="1.5"/>
              <line x1="0" y1="50" x2="500" y2="50" stroke="#f1f5f9" strokeWidth="1.5"/>
              <line x1="0" y1="78" x2="500" y2="78" stroke="#f1f5f9" strokeWidth="1.5"/>
              {(() => {
                const sorted = [...timeline].sort((a,b) => new Date(a.date)-new Date(b.date));
                const pts = sorted.map((e,i) => ({
                  x: sorted.length > 1 ? (i/(sorted.length-1))*440+30 : 250,
                  y: 90 - ((Math.min(e.egfr,150)/150)*70),
                  e
                }));
                return (
                  <g>
                    {pts.length > 1 && <polyline fill="none" stroke="#4f46e5" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={pts.map(p=>`${p.x},${p.y}`).join(' ')} />}
                    {pts.map((p,i) => (
                      <g key={p.e.id}>
                        <circle cx={p.x} cy={p.y} r="4" fill="#4f46e5" />
                        <text x={p.x} y={p.y-9} textAnchor="middle" fill="#4338ca" fontSize="9" fontWeight="bold">{p.e.egfr}</text>
                        <text x={p.x} y="96" textAnchor="middle" fill="#94a3b8" fontSize="8">{p.e.date.slice(5)}</text>
                      </g>
                    ))}
                  </g>
                );
              })()}
            </svg>
          </div>
        )}

        {/* Table */}
        {timeline.length === 0 ? (
          <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'40px 0', gap:'12px', textAlign:'center' }}>
            <div style={{ width:'52px', height:'52px', borderRadius:'50%', background:'#f1f5f9', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
            </div>
            <div style={{ fontSize:'13px', fontWeight:'700', color:'#64748b' }}>No snapshots logged yet</div>
            <div style={{ fontSize:'12px', color:'#94a3b8' }}>Enter patient data and click "Log Snapshot" to begin tracking.</div>
          </div>
        ) : (
          <div style={{ overflowX:'auto', borderRadius:'12px', border:'1px solid #e2e8f0' }} className="custom-scrollbar">
            <table style={{ width:'100%', borderCollapse:'collapse', minWidth:'580px', fontSize:'12px' }}>
              <thead>
                <tr style={{ background:'#f8fafc', borderBottom:'1px solid #e2e8f0' }}>
                  {['Date','Age','Ht / Wt','SCr','eGFR','ACR','FIB-4'].map(h => (
                    <th key={h} style={{ padding:'10px 12px', textAlign:'left', fontWeight:'800', color:'#64748b', fontSize:'10px', textTransform:'uppercase', letterSpacing:'0.05em', whiteSpace:'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {timeline.map((item, idx) => (
                  <tr key={item.id} style={{ borderBottom:'1px solid #f1f5f9', background: idx % 2 === 0 ? 'white' : '#fafbfc' }}>
                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#1e293b' }}>{item.date}</td>
                    <td style={{ padding:'10px 12px', color:'#475569' }}>{item.age.toFixed(1)} y</td>
                    <td style={{ padding:'10px 12px', color:'#64748b' }}>{item.height} / {item.weight}</td>
                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#475569' }}>{item.creatinine}</td>
                    <td style={{ padding:'10px 12px', fontWeight:'800', color:'#4f46e5' }}>{item.egfr}</td>
                    <td style={{ padding:'10px 12px' }}>
                      <span style={{ padding:'2px 8px', borderRadius:'99px', fontSize:'10px', fontWeight:'700', background:'#eef2ff', color:'#4338ca', border:'1px solid #c7d2fe' }}>{item.albuminuria}</span>
                    </td>
                    <td style={{ padding:'10px 12px', fontWeight:'700', color:'#059669' }}>{item.fib4 !== null ? item.fib4 : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
  );
}

export { LedgerPanel };
