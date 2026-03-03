// All API calls in one place.
// VITE_API_URL can be set in a .env file to point at the production VM,
// e.g. VITE_API_URL=http://200.69.13.70:5017
// When running `npm run dev` the vite proxy forwards /api and /health to localhost:5000.
const BASE = import.meta.env.VITE_API_URL ?? ''

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} returned ${res.status}`)
  return res.json()
}

export const getHealth = () => get('/health')

export const getDevices = () => get('/api/report/devices')

export const getSamples = (deviceId, sampleType, hours = 24) => {
  const params = new URLSearchParams({ device_id: deviceId, hours })
  if (sampleType) params.set('sample_type', sampleType)
  return get(`/api/report/samples?${params}`)
}

export const getLatest = (deviceId) =>
  get(`/api/report/latest?device_id=${deviceId}`)
