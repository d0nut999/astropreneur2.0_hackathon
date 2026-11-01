/**
 * Employees & leave: who is working, team presence, leave requests with a recommendation (HR decides),
 * alerts, balances, and the handbook assistant.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import InlineDrafts from '../components/InlineDrafts'

const GROUPS = [
  { key: 'approve', title: '✅ Within the rules', hint: 'Enough days left and the team stays at 70% or more.', cls: 'border-green-200' },
  { key: 'move', title: '⚠️ Team would be too empty', hint: 'Suggested: propose other dates.', cls: 'border-amber-300' },
  { key: 'over_limit', title: '⛔ Over the yearly limit', hint: 'Suggested: decline politely and offer a meeting.', cls: 'border-red-300' },
  { key: 'sick', title: '🩺 Sick leave', hint: 'Never refused for staffing. Long absences are flagged for follow-up.', cls: 'border-sky-300' },
]

function Stat({ label, value, sub, color = 'text-gray-900' }) {
  return (
    <div className="bg-white p-5 rounded-lg shadow">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

function RequestCard({ r, min, onDone }) {
  const ev = r.evaluation
  const [mode, setMode] = useState(null) // 'reject' | 'approve_anyway'
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const sick = r.type === 'sick'
  const go = async (action, extra = {}) => {
    setBusy(action)
    setErr('')
    try {
      await apiPost(`/employees/leave/${r.id}/decide`, { action, note, ...extra })
      await onDone()
    } catch (e) {
      setErr(e.response?.data?.detail || 'Action failed')
    } finally {
      setBusy('')
    }
  }
  const btn = 'px-3 py-1.5 text-sm rounded-lg font-medium disabled:opacity-50'
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex flex-wrap justify-between gap-2">
        <div>
          <p className="font-semibold text-gray-900">
            {r.employee_name} <span className="text-gray-500 font-normal text-sm">· {r.team}</span>
          </p>
          <p className="text-sm text-gray-700">
            {sick ? 'Sick leave' : 'Paid leave'}: {r.label} · <b>{ev.days}</b> working day{ev.days !== 1 ? 's' : ''}
            {r.reason_from_employee && <span className="text-gray-500"> · “{r.reason_from_employee}”</span>}
          </p>
        </div>
        <div className="text-right text-xs text-gray-500">
          {sick ? (
            <p>Sick days this year: <b className={ev.sick_used + ev.days > 60 ? 'text-red-600' : ''}>{ev.sick_used} → {ev.sick_used + ev.days}</b></p>
          ) : (
            <p>Leave used: <b className={ev.annual_used + ev.days > 30 ? 'text-red-600' : ''}>{ev.annual_used} → {ev.annual_used + ev.days}</b> / 30</p>
          )}
          {!sick && <p>Team lowest: <b className={ev.min_presence < min ? 'text-amber-700' : 'text-green-700'}>{ev.min_presence}%</b></p>}
          {r.email_id && <Link to={`/inbox?id=${r.email_id}`} className="text-blue-600 hover:underline">original email</Link>}
        </div>
      </div>
      <ul className="mt-2 text-sm text-gray-700 list-disc pl-5 space-y-0.5">
        {ev.reasons.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
      {ev.recommendation === 'sick_alert' && (
        <div className="mt-3 p-3 rounded bg-red-50 border border-red-200 text-sm text-red-800">
          <b>HR action needed:</b> call {r.employee_name.split(' ')[0]} to ask how they are, offer occupational-health
          support, and plan cover for the team. Record the absence (it is a right) — no diagnosis is asked or stored.
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2 items-center">
        {(ev.recommendation === 'approve' || sick) && (
          <button onClick={() => go('approve')} disabled={!!busy} className={`${btn} bg-green-600 text-white hover:bg-green-700`}>
            {busy === 'approve' ? 'Saving…' : sick ? 'Record sick leave' : 'Approve'}
          </button>
        )}
        {ev.recommendation === 'move' && ev.alternatives.length > 0 && (
          <button onClick={() => go('propose')} disabled={!!busy} className={`${btn} bg-amber-500 text-white hover:bg-amber-600`}>
            {busy === 'propose' ? 'Drafting…' : 'Propose other dates'}
          </button>
        )}
        {ev.recommendation === 'over_limit' && (
          <button onClick={() => go('meeting')} disabled={!!busy} className={`${btn} bg-red-600 text-white hover:bg-red-700`}>
            {busy === 'meeting' ? 'Drafting…' : 'Decline & offer a meeting'}
          </button>
        )}
        {['move', 'over_limit'].includes(ev.recommendation) && mode !== 'approve' && (
          <button onClick={() => { setMode('approve'); setErr('') }} className={`${btn} border text-gray-700 hover:bg-gray-50`}>Approve anyway…</button>
        )}
        {!sick && mode !== 'reject' && (
          <button onClick={() => { setMode('reject'); setErr('') }} className={`${btn} border border-red-300 text-red-700 hover:bg-red-50`}>Reject…</button>
        )}
      </div>
      {mode && (
        <div className="mt-3 p-3 rounded border bg-gray-50">
          <p className="text-sm text-gray-700 mb-2">
            {mode === 'reject' ? 'Why? (sent to the employee and saved in the audit log)' : 'Why approve against the recommendation? (saved in the audit log)'}
          </p>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} className="w-full border rounded px-2 py-1 text-sm"
            placeholder={mode === 'reject' ? 'e.g. the end of quarter closing needs the whole team that week.' : 'e.g. exceptional family situation, agreed with the manager.'} />
          <div className="flex gap-2 mt-2">
            <button onClick={() => go(mode)} disabled={!!busy}
              className={`${btn} ${mode === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'} text-white`}>
              {busy ? 'Saving…' : mode === 'reject' ? 'Reject' : 'Approve'}
            </button>
            <button onClick={() => setMode(null)} className={`${btn} border`}>Cancel</button>
          </div>
        </div>
      )}
      {err && <p className="text-sm text-red-700 mt-2">{err}</p>}
    </div>
  )
}

function AskHandbook({ employees }) {
  const [q, setQ] = useState('')
  const [emp, setEmp] = useState('')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
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
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900">Ask the handbook</h2>
      <p className="text-sm text-gray-500 mb-3">
        What an employee would get by email. Answers come only from the handbook (with the section) and the
        employee's own balance; anything else is forwarded to HR. Nothing is sent from here.
      </p>
      <div className="flex flex-wrap gap-2 mb-2">
        <select value={emp} onChange={(e) => setEmp(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
          <option value="">Asked by… (optional)</option>
          {employees.map((e) => <option key={e.id} value={e.id}>{e.name} · {e.team}</option>)}
        </select>
        {['How many leave days do I have left?', 'Can I work from home on Fridays?', 'Is there a training budget?', 'Can I bring my dog?'].map((x) => (
          <button key={x} onClick={() => setQ(x)} className="text-xs px-2 py-1 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-700">{x}</button>
        ))}
      </div>
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && q.trim() && ask()}
          placeholder="Type a question…" className="flex-1 border rounded px-3 py-2 text-sm" />
        <button onClick={ask} disabled={busy || !q.trim()} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium disabled:opacity-50">
          {busy ? 'Thinking…' : 'Ask'}
        </button>
      </div>
      {res && (
        <div className="mt-3 p-3 rounded border bg-gray-50 text-sm">
          {res.error ? <p className="text-red-700">{res.error}</p> : (
            <>
              {res.answer && <p className="text-gray-800">{res.answer}</p>}
              {res.forwarded && <p className="text-amber-800 mt-1">↪ Not (fully) covered by the handbook: this part would be forwarded to HR.</p>}
              {res.sections?.length > 0 && (
                <p className="text-xs text-gray-500 mt-2">Sources: {res.sections.map((s) => `§${s.n} ${s.title}`).join(' · ')} · {res.source === 'ai' ? 'AI, checked against the handbook' : 'offline rules'}</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function Employees() {
  const [d, setD] = useState(null)
  const [team, setTeam] = useState('')
  const [search, setSearch] = useState('')

  const load = async () => {
    const r = await apiGet('/employees/overview')
    setD(r.data)
  }
  useEffect(() => { load() }, [])
  const afterDecision = async () => {
    await load()
    setTimeout(() => document.getElementById('inline-drafts')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 150)
  }

  const groups = useMemo(() => {
    const g = { approve: [], move: [], over_limit: [], sick: [] }
    for (const r of d?.requests || []) {
      if (r.type === 'sick') g.sick.push(r)
      else g[r.evaluation.recommendation]?.push(r)
    }
    return g
  }, [d])

  if (!d) return <p className="text-gray-500">Loading…</p>
  const rows = d.employees.filter((e) => (!team || e.team === team) && (!search || e.name.toLowerCase().includes(search.toLowerCase())))
  const min = d.rules.team_min_presence
  const pct = (n) => (d.total ? Math.round((100 * n) / d.total) : 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Employees</h1>
        <p className="text-gray-600 mt-1">
          {d.is_today ? 'Today' : 'Next working day'}: {d.day_label}. Rules: {d.rules.annual_leave_days} paid leave days per year ·
          teams keep at least {min}% at work · sick leave above {d.rules.sick_alert_days} days is flagged. HR decides every request.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Employees" value={d.total} />
        <Stat label="Working" value={`${d.working}`} sub={`${d.working_pct}% of the company`} color="text-green-700" />
        <Stat label="On paid leave" value={d.on_annual} sub={`${pct(d.on_annual)}%`} color="text-teal-700" />
        <Stat label="On sick leave" value={d.on_sick} sub={`${pct(d.on_sick)}%`} color="text-sky-700" />
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex h-4 rounded-full overflow-hidden mb-2">
          <div className="bg-green-500" style={{ width: `${pct(d.working)}%` }} title="Working" />
          <div className="bg-teal-400" style={{ width: `${pct(d.on_annual)}%` }} title="Paid leave" />
          <div className="bg-sky-400" style={{ width: `${pct(d.on_sick)}%` }} title="Sick" />
        </div>
        <p className="text-xs text-gray-500 mb-5">■ <span className="text-green-600">working</span> · ■ <span className="text-teal-600">paid leave</span> · ■ <span className="text-sky-600">sick</span></p>
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Presence per team (line = {min}% minimum)</p>
        <div className="space-y-2">
          {d.teams.map((t) => (
            <div key={t.team} className="flex items-center gap-3 text-sm">
              <span className="w-36 text-gray-700">{t.team}</span>
              <div className="flex-1 h-3 bg-gray-100 rounded-full relative">
                <div className={`h-3 rounded-full ${t.below_min ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${t.presence}%` }} />
                <div className="absolute top-[-3px] h-[18px] w-0.5 bg-gray-700" style={{ left: `${min}%` }} />
              </div>
              <span className={`w-28 text-right ${t.below_min ? 'text-red-700 font-semibold' : 'text-gray-600'}`}>{t.working}/{t.size} · {t.presence}%</span>
              <span className="w-56 text-xs text-gray-500 truncate">{t.away.map((a) => `${a.name}${a.type === 'sick' ? ' (sick)' : ''}`).join(', ')}</span>
            </div>
          ))}
        </div>
      </div>

      {d.alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="font-semibold text-red-800 mb-1">Needs HR attention</p>
          <ul className="text-sm text-red-800 list-disc pl-5 space-y-0.5">
            {d.alerts.map((a, i) => <li key={i}>{a.text}</li>)}
          </ul>
        </div>
      )}

      <div id="requests">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Leave requests ({d.requests.length})</h2>
        <p className="text-sm text-gray-500 mb-3">
          Read from employees' emails (or entered by HR). The checks are rules in code; the recommendation is only a suggestion.
          Going against it needs a reason. Every reply waits for your click.
        </p>
        <InlineDrafts drafts={d.pending_replies} onDone={load} title="Replies to employees waiting for your approval" />
        {d.requests.length === 0 && <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">No pending leave requests.</div>}
        <div className="space-y-5">
          {GROUPS.filter((g) => groups[g.key].length).map((g) => (
            <div key={g.key} className={`rounded-lg border-2 ${g.cls} p-4 bg-gray-50`}>
              <p className="font-semibold text-gray-900">{g.title} <span className="text-gray-500 font-normal">({groups[g.key].length})</span></p>
              <p className="text-xs text-gray-500 mb-3">{g.hint}</p>
              <div className="space-y-3">
                {groups[g.key].map((r) => <RequestCard key={r.id} r={r} min={min} onDone={afterDecision} />)}
              </div>
            </div>
          ))}
        </div>
        {d.recent.length > 0 && (
          <div className="mt-4 text-sm text-gray-600">
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Recently decided</p>
            {d.recent.map((r) => (
              <p key={r.id}>{r.employee_name} · {r.label} · <b>{r.status}</b>{r.hr_note && <span className="text-gray-500"> — {r.hr_note}</span>}</p>
            ))}
          </div>
        )}
      </div>

      <AskHandbook employees={d.employees} />

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 flex flex-wrap gap-2 items-center border-b">
          <h2 className="text-lg font-semibold text-gray-900 mr-auto">All employees · {new Date(d.day).getFullYear()} balances</h2>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name" className="border rounded px-2 py-1 text-sm" />
          <select value={team} onChange={(e) => setTeam(e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="">All teams</option>
            {d.teams.map((t) => <option key={t.team}>{t.team}</option>)}
          </select>
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500 text-xs uppercase">
            <tr><th className="px-4 py-2">Name</th><th className="px-4">Team</th><th className="px-4">{d.is_today ? 'Today' : d.day_label.split(' ')[0]}</th><th className="px-4">Paid leave used</th><th className="px-4 pr-6 text-right">Sick days</th></tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="px-4 py-2">{e.name}<span className="block text-xs text-gray-400">{e.title}</span></td>
                <td className="px-4">{e.team}</td>
                <td className="px-4">{e.today === 'working' ? <span className="text-green-700">working</span> : e.today === 'sick' ? <span className="text-sky-700">sick</span> : <span className="text-teal-700">on leave</span>}</td>
                <td className="px-4 w-72">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full">
                      <div className={`h-2 rounded-full ${e.annual_used >= d.rules.annual_leave_days ? 'bg-red-500' : e.annual_used >= 25 ? 'bg-amber-500' : 'bg-teal-500'}`} style={{ width: `${Math.min(100, (100 * e.annual_used) / d.rules.annual_leave_days)}%` }} />
                    </div>
                    <span className="w-20 text-right whitespace-nowrap">{e.annual_used} / {d.rules.annual_leave_days} d</span>
                  </div>
                </td>
                <td className={`px-4 pr-6 text-right whitespace-nowrap ${e.sick_used > d.rules.sick_alert_days ? 'text-red-700 font-semibold' : 'text-gray-700'}`}>
                  {e.sick_used} d{e.sick_used > d.rules.sick_alert_days && ' ⚠'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
