/**
 * Follow-ups: every candidate we are waiting for, oldest silence first.
 * Reminders are drafts (approve inline); after the maximum, HR decides.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import InlineDrafts from '../components/InlineDrafts'
import { FollowUpActions, STATE_LABEL } from '../components/FollowUpPanel'

const BADGE = {
  due: 'bg-orange-100 text-orange-800',
  your_call: 'bg-red-100 text-red-800',
  drafted: 'bg-yellow-100 text-yellow-800',
  waiting: 'bg-gray-100 text-gray-700',
}

export default function FollowUps() {
  const [data, setData] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    const [f, d] = await Promise.all([apiGet('/followups'), apiGet('/approvals')])
    setData(f.data)
    setDrafts(d.data.filter((x) => x.type === 'reminder' || (x.type === 'rejection' && x.subject.startsWith('Your application'))))
  }
  useEffect(() => { load() }, [])

  const remindAll = async () => {
    setBusy(true)
    try {
      const r = await apiPost('/followups/remind_due')
      setMsg(r.data.message)
      await load()
    } finally {
      setBusy(false)
    }
  }
  const shift = async (hours) => {
    await apiPost('/followups/demo_clock', { hours })
    await load()
  }

  if (!data) return <p className="text-gray-500">Loading…</p>
  const { items, counts } = data

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Follow-ups</h1>
          <p className="text-gray-600 mt-1">
            Candidates we are waiting for. A reminder is due after {data.after_hours} h of silence; each one has a
            fresh personal link. After {data.max_reminders} reminders, you decide. Nothing is sent without your click.
          </p>
        </div>
        {counts.due > 0 && (
          <button onClick={remindAll} disabled={busy}
            className="px-4 py-2 rounded-lg bg-orange-500 text-white font-medium hover:bg-orange-600 disabled:opacity-50">
            {busy ? 'Drafting…' : `Prepare ${counts.due} due reminder${counts.due > 1 ? 's' : ''}`}
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2 my-4 text-sm">
        {['due', 'your_call', 'drafted', 'waiting'].map((s) => (
          <span key={s} className={`px-3 py-1 rounded-full ${BADGE[s]}`}>{STATE_LABEL[s]}: {counts[s]}</span>
        ))}
        {data.dev && (
          <span className="ml-auto flex items-center gap-2 text-xs text-gray-500">
            Demo clock: {data.demo_shift_hours ? `+${data.demo_shift_hours / 24} days` : 'now'}
            <button onClick={() => shift(data.demo_shift_hours + 72)} className="px-2 py-1 rounded border hover:bg-white">⏩ +3 days</button>
            {data.demo_shift_hours > 0 && <button onClick={() => shift(0)} className="px-2 py-1 rounded border hover:bg-white">Back to now</button>}
          </span>
        )}
      </div>
      {msg && <p className="mb-4 text-sm text-gray-700">{msg}</p>}

      <InlineDrafts drafts={drafts} onDone={load} title="Follow-up emails waiting for your approval" />

      {items.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-10 text-center text-gray-500">
          Nobody to chase. Candidates appear here once their invitation or scheduling email was sent.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow divide-y">
          {items.map((f) => (
            <div key={f.application_id} className="p-5 flex flex-wrap items-center gap-4 justify-between">
              <div className="min-w-[280px]">
                <div className="flex items-center gap-2">
                  <Link to={`/candidates/${f.application_id}`} className="font-semibold text-blue-700 hover:underline">
                    {f.alias}
                  </Link>
                  <span className="text-gray-500 text-sm">{f.candidate_name} · {f.job_title}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${BADGE[f.state]}`}>{STATE_LABEL[f.state]}</span>
                  <span className="text-sm text-gray-700">{f.reason}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Waiting for {f.waiting_for} · last email {f.last_contact_ago} · reminders {f.reminders_sent}/{f.max_reminders}
                  {f.link_expired && ' · link expired'}
                </p>
              </div>
              <FollowUpActions f={f} onDone={load} compact />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
