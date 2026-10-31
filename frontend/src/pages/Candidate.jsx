/**
 * Candidate page: score breakdown with evidence quotes, security flags, anonymized CV, HR actions.
 * All CV / AI text is rendered as plain text.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import StatusBadge from '../components/StatusBadge'
import ScoreBar from '../components/ScoreBar'
import RecommendationBadge from '../components/RecommendationBadge'
import { baseURL } from '../api/client'
import SchedulingPanel from '../components/SchedulingPanel'

export default function Candidate() {
  const { id } = useParams()
  const [c, setC] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showName, setShowName] = useState(false)
  const [showCv, setShowCv] = useState(false)
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const [note, setNote] = useState('')
  const [decisionError, setDecisionError] = useState('')

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

  const rec = c?.evaluation?.recommendation
  const needsReason = (d) => d === 'reject' || (d === 'advance' && rec === 'Not recommended')

  const decide = async (decision) => {
    setDecisionError('')
    if (needsReason(decision) && note.trim().length < 10) {
      setDecisionError(decision === 'reject'
        ? 'Please write a short reason for the rejection (10+ characters) in the box above. It is saved in the audit log, so the decision can be explained later.'
        : `The AI recommended "${rec}". To advance this candidate, please write a short reason (10+ characters) in the box above.`)
      return
    }
    setBusy(decision)
    setNotice('')
    try {
      const res = await apiPost(`/candidates/${id}/decision`, { decision, note })
      setNotice(res.data.message)
      await load()
    } catch (err) {
      setDecisionError(err.response?.data?.detail || 'Could not save the decision')
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
                        {cr.match === 'paraphrase' ? '≈ close rewording of the CV' : cr.verified ? '✓ found in CV' : '✗ not found in CV'}
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
          {c.status === 'VIDEO_SUBMITTED' && (
            <button onClick={() => act('evaluate', `/candidates/${id}/evaluate`, 'Answers evaluated.')} disabled={!!busy}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50">
              {busy === 'evaluate' ? 'Evaluating…' : 'Evaluate answers'}
            </button>
          )}
          {c.status === 'EVALUATED' && (
            <div className="w-full">
              <button onClick={() => act('evaluate', `/candidates/${id}/evaluate`, 'Answers re-evaluated.')} disabled={!!busy}
                className="float-right px-3 py-1.5 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50">
                {busy === 'evaluate' ? 'Re-evaluating…' : '↻ Re-evaluate answers'}
              </button>
              <p className="text-sm text-gray-700 mb-2">
                The AI recommends <RecommendationBadge value={c.evaluation?.recommendation} />. The final decision is yours.
              </p>
              <textarea value={note} onChange={(e) => { setNote(e.target.value); setDecisionError('') }}
                placeholder="Reason — required to reject, or to advance someone the AI did not recommend (e.g. 'Not enough database experience')"
                className={`w-full border rounded-lg p-2 text-sm h-16 mb-2 ${decisionError ? 'border-red-400 ring-2 ring-red-200' : ''}`} />
              {decisionError && <p className="text-sm text-red-700 mb-2">{decisionError}</p>}
              <div className="flex gap-3">
                <button onClick={() => decide('advance')} disabled={!!busy}
                  className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50">
                  {busy === 'advance' ? 'Saving…' : '✓ Advance to final interview'}
                </button>
                <button onClick={() => decide('reject')} disabled={!!busy}
                  className="px-4 py-2 rounded-lg bg-gray-700 text-white font-medium hover:bg-gray-800 disabled:opacity-50">
                  {busy === 'reject' ? 'Saving…' : '✗ Reject'}
                </button>
              </div>
            </div>
          )}
          {c.status === 'DECIDED' && c.final_decision && (
            <div className="text-sm">
              <RecommendationBadge value={c.final_decision.decision} large />
              <span className="ml-3 text-gray-600">
                {c.final_decision.agrees_with_ai ? 'Same as the AI recommendation' : `Different from the AI (${c.final_decision.ai_recommendation})`}
                {' · '}{new Date(c.final_decision.created_at).toLocaleString()}
              </span>
              {c.final_decision.note && <p className="mt-2 text-gray-700">Note: "{c.final_decision.note}"</p>}
              {c.final_decision.decision === 'reject' && <Link to="/approvals" className="block mt-2 text-blue-600 hover:underline">The email to the candidate is in Approvals →</Link>}
            </div>
          )}
          {quarantined && <p className="text-sm text-gray-600">Blocked CVs cannot be scored or shortlisted automatically.</p>}
          {c.status !== 'EVALUATED' && <p className="text-xs text-gray-400 ml-auto">Only a logged-in human can shortlist or decide. The AI cannot.</p>}
        </div>
      </div>

      {(c.scheduling || c.final_decision?.decision === 'advance') && (
        <SchedulingPanel c={c} id={id} busy={busy} act={act} reload={load} setNotice={setNotice} />
      )}

      {c.evaluation && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">AI recommendation (you decide)</p>
              <div className="flex items-center gap-3">
                <RecommendationBadge value={c.evaluation.recommendation} large />
                <span className="text-sm text-gray-600">Confidence: {Math.round(c.evaluation.confidence * 100)}%</span>
              </div>
            </div>
            <div className="flex gap-6 text-center">
              <div><div className="text-2xl font-bold">{Math.round(c.evaluation.summary_json.cv_score)}</div><div className="text-xs text-gray-500">CV · 40%</div></div>
              <div><div className="text-2xl font-bold">{Math.round(c.evaluation.summary_json.interview_score)}</div><div className="text-xs text-gray-500">Interview · 60%</div></div>
              <div><div className="text-2xl font-bold text-blue-700">{Math.round(c.evaluation.summary_json.combined)}</div><div className="text-xs text-gray-500">Combined</div></div>
            </div>
          </div>
          <p className="text-gray-800 mb-2">{c.evaluation.summary_json.summary}</p>
          <ul className="text-sm text-gray-600 list-disc list-inside mb-2">
            {c.evaluation.summary_json.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          {c.evaluation.summary_json.flags?.length > 0 && (
            <p className="text-sm text-amber-800 bg-amber-50 rounded p-2 mb-2">⚠ Manipulation attempt in the answers: "{c.evaluation.summary_json.flags[0]}"</p>
          )}
          <div className="grid md:grid-cols-3 gap-3 mt-4">
            {c.evaluation.per_question_json.questions.map((q, i) => (
              <div key={q.question_id} className="border rounded-lg p-3">
                <div className="flex justify-between text-sm font-medium mb-1"><span>Question {i + 1}</span><span>{q.score}/5</span></div>
                <ScoreBar value={q.score} max={5} small />
                {q.evidence && (
                  <p className={`text-xs mt-2 italic ${q.verified ? 'text-blue-900' : 'text-red-700'}`}>
                    "{q.evidence}" {q.match === 'paraphrase' ? '≈ close rewording of the answer' : q.verified ? '✓ in answer' : '✗ not in answer'}
                  </p>
                )}
                <p className="text-xs text-gray-600 mt-1">{q.reason}</p>
                {q.note && <p className="text-xs text-red-700 mt-1">{q.note}</p>}
              </div>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-3">
            Evaluated by {c.evaluation.summary_json.source === 'ai' ? `AI (${c.evaluation.summary_json.model})` : 'offline rules'} ·
            only the content of the answers is judged (not style, language or identity) · recommendation computed by code
          </p>
        </div>
      )}

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
