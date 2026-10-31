/**
 * Approvals (drafts) page: every outgoing email waits here.
 * Nothing is sent until HR clicks "Approve & send".
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost, apiPut } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function Approvals() {
  const [drafts, setDrafts] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('pending')
  const [editing, setEditing] = useState(null) // { id, subject, body }
  const [notice, setNotice] = useState('')
  const [picked, setPicked] = useState([])
  const [sending, setSending] = useState(false)

  const load = async () => {
    try {
      const res = await apiGet(`/approvals?status=${tab}`)
      setDrafts(res.data)
    } catch (err) {
      console.error('Failed to load approvals:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tab])

  const update = (id, patch) => setDrafts(drafts.map((d) => (d.id === id ? { ...d, ...patch } : d)))

  const handleApprove = async (draftId) => {
    try {
      const res = await apiPost(`/approvals/${draftId}/approve`, {})
      update(draftId, { status: res.data.status || 'approved' })
      setNotice(res.data.message ? `${res.data.message}${res.data.to ? ` → ${res.data.to}` : ''}` : 'Approved')
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Approval failed')
    }
  }

  const handleReject = async (draftId) => {
    try {
      await apiPost(`/approvals/${draftId}/reject`, {})
      update(draftId, { status: 'rejected' })
      setNotice('Draft rejected. Nothing was sent.')
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Rejection failed')
    }
  }

  const saveEdit = async () => {
    try {
      await apiPut(`/approvals/${editing.id}`, { subject: editing.subject, body: editing.body })
      update(editing.id, { subject: editing.subject, body: editing.body })
      setEditing(null)
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Could not save')
    }
  }

  const pending = drafts.filter((d) => d.status === 'pending')
  const togglePick = (id) => setPicked(picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id])

  const approveSelected = async () => {
    setSending(true)
    try {
      const res = await apiPost('/approvals/bulk_approve', { ids: picked })
      setNotice(res.data.message)
      setPicked([])
      await load()
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Could not send')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Approval Queue</h1>
      <p className="text-gray-500 text-sm mb-4">The AI drafts. You read, edit, and decide. Nothing leaves without your click.</p>

      <div className="flex gap-2 mb-4">
        {['pending', 'sent', 'approved', 'rejected', 'all'].map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium capitalize ${
              tab === t ? 'bg-gray-900 text-white' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'pending' && pending.length > 1 && (
        <div className="sticky top-0 z-10 mb-4 bg-white rounded-lg shadow px-4 py-3 flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" className="h-4 w-4" checked={picked.length === pending.length}
              onChange={(e) => setPicked(e.target.checked ? pending.map((d) => d.id) : [])} />
            Select all ({pending.length})
          </label>
          <span className="text-gray-500">Read each email below, untick any you want to keep back.</span>
          <button onClick={approveSelected} disabled={!picked.length || sending}
            className="ml-auto px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-40">
            {sending ? 'Sending…' : `Approve & send selected (${picked.length})`}
          </button>
        </div>
      )}

      {notice && <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-900">{notice}</div>}

      <div className="space-y-4">
        {drafts.map((draft) => (
          <div key={draft.id} className={`bg-white p-6 rounded-lg shadow ${picked.includes(draft.id) ? 'ring-2 ring-green-400' : ''}`}>
            <div className="flex justify-between items-start mb-3">
              <div className="min-w-0 flex gap-3">
                {draft.status === 'pending' && pending.length > 1 && (
                  <input type="checkbox" className="h-4 w-4 mt-1.5" checked={picked.includes(draft.id)} onChange={() => togglePick(draft.id)} />
                )}
                <div className="min-w-0">
                {editing?.id === draft.id ? (
                  <input className="w-full border rounded px-2 py-1 text-lg font-semibold" value={editing.subject}
                    onChange={(e) => setEditing({ ...editing, subject: e.target.value })} />
                ) : (
                  <h2 className="text-xl font-semibold">{draft.subject}</h2>
                )}
                <p className="text-sm text-gray-600 mt-1">
                  To: <span className="font-medium">{draft.to_addr || '—'}</span> · Type: <span className="font-medium">{draft.type}</span>
                  {draft.email_id && (
                    <> · <Link to={`/inbox?id=${draft.email_id}`} className="text-blue-600 hover:underline">original email</Link></>
                  )}
                  {draft.application_id && (
                    <> · <Link to={`/candidates/${draft.application_id}`} className="text-blue-600 hover:underline">← Candidate #{String(draft.application_id).padStart(3, '0')}</Link></>
                  )}
                </p>
                </div>
              </div>
              <StatusBadge status={draft.status} />
            </div>

            {editing?.id === draft.id ? (
              <textarea className="w-full border rounded p-3 text-sm h-48 mb-4" value={editing.body}
                onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
            ) : (
              <div className="bg-gray-50 p-4 rounded mb-4 max-h-48 overflow-y-auto">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{draft.body}</p>
              </div>
            )}

            {draft.status === 'pending' && (
              <div className="flex gap-3">
                {editing?.id === draft.id ? (
                  <>
                    <button onClick={saveEdit} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Save</button>
                    <button onClick={() => setEditing(null)} className="border px-4 py-2 rounded hover:bg-gray-50">Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => handleApprove(draft.id)} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                      Approve &amp; send
                    </button>
                    <button onClick={() => setEditing({ id: draft.id, subject: draft.subject, body: draft.body })}
                      className="border border-gray-300 px-4 py-2 rounded hover:bg-gray-50">
                      Edit
                    </button>
                    <button onClick={() => handleReject(draft.id)} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                      Reject
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {drafts.length === 0 && <p className="text-gray-500">No {tab === 'all' ? '' : tab} drafts.</p>}
    </div>
  )
}
