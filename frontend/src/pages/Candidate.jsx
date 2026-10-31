/**
 * Candidate page: score breakdown with evidence quotes, security flags, anonymized CV, HR actions.
 * All CV / AI text is rendered as plain text.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import StatusBadge from '../components/StatusBadge'
import ScoreBar from '../components/ScoreBar'

export default function Candidate() {
  const { id } = useParams()
  const [c, setC] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showName, setShowName] = useState(false)
  const [showCv, setShowCv] = useState(false)
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')

  const load = async () => {
    try {
      const res = await apiGet(`/candidates/${id}`)
      setC(res.data)
    } catch {
      setNotice('Candidate not found.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const act = async (label, path, msg) => {
    setBusy(label)
    setNotice('')
    try {
      await apiPost(path)
      setNotice(msg)
      await load()
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Action failed')
    } finally {
      setBusy('')
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading...</div>
  if (!c) return <div className="text-gray-500">{notice}</div>

  const s = c.score
  const quarantined = c.status === 'QUARANTINED'

  return (
    <div>
      {c.job && <Link to={`/jobs/${c.job.id}`} className="text-sm text-blue-600 hover:underline">← {c.job.title}</Link>}

      <div className="flex flex-wrap items-start justify-between gap-4 mt-2 mb-6">
        <div>
          <h1 className="text-3xl font-bold">{showName ? c.name : c.alias}</h1>
          <p className="text-sm text-gray-500">
            {showName ? c.email : 'Identity hidden while you review the evidence. '}
            <button onClick={() => setShowName(!showName)} className="text-blue-600 hover:underline ml-1">
              {showName ? 'Hide identity' : 'Reveal identity'}
            </button>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={c.status} />
          {c.email_id && <Link to={`/inbox?id=${c.email_id}`} className="text-sm text-blue-600 hover:underline">Original email →</Link>}
        </div>
      </div>

      {notice && <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-900">{notice}</div>}

      {quarantined && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 mb-6 text-red-900">
          <p className="font-semibold mb-2">🛡️ Blocked by the security gate — this CV was never shown to the AI</p>
          {c.security?.flags?.map((f, i) => <p key={i} className="text-sm">• {f}</p>)}
          {c.security?.hidden_text?.length > 0 && (
            <div className="mt-3 text-sm">
              <p className="font-medium">Hidden text found in the file (invisible to a human reader):</p>
              {c.security.hidden_text.map((t, i) => <p key={i} className="italic">"{t}"</p>)}
            </div>
          )}
        </div>
      )}

      {s && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Overall match</p>
            <p className="text-5xl font-bold mb-3">{Math.round(s.total)}<span className="text-xl text-gray-400">/100</span></p>
            <ScoreBar value={s.total} small />
            <p className="text-sm text-gray-700 mt-4">{s.summary}</p>
            {s.strengths?.length > 0 && (
              <div className="mt-4">
                <p className="text-xs uppercase text-gray-500 mb-1">Strengths</p>
                {s.strengths.map((x, i) => <p key={i} className="text-sm text-green-800">+ {x}</p>)}
              </div>
            )}
            {s.gaps?.length > 0 && (
              <div className="mt-3">
                <p className="text-xs uppercase text-gray-500 mb-1">Gaps</p>
                {s.gaps.map((x, i) => <p key={i} className="text-sm text-red-800">– {x}</p>)}
              </div>
            )}
            {s.flags?.map((f, i) => <p key={i} className="text-sm text-amber-700 mt-3">⚠ {f}</p>)}
            <p className="text-[11px] text-gray-400 mt-4">
              Scored by {s.source === 'ai' ? `AI (${s.model})` : 'offline keyword rules'} · total computed by code, not by the AI
            </p>
          </div>

          <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">Score per criterion — with proof from the CV</p>
            <div className="space-y-4">
              {s.criteria.map((cr) => (
                <div key={cr.key} className="border-b last:border-0 pb-4 last:pb-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium">
                      {cr.label}
                      <span className="text-xs text-gray-400 ml-2">{Math.round(cr.weight)}%{cr.must_have ? ' · must-have' : ''}</span>
                    </span>
                    <span className="font-semibold">{cr.score}/5</span>
                  </div>
                  <ScoreBar value={cr.score} max={5} small />
                  {cr.evidence ? (
                    <div className={`mt-2 border-l-4 pl-3 py-1 text-sm ${cr.verified ? 'border-blue-400 bg-blue-50' : 'border-red-400 bg-red-50'}`}>
                      <span className="italic">"{cr.evidence}"</span>
                      <span className={`ml-2 text-xs ${cr.verified ? 'text-green-700' : 'text-red-700'}`}>
                        {cr.verified ? '✓ found in CV' : '✗ not found in CV'}
                      </span>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-gray-400">No evidence in the CV.</p>
                  )}
                  <p className="text-sm text-gray-600 mt-1">{cr.reason}</p>
                  {cr.note && <p className="text-xs text-red-700 mt-1">{cr.note} (AI had said {cr.ai_score}/5)</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">Your decision</p>
        <div className="flex flex-wrap gap-3 items-center">
          {c.status === 'SCORED' && (
            <button onClick={() => act('shortlist', `/candidates/${id}/shortlist`, 'Shortlisted. Next step: send an interview invitation.')}
              disabled={!!busy} className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50">
              {busy === 'shortlist' ? 'Saving…' : '✓ Shortlist'}
            </button>
          )}
          {['SCREENED', 'SCORED'].includes(c.status) && (
            <button onClick={() => act('score', `/candidates/${id}/score`, 'Re-scored.')} disabled={!!busy}
              className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50">
              {busy === 'score' ? 'Scoring…' : c.status === 'SCREENED' ? 'Score now' : 'Re-score'}
            </button>
          )}
          {c.status === 'SHORTLISTED' && !c.interview?.invite_status && (
            <button onClick={() => act('invite', `/candidates/${id}/invite`, 'Invitation drafted with 3 questions. Review and approve it in Approvals — nothing has been sent yet.')}
              disabled={!!busy} className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50">
              {busy === 'invite' ? 'Preparing questions…' : '✉️ Prepare interview invitation'}
            </button>
          )}
          {c.status === 'SHORTLISTED' && c.interview?.invite_status === 'pending' && (
            <Link to="/approvals" className="px-4 py-2 rounded-lg bg-yellow-100 text-yellow-900 font-medium hover:bg-yellow-200">
              Invitation waiting for your approval →
            </Link>
          )}
          {c.status === 'SHORTLISTED' && c.interview?.invite_status === 'rejected' && (
            <p className="text-sm text-gray-600">You rejected the invitation draft. Nothing was sent.</p>
          )}
          {c.status === 'INVITED' && (
            <p className="text-sm text-indigo-800">
              Invitation sent ✓ — waiting for the candidate's answers.
              {c.interview?.portal_link && (
                <a href={new URL(c.interview.portal_link).pathname} target="_blank" rel="noreferrer"
                  className="ml-2 text-blue-600 hover:underline">Open the candidate's link (demo) ↗</a>
              )}
            </p>
          )}
          {c.status === 'VIDEO_SUBMITTED' && <p className="text-sm text-cyan-800">Answers received ✓ — evaluation comes in the next step.</p>}
          {quarantined && <p className="text-sm text-gray-600">Blocked CVs cannot be scored or shortlisted automatically.</p>}
          <p className="text-xs text-gray-400 ml-auto">Only a logged-in human can shortlist. The AI cannot.</p>
        </div>
      </div>

      {c.interview?.questions?.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">
            Written interview {c.interview.submitted_at ? `· answered ${new Date(c.interview.submitted_at).toLocaleString()}` : ''}
          </p>
          {c.interview.answer_flags?.length > 0 && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 mb-4 text-sm text-amber-900">
              ⚠ The answers contain text that tries to instruct the AI: "{c.interview.answer_flags[0]}"
            </div>
          )}
          <div className="space-y-5">
            {c.interview.questions.map((q, i) => {
              const a = c.interview.answers?.find((x) => x.question_id === q.id)
              return (
                <div key={q.id}>
                  <p className="font-medium">
                    {i + 1}. {q.text}
                    <span className={`ml-2 text-xs rounded px-2 py-0.5 ${q.is_tailored ? 'bg-purple-50 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                      {q.is_tailored ? 'tailored to this CV' : 'same for all candidates'}
                    </span>
                  </p>
                  <p className="text-xs text-gray-400 mt-1">What a good answer contains (HR only): {q.rubric}</p>
                  {a && <div className="mt-2 rounded bg-gray-50 p-3 text-sm whitespace-pre-wrap">{a.answer}</div>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {c.anonymized_cv && (
        <div className="bg-white rounded-lg shadow p-6">
          <button onClick={() => setShowCv(!showCv)} className="text-sm font-medium text-blue-700 hover:underline">
            {showCv ? '▾' : '▸'} What the AI saw: the anonymized CV ({c.removed_personal_info} personal details removed)
          </button>
          {showCv && <pre className="mt-3 text-sm whitespace-pre-wrap bg-gray-50 rounded p-4 font-sans">{c.anonymized_cv}</pre>}
        </div>
      )}
    </div>
  )
}
