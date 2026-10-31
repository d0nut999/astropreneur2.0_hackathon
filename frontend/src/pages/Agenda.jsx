/**
 * Agenda: meetings and deadlines the AI found in emails.
 * They are only SUGGESTIONS until HR clicks Confirm.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import { prettyDate } from '../utils/format'

const STATUS_STYLE = {
  suggested: 'bg-yellow-50 text-yellow-800 ring-yellow-200',
  confirmed: 'bg-green-50 text-green-800 ring-green-200',
  dismissed: 'bg-gray-100 text-gray-500 ring-gray-200',
}

export default function Agenda() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showDismissed, setShowDismissed] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const res = await apiGet('/events')
      setEvents(res.data)
    } catch {
      setError('Could not load the agenda.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const decide = async (id, action) => {
    try {
      await apiPost(`/events/${id}/${action}`)
      setEvents(events.map((ev) => (ev.id === id ? { ...ev, status: action === 'confirm' ? 'confirmed' : 'dismissed' } : ev)))
    } catch (err) {
      setError(err.response?.data?.detail || 'Action failed')
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading…</div>

  const visible = events.filter((ev) => showDismissed || ev.status !== 'dismissed')
  const groups = visible.reduce((acc, ev) => {
    const k = ev.date || 'No date'
    ;(acc[k] = acc[k] || []).push(ev)
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Agenda</h1>
          <p className="text-gray-500 text-sm">Meetings and deadlines found in your emails. Confirm the ones you accept.</p>
        </div>
        <label className="text-sm text-gray-600 flex items-center gap-2">
          <input type="checkbox" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} />
          Show dismissed
        </label>
      </div>

      {error && <div className="mb-4 rounded bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-800">{error}</div>}

      {visible.length === 0 && (
        <p className="text-gray-500">Nothing yet. Load emails from the <Link to="/inbox" className="text-blue-600 hover:underline">Inbox</Link>.</p>
      )}

      <div className="space-y-6">
        {Object.entries(groups).map(([date, list]) => (
          <div key={date}>
            <h2 className="text-lg font-semibold mb-2">{prettyDate(date === 'No date' ? null : date)}</h2>
            <div className="space-y-2">
              {list.map((ev) => (
                <div key={ev.id} className="bg-white rounded-lg shadow p-4 flex items-center gap-4">
                  <div className="w-16 text-center">
                    <div className="text-2xl">{ev.type === 'meeting' ? '📅' : '⏰'}</div>
                    <div className="text-sm font-semibold text-gray-700">{ev.time || (ev.type === 'deadline' ? 'Due' : '')}</div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{ev.title}</div>
                    <div className="text-sm text-gray-500 truncate">
                      {ev.type === 'meeting' ? 'Meeting' : 'Deadline'}
                      {ev.location && ` · ${ev.location}`}
                      {ev.with_people?.length > 0 && ` · with ${ev.with_people.join(', ')}`}
                    </div>
                    <Link to={`/inbox?id=${ev.email_id}`} className="text-xs text-blue-600 hover:underline">
                      From: {ev.email_from} — "{ev.email_subject}"
                    </Link>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ring-1 ${STATUS_STYLE[ev.status]}`}>{ev.status}</span>
                  {ev.status === 'suggested' && (
                    <div className="flex gap-2">
                      <button onClick={() => decide(ev.id, 'confirm')} className="px-3 py-1.5 rounded bg-green-600 text-white text-sm hover:bg-green-700">
                        Confirm
                      </button>
                      <button onClick={() => decide(ev.id, 'dismiss')} className="px-3 py-1.5 rounded border border-gray-300 text-sm hover:bg-gray-50">
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
