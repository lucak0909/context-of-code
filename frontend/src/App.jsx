import { useState, useEffect, useCallback } from 'react'
import { getDevices, getSamples, getLatest } from './api'
import StatusBadge from './components/StatusBadge'
import DeviceSelector from './components/DeviceSelector'
import MetricCard from './components/MetricCard'
import NetworkChart from './components/NetworkChart'

const POLL_INTERVAL_MS = 60_000 // refresh data every 60 seconds

export default function App() {
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [networkSamples, setNetworkSamples] = useState([])
  const [cloudSamples, setCloudSamples] = useState([])
  const [latest, setLatest] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load device list once on mount
  useEffect(() => {
    getDevices()
      .then((data) => {
        setDevices(data)
        if (data.length > 0) setSelectedDevice(data[0].id)
      })
      .catch(() => setError('Could not load devices. Is the API reachable?'))
  }, [])

  // Fetch samples + latest whenever the selected device changes, then poll
  const refresh = useCallback(() => {
    if (!selectedDevice) return
    setLoading(true)
    Promise.all([
      getSamples(selectedDevice, 'desktop_network', 24),
      getSamples(selectedDevice, 'cloud_latency', 24),
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

  const net = latest.desktop_network ?? {}
  const cloud = latest.cloud_latency ?? {}

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
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="main">
        {/* ── Desktop Network Section ── */}
        <section>
          <h2 className="section-title">Desktop Network (last 24 h)</h2>

          <div className="metric-row">
            <MetricCard label="Latency" value={net.latency_ms} unit="ms" />
            <MetricCard label="Packet Loss" value={net.packet_loss_pct} unit="%" />
            <MetricCard label="Download" value={net.down_mbps} unit="Mbps" />
            <MetricCard label="Upload" value={net.up_mbps} unit="Mbps" />
          </div>

          <div className="chart-grid">
            <NetworkChart
              title="Latency"
              data={networkSamples}
              lines={[{ key: 'latency_ms', color: '#38bdf8', name: 'Latency' }]}
              unit=" ms"
            />
            <NetworkChart
              title="Packet Loss"
              data={networkSamples}
              lines={[{ key: 'packet_loss_pct', color: '#f87171', name: 'Packet Loss' }]}
              unit="%"
            />
            <NetworkChart
              title="Download Speed"
              data={networkSamples}
              lines={[{ key: 'down_mbps', color: '#4ade80', name: 'Download' }]}
              unit=" Mbps"
            />
            <NetworkChart
              title="Upload Speed"
              data={networkSamples}
              lines={[{ key: 'up_mbps', color: '#fb923c', name: 'Upload' }]}
              unit=" Mbps"
            />
          </div>
        </section>

        {/* ── Cloud Latency Section ── */}
        <section>
          <h2 className="section-title">Cloud Latency (last 24 h)</h2>

          <div className="metric-row">
            <MetricCard label="EU Latency" value={cloud.latency_eu_ms} unit="ms" />
            <MetricCard label="US Latency" value={cloud.latency_us_ms} unit="ms" />
            <MetricCard label="Asia Latency" value={cloud.latency_asia_ms} unit="ms" />
          </div>

          <NetworkChart
            title="Global Cloud Latency"
            data={cloudSamples}
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
