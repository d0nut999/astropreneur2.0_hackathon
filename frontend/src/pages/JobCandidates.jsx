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

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  const ranked = rows.filter((r) => r.status !== 'QUARANTINED')
  const blocked = rows.filter((r) => r.status === 'QUARANTINED')
  const unscored = ranked.filter((r) => r.total === null).length

  return (
    <div>
      <Link to="/jobs" className="text-sm text-blue-600 hover:underline">← All jobs</Link>
      <div className="flex flex-wrap items-start justify-between gap-4 mt-2 mb-6">
        <div>
          <h1 className="text-3xl font-bold">{job?.title}</h1>
          <p className="text-gray-500 text-sm">Ranked by evidence from each CV. The AI suggests, you shortlist.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm bg-white border rounded-lg px-3 py-2 cursor-pointer">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            <span><b>Blind mode</b> (hide names)</span>
          </label>
          {unscored > 0 && (
            <button onClick={scoreAll} disabled={busy}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {busy ? 'Scoring…' : `Score ${unscored} new`}
            </button>
          )}
        </div>
      </div>

      {notice && <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-900">{notice}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left w-12">#</th>
              <th className="px-4 py-3 text-left">Candidate</th>
              <th className="px-4 py-3 text-left w-56">Score</th>
              <th className="px-4 py-3 text-left">Breakdown</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {ranked.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-4 font-bold text-lg text-gray-400">{r.rank ?? '–'}</td>
                <td className="px-4 py-4">
                  <Link to={`/candidates/${r.id}`} className="font-semibold text-blue-700 hover:underline">
                    {blind ? r.alias : r.name}
                  </Link>
                  <p className="text-xs text-gray-500 line-clamp-2 max-w-md">{r.summary}</p>
                  {r.flags.map((f, i) => (
                    <p key={i} className="text-xs text-amber-700 mt-1">⚠ {f}</p>
                  ))}
                </td>
                <td className="px-4 py-4">
                  <ScoreBar value={r.total} />
                  {r.scored_by === 'offline' && <p className="text-[11px] text-gray-400 mt-1">offline scoring</p>}
                </td>
                <td className="px-4 py-4">
                  <div className="space-y-1 min-w-[180px]">
                    {r.criteria.map((c) => (
                      <div key={c.label} className="flex items-center gap-2" title={`${c.label}: ${c.score}/5`}>
                        <span className="text-[11px] text-gray-500 w-24 truncate">{c.label}</span>
                        <div className="flex-1"><ScoreBar value={c.score} max={5} small /></div>
                      </div>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-4 space-y-1">
                  <StatusBadge status={r.status} />
                  {r.recommendation && !r.decision && <div className="text-xs text-gray-500">AI: <RecommendationBadge value={r.recommendation} /></div>}
                  {r.decision && <div><RecommendationBadge value={r.decision} /></div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {ranked.length === 0 && (
          <p className="p-6 text-gray-500 text-sm">
            No candidates yet. Go to the <Link to="/inbox" className="text-blue-600 hover:underline">Inbox</Link> and load emails —
            applications with a CV land here automatically.
          </p>
        )}
      </div>

      {blocked.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2">🛡️ Blocked by the security gate ({blocked.length})</h2>
          <p className="text-sm text-gray-500 mb-3">These CVs were never shown to the AI. A human can review them.</p>
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
