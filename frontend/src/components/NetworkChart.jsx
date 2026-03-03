import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

// Reusable time-series line chart.
// props:
//   title  – chart heading string
//   data   – array of sample objects (must have a `ts` ISO string field)
//   lines  – array of { key, color, name } — one line per metric
//   unit   – y-axis label suffix (optional)
export default function NetworkChart({ title, data, lines, unit = '' }) {
  // Format the ISO timestamp to HH:MM for the x-axis labels
  function formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!data || data.length === 0) {
    return (
      <div className="chart-box">
        <h3 className="chart-title">{title}</h3>
        <p className="muted">No data available for this period.</p>
      </div>
    )
  }

  return (
    <div className="chart-box">
      <h3 className="chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="ts"
            tickFormatter={formatTime}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            unit={unit}
            width={50}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
            labelFormatter={(ts) => new Date(ts).toLocaleString()}
            formatter={(val, name) => [val != null ? val.toFixed(2) + unit : '—', name]}
          />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
          {lines.map((l) => (
            <Line
              key={l.key}
              type="monotone"
              dataKey={l.key}
              name={l.name}
              stroke={l.color}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
