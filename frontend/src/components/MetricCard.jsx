// Single stat tile — shows one current metric value.
export default function MetricCard({ label, value, unit }) {
  const display = value == null ? '—' : typeof value === 'number' ? value.toFixed(1) : value
  return (
    <div className="metric-card">
      <div className="metric-value">
        {display}
        {value != null && unit && <span className="metric-unit"> {unit}</span>}
      </div>
      <div className="metric-label">{label}</div>
    </div>
  )
}
