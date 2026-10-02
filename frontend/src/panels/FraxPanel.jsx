/**
 * FRAX panel: RECORD the official FRAX result. Nothing is computed here.
 *
 * This tab used to show a FRAX-branded probability from a logistic formula whose
 * coefficients had no published source -- FRAX is the University of Sheffield's
 * proprietary algorithm and its coefficients are not public. A number carrying
 * the FRAX name is trusted as FRAX, so it was removed rather than relabelled.
 *
 * The clinician now runs the official calculator (India model) and types in the
 * two ten-year probabilities it returns. This panel stores them, compares them
 * with a named treatment threshold, and feeds the Overview and printed summary.
 *
 * The thresholds are the US NOF/BHOF intervention thresholds (MOF >= 20% or hip
 * >= 3%). They are labelled as such: India has no nationally validated FRAX
 * intervention threshold, and the UK (NOGG) uses age-dependent ones instead.
 */
import { useFrax, usePatient } from "../state.jsx";
import { ProbBar, StatusBadge, SectionHeader, InputWithUnit, EmptyState, heroTone } from "../ui.jsx";
import { rangeProblem } from "../clinicalRanges.js";

const OFFICIAL_FRAX_URL = 'https://frax.shef.ac.uk/FRAX/tool.aspx';

function FraxPanel() {
  const { metrics, hasManual, fraxMofEntered, setFraxMofEntered,
          fraxHfEntered, setFraxHfEntered } = useFrax();
  const { age, evalAge } = usePatient();
  const fraxMetrics = metrics;
  const toNumberOrBlank = (e) => e.target.value === "" ? "" : parseFloat(e.target.value);
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column' }}>
      <SectionHeader
        title="FRAX · 10-Year Fracture Probability"
        subtitle="Result from the official FRAX calculator (India model), entered by the clinician"
        badge={hasManual ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'Above US threshold' : 'Below US threshold') : null}
        badgeVariant={hasManual ? (fraxMetrics.isHighMof || fraxMetrics.isHighHf ? 'high' : 'low') : 'info'}
      />

      <div style={{ marginTop:'14px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#3730a3', lineHeight:'1.7' }}>
        <strong>This workspace does not calculate FRAX.</strong> Run the official calculator
        (University of Sheffield, <em>Asia → India</em> model) at{' '}
        <a href={OFFICIAL_FRAX_URL} target="_blank" rel="noopener noreferrer" style={{ color:'#4338ca', fontWeight:700 }}>frax.shef.ac.uk</a>,
        then enter the two probabilities it reports below.
      </div>

      {age !== "" && (evalAge < 40 || evalAge > 90) && (
        <div style={{ marginTop:'12px', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#92400e', lineHeight:'1.6' }}>
          ⚠ FRAX is defined for ages 40–90. This patient is {evalAge} years; the official tool will not give a valid probability outside that range.
        </div>
      )}

      <div className="form-grid" style={{ marginTop:'16px' }}>
        <InputWithUnit label="Major osteoporotic fracture" value={fraxMofEntered} onChange={e => setFraxMofEntered(toNumberOrBlank(e))}
          placeholder="from FRAX" step="0.1" unit="%" problem={rangeProblem('fraxPct', fraxMofEntered)} />
        <InputWithUnit label="Hip fracture" value={fraxHfEntered} onChange={e => setFraxHfEntered(toNumberOrBlank(e))}
          placeholder="from FRAX" step="0.1" unit="%" problem={rangeProblem('fraxPct', fraxHfEntered)} />
      </div>

      {/* Hip fracture is one of the four sites counted in "major osteoporotic
          fracture", so FRAX never reports hip > MOF. If it does here, the two
          boxes were almost certainly swapped. */}
      {hasManual && fraxMetrics.hfProb > fraxMetrics.mofProb && (
        <div role="alert" style={{ marginTop:'12px', background:'#fef2f2', border:'1px solid #fecaca', borderRadius:'10px', padding:'12px 14px', fontSize:'12px', color:'#991b1b', lineHeight:'1.6' }}>
          ⚠ Hip-fracture probability is higher than major-osteoporotic-fracture probability. FRAX never reports this (hip is
          one of the major fracture sites) — check whether the two values were entered in the wrong boxes.
        </div>
      )}

      {!hasManual ? (
        <EmptyState title="Enter both FRAX probabilities"
          hint="Nothing is shown until both values from the official calculator are entered." />
      ) : (<React.Fragment>
      {/* MOF card */}
      <div style={{ ...heroTone(fraxMetrics.isHighMof ? 'high' : 'low'), borderRadius:'16px', padding:'22px', marginTop:'16px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'8px' }}>
          <div>
            <div style={{ fontSize:'10px', fontWeight:'800', color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:'6px' }}>Major Osteoporotic Fracture</div>
            <div style={{ display:'flex', alignItems:'baseline', gap:'8px' }}>
              <span className="hero-value" style={{ fontSize:'44px', fontWeight:'900', color: fraxMetrics.isHighMof ? '#dc2626' : '#16a34a', lineHeight:1 }}>{fraxMetrics.mofProb.toFixed(1)}</span>
              <span style={{ fontSize:'18px', fontWeight:'700', color:'#64748b' }}>%</span>
            </div>
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability — spine, hip, forearm, shoulder (as entered)</div>
          </div>
          <StatusBadge text={fraxMetrics.isHighMof ? 'At/above 20%' : 'Below 20%'} variant={fraxMetrics.isHighMof ? 'high' : 'low'} />
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
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'3px' }}>10-yr probability of hip fracture (as entered)</div>
          </div>
          <StatusBadge text={fraxMetrics.isHighHf ? 'At/above 3%' : 'Below 3%'} variant={fraxMetrics.isHighHf ? 'high' : 'low'} />
        </div>
        <ProbBar prob={fraxMetrics.hfProb} maxProb={15} threshold={3} />
      </div>
      </React.Fragment>)}

      <div style={{ marginTop:'auto', paddingTop:'20px', borderTop:'1px solid #f1f5f9', fontSize:'11px', color:'#94a3b8', lineHeight:'1.7' }}>
        Thresholds shown are the US NOF/BHOF intervention thresholds (MOF ≥ 20% or hip ≥ 3%), which BHOF applies to
        postmenopausal women and men aged ≥ 50 with low bone mass (osteopenia). India has no nationally validated FRAX
        intervention threshold, and UK NOGG uses age-dependent thresholds — treatment decisions rest with the clinician.
      </div>
    </div>
  );
}

export { FraxPanel };
