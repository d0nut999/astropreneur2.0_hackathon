/**
 * Urgency badge: urgent / normal / low / flagged.
 */
const styles = {
  urgent: { cls: 'bg-red-100 text-red-800 ring-red-200', label: 'Urgent', dot: 'bg-red-500' },
  flagged: { cls: 'bg-amber-100 text-amber-900 ring-amber-300', label: 'Suspicious', dot: 'bg-amber-500' },
  normal: { cls: 'bg-blue-50 text-blue-800 ring-blue-200', label: 'Normal', dot: 'bg-blue-400' },
  low: { cls: 'bg-gray-100 text-gray-600 ring-gray-200', label: 'Low', dot: 'bg-gray-400' },
}

export default function UrgencyBadge({ urgency, small = false }) {
  const s = styles[urgency] || styles.normal
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full ring-1 font-medium ${s.cls} ${
        small ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}
