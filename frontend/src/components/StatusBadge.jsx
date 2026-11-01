/**
 * Status badge: soft color + dot, sentence case.
 */
const STYLES = {
  RECEIVED: ['bg-slate-100 text-slate-700', 'bg-slate-400', 'Received'],
  SCREENED: ['bg-slate-100 text-slate-700', 'bg-slate-400', 'Screened'],
  SCORED: ['bg-brand-50 text-brand-700', 'bg-brand-500', 'Scored'],
  SHORTLISTED: ['bg-amber-50 text-amber-800', 'bg-amber-500', 'Shortlisted'],
  INVITED: ['bg-sky-50 text-sky-700', 'bg-sky-500', 'Invited'],
  VIDEO_SUBMITTED: ['bg-violet-50 text-violet-700', 'bg-violet-500', 'Answered'],
  EVALUATED: ['bg-orange-50 text-orange-700', 'bg-orange-500', 'Evaluated'],
  DECIDED: ['bg-emerald-50 text-emerald-700', 'bg-emerald-500', 'Decided'],
  QUARANTINED: ['bg-rose-50 text-rose-700', 'bg-rose-500', 'Blocked'],
  pending: ['bg-amber-50 text-amber-800', 'bg-amber-500', 'Pending'],
  approved: ['bg-emerald-50 text-emerald-700', 'bg-emerald-500', 'Approved'],
  rejected: ['bg-rose-50 text-rose-700', 'bg-rose-500', 'Rejected'],
  sent: ['bg-emerald-50 text-emerald-700', 'bg-emerald-500', 'Sent'],
}

export default function StatusBadge({ status }) {
  const [cls, dot, label] = STYLES[status] || ['bg-slate-100 text-slate-700', 'bg-slate-400', status]
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}
