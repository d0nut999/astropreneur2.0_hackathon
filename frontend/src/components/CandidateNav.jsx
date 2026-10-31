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
      <Link to={`/jobs/${job.id}`} className="text-blue-600 hover:underline">← {job.title}</Link>
      {rows.length > 1 && (
        <div className="flex items-center gap-2">
          {prev ? <Link to={`/candidates/${prev.id}`} className="px-3 py-1 rounded border bg-white hover:bg-gray-50">‹ {label(prev)}</Link>
            : <span className="px-3 py-1 text-gray-300">‹</span>}
          <span className="text-gray-500">{idx + 1} / {rows.length}</span>
          {next ? <Link to={`/candidates/${next.id}`} className="px-3 py-1 rounded border bg-white hover:bg-gray-50">{label(next)} ›</Link>
            : <span className="px-3 py-1 text-gray-300">›</span>}
        </div>
      )}
    </div>
  )
}
