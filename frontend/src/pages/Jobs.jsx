/**
 * Jobs listing page.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../api'

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet('/jobs')
      .then((res) => setJobs(res.data))
      .catch((err) => console.error('Failed to load jobs:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Jobs</h1>
      <p className="text-gray-500 text-sm mb-6">Candidates who apply by email are screened, anonymized and scored automatically.</p>

      <div className="space-y-4">
        {jobs.map((job) => {
          const scored = (job.status_counts?.SCORED || 0) + (job.status_counts?.SHORTLISTED || 0)
          return (
            <Link key={job.id} to={`/jobs/${job.id}`} className="block bg-white p-6 rounded-lg shadow hover:shadow-md transition">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-blue-700">{job.title}</h2>
                  <p className="text-gray-600 mt-2 whitespace-pre-line line-clamp-3 text-sm">{job.description}</p>
                </div>
                <div className="flex gap-3 text-center shrink-0">
                  <div className="px-3">
                    <div className="text-2xl font-bold">{job.applications}</div>
                    <div className="text-xs text-gray-500">applications</div>
                  </div>
                  <div className="px-3">
                    <div className="text-2xl font-bold text-purple-600">{scored}</div>
                    <div className="text-xs text-gray-500">scored</div>
                  </div>
                  <div className="px-3">
                    <div className="text-2xl font-bold text-amber-600">{job.quarantined || 0}</div>
                    <div className="text-xs text-gray-500">blocked</div>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
                {job.rubric?.map((c) => (
                  <span key={c.key} className="text-xs bg-gray-100 text-gray-700 rounded px-2 py-1">
                    {c.label} · {Math.round(c.weight)}%{c.must_have ? ' · must-have' : ''}
                  </span>
                ))}
              </div>
            </Link>
          )
        })}
      </div>

      {jobs.length === 0 && <p className="text-gray-500">No jobs yet. Run <code>python scripts/seed.py</code> in the backend.</p>}
    </div>
  )
}
