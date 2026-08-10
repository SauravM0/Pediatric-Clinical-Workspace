/**
 * Application chrome (M6 panel extraction): header, patient identity bar, tabs.
 *
 * The frame around the workspace rather than any one module's content, so it
 * lives apart from `panels/` -- those are the tab bodies, these are what
 * surrounds them.
 *
 * The identity bar is a safety feature, not decoration: every printed result
 * has to be attributable to a named patient on a dated exam, which is why it
 * sits above the fold on every tab rather than inside one.
 */
import { useShell } from "./state.jsx";

function AppHeader() {
  const { resetAll } = useShell();
  return (
    <header style={{ background:'white', borderBottom:'1px solid #e8ecf0', position:'sticky', top:0, zIndex:50, boxShadow:'0 1px 4px rgba(0,0,0,0.05)' }}>
      <div className="app-header-inner">
        <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
          <div style={{ width:'36px', height:'36px', borderRadius:'10px', background:'linear-gradient(135deg,#4f46e5,#7c3aed)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <div>
            <div className="app-title" style={{ fontSize:'15px', fontWeight:'900', color:'#0f172a', lineHeight:1.2 }}>Pediatric Clinical Workspace</div>
            <div className="app-subtitle" style={{ fontSize:'10px', fontWeight:'700', color:'#94a3b8', letterSpacing:'0.06em', textTransform:'uppercase' }}>Growth · TW3 Bone Age · QRISK3 · Renal · FRAX · FIB-4</div>
          </div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:'8px', flexShrink:0 }}>
          <button
            onClick={resetAll}
            className="reset-button"
            style={{ display:'flex', alignItems:'center', gap:'7px', padding:'8px 18px', background:'white', border:'1.5px solid #fca5a5', borderRadius:'9px', fontSize:'13px', fontWeight:'700', color:'#dc2626', cursor:'pointer', whiteSpace:'nowrap', transition:'all 0.15s', boxShadow:'0 1px 3px rgba(220,38,38,0.08)' }}
            onMouseEnter={e => { e.currentTarget.style.background='#fff1f2'; e.currentTarget.style.borderColor='#f87171'; }}
            onMouseLeave={e => { e.currentTarget.style.background='white'; e.currentTarget.style.borderColor='#fca5a5'; }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.77"/>
            </svg>
            Reset Patient
          </button>
        </div>
      </div>
    </header>
  );
}

function PatientIdentityBar() {
  const { patientName, setPatientName, patientMrn, setPatientMrn,
          examDate, setExamDate, age, gender, exportFullReport } = useShell();
  return (
    <div className="patient-bar no-print">
      <div className="patient-bar-inner">
        <div className="patient-field" style={{ flex:'2 1 200px' }}>
          <label htmlFor="pt-name">Patient name</label>
          <input id="pt-name" type="text" value={patientName} onChange={e => setPatientName(e.target.value)} placeholder="Full name" />
        </div>
        <div className="patient-field" style={{ flex:'1 1 130px' }}>
          <label htmlFor="pt-mrn">MRN / ID</label>
          <input id="pt-mrn" type="text" value={patientMrn} onChange={e => setPatientMrn(e.target.value)} placeholder="e.g. 004821" />
        </div>
        <div className="patient-field" style={{ flex:'1 1 140px' }}>
          <label htmlFor="pt-date">Exam date</label>
          <input id="pt-date" type="date" value={examDate} onChange={e => setExamDate(e.target.value)} />
        </div>
        <div className="patient-field" style={{ flex:'1 1 120px' }}>
          <label>Age / Sex</label>
          <div className="patient-reflect">
            {age !== "" ? `${age} yr` : '— yr'} · {gender === 'boys' ? 'Male' : gender === 'girls' ? 'Female' : '—'}
          </div>
        </div>
        <button onClick={exportFullReport} title="Print a combined summary of every module"
          style={{ marginLeft:'auto', alignSelf:'center', display:'flex', alignItems:'center', gap:'7px', padding:'8px 16px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'13px', fontWeight:'700', cursor:'pointer', whiteSpace:'nowrap' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
          Export report
        </button>
      </div>
    </div>
  );
}

function TabBar() {
  const { TABS, activeTab, setActiveTab, moduleStatus, timeline } = useShell();
  return (
    <div className="card tab-card" style={{ padding:'6px' }}>
      <div className="tab-scroll custom-scrollbar">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`${activeTab === tab.id ? 'tab-active' : 'tab-inactive'} tab-button`}>
            {tab.label}
            {moduleStatus[tab.id] && (
              <span className={`status-dot status-dot-${moduleStatus[tab.id].state}`}
                title={moduleStatus[tab.id].label}></span>
            )}
            {tab.id === 'timeline' && timeline.length > 0 && (
              <span style={{ marginLeft:'6px', background:'#4f46e5', color:'white', fontSize:'9px', fontWeight:'800', padding:'1px 6px', borderRadius:'99px' }}>{timeline.length}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export { AppHeader, PatientIdentityBar, TabBar };
