/**
 * Growth panel.
 *
 * Charts, centiles and the printable report. The heaviest of the extracted
 * panels because it owns the report-export path as well as the display.
 */
import { useGrowth } from "../state.jsx";
import { MetricRow, SectionHeader, EmptyState } from "../ui.jsx";
import { SDSBar, GrowthChart, GrowthChartCombined } from "../charts.jsx";

function GrowthPanel() {
  const { age, evalAge, evalGender, evalHeight, evalWeight, examDate, exportGrowthReportPdf, gender, growthChartMeasure, growthMetrics, growthSeries, hasManualGrowth, height, moduleStatus, patientMrn, patientName, printGrowthReport, setGrowthChartMeasure, setShowChart, showChart, timeline, weight } = useGrowth();
  const gm = growthMetrics;
  const heightSeries = timeline.map(t => ({ age: t.age, value: t.height })).filter(p => p.value > 0);
  const weightSeries = timeline.map(t => ({ age: t.age, value: t.weight })).filter(p => p.value > 0);
  const bmiSeries = timeline.map(t => ({ age: t.age, value: (t.height>0 ? t.weight/Math.pow(t.height/100,2) : 0) })).filter(p => p.value > 0);
  const pctTxt = (p) => (p === null || p === undefined) ? '—' : p.toFixed(1) + 'th';
  const zTxt = (z) => (z === null || z === undefined) ? '—' : (z >= 0 ? '+' : '') + z.toFixed(2);
  const inRange = evalAge >= 0 && evalAge <= 19;
  return (
  <div style={{ flex:1 }}>
    <div className="report-only" style={{ fontSize:'13px', fontWeight:'700', color:'#334155', borderBottom:'1px solid #e5e7eb', paddingBottom:'8px' }}>
      {(patientName || 'Unnamed patient')} · MRN {(patientMrn || '—')} · {age !== "" ? `${age} yr` : '— yr'} · {gender === 'boys' ? 'Male' : gender === 'girls' ? 'Female' : '—'} · Exam {examDate}
    </div>
    <SectionHeader
      title="Pediatric Growth Chart · WHO (<5y) + IAP 2015 India (5–18y)"
      subtitle="Real L,M,S percentiles · height, weight & BMI · WHO under 5y, IAP 2015 India 5–18y (fit from the paper's published tables)."
      badge={moduleStatus.growth.state !== 'none' ? moduleStatus.growth.label : null}
      badgeVariant={moduleStatus.growth.state === 'high' ? 'high' : moduleStatus.growth.state === 'borderline' ? 'mid' : 'low'}
    />

    {!hasManualGrowth ? (
      <EmptyState title="Enter patient measurements"
        hint="Age, biological sex, height and weight are required to plot the growth chart. Values recalculate automatically as you type." />
    ) : !inRange ? (
      <EmptyState title="Pediatric workspace inactive"
        hint="The growth reference covers ages 0–19 years. Enter an age in that range to use the growth engine." />
    ) : (
      <div style={{ marginTop:'4px' }}>
        {/* Export PDF -- kept up top so exporting the growth report is one
            click and never requires opening the chart below. */}
        <div className="no-print" style={{ display:'flex', justifyContent:'flex-end', marginTop:'12px', marginBottom:'8px' }}>
          <button onClick={exportGrowthReportPdf}
            style={{ display:'flex', alignItems:'center', gap:'6px', padding:'8px 14px', background:'#4f46e5', color:'white', border:'none', borderRadius:'9px', fontSize:'12px', fontWeight:'700', cursor:'pointer' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
            Export PDF
          </button>
        </div>

        {/* Summary strip */}
        <div className="summary-grid" style={{ marginBottom:'16px' }}>
          <div style={{ background: gm.stuntingVariant === 'low' ? '#f0fdf4' : gm.stuntingVariant === 'mid' ? '#fffbeb' : '#fff1f2', borderRadius:'12px', padding:'14px 16px', border:`1px solid ${gm.stuntingVariant === 'low' ? '#bbf7d0' : gm.stuntingVariant === 'mid' ? '#fde68a' : '#fecaca'}` }}>
            <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.06em', color:'#94a3b8', marginBottom:'4px' }}>Height Status</div>
            <div style={{ fontSize:'15px', fontWeight:'900', color: gm.stuntingVariant === 'low' ? '#16a34a' : gm.stuntingVariant === 'mid' ? '#d97706' : '#dc2626' }}>{gm.stuntingClass}</div>
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'2px' }}>{pctTxt(gm.heightPct)} percentile</div>
          </div>
          <div style={{ background: gm.underweightVariant === 'low' ? '#f0fdf4' : gm.underweightVariant === 'mid' ? '#fffbeb' : '#fff1f2', borderRadius:'12px', padding:'14px 16px', border:`1px solid ${gm.underweightVariant === 'low' ? '#bbf7d0' : gm.underweightVariant === 'mid' ? '#fde68a' : '#fecaca'}` }}>
            <div style={{ fontSize:'10px', fontWeight:'800', textTransform:'uppercase', letterSpacing:'0.06em', color:'#94a3b8', marginBottom:'4px' }}>Weight / BMI Status</div>
            <div style={{ fontSize:'15px', fontWeight:'900', color: gm.underweightVariant === 'low' ? '#16a34a' : gm.underweightVariant === 'mid' ? '#d97706' : '#dc2626' }}>{gm.underweightClass}</div>
            <div style={{ fontSize:'11px', color:'#94a3b8', marginTop:'2px' }}>BMI {pctTxt(gm.bmiPct)} percentile</div>
          </div>
        </div>

        {/* Metric rows */}
        <MetricRow label="Chronological Age" value={evalAge.toFixed(1)} unit="yrs" />
        <MetricRow label="BMI" value={gm.bmiVal.toFixed(1)} unit="kg/m²" sub={`z ${zTxt(gm.bmiZ)} · ${pctTxt(gm.bmiPct)} pct`} />
        <MetricRow label="Median Weight for Age" value={gm.ref.wtMean !== null ? gm.ref.wtMean.toFixed(1) : "N/A"} unit="kg" sub={`Actual: ${evalWeight} kg`} />
        <MetricRow label="Median Height for Age" value={gm.ref.htMean !== null ? gm.ref.htMean.toFixed(1) : "N/A"} unit="cm" sub={`Actual: ${evalHeight} cm`} />
        <MetricRow label="Height Age (HA)" value={gm.heightAge.decimal ? gm.heightAge.decimal.toFixed(1) : "N/A"} unit="yrs equiv." />
        <MetricRow label="Weight Age (WA)" value={gm.weightAge.decimal ? gm.weightAge.decimal.toFixed(1) : "N/A"} unit="yrs equiv." />

        {/* Height SDS with bar */}
        <div style={{ padding:'14px 0', borderBottom:'1px solid #f1f5f9' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:'10px' }}>
            <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b' }}>Height SDS ({evalAge*12 >= 60 ? 'IAP' : 'WHO'})</span>
            <div>
              <span style={{ fontSize:'32px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{zTxt(gm.heightZ)}</span>
              <span style={{ fontSize:'11px', color:'#94a3b8', marginLeft:'6px' }}>SD</span>
            </div>
          </div>
          {gm.heightZ !== null ? <SDSBar z={gm.heightZ} /> : <div style={{ fontSize:'11px', color:'#94a3b8' }}>Out of reference range.</div>}
        </div>

        {/* BMI SDS with bar */}
        <div style={{ padding:'14px 0' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:'10px' }}>
            <span style={{ fontSize:'11px', fontWeight:'700', letterSpacing:'0.05em', textTransform:'uppercase', color:'#64748b' }}>BMI SDS (WHO)</span>
            <div>
              <span style={{ fontSize:'32px', fontWeight:'900', color:'#1e293b', lineHeight:1 }}>{zTxt(gm.bmiZ)}</span>
              <span style={{ fontSize:'11px', color:'#94a3b8', marginLeft:'6px' }}>SD</span>
            </div>
          </div>
          {gm.bmiZ !== null ? <SDSBar z={gm.bmiZ} /> : <div style={{ fontSize:'11px', color:'#94a3b8' }}>Out of reference range.</div>}
        </div>

        {/* ── Growth chart (optional visualisation) ── collapsed by default so the
            numbers above stay the primary read. The H+W / BMI toggle lives inside.
            The chart body is display-toggled (not unmounted) so PDF export -- which
            reads this exact markup -- keeps working whether it is open or closed. */}
        <div className="no-print" style={{ marginTop:'18px', borderTop:'1px solid #f1f5f9', paddingTop:'14px' }}>
          <button onClick={() => setShowChart(s => !s)}
            style={{ width:'100%', display:'flex', alignItems:'center', gap:'10px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:'10px', padding:'11px 14px', cursor:'pointer', textAlign:'left' }}>
            <span style={{ color:'#4f46e5', fontWeight:'800', fontSize:'13px', transform: showChart ? 'rotate(90deg)' : 'none', transition:'transform 0.15s', display:'inline-block' }}>▸</span>
            <span style={{ fontSize:'13px', fontWeight:'800', color:'#334155' }}>{showChart ? 'Hide growth chart' : 'Show growth chart'}</span>
            <span style={{ marginLeft:'auto', fontSize:'11px', color:'#94a3b8', fontWeight:'600' }}>Optional visualisation — the numbers above are the primary read</span>
          </button>
        </div>

        <div style={{ display: showChart ? 'block' : 'none', marginTop:'12px' }}>
          {/* H+W / BMI toggle */}
          <div className="no-print" style={{ display:'flex', gap:'4px', background:'#f1f5f9', padding:'4px', borderRadius:'10px', marginBottom:'10px', width:'fit-content' }}>
            {[{ key:'combined', label:'Growth Chart (H+W)' }, { key:'bmi', label:'BMI' }].map(({key:mkey,label}) => (
              <button key={mkey} onClick={() => setGrowthChartMeasure(mkey)}
                className="toggle-btn"
                style={{ background: growthChartMeasure===mkey ? 'white' : 'transparent', color: growthChartMeasure===mkey ? '#1e293b' : '#64748b', boxShadow: growthChartMeasure===mkey ? '0 1px 3px rgba(0,0,0,0.12)' : 'none' }}>
                {label}
              </button>
            ))}
          </div>

          {/* Growth centile chart (auto-filled from patient data). Sized for A4 print --
              see printGrowthReport() below, which prints this exact same markup. */}
          <div id="growth-chart-print" style={{ border:'1px solid #eef2f7', borderRadius:'12px', padding:'8px', marginBottom:'16px', background:'white', overflowX:'auto' }}>
            {growthChartMeasure === 'combined' ? (
              <GrowthChartCombined
                sex={evalGender} ageYears={evalAge}
                heightValue={evalHeight} weightValue={evalWeight}
                heightData={growthSeries[evalGender].height} weightData={growthSeries[evalGender].weight}
                heightSeries={heightSeries} weightSeries={weightSeries}
              />
            ) : (
              <GrowthChart measure="bmi" sex={evalGender} ageYears={evalAge} value={gm.bmiVal} series={bmiSeries} chartData={growthSeries[evalGender].bmi} />
            )}
          </div>
          {growthChartMeasure==='combined' && !gm.weightAvailable && (
            <div style={{ fontSize:'11px', color:'#d97706', background:'#fffbeb', border:'1px solid #fde68a', borderRadius:'8px', padding:'8px 12px', marginBottom:'12px' }}>
              Weight-for-age has no reference data at this age. Use BMI-for-age for weight status instead.
            </div>
          )}
        </div>
      </div>
    )}
  </div>
  );
}

export { GrowthPanel };
