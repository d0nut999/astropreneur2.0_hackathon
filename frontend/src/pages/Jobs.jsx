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
      <div className="flex flex-wrap justify-between items-end gap-3 mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-1">Jobs</h1>
          <p className="text-gray-500 text-sm">Candidates who apply by email are screened, anonymized and scored automatically.</p>
        </div>
        <Link to="/jobs/new" className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700">＋ New job post</Link>
      </div>

      <div className="space-y-4">
        {jobs.map((job) => {
          const scored = (job.status_counts?.SCORED || 0) + (job.status_counts?.SHORTLISTED || 0)
          return (
            <div key={job.id} className="bg-white rounded-lg shadow hover:shadow-md transition">
            <Link to={job.post?.status === 'draft' ? `/jobs/${job.id}/post` : `/jobs/${job.id}`} className="block p-6 pb-3">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-blue-700">
                    {job.title}
                    {job.post && (
                      <span className={`ml-2 align-middle text-xs px-2 py-0.5 rounded-full ${job.post.status === 'published' ? 'bg-green-100 text-green-800' : job.post.status === 'closed' ? 'bg-gray-200 text-gray-700' : 'bg-yellow-100 text-yellow-800'}`}>
                        {job.post.code} · {job.post.status === 'draft' ? 'draft' : job.post.status}
                      </span>
                    )}
                  </h2>
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
            {job.post && (
              <div className="px-6 pb-4 flex gap-4 text-sm">
                <Link to={`/jobs/${job.id}/post`} className="text-blue-600 hover:underline">Job post →</Link>
                {job.post.public_slug && <a href={`/careers/${job.post.public_slug}`} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">Public page ↗</a>}
              </div>
            )}
            {!job.post && <div className="pb-3" />}
            </div>
          )
        })}
      </div>

      {jobs.length === 0 && <p className="text-gray-500">No jobs yet. Run <code>python scripts/seed.py</code> in the backend.</p>}
    </div>
  )
}
