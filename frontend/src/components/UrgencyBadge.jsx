/**
 * Urgency badge: urgent / normal / low / flagged.
 */
const styles = {
  urgent: { cls: 'bg-rose-100 text-rose-800 ring-rose-200', label: 'Urgent', dot: 'bg-rose-500' },
  flagged: { cls: 'bg-amber-100 text-amber-900 ring-amber-300', label: 'Suspicious', dot: 'bg-amber-500' },
  normal: { cls: 'bg-brand-50 text-brand-800 ring-brand-200', label: 'Normal', dot: 'bg-brand-400' },
  low: { cls: 'bg-slate-100 text-slate-600 ring-slate-200', label: 'Low', dot: 'bg-slate-400' },
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
