/**
 * Approvals (drafts) page.
 */
import { useEffect, useState } from 'react'
import { apiGet, apiPost } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function Approvals() {
  const [drafts, setDrafts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiGet('/approvals')
        setDrafts(res.data)
      } catch (err) {
        console.error('Failed to load approvals:', err)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  const handleApprove = async (draftId) => {
    try {
      await apiPost(`/approvals/${draftId}/approve`, {})
      setDrafts(drafts.map(d => d.id === draftId ? { ...d, status: 'approved' } : d))
    } catch (err) {
      console.error('Approval failed:', err)
    }
  }

  const handleReject = async (draftId) => {
    try {
      await apiPost(`/approvals/${draftId}/reject`, {})
      setDrafts(drafts.map(d => d.id === draftId ? { ...d, status: 'rejected' } : d))
    } catch (err) {
      console.error('Rejection failed:', err)
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Approval Queue</h1>

      <div className="space-y-4">
        {drafts.map((draft) => (
          <div key={draft.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-semibold">{draft.subject}</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Type: <span className="font-medium">{draft.type}</span>
                </p>
              </div>
              <StatusBadge status={draft.status} />
            </div>

            <div className="bg-gray-50 p-4 rounded mb-4 max-h-48 overflow-y-auto">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{draft.body}</p>
            </div>

            {draft.status === 'pending' && (
              <div className="flex gap-3">
                <button
                  onClick={() => handleApprove(draft.id)}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReject(draft.id)}
                  className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {drafts.length === 0 && (
        <p className="text-gray-500">No pending approvals.</p>
      )}
    </div>
  )
}
