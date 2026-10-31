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
    const load = async () => {
      try {
        const res = await apiGet('/jobs')
        setJobs(res.data)
      } catch (err) {
        console.error('Failed to load jobs:', err)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Job Postings</h1>

      <div className="space-y-4">
        {jobs.map((job) => (
          <div key={job.id} className="bg-white p-6 rounded-lg shadow hover:shadow-lg">
            <Link to={`/job/${job.id}`} className="no-underline">
              <h2 className="text-xl font-semibold text-blue-600 hover:underline">
                {job.title}
              </h2>
            </Link>
            <p className="text-gray-600 mt-2">{job.description}</p>
            <p className="text-sm text-gray-500 mt-2">
              Created: {new Date(job.created_at).toLocaleDateString()}
            </p>
          </div>
        ))}
      </div>

      {jobs.length === 0 && <p className="text-gray-500">No jobs found.</p>}
    </div>
  )
}
