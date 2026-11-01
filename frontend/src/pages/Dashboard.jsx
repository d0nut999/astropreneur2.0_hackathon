/**
 * Dashboard ("Today"): what the HR manager should look at first.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import CategoryTag from '../components/CategoryTag'
import DemoControls from '../components/DemoControls'
import { timeAgo } from '../utils/format'
import Icon from '../components/Icon'

function Metric({ label, value, to, tone = 'text-slate-900' }) {
  return (
    <Link to={to} className="group flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-slate-50">
      <span className="text-sm text-slate-600 group-hover:text-slate-900">{label}</span>
      <span className={`text-sm font-semibold tabular-nums ${value ? tone : 'text-slate-300'}`}>{value || 0}</span>
    </Link>
  )
}

function AreaCard({ icon, title, sub, to, children }) {
  return (
    <div className="card p-2">
      <Link to={to} className="flex items-center gap-3 px-3 pb-2 pt-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600"><Icon name={icon} className="h-5 w-5" /></span>
        <div className="flex-1">
          <p className="font-semibold text-slate-900">{title}</p>
          <p className="text-xs text-slate-500">{sub}</p>
        </div>
        <Icon name="chevronRight" className="h-4 w-4 text-slate-400" />
      </Link>
      <div className="mt-1 border-t border-slate-100 pt-1">{children}</div>
    </div>
  )
}

export default function Dashboard() {
  const [digest, setDigest] = useState(null)
  const [staff, setStaff] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      const res = await apiGet('/digest/today')
      setDigest(res.data)
      apiGet('/employees/overview').then((r) => setStaff(r.data)).catch(() => {})
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

  if (loading) return <div className="text-center text-slate-500">Loading...</div>
  if (!digest) return <div className="text-center text-slate-500">Could not reach the backend (http://localhost:8000).</div>

  const meetingsToday = digest.upcoming_events?.filter((e) => e.day === 'today') || []

  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="text-sm text-slate-500">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
          <h1 className="page-title mt-0.5">Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}</h1>
        </div>
      </div>

      <div className="card mb-6 flex gap-4 border-l-4 border-l-brand-500 p-5">
        <Icon name="sun" className="mt-0.5 h-5 w-5 shrink-0 text-brand-500" />
        <div>
          <p className="eyebrow mb-1">Daily brief</p>
          <p className="leading-relaxed text-slate-800">{digest.summary}</p>
          {digest.total_new_emails === 0 && (
            <button onClick={loadDemo} disabled={busy} className="btn-primary mt-3">{busy ? 'Analyzing emails…' : 'Load demo emails'}</button>
          )}
        </div>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <AreaCard icon="briefcase" title="Recruitment" sub="Future employees" to="/jobs">
          <Metric label="New applications to review" value={digest.pending_applications_count} to="/jobs" tone="text-brand-700" />
          <Metric label="Candidates waiting for your decision" value={digest.awaiting_decision_count} to="/jobs" tone="text-brand-700" />
          <Metric label="Follow-ups due" value={(digest.followups_due_count ?? 0) + (digest.followups_your_call_count ?? 0)} to="/followups" tone="text-amber-600" />
          <Metric label="Interview spots free (7 days)" value={digest.interview_spots_7_days} to="/calendar" />
        </AreaCard>
        <AreaCard icon="users" title="Employees" sub="Current staff" to="/employees">
          <Metric label="Working today" value={staff ? `${staff.working} / ${staff.total}` : '…'} to="/employees" tone="text-emerald-700" />
          <Metric label="Leave requests to decide" value={digest.leave_pending_count} to="/employees/leave" tone="text-brand-700" />
          <Metric label="Alerts (staffing, long sick leave)" value={staff?.alerts?.length} to="/employees" tone="text-rose-600" />
          <Metric label="Emails waiting for your approval" value={digest.pending_approvals_count} to="/approvals" tone="text-brand-700" />
        </AreaCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="px-5 py-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">Needs your attention <span className="ml-1 text-sm font-normal text-slate-400">{digest.high_urgency_count} urgent · {digest.flagged_count ?? 0} blocked</span></h2>
            <Link to="/inbox" className="link text-sm">Open inbox</Link>
          </div>
          {(!digest.urgent_emails || digest.urgent_emails.length === 0) && (
            <p className="p-5 text-slate-500 text-sm">Nothing urgent right now.</p>
          )}
          <div className="divide-y">
            {digest.urgent_emails?.map((e) => (
              <Link key={e.id} to={`/inbox?id=${e.id}`} className="block p-5 hover:bg-slate-50">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-semibold text-slate-900">{e.from_name || e.from_addr}</span>
                  <span className="text-xs text-slate-400">{timeAgo(e.received_at)}</span>
                </div>
                <p className="mb-2 text-sm text-slate-600">{e.summary}</p>
                <div className="flex flex-wrap gap-2 items-center">
                  <CategoryTag category={e.category} />
                  {e.reasons.map((r, i) => (
                    <span key={i} className="chip bg-rose-50 text-rose-700">{r}</span>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="px-5 py-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">Coming up</h2>
            <Link to="/calendar" className="link text-sm">Calendar</Link>
          </div>
          {(!digest.upcoming_events || digest.upcoming_events.length === 0) && (
            <p className="p-5 text-slate-500 text-sm">No meetings or deadlines today or tomorrow.</p>
          )}
          <div className="divide-y">
            {digest.upcoming_events?.map((ev) => (
              <div key={ev.id} className="p-4 flex gap-3">
                <div className="text-center w-20 shrink-0">
                  <div className="text-[11px] font-medium uppercase text-slate-400">{ev.day}</div>
                  <div className="text-sm font-semibold tabular-nums text-slate-800">{ev.time || '—'}</div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-800">{ev.title}</div>
                  <div className="text-xs text-slate-500 truncate">
                    {ev.location}{ev.location && ev.with_people?.length ? ' · ' : ''}{ev.with_people?.join(', ')}
                  </div>
                  {ev.status === 'suggested' && <div className="text-xs text-amber-700">Not confirmed yet</div>}
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
