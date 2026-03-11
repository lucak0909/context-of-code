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

// BytesChart: displays MB transferred per 30s interval (delta of cumulative OS counters).
// Negative deltas caused by reboots or interface resets are shown as gaps rather than dips.
export default function BytesChart({ title, data }) {
  function formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Compute per-interval delta from cumulative OS counters.
  // Negative deltas (reboot/interface reset) are clamped to null so the chart gaps instead of dipping.
  const chartData = data
    ? data.map((row, i) => {
        const prev = i > 0 ? data[i - 1] : null
        const sentDelta =
          prev && row.bytes_sent != null && prev.bytes_sent != null
            ? row.bytes_sent - prev.bytes_sent
            : null
        const recvDelta =
          prev && row.bytes_recv != null && prev.bytes_recv != null
            ? row.bytes_recv - prev.bytes_recv
            : null
        return {
          ...row,
          bytes_sent_mb: sentDelta != null && sentDelta >= 0 ? sentDelta / 1_000_000 : null,
          bytes_recv_mb: recvDelta != null && recvDelta >= 0 ? recvDelta / 1_000_000 : null,
        }
      })
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
            unit=" MB/interval"
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
