/**
 * Email category tag.
 */
export const CATEGORY_LABELS = {
  candidate_application: { label: 'Application', cls: 'bg-purple-50 text-purple-700' },
  candidate_reply: { label: 'Candidate', cls: 'bg-violet-50 text-violet-700' },
  work_meeting: { label: 'Meeting', cls: 'bg-emerald-50 text-emerald-700' },
  work_request: { label: 'Request', cls: 'bg-sky-50 text-sky-700' },
  work_info: { label: 'Info', cls: 'bg-slate-100 text-slate-600' },
  spam_phishing: { label: 'Phishing', cls: 'bg-rose-50 text-rose-700' },
  leave_request: { label: 'Leave', cls: 'bg-teal-50 text-teal-700' },
  employee_question: { label: 'Employee question', cls: 'bg-brand-50 text-brand-700' },
}

export default function CategoryTag({ category }) {
  const c = CATEGORY_LABELS[category] || { label: category, cls: 'bg-slate-100 text-slate-600' }
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${c.cls}`}>{c.label}</span>
}
