// Dropdown that lets the user pick which device to view.
export default function DeviceSelector({ devices, selected, onChange }) {
  if (!devices.length) return <span className="muted">No devices found</span>

  return (
    <select
      className="device-select"
      value={selected ?? ''}
      onChange={(e) => onChange(e.target.value)}
    >
      {devices.map((d) => (
        <option key={d.id} value={d.id}>
          {d.name} ({d.device_type})
        </option>
      ))}
    </select>
  )
}
