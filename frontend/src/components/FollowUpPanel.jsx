/**
 * "We are waiting for this candidate": shown on the candidate page.
 * Reminder = a draft (new personal link) that appears in the yellow box; nothing is sent without a click.
 */
import { useEffect, useState } from 'react'
import { apiPost } from '../api'

const STYLE = {
  due: 'border-orange-300 bg-orange-50',
  your_call: 'border-rose-300 bg-rose-50',
  drafted: 'border-amber-300 bg-amber-50',
  waiting: 'border-slate-200 bg-white',
}
export const STATE_LABEL = {
  due: 'Reminder due',
  your_call: 'Your call',
  drafted: 'Reminder drafted',
  waiting: 'Waiting',
}

export function FollowUpActions({ f, onDone, compact = false }) {
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')
  const [closing, setClosing] = useState(false)
  const [note, setNote] = useState('')
  useEffect(() => { setMsg('') }, [f.state, f.reminders_sent])  // old messages disappear once things move on
  const run = async (label, path, data) => {
    setBusy(label)
    setMsg('')
    try {
      const r = await apiPost(path, data)
      setMsg(r.data.message)
      setClosing(false)
      await onDone?.(label)
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Action failed')
    } finally {
      setBusy('')
    }
  }
  const size = compact ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'
  return (
    <div>
      <div className="flex flex-wrap gap-2 items-center">
        {f.can_remind && (
          <button onClick={() => run('remind', `/followups/${f.application_id}/remind`)} disabled={!!busy}
            className={`${size} rounded-lg font-medium disabled:opacity-50 bg-orange-500 text-white hover:bg-orange-600`}>
            {busy === 'remind' ? 'Drafting…' : f.reminders_sent + 1 >= f.max_reminders ? 'Prepare last reminder' : 'Prepare reminder'}
          </button>
        )}
        {f.can_close && !closing && (
          <button onClick={() => setClosing(true)} disabled={!!busy}
            className={`${size} rounded-lg border border-rose-300 text-rose-700 hover:bg-rose-50 disabled:opacity-50`}>
            Close application…
          </button>
        )}
      </div>
      {closing && (
        <div className="mt-3 p-3 rounded-lg border border-rose-200 bg-white">
          <p className="text-sm text-slate-700 mb-2">
            Close the application for no response? This is saved as your decision, and a polite email (inviting them
            to reply if it was a mistake) is drafted for your approval.
          </p>
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note for the audit log"
            className="w-full border rounded px-3 py-1.5 text-sm mb-2" />
          <div className="flex gap-2">
            <button onClick={() => run('close', `/followups/${f.application_id}/close`, { note })} disabled={!!busy}
              className="btn bg-rose-600 text-white hover:bg-rose-700">
              {busy === 'close' ? 'Closing…' : 'Yes, close it'}
            </button>
            <button onClick={() => setClosing(false)} className="px-3 py-1.5 text-sm rounded-lg border">Cancel</button>
          </div>
        </div>
      )}
      {msg && <p className="text-sm text-slate-700 mt-2">{msg}</p>}
    </div>
  )
}

export default function FollowUpPanel({ f, onDone }) {
  if (!f) return null
  return (
    <div id="followup" className={`rounded-lg shadow p-6 mb-6 border ${STYLE[f.state]}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Follow-up</p>
          <p className="font-semibold text-slate-900">{STATE_LABEL[f.state]} · {f.waiting_for}</p>
          <p className="text-sm text-slate-700 mt-1">{f.reason}</p>
          <p className="text-xs text-slate-500 mt-2">
            Last email {f.last_contact_ago} · Reminders sent {f.reminders_sent}/{f.max_reminders}
            {f.link_expires_at && <> · Link {f.link_expired ? 'expired' : 'valid until ' + new Date(f.link_expires_at).toLocaleString([], { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</>}
          </p>
        </div>
        <FollowUpActions f={f} onDone={onDone} />
      </div>
    </div>
  )
}
