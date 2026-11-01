/**
 * Ranked candidates for one job.
 * "Blind mode" (on by default) hides names so HR judges the evidence first.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import StatusBadge from '../components/StatusBadge'
import ScoreBar from '../components/ScoreBar'
import RecommendationBadge from '../components/RecommendationBadge'

export default function JobCandidates() {
  const { id } = useParams()
  const [job, setJob] = useState(null)
  const [rows, setRows] = useState([])
  const [blind, setBlind] = useState(true)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [selected, setSelected] = useState([])

  const load = async () => {
    try {
      const [j, c] = await Promise.all([apiGet(`/jobs/${id}`), apiGet(`/candidates?job_id=${id}`)])
      setJob(j.data)
      setRows(c.data)
    } catch {
      setNotice('Could not load candidates. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const scoreAll = async () => {
    setBusy(true)
    try {
      const res = await apiPost(`/jobs/${id}/score_all`)
      setNotice(`${res.data.scored} candidate(s) scored.`)
      await load()
    } finally {
      setBusy(false)
    }
  }

  const eligible = (r) => r.status === 'SCORED' || (r.status === 'SHORTLISTED' && !r.has_invite)
  const toggle = (id) => setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id])

  const bulkInvite = async () => {
    setBusy(true)
    try {
      const res = await apiPost('/candidates/bulk/shortlist_and_invite', { ids: selected })
      const failed = res.data.results.filter((r) => !r.ok)
      setNotice(res.data.message + (failed.length ? ` Skipped: ${failed.map((f) => `${f.label} (${f.message})`).join(', ')}.` : ''))
      setSelected([])
      await load()
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Bulk action failed')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="text-center text-slate-500">Loading...</div>

  const ranked = rows.filter((r) => r.status !== 'QUARANTINED')
  const blocked = rows.filter((r) => r.status === 'QUARANTINED')
  const unscored = ranked.filter((r) => r.total === null).length

  return (
    <div>
      <Link to="/jobs" className="text-sm text-brand-600 hover:underline">← All jobs</Link>
      <div className="flex flex-wrap items-start justify-between gap-4 mt-2 mb-6">
        <div>
          <h1 className="page-title">{job?.title}</h1>
          <p className="text-slate-500 text-sm">Ranked by evidence from each CV. The AI suggests, you shortlist.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm bg-white border rounded-lg px-3 py-2 cursor-pointer">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            <span><b>Blind mode</b> (hide names)</span>
          </label>
          {unscored > 0 && (
            <button onClick={scoreAll} disabled={busy}
              className="btn-primary">
              {busy ? 'Scoring…' : `Score ${unscored} new`}
            </button>
          )}
        </div>
      </div>

      {notice && (
        <div className="mb-4 rounded-lg bg-brand-50 border border-brand-200 px-4 py-2 text-sm text-brand-900">
          {notice} {notice.includes('Approvals') && <Link to="/approvals" className="underline font-medium">Review them →</Link>}
        </div>
      )}

      {ranked.some(eligible) && (
        <div className="card sticky top-0 z-10 mb-3 px-4 py-3 flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium">{selected.length} selected</span>
          <button onClick={() => setSelected(ranked.filter((r) => eligible(r) && (r.total ?? 0) >= 70).map((r) => r.id))}
            className="btn-secondary">Select all ≥ 70</button>
          <button onClick={() => setSelected([])} className="btn-secondary">Clear</button>
          <button onClick={bulkInvite} disabled={!selected.length || busy}
            className="btn-success ml-auto disabled:opacity-40">
            {busy ? 'Preparing personal invitations…' : `✓ Shortlist & prepare invitations (${selected.length})`}
          </button>
          <span className="w-full text-xs text-slate-500">
            Each candidate gets their own email: 2 common questions + 1 tailored to their CV. Nothing is sent until you approve in Approvals.
          </span>
        </div>
      )}

      <div className="card overflow-hidden mb-8">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              <th className="px-3 py-3 w-8"></th>
              <th className="px-4 py-3 text-left w-12">#</th>
              <th className="px-4 py-3 text-left">Candidate</th>
              <th className="px-4 py-3 text-left w-56">Score</th>
              <th className="px-4 py-3 text-left">Breakdown</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {ranked.map((r) => (
              <tr key={r.id} className={`hover:bg-slate-50 ${selected.includes(r.id) ? 'bg-emerald-50' : ''}`}>
                <td className="px-3 py-4">
                  {eligible(r) && <input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggle(r.id)} className="h-4 w-4" />}
                </td>
                <td className="px-4 py-4 font-bold text-lg text-slate-400">{r.rank ?? '–'}</td>
                <td className="px-4 py-4">
                  <Link to={`/candidates/${r.id}`} className="font-semibold text-brand-700 hover:underline">
                    {blind ? r.alias : r.name}
                  </Link>
                  <p className="text-xs text-slate-500 line-clamp-2 max-w-md">{r.summary}</p>
                  {r.flags.map((f, i) => (
                    <p key={i} className="text-xs text-amber-700 mt-1">{f}</p>
                  ))}
                </td>
                <td className="px-4 py-4">
                  <ScoreBar value={r.total} />
                  {r.scored_by === 'offline' && <p className="text-[11px] text-slate-400 mt-1">offline scoring</p>}
                </td>
                <td className="px-4 py-4">
                  <div className="space-y-1 min-w-[180px]">
                    {r.criteria.map((c) => (
                      <div key={c.label} className="flex items-center gap-2" title={`${c.label}: ${c.score}/5`}>
                        <span className="text-[11px] text-slate-500 w-24 truncate">{c.label}</span>
                        <div className="flex-1"><ScoreBar value={c.score} max={5} small /></div>
                      </div>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-4 space-y-1">
                  <StatusBadge status={r.status} />
                  {r.recommendation && !r.decision && <div className="text-xs text-slate-500">AI: <RecommendationBadge value={r.recommendation} /></div>}
                  {r.decision && <div><RecommendationBadge value={r.decision} /></div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {ranked.length === 0 && (
          <p className="p-6 text-slate-500 text-sm">
            No candidates yet. Go to the <Link to="/inbox" className="text-brand-600 hover:underline">Inbox</Link> and load emails —
            applications with a CV land here automatically.
          </p>
        )}
      </div>

      {blocked.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2">Blocked by the security gate ({blocked.length})</h2>
          <p className="text-sm text-slate-500 mb-3">These CVs were never shown to the AI. A human can review them.</p>
          <div className="space-y-2">
            {blocked.map((r) => (
              <Link key={r.id} to={`/candidates/${r.id}`}
                className="block bg-amber-50 border border-amber-200 rounded-lg p-4 hover:bg-amber-100">
                <div className="flex justify-between">
                  <span className="font-medium">{blind ? r.alias : r.name}</span>
                  <StatusBadge status={r.status} />
                </div>
                <p className="text-sm text-amber-800 mt-1">Reason: {r.flags.join(', ')}</p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
