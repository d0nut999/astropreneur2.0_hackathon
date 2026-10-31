/**
 * Dashboard ("Today"): what the HR manager should look at first.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import CategoryTag from '../components/CategoryTag'
import DemoControls from '../components/DemoControls'
import { timeAgo } from '../utils/format'

function Card({ label, value, color, to }) {
  return (
    <Link to={to} className="bg-white p-5 rounded-lg shadow hover:shadow-md transition">
      <p className="text-gray-600 text-sm mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </Link>
  )
}

export default function Dashboard() {
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

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

  useEffect(() => {
    load()
  }, [])

  const loadDemo = async () => {
    setBusy(true)
    try {
      await apiPost('/emails/load_demo')
      await load()
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading...</div>
  if (!digest) return <div className="text-center text-gray-500">Could not reach the backend (http://localhost:8000).</div>

  const meetingsToday = digest.upcoming_events?.filter((e) => e.day === 'today') || []

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold">Today</h1>
        <span className="text-sm text-gray-500">
          {new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}
        </span>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg p-5 mb-6 shadow">
        <p className="text-xs uppercase tracking-wide opacity-80 mb-1">Your daily brief</p>
        <p className="text-lg">{digest.summary}</p>
        {digest.total_new_emails === 0 && (
          <button onClick={loadDemo} disabled={busy}
            className="mt-3 bg-white text-blue-700 px-4 py-2 rounded font-medium text-sm hover:bg-blue-50 disabled:opacity-50">
            {busy ? 'Analyzing emails…' : 'Load demo emails'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card label="Urgent emails" value={digest.high_urgency_count} color="text-red-600" to="/inbox" />
        <Card label="Meetings today" value={meetingsToday.length} color="text-emerald-600" to="/agenda" />
        <Card label="Waiting for your approval" value={digest.pending_approvals_count} color="text-blue-600" to="/approvals" />
        <Card label="Suspicious emails blocked" value={digest.flagged_count ?? 0} color="text-amber-600" to="/inbox" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="px-5 py-4 border-b flex justify-between items-center">
            <h2 className="text-lg font-semibold">Needs your attention</h2>
            <Link to="/inbox" className="text-sm text-blue-600 hover:underline">Open inbox →</Link>
          </div>
          {(!digest.urgent_emails || digest.urgent_emails.length === 0) && (
            <p className="p-5 text-gray-500 text-sm">Nothing urgent right now.</p>
          )}
          <div className="divide-y">
            {digest.urgent_emails?.map((e) => (
              <Link key={e.id} to={`/inbox?id=${e.id}`} className="block p-5 hover:bg-gray-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold">{e.from_name || e.from_addr}</span>
                  <span className="text-xs text-gray-400">{timeAgo(e.received_at)}</span>
                </div>
                <p className="text-gray-800 mb-2">{e.summary}</p>
                <div className="flex flex-wrap gap-2 items-center">
                  <CategoryTag category={e.category} />
                  {e.reasons.map((r, i) => (
                    <span key={i} className="text-xs bg-red-50 text-red-700 rounded px-2 py-0.5">{r}</span>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="px-5 py-4 border-b flex justify-between items-center">
            <h2 className="text-lg font-semibold">Coming up</h2>
            <Link to="/agenda" className="text-sm text-blue-600 hover:underline">Agenda →</Link>
          </div>
          {(!digest.upcoming_events || digest.upcoming_events.length === 0) && (
            <p className="p-5 text-gray-500 text-sm">No meetings or deadlines today or tomorrow.</p>
          )}
          <div className="divide-y">
            {digest.upcoming_events?.map((ev) => (
              <div key={ev.id} className="p-4 flex gap-3">
                <div className="text-center w-20 shrink-0">
                  <div className="text-xs uppercase text-gray-500">{ev.day}</div>
                  <div className="font-semibold">{ev.time || '—'}</div>
                </div>
                <div className="min-w-0">
                  <div className="font-medium truncate">{ev.type === 'interview' ? '🤝' : ev.type === 'meeting' ? '📅' : '⏰'} {ev.title}</div>
                  <div className="text-xs text-gray-500 truncate">
                    {ev.location}{ev.location && ev.with_people?.length ? ' · ' : ''}{ev.with_people?.join(', ')}
                  </div>
                  {ev.status === 'suggested' && <div className="text-xs text-yellow-700">Not confirmed yet</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <DemoControls onReset={load} />
    </div>
  )
}
