/**
 * Employees area: Overview (presence), Leave requests (HR decides), Questions & handbook, Directory.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import InlineDrafts from '../components/InlineDrafts'
import Icon from '../components/Icon'

const GROUPS = [
  { key: 'approve', title: 'Within the rules', hint: 'Enough days left and the team keeps at least the minimum presence.', dot: 'bg-emerald-500' },
  { key: 'move', title: 'Team would be under-staffed', hint: 'Suggested: propose other dates.', dot: 'bg-amber-500' },
  { key: 'over_limit', title: 'Over the yearly limit', hint: 'Suggested: decline politely and offer a meeting.', dot: 'bg-rose-500' },
  { key: 'sick', title: 'Sick leave', hint: 'Never refused for staffing. Long absences are flagged for follow-up.', dot: 'bg-sky-500' },
]

function useOverview() {
  const [d, setD] = useState(null)
  const load = async () => {
    const r = await apiGet('/employees/overview')
    setD(r.data)
  }
  useEffect(() => { load() }, [])
  return [d, load]
}

function Header({ title, sub, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="page-title">{title}</h1>
        {sub && <p className="page-sub">{sub}</p>}
      </div>
      {children}
    </div>
  )
}

function Stat({ label, value, sub, tone = 'text-slate-900' }) {
  return (
    <div className="card p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tracking-tight ${tone}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

function RequestCard({ r, min, onDone }) {
  const ev = r.evaluation
  const [mode, setMode] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const sick = r.type === 'sick'
  const go = async (action) => {
    setBusy(action)
    setErr('')
    try {
      await apiPost(`/employees/leave/${r.id}/decide`, { action, note })
      await onDone()
    } catch (e) {
      setErr(e.response?.data?.detail || 'Action failed')
    } finally {
      setBusy('')
    }
  }
  return (
    <div className="card p-5">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900">{r.employee_name} <span className="text-sm font-normal text-slate-500">· {r.team}</span></p>
          <p className="mt-0.5 text-sm text-slate-700">
            {sick ? 'Sick leave' : 'Paid leave'} · {r.label} · <b>{ev.days}</b> working day{ev.days !== 1 ? 's' : ''}
            {r.reason_from_employee && <span className="text-slate-500"> · “{r.reason_from_employee}”</span>}
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          {sick
            ? <p>Sick days this year <b className={ev.sick_used + ev.days > 60 ? 'text-rose-600' : 'text-slate-800'}>{ev.sick_used} → {ev.sick_used + ev.days}</b></p>
            : <p>Leave used <b className={ev.annual_used + ev.days > 30 ? 'text-rose-600' : 'text-slate-800'}>{ev.annual_used} → {ev.annual_used + ev.days}</b> / 30</p>}
          {!sick && <p>Lowest team presence <b className={ev.min_presence < min ? 'text-amber-700' : 'text-emerald-700'}>{ev.min_presence}%</b></p>}
          {r.email_id && <Link to={`/inbox?id=${r.email_id}`} className="link">Original email</Link>}
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-sm text-slate-600">
        {ev.reasons.map((x, i) => (
          <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />{x}</li>
        ))}
      </ul>
      {ev.recommendation === 'sick_alert' && (
        <div className="mt-3 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0" />
          <p><b>HR follow-up needed.</b> Call {r.employee_name.split(' ')[0]} to ask how they are, offer occupational-health
            support and plan cover for the team. Record the absence (it is a right); no diagnosis is asked or stored.</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {(ev.recommendation === 'approve' || sick) && (
          <button onClick={() => go('approve')} disabled={!!busy} className="btn-success btn-sm">{busy === 'approve' ? 'Saving…' : sick ? 'Record sick leave' : 'Approve'}</button>
        )}
        {ev.recommendation === 'move' && ev.alternatives.length > 0 && (
          <button onClick={() => go('propose')} disabled={!!busy} className="btn-primary btn-sm">{busy === 'propose' ? 'Drafting…' : 'Propose other dates'}</button>
        )}
        {ev.recommendation === 'over_limit' && (
          <button onClick={() => go('meeting')} disabled={!!busy} className="btn-primary btn-sm">{busy === 'meeting' ? 'Drafting…' : 'Decline & offer a meeting'}</button>
        )}
        {['move', 'over_limit'].includes(ev.recommendation) && mode !== 'approve' && (
          <button onClick={() => { setMode('approve'); setErr('') }} className="btn-secondary btn-sm">Approve anyway…</button>
        )}
        {!sick && mode !== 'reject' && (
          <button onClick={() => { setMode('reject'); setErr('') }} className="btn-danger btn-sm">Reject…</button>
        )}
      </div>
      {mode && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="mb-2 text-sm text-slate-700">
            {mode === 'reject' ? 'Reason (sent to the employee and saved in the audit log)' : 'Why approve against the recommendation? (saved in the audit log)'}
          </p>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} className="input"
            placeholder={mode === 'reject' ? 'e.g. the quarter closing needs the whole team that week.' : 'e.g. exceptional family situation, agreed with the manager.'} />
          <div className="mt-2 flex gap-2">
            <button onClick={() => go(mode)} disabled={!!busy} className={mode === 'reject' ? 'btn btn-sm bg-rose-600 text-white hover:bg-rose-700' : 'btn-success btn-sm'}>
              {busy ? 'Saving…' : mode === 'reject' ? 'Reject' : 'Approve'}
            </button>
            <button onClick={() => setMode(null)} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}
      {err && <p className="mt-2 text-sm text-rose-700">{err}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ Overview */
