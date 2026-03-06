import { useState, useEffect } from 'react'
import { getHealth } from '../api'

// Polls /health every 30 seconds and shows a green/red status dot.
export default function StatusBadge() {
  const [status, setStatus] = useState(null) // 'ok' | 'error' | null

  useEffect(() => {
    function check() {
      getHealth()
        .then(() => setStatus('ok'))
        .catch(() => setStatus('error'))
    }
    check()
    const id = setInterval(check, 30_000)
    return () => clearInterval(id)
  }, [])

  const color = status === 'ok' ? '#22c55e' : status === 'error' ? '#ef4444' : '#6b7280'
  const label = status === 'ok' ? 'API online' : status === 'error' ? 'API offline' : 'Checking…'

  return (
    <div className="status-badge">
      <span className="status-dot" style={{ background: color }} />
      <span>{label}</span>
    </div>
  )
}
