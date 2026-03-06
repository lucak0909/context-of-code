import { useState, useEffect, useCallback } from 'react'
import { getDevices, getSamples, getLatest } from './api'
import AuthScreen from './components/AuthScreen'
import StatusBadge from './components/StatusBadge'
import DeviceSelector from './components/DeviceSelector'
import MetricCard from './components/MetricCard'
import NetworkChart from './components/NetworkChart'

const POLL_INTERVAL_MS = 60_000 // refresh data every 60 seconds
const STALE_THRESHOLD_MS = 15.1 * 60 * 1000 // 15.1 minutes in ms
const SESSION_KEY = 'nm_user'

function isStale(ts) {
  if (!ts) return true
  return Date.now() - new Date(ts).getTime() > STALE_THRESHOLD_MS
}

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY))
  } catch {
    return null
  }
}

export default function App() {
  const [user, setUser] = useState(loadUser)

  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [networkSamples, setNetworkSamples] = useState([])
  const [cloudSamples, setCloudSamples] = useState([])
  const [latest, setLatest] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function handleAuth(userData) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(userData))
    setUser(userData)
  }

  function handleLogout() {
    localStorage.removeItem(SESSION_KEY)
    setUser(null)
    setDevices([])
    setSelectedDevice(null)
    setNetworkSamples([])
    setCloudSamples([])
    setLatest({})
  }

  // Load device list when user changes
  useEffect(() => {
    if (!user) return
    getDevices(user.user_id)
      .then((data) => {
        setDevices(data)
        if (data.length > 0) setSelectedDevice(data[0].id)
      })
      .catch(() => setError('Could not load devices. Is the API reachable?'))
  }, [user])

  const refresh = useCallback(() => {
    if (!selectedDevice) return
    setLoading(true)
    Promise.all([
      getSamples(selectedDevice, 'desktop_network', 1),
      getSamples(selectedDevice, 'cloud_latency', 1),
      getLatest(selectedDevice),
    ])
      .then(([net, cloud, lat]) => {
        setNetworkSamples(net)
        setCloudSamples(cloud)
        setLatest(lat)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(() => setError('Failed to fetch metrics.'))
      .finally(() => setLoading(false))
  }, [selectedDevice])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refresh])

  if (!user) {
    return <AuthScreen onAuth={handleAuth} />
  }

  const net = latest.desktop_network ?? {}
  const cloud = latest.cloud_latency ?? {}

  const netStale = isStale(net.ts)
  const cloudStale = isStale(cloud.ts)
  const cutoffMs = Date.now() - STALE_THRESHOLD_MS
  const freshNetworkSamples = networkSamples.filter(s => s.ts && new Date(s.ts).getTime() > cutoffMs)
  const freshCloudSamples = cloudSamples.filter(s => s.ts && new Date(s.ts).getTime() > cutoffMs)

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <h1 className="app-title">Network Monitor</h1>
          <StatusBadge />
        </div>
        <div className="header-right">
          <DeviceSelector
            devices={devices}
            selected={selectedDevice}
            onChange={setSelectedDevice}
          />
          {lastUpdated && (
            <span className="muted last-updated">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button className="refresh-btn" onClick={refresh} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh'}
          </button>
          <span className="muted">{user.email}</span>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {!error && (netStale || cloudStale) && (
        <div className="error-banner">
          No recent data — last sample is more than 15 minutes old. Is the agent running?
        </div>
      )}

      <main className="main">
        {/* ── Desktop Network Section ── */}
        <section>
          <h2 className="section-title">Desktop Network (last 15 min)</h2>

          <div className="metric-row">
            <MetricCard label="Latency" value={netStale ? null : net.latency_ms} unit="ms" />
            <MetricCard label="Packet Loss" value={netStale ? null : net.packet_loss_pct} unit="%" />
            <MetricCard label="Download" value={netStale ? null : net.down_mbps} unit="Mbps" />
            <MetricCard label="Upload" value={netStale ? null : net.up_mbps} unit="Mbps" />
          </div>

          <div className="chart-grid">
            <NetworkChart
              title="Latency"
              data={freshNetworkSamples}
              lines={[{ key: 'latency_ms', color: '#38bdf8', name: 'Latency' }]}
              unit=" ms"
            />
            <NetworkChart
              title="Packet Loss"
              data={freshNetworkSamples}
              lines={[{ key: 'packet_loss_pct', color: '#f87171', name: 'Packet Loss' }]}
              unit="%"
            />
            <NetworkChart
              title="Download Speed"
              data={freshNetworkSamples}
              lines={[{ key: 'down_mbps', color: '#4ade80', name: 'Download' }]}
              unit=" Mbps"
            />
            <NetworkChart
              title="Upload Speed"
              data={freshNetworkSamples}
              lines={[{ key: 'up_mbps', color: '#fb923c', name: 'Upload' }]}
              unit=" Mbps"
            />
          </div>
        </section>

        {/* ── Cloud Latency Section ── */}
        <section>
          <h2 className="section-title">Cloud Latency (last 15 min)</h2>

          <div className="metric-row">
            <MetricCard label="EU Latency" value={cloudStale ? null : cloud.latency_eu_ms} unit="ms" />
            <MetricCard label="US Latency" value={cloudStale ? null : cloud.latency_us_ms} unit="ms" />
            <MetricCard label="Asia Latency" value={cloudStale ? null : cloud.latency_asia_ms} unit="ms" />
          </div>

          <NetworkChart
            title="Global Cloud Latency"
            data={freshCloudSamples}
            lines={[
              { key: 'latency_eu_ms', color: '#a78bfa', name: 'EU' },
              { key: 'latency_us_ms', color: '#34d399', name: 'US' },
              { key: 'latency_asia_ms', color: '#fbbf24', name: 'Asia' },
            ]}
            unit=" ms"
          />
        </section>
      </main>
    </div>
  )
}
