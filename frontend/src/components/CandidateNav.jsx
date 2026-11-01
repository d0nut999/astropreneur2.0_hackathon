/**
 * Breadcrumb + previous / next candidate in the job's ranking, so HR never has to go back to the list.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../api'

export default function CandidateNav({ job, currentId, showNames }) {
  const [rows, setRows] = useState([])
  useEffect(() => {
    if (job?.id) apiGet(`/candidates?job_id=${job.id}`).then((r) => setRows(r.data)).catch(() => {})
  }, [job?.id, currentId])
  if (!job) return null
  const idx = rows.findIndex((r) => String(r.id) === String(currentId))
  const prev = idx > 0 ? rows[idx - 1] : null
  const next = idx >= 0 && idx < rows.length - 1 ? rows[idx + 1] : null
  const label = (r) => (showNames ? r.name : r.alias)
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
      <Link to={`/jobs/${job.id}`} className="text-brand-600 hover:underline">← {job.title}</Link>
      {rows.length > 1 && (
        <div className="flex items-center gap-2">
          {prev ? <Link to={`/candidates/${prev.id}`} className="btn-secondary">‹ {label(prev)}</Link>
            : <span className="px-3 py-1 text-slate-300">‹</span>}
          <span className="text-slate-500">{idx + 1} / {rows.length}</span>
          {next ? <Link to={`/candidates/${next.id}`} className="btn-secondary">{label(next)} ›</Link>
            : <span className="px-3 py-1 text-slate-300">›</span>}
        </div>
      )}
    </div>
  )
}
