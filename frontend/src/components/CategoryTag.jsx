/**
 * Email category tag.
 */
export const CATEGORY_LABELS = {
  candidate_application: { label: 'Application', cls: 'bg-purple-50 text-purple-700' },
  candidate_reply: { label: 'Candidate', cls: 'bg-violet-50 text-violet-700' },
  work_meeting: { label: 'Meeting', cls: 'bg-emerald-50 text-emerald-700' },
  work_request: { label: 'Request', cls: 'bg-sky-50 text-sky-700' },
  work_info: { label: 'Info', cls: 'bg-gray-100 text-gray-600' },
  spam_phishing: { label: 'Phishing', cls: 'bg-red-50 text-red-700' },
}

export default function CategoryTag({ category }) {
  const c = CATEGORY_LABELS[category] || { label: category, cls: 'bg-gray-100 text-gray-600' }
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${c.cls}`}>{c.label}</span>
}
