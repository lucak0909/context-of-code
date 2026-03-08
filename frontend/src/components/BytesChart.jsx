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

// BytesChart: displays cumulative bytes sent and received (converted from bytes to MB).
// Raw values from the agent are bytes since boot. Old rows with null values are skipped
// via connectNulls — the chart starts from the first row that has real data.
export default function BytesChart({ title, data }) {
  function formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Convert raw bytes to MB for each data point. Null values remain null (connectNulls handles them).
  const chartData = data
    ? data.map((row) => ({
        ...row,
        bytes_sent_mb: row.bytes_sent != null ? row.bytes_sent / 1_000_000 : null,
        bytes_recv_mb: row.bytes_recv != null ? row.bytes_recv / 1_000_000 : null,
      }))
    : []

  if (!chartData || chartData.length === 0 || chartData.every(r => r.bytes_sent_mb == null && r.bytes_recv_mb == null)) {
    return (
      <div className="chart-box">
        <h3 className="chart-title">{title}</h3>
        <p className="muted">No data yet.</p>
      </div>
    )
  }

  return (
    <div className="chart-box">
      <h3 className="chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="ts"
            tickFormatter={formatTime}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            unit=" MB"
            width={70}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
            labelFormatter={(ts) => new Date(ts).toLocaleString()}
            formatter={(value) => value != null ? `${value.toFixed(1)} MB` : 'N/A'}
          />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="bytes_sent_mb"
            name="Sent"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="bytes_recv_mb"
            name="Received"
            stroke="#fb923c"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
