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

// TcpConnectionsChart: displays the count of ESTABLISHED TCP connections over time.
// Null values (from old rows or psutil failures) are skipped via connectNulls.
export default function TcpConnectionsChart({ title, data }) {
  function formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!data || data.length === 0 || data.every(r => r.tcp_connections == null)) {
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
            unit=" conns"
            width={70}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
            labelFormatter={(ts) => new Date(ts).toLocaleString()}
            formatter={(value) => value != null ? `${value} connections` : 'N/A'}
          />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="tcp_connections"
            name="TCP Connections"
            stroke="#818cf8"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