function Overview({ d }) {
  const min = d.rules.team_min_presence
  const pct = (n) => (d.total ? Math.round((100 * n) / d.total) : 0)
  return (
    <>
      <Header title="Employees" sub={`${d.is_today ? 'Today' : 'Next working day'} · ${d.day_label}. Teams should keep at least ${min}% of their people at work.`}>
        {d.requests.length > 0 && (
          <Link to="/employees/leave" className="btn-primary">
            {d.requests.length} leave request{d.requests.length > 1 ? 's' : ''} to decide <Icon name="arrowRight" />
          </Link>
        )}
      </Header>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Employees" value={d.total} />
        <Stat label="Working" value={d.working} sub={`${d.working_pct}% of the company`} tone="text-emerald-700" />
        <Stat label="On paid leave" value={d.on_annual} sub={`${pct(d.on_annual)}%`} />
        <Stat label="On sick leave" value={d.on_sick} sub={`${pct(d.on_sick)}%`} />
      </div>

      {d.alerts.length > 0 && (
        <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50/70 p-4">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-rose-800"><Icon name="alert" /> Needs HR attention</p>
          <ul className="space-y-1 text-sm text-rose-800">{d.alerts.map((a, i) => <li key={i}>{a.text}</li>)}</ul>
        </div>
      )}

      <div className="card mt-6 p-6">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="font-semibold">Presence by team</h2>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-500" />at work</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-px bg-slate-700" />{min}% minimum</span>
          </div>
        </div>
        <div className="mb-6 mt-4 flex h-2.5 overflow-hidden rounded-full bg-slate-100">
          <div className="bg-emerald-500" style={{ width: `${pct(d.working)}%` }} title="Working" />
          <div className="bg-brand-400" style={{ width: `${pct(d.on_annual)}%` }} title="Paid leave" />
          <div className="bg-sky-400" style={{ width: `${pct(d.on_sick)}%` }} title="Sick" />
        </div>
        <div className="space-y-3">
          {d.teams.map((t) => (
            <div key={t.team} className="grid grid-cols-[150px_1fr_90px] items-center gap-4 text-sm">
              <span className="font-medium text-slate-700">{t.team}</span>
              <div className="relative h-2 rounded-full bg-slate-100">
                <div className={`h-2 rounded-full ${t.below_min ? 'bg-rose-500' : 'bg-emerald-500'}`} style={{ width: `${t.presence}%` }} />
                <div className="absolute -top-1 h-4 w-px bg-slate-700" style={{ left: `${min}%` }} />
              </div>
              <span className={`text-right tabular-nums ${t.below_min ? 'font-semibold text-rose-700' : 'text-slate-600'}`}>{t.working}/{t.size} · {t.presence}%</span>
              {t.away.length > 0 && (
                <span className="col-start-2 -mt-2 text-xs text-slate-400">Away: {t.away.map((a) => `${a.name}${a.type === 'sick' ? ' (sick)' : ''}`).join(', ')}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

/* ------------------------------------------------------------------ Leave requests */
function Leave({ d, load }) {
  const min = d.rules.team_min_presence
  const groups = useMemo(() => {
    const g = { approve: [], move: [], over_limit: [], sick: [] }
    for (const r of d.requests) {
      if (r.type === 'sick') g.sick.push(r)
      else g[r.evaluation.recommendation]?.push(r)
    }
    return g
  }, [d])
  const afterDecision = async () => {
    await load()
    setTimeout(() => document.getElementById('inline-drafts')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 150)
  }
  return (
    <>
      <Header title="Leave requests"
        sub={`Read from employees' emails. Rules: ${d.rules.annual_leave_days} paid days per year · teams keep ${min}% at work · sick leave above ${d.rules.sick_alert_days} days is flagged. The recommendation is only a suggestion; you decide.`} />
      <InlineDrafts drafts={d.leave_replies} onDone={load} title="Replies waiting for your approval" />
      {d.requests.length === 0 && (
        <div className="card p-10 text-center text-sm text-slate-500">No pending leave requests.</div>
      )}
      <div className="space-y-8">
        {GROUPS.filter((g) => groups[g.key].length).map((g) => (
          <section key={g.key}>
            <div className="mb-3 flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${g.dot}`} />
              <h2 className="font-semibold">{g.title}</h2>
              <span className="text-sm text-slate-400">{groups[g.key].length}</span>
              <span className="ml-2 text-sm text-slate-500">{g.hint}</span>
            </div>
            <div className="space-y-3">{groups[g.key].map((r) => <RequestCard key={r.id} r={r} min={min} onDone={afterDecision} />)}</div>
          </section>
        ))}
      </div>
      {d.recent.length > 0 && (
        <div className="card mt-8 p-5">
          <p className="eyebrow mb-3">Recently decided</p>
          <div className="divide-y divide-slate-100 text-sm">
            {d.recent.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-2">
                <span className="text-slate-700">{r.employee_name} · {r.label}</span>
                <span className="chip bg-slate-100 capitalize text-slate-700">{r.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

/* ------------------------------------------------------------------ Handbook */
function Handbook({ d, load }) {
  const [q, setQ] = useState('')
  const [emp, setEmp] = useState('')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [sections, setSections] = useState([])
  useEffect(() => { apiGet('/employees/handbook').then((r) => setSections(r.data)) }, [])
  const ask = async () => {
    setBusy(true)
    try {
      const r = await apiPost('/employees/ask', { question: q, employee_id: emp ? Number(emp) : null })
      setRes(r.data)
    } catch (e) {
      setRes({ error: e.response?.data?.detail || 'Failed' })
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <Header title="Questions & handbook"
        sub="Employees' questions are answered only from the handbook (with the section) and their own balance. Anything else is forwarded to HR. You approve every reply." />
      <InlineDrafts drafts={d.question_replies} onDone={load} title="Replies to employees waiting for your approval" />
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="card p-6 lg:col-span-3">
          <h2 className="font-semibold">Try the assistant</h2>
          <p className="mb-4 text-sm text-slate-500">What an employee would receive by email. Nothing is sent from here.</p>
          <select value={emp} onChange={(e) => setEmp(e.target.value)} className="input mb-3">
            <option value="">Asked by… (optional, needed for balance questions)</option>
            {d.employees.map((e) => <option key={e.id} value={e.id}>{e.name} · {e.team}</option>)}
          </select>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {['How many leave days do I have left?', 'Can I work from home on Fridays?', 'Is there a training budget?', 'Can I bring my dog?'].map((x) => (
              <button key={x} onClick={() => setQ(x)} className="chip bg-slate-100 text-slate-600 hover:bg-slate-200">{x}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && q.trim() && ask()}
              placeholder="Type a question…" className="input" />
            <button onClick={ask} disabled={busy || !q.trim()} className="btn-primary">{busy ? 'Thinking…' : 'Ask'}</button>
          </div>
          {res && (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
              {res.error ? <p className="text-rose-700">{res.error}</p> : (
                <>
                  {res.answer && <p className="leading-relaxed text-slate-800">{res.answer}</p>}
                  {res.forwarded && (
                    <p className="mt-2 flex items-center gap-1.5 text-amber-800"><Icon name="forward" /> Not (fully) covered by the handbook: forwarded to HR.</p>
                  )}
                  {res.sections?.length > 0 && (
                    <p className="mt-3 text-xs text-slate-500">Sources: {res.sections.map((s) => `§${s.n} ${s.title}`).join(' · ')} · {res.source === 'ai' ? 'AI, checked against the handbook' : 'offline rules'}</p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
        <div className="card p-6 lg:col-span-2">
          <h2 className="mb-3 font-semibold">Employee handbook</h2>
          <ol className="space-y-2 text-sm">
            {sections.map((s) => (
              <li key={s.n}>
                <details className="group">
                  <summary className="cursor-pointer list-none text-slate-700 hover:text-slate-900">
                    <span className="mr-2 text-slate-400 tabular-nums">§{s.n}</span>{s.title}
                  </summary>
                  <p className="mt-1 pl-7 text-slate-500">{s.text}</p>
                </details>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </>
  )
}

/* ------------------------------------------------------------------ Directory */
function Directory({ d }) {
  const [team, setTeam] = useState('')
  const [search, setSearch] = useState('')
  const rows = d.employees.filter((e) => (!team || e.team === team) && (!search || e.name.toLowerCase().includes(search.toLowerCase())))
  const lim = d.rules.annual_leave_days
  return (
    <>
      <Header title="Directory" sub={`${d.total} employees · leave balances for ${new Date(d.day).getFullYear()}`}>
        <div className="flex gap-2">
          <div className="relative">
            <Icon name="search" className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name" className="input w-56 pl-8" />
          </div>
          <select value={team} onChange={(e) => setTeam(e.target.value)} className="input w-44">
            <option value="">All teams</option>
            {d.teams.map((t) => <option key={t.team}>{t.team}</option>)}
          </select>
        </div>
      </Header>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium text-slate-500">
            <tr>
              <th className="px-5 py-3">Name</th><th className="px-4 py-3">Team</th>
              <th className="px-4 py-3">{d.is_today ? 'Today' : d.day_label.split(' ')[0]}</th>
              <th className="px-4 py-3">Paid leave used</th><th className="px-5 py-3 text-right">Sick days</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((e) => (
              <tr key={e.id} className="hover:bg-slate-50/60">
                <td className="px-5 py-3"><p className="font-medium text-slate-800">{e.name}</p><p className="text-xs text-slate-400">{e.title}</p></td>
                <td className="px-4 py-3 text-slate-600">{e.team}</td>
                <td className="px-4 py-3">
                  {e.today === 'working' ? <span className="chip bg-emerald-50 text-emerald-700">Working</span>
                    : e.today === 'sick' ? <span className="chip bg-sky-50 text-sky-700">Sick</span>
                      : <span className="chip bg-brand-50 text-brand-700">On leave</span>}
                </td>
                <td className="w-72 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="h-1.5 flex-1 rounded-full bg-slate-100">
                      <div className={`h-1.5 rounded-full ${e.annual_used >= lim ? 'bg-rose-500' : e.annual_used >= lim - 5 ? 'bg-amber-500' : 'bg-brand-500'}`}
                        style={{ width: `${Math.min(100, (100 * e.annual_used) / lim)}%` }} />
                    </div>
                    <span className="w-16 text-right tabular-nums text-slate-600">{e.annual_used} / {lim}</span>
                  </div>
                </td>
                <td className={`px-5 py-3 text-right tabular-nums ${e.sick_used > d.rules.sick_alert_days ? 'font-semibold text-rose-700' : 'text-slate-600'}`}>
                  {e.sick_used}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export default function Employees({ section = 'overview' }) {
  const [d, load] = useOverview()
  if (!d) return <p className="text-sm text-slate-500">Loading…</p>
  if (section === 'leave') return <Leave d={d} load={load} />
  if (section === 'handbook') return <Handbook d={d} load={load} />
  if (section === 'directory') return <Directory d={d} />
  return <Overview d={d} />
}
