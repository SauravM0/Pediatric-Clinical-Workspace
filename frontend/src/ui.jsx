/**
 * Shared presentational primitives.
 *
 * Extracted from app.jsx (M6). Stateless building blocks used by every panel;
 * pulling them out is what lets a panel be extracted later without dragging
 * the whole file along.
 */
import { probToPercent } from "./growthMath.js";

        function ProbBar({ prob, maxProb, threshold, label }) {
          const left = probToPercent(prob, maxProb);
          const threshLeft = probToPercent(threshold, maxProb);
          return (
            <div style={{ paddingTop: '8px', paddingBottom: '4px' }}>
              <div className="prob-track" style={{ position:'relative' }}>
                {/* threshold line */}
                <div style={{ position:'absolute', top:'-6px', left:`${threshLeft}%`, width:'2px', height:'20px', background:'#475569', borderRadius:'1px', transform:'translateX(-50%)' }}></div>
                <div className="prob-marker" style={{ left: `${left}%` }}></div>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', marginTop:'6px', fontSize:'9px', fontWeight:'700', color:'#94a3b8', letterSpacing:'0.05em', textTransform:'uppercase' }}>
                <span>0%</span>
                <span style={{ color:'#475569' }}>Tx threshold: {threshold}%</span>
                <span>{maxProb}%</span>
              </div>
            </div>
          );
        }

        function StatusBadge({ text, variant }) {
          const styles = {
            low:  'risk-badge-low',
            mid:  'risk-badge-mid',
            high: 'risk-badge-high',
            info: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
            neutral: 'bg-slate-100 text-slate-600 border border-slate-200',
          };
          // Pair colour with a shape so risk is not conveyed by colour alone
          // (colour-blind accessibility): ✓ normal · ! borderline · ▲ high.
          const glyph = { low: '✓', mid: '!', high: '▲' }[variant];
          return (
            <span style={{ display:'inline-flex', alignItems:'center', gap:'5px', padding:'3px 10px', borderRadius:'99px', fontSize:'11px', fontWeight:'700' }} className={styles[variant] || styles.neutral}>
              {glyph && <span aria-hidden="true" style={{ fontSize:'10px', lineHeight:1 }}>{glyph}</span>}
              {text}
            </span>
          );
        }

        function MetricRow({ label, value, unit, sub, children, accent }) {
          return (
            <div style={{ display:'flex', flexDirection:'column', gap:'6px', padding:'14px 0', borderBottom:'1px solid #f1f5f9' }}>
              <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:'12px', flexWrap:'wrap' }}>
                <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b', paddingTop:'6px' }}>{label}</span>
                <div style={{ textAlign:'right' }}>
                  <span style={{ fontSize:'32px', fontWeight:'900', color: accent || '#1e293b', lineHeight:1 }}>{value}</span>
                  {unit && <span style={{ fontSize:'12px', fontWeight:'500', color:'#94a3b8', marginLeft:'6px' }}>{unit}</span>}
                  {sub && <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'2px' }}>{sub}</div>}
                </div>
              </div>
              {children}
            </div>
          );
        }

        function SectionHeader({ title, subtitle, badge, badgeVariant }) {
          return (
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', paddingBottom:'14px', borderBottom:'1.5px solid #f1f5f9', marginBottom:'4px', gap:'8px' }}>
              <div>
                <h3 style={{ fontSize:'13px', fontWeight:'800', color:'#334155', letterSpacing:'0.01em' }}>{title}</h3>
                {subtitle && <p style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>{subtitle}</p>}
              </div>
              {badge && <StatusBadge text={badge} variant={badgeVariant || 'info'} />}
            </div>
          );
        }

        function FraxToggleRow({ label, value, setter }) {
          return (
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'8px 0', borderBottom:'1px solid #f8fafc' }}>
              <span style={{ fontSize:'12px', fontWeight:'600', color:'#475569' }}>{label}</span>
              <div className="toggle-pill">
                <button className={`toggle-btn ${value === 'yes' ? 'toggle-on' : 'toggle-off'}`} onClick={() => setter('yes')}>Yes</button>
                <button className={`toggle-btn ${value === 'no' ? 'toggle-on' : 'toggle-off'}`} onClick={() => setter('no')}>No</button>
              </div>
            </div>
          );
        }

        function InputWithUnit({ label, value, onChange, placeholder, step, unit, accent }) {
          return (
            <div style={{ minWidth:0 }}>
              <label className="field-label">{label}</label>
              <div style={{ position:'relative', display:'flex', alignItems:'center' }}>
                <input
                  type="number"
                  step={step || 'any'}
                  placeholder={placeholder || '—'}
                  value={value}
                  onChange={onChange}
                  className="input-field"
                  style={{
                    paddingRight: unit ? '44px' : '12px',
                    color: accent || '#1e293b',
                    minWidth:0,
                    width:'100%',
                  }}
                />
                {unit && (
                  <span style={{ position:'absolute', right:'10px', fontSize:'10px', fontWeight:'700', color:'#94a3b8', textTransform:'uppercase', pointerEvents:'none', whiteSpace:'nowrap' }}>{unit}</span>
                )}
              </div>
            </div>
          );
        }

        // Reusable "this module needs input" / empty state for a result panel.
        // One component so every tab's needs-input affordance looks identical
        // (previously each tab hand-rolled its own inline version).
        function EmptyState({ title, hint, tone }) {
          const c = tone === 'violet' ? { bg:'#f5f3ff', stroke:'#a78bfa' } : { bg:'#f1f5f9', stroke:'#94a3b8' };
          return (
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', flex:1, gap:'12px', padding:'40px 0', textAlign:'center', minHeight:'220px' }}>
              <div style={{ width:'56px', height:'56px', borderRadius:'50%', background:c.bg, display:'flex', alignItems:'center', justifyContent:'center' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={c.stroke} strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </div>
              <div style={{ fontSize:'14px', fontWeight:'700', color:'#475569' }}>{title}</div>
              {hint && <div style={{ fontSize:'12px', color:'#94a3b8', maxWidth:'300px', lineHeight:'1.6' }}>{hint}</div>}
            </div>
          );
        }

        // Tone (background + border) for a result hero card, keyed to clinical
        // variant so an abnormal result visibly colours its whole card -- not
        // just the number -- and the same language is reused across every tab.
        function heroTone(variant) {
          if (variant === 'high') return { background:'linear-gradient(135deg,#fff1f2,#fef2f2)', border:'1.5px solid #fecaca' };
          if (variant === 'mid')  return { background:'linear-gradient(135deg,#fffbeb,#fefce8)', border:'1.5px solid #fde68a' };
          if (variant === 'low')  return { background:'linear-gradient(135deg,#f0fdf4,#f7fee7)', border:'1.5px solid #bbf7d0' };
          return { background:'#f8fafc', border:'1.5px solid #e2e8f0' };
        }

        // Map a clinical variant (low/mid/high) to a status-dot state so the
        // Overview cards and the tab-bar dots stay in one vocabulary.
        function variantToState(v) {
          return v === 'high' ? 'high' : v === 'mid' ? 'borderline' : v === 'low' ? 'normal' : 'none';
        }

        // Break a date of birth into calendar years/months/days plus the TRUE
        // decimal age in years (total-days / 365.25) that the clinical engines
        // consume. Returns null for an empty, invalid, or future date.
        function computeAgeParts(dobStr) {
          if (!dobStr) return null;
          const b = new Date(dobStr + 'T00:00:00');
          const now = new Date();
          if (isNaN(b.getTime()) || b > now) return null;
          let years = now.getFullYear() - b.getFullYear();
          let months = now.getMonth() - b.getMonth();
          let days = now.getDate() - b.getDate();
          if (days < 0) { months -= 1; days += new Date(now.getFullYear(), now.getMonth(), 0).getDate(); }
          if (months < 0) { years -= 1; months += 12; }
          const decimal = (now - b) / (365.25 * 24 * 3600 * 1000);
          return { years, months, days, decimal };
        }

export { ProbBar, StatusBadge, MetricRow, SectionHeader, FraxToggleRow,
         InputWithUnit, EmptyState, heroTone, variantToState,
         computeAgeParts };
