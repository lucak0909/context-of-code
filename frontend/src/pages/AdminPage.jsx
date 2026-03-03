import { useState, useEffect, useCallback } from 'react'
import { getAdmin, getDevices, getLatest, getSamples } from '../api'

const POLL_MS = 30_000

export default function AdminPage() {
  const [stats, setStats] = useState(null)
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [latest, setLatest] = useState({})
  const [networkSamples, setNetworkSamples] = useState([])
  const [cloudSamples, setCloudSamples] = useState([])
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  // Fetch top-level stats + device list
  function fetchStats() {
    Promise.all([getAdmin(), getDevices()])
      .then(([s, d]) => {
        setStats(s)
        setDevices(d)
        if (d.length > 0 && !selectedDevice) setSelectedDevice(d[0].id)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(() => setError('Could not reach the API'))
  }

  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, POLL_MS)
    return () => clearInterval(id)
  }, [])

  // Fetch device-specific data whenever selectedDevice changes
  const fetchDeviceData = useCallback(() => {
    if (!selectedDevice) return
    Promise.all([
      getLatest(selectedDevice),
      getSamples(selectedDevice, 'desktop_network', 24),
      getSamples(selectedDevice, 'cloud_latency', 24),
    ]).then(([lat, net, cloud]) => {
      setLatest(lat)
      setNetworkSamples(net)
      setCloudSamples(cloud)
    }).catch(() => setError('Could not load device data'))
  }, [selectedDevice])

  useEffect(() => { fetchDeviceData() }, [fetchDeviceData])

  const net = latest.desktop_network ?? {}
  const cloud = latest.cloud_latency ?? {}
  const selectedDev = devices.find(d => d.id === selectedDevice)

  return (
    <div className="admin-page">
      <header className="admin-header">
        <h1 className="admin-title">Admin</h1>
        {lastUpdated && <span className="muted">Updated {lastUpdated.toLocaleTimeString()}</span>}
        <button className="refresh-btn" onClick={() => { fetchStats(); fetchDeviceData() }}>Refresh</button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {stats && (
        <main className="admin-main">
          {/* ── DB overview ── */}
          <section>
            <h2 className="section-title">DB Overview</h2>
            <div className="admin-grid">
              <StatCard label="Users" value={stats.total_users} />
              <StatCard label="Devices" value={stats.total_devices} />
              <StatCard label="Total Samples" value={stats.total_samples} />
              <StatCard label="Latest Sample" value={stats.latest_sample_ts ? new Date(stats.latest_sample_ts).toLocaleString() : '—'} small />
            </div>

            <table className="admin-table" style={{ marginTop: 16 }}>
              <thead>
                <tr><th>Sample Type</th><th>Count</th></tr>
              </thead>
              <tbody>
                {Object.entries(stats.samples_by_type ?? {}).map(([type, count]) => (
                  <tr key={type}>
                    <td>{type}</td>
                    <td>{count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* ── Device inspector ── */}
          <section>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <h2 className="section-title" style={{ marginBottom: 0 }}>Device Inspector</h2>
              <select
                className="device-select"
                value={selectedDevice ?? ''}
                onChange={e => setSelectedDevice(e.target.value)}
              >
                {devices.map(d => (
                  <option key={d.id} value={d.id}>{d.name} ({d.device_type})</option>
                ))}
              </select>
            </div>

            {selectedDev && (
              <p className="muted" style={{ marginBottom: 16 }}>
                ID: {selectedDev.id} &nbsp;·&nbsp; Created: {selectedDev.created_at ? new Date(selectedDev.created_at).toLocaleString() : '—'}
              </p>
            )}

            {/* Latest values */}
            <h3 className="admin-sub-title">Latest Desktop Network</h3>
            <div className="admin-grid" style={{ marginBottom: 20 }}>
              <StatCard label="Latency" value={net.latency_ms != null ? `${net.latency_ms?.toFixed(1)} ms` : '—'} small />
              <StatCard label="Packet Loss" value={net.packet_loss_pct != null ? `${net.packet_loss_pct?.toFixed(1)} %` : '—'} small />
              <StatCard label="Download" value={net.down_mbps != null ? `${net.down_mbps?.toFixed(2)} Mbps` : '—'} small />
              <StatCard label="Upload" value={net.up_mbps != null ? `${net.up_mbps?.toFixed(2)} Mbps` : '—'} small />
            </div>

            <h3 className="admin-sub-title">Latest Cloud Latency</h3>
            <div className="admin-grid" style={{ marginBottom: 24 }}>
              <StatCard label="EU" value={cloud.latency_eu_ms != null ? `${cloud.latency_eu_ms?.toFixed(1)} ms` : '—'} small />
              <StatCard label="US" value={cloud.latency_us_ms != null ? `${cloud.latency_us_ms?.toFixed(1)} ms` : '—'} small />
              <StatCard label="Asia" value={cloud.latency_asia_ms != null ? `${cloud.latency_asia_ms?.toFixed(1)} ms` : '—'} small />
            </div>

            {/* Recent samples tables */}
            <SamplesTable title="Recent Desktop Network (last 24 h)" rows={networkSamples} columns={NET_COLS} />
            <SamplesTable title="Recent Cloud Latency (last 24 h)" rows={cloudSamples} columns={CLOUD_COLS} />
          </section>
        </main>
      )}
    </div>
  )
}

const NET_COLS = [
  { key: 'ts', label: 'Time', fmt: v => new Date(v).toLocaleString() },
  { key: 'latency_ms', label: 'Latency (ms)', fmt: v => v?.toFixed(1) ?? '—' },
  { key: 'packet_loss_pct', label: 'Loss %', fmt: v => v?.toFixed(1) ?? '—' },
  { key: 'down_mbps', label: 'Down Mbps', fmt: v => v?.toFixed(2) ?? '—' },
  { key: 'up_mbps', label: 'Up Mbps', fmt: v => v?.toFixed(2) ?? '—' },
  { key: 'test_method', label: 'Method', fmt: v => v ?? '—' },
]

const CLOUD_COLS = [
  { key: 'ts', label: 'Time', fmt: v => new Date(v).toLocaleString() },
  { key: 'latency_eu_ms', label: 'EU (ms)', fmt: v => v?.toFixed(1) ?? '—' },
  { key: 'latency_us_ms', label: 'US (ms)', fmt: v => v?.toFixed(1) ?? '—' },
  { key: 'latency_asia_ms', label: 'Asia (ms)', fmt: v => v?.toFixed(1) ?? '—' },
]

function SamplesTable({ title, rows, columns }) {
  if (!rows.length) return (
    <div style={{ marginBottom: 24 }}>
      <h3 className="admin-sub-title">{title}</h3>
      <p className="muted">No data in last 24 h</p>
    </div>
  )
  return (
    <div style={{ marginBottom: 24 }}>
      <h3 className="admin-sub-title">{title} ({rows.length} rows)</h3>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {[...rows].reverse().map((row, i) => (
              <tr key={i}>
                {columns.map(c => <td key={c.key}>{c.fmt(row[c.key])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatCard({ label, value, small = false }) {
  return (
    <div className="metric-card">
      <div className={small ? 'admin-stat-value-sm' : 'metric-value'}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div className="metric-label">{label}</div>
    </div>
  )
}
