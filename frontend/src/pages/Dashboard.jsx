/**
 * Dashboard page.
 */
import { useEffect, useState } from 'react'
import { apiGet } from '../api'

export default function Dashboard() {
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiGet('/digest/today')
        setDigest(res.data)
      } catch (err) {
        console.error('Failed to load digest:', err)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  if (!digest)
    return <div className="text-center text-gray-500">No data</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm mb-1">High Urgency Emails</p>
          <p className="text-3xl font-bold text-red-600">{digest.high_urgency_count}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm mb-1">Needs Human Review</p>
          <p className="text-3xl font-bold text-yellow-600">{digest.needs_human_count}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm mb-1">Pending Approvals</p>
          <p className="text-3xl font-bold text-blue-600">{digest.pending_approvals_count}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm mb-1">Pending Applications</p>
          <p className="text-3xl font-bold text-purple-600">{digest.pending_applications_count}</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-2">Summary</h2>
        <p className="text-gray-700">{digest.summary}</p>
      </div>
    </div>
  )
}
