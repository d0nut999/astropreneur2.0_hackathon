/**
 * Emails waiting for approval, shown where HR is working (candidate page, inbox).
 * Same rules as the Approvals page: read, edit, approve & send, or reject. Nothing is sent without the click.
 */
import { useState } from 'react'
import { apiPost, apiPut } from '../api'
import Icon from './Icon'

const TYPE_LABEL = { invite: 'Interview invitation', reply: 'Reply', reminder: 'Reminder', rejection: 'Rejection' }

export default function InlineDrafts({ drafts, onDone, title = 'Email waiting for your approval' }) {
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(null)
  const [msg, setMsg] = useState('')
  if (!drafts?.length) return null

  const act = async (id, fn, text) => {
    setBusy(id)
    setMsg('')
    try {
      const r = await fn()
      setMsg(r?.data?.message && r.data.message !== 'Sent' ? r.data.message : text)
      setEditing(null)
      await onDone?.()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Action failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div id="inline-drafts" className="mb-6 rounded-xl border border-amber-200 bg-amber-50/70 p-5 shadow-card">
      <p className="mb-1 flex items-center gap-2 text-sm font-semibold text-amber-900"><Icon name="mail" className="h-4 w-4" />{drafts.length > 1 ? `${drafts.length} emails waiting for your approval` : title}</p>
      <p className="text-xs text-amber-800 mb-3">Read it, edit if needed, then send. Nothing leaves HR Buddy without your click.</p>
      {msg && <p className="text-sm text-emerald-800 bg-emerald-50 rounded px-3 py-2 mb-3">{msg}</p>}
      <div className="space-y-4">
        {drafts.map((d) => (
          <div key={d.id} className="bg-white rounded-lg border p-4">
            <div className="flex flex-wrap justify-between gap-2 mb-2">
              <div className="min-w-0">
                {editing?.id === d.id ? (
                  <input className="w-full border rounded px-2 py-1 font-semibold" value={editing.subject}
                    onChange={(e) => setEditing({ ...editing, subject: e.target.value })} />
                ) : (
                  <p className="font-semibold">{d.subject}</p>
                )}
                <p className="text-xs text-slate-500">{TYPE_LABEL[d.type] || d.type} · to {d.to_addr || 'candidate'}</p>
              </div>
            </div>
            {editing?.id === d.id ? (
              <textarea className="w-full border rounded p-3 text-sm h-56 mb-3" value={editing.body}
                onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
            ) : (
              <div className="bg-slate-50 rounded p-3 text-sm whitespace-pre-wrap max-h-60 overflow-y-auto mb-3">{d.body}</div>
            )}
            <div className="flex flex-wrap gap-2">
              {editing?.id === d.id ? (
                <>
                  <button disabled={busy === d.id} onClick={() => act(d.id, () => apiPut(`/approvals/${d.id}`, { subject: editing.subject, body: editing.body }), 'Saved.')}
                    className="btn-primary">Save</button>
                  <button onClick={() => setEditing(null)} className="btn-secondary">Cancel</button>
                </>
              ) : (
                <>
                  <button disabled={busy === d.id} onClick={() => act(d.id, () => apiPost(`/approvals/${d.id}/approve`), 'Sent ✓')}
                    className="btn-success">
                    {busy === d.id ? 'Sending…' : 'Approve & send'}
                  </button>
                  <button onClick={() => setEditing({ id: d.id, subject: d.subject, body: d.body })}
                    className="btn-secondary">Edit</button>
                  <button disabled={busy === d.id} onClick={() => act(d.id, () => apiPost(`/approvals/${d.id}/reject`), 'Rejected. Nothing was sent.')}
                    className="btn-danger">Reject</button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
