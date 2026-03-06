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

// MobileChart: displays WiFi RSSI (dBm) and link speed (Mbps) for mobile_wifi samples.
// Renders an empty-state message when no data is available — this is expected before
// any mobile agent has submitted data (Phase 8), so it must not crash or show an error.
export default function MobileChart({ title, data }) {
  function formatTime(ts) {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!data || data.length === 0) {
    return (
      <div className="chart-box">
        <h3 className="chart-title">{title}</h3>
        <p className="muted">No mobile data for this device in this period.</p>
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
          {/* Left Y-axis for RSSI (dBm, typically -100 to 0) */}
          <YAxis
            yAxisId="rssi"
            orientation="left"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            unit=" dBm"
            width={60}
          />
          {/* Right Y-axis for link speed (Mbps) */}
          <YAxis
            yAxisId="speed"
            orientation="right"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            unit=" Mbps"
            width={60}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
            labelFormatter={(ts) => new Date(ts).toLocaleString()}
          />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
          <Line
            yAxisId="rssi"
            type="monotone"
            dataKey="wifi_rssi_dbm"
            name="WiFi RSSI"
            stroke="#818cf8"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
          <Line
            yAxisId="speed"
            type="monotone"
            dataKey="link_speed_mbps"
            name="Link Speed"
            stroke="#34d399"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
