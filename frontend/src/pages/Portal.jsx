/**
 * Candidate portal (public, opened from the invitation email).
 * The candidate only sees the questions. Answers are plain text.
 */
import { useEffect, useState } from 'react'
import { Logo } from '../components/Icon'
import { useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'

export default function Portal() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [answers, setAnswers] = useState({})
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState('')

  useEffect(() => {
    apiGet(`/portal/${token}`)
      .then((res) => {
        setSession(res.data)
        setAnswers(Object.fromEntries(res.data.questions.map((q) => [q.id, ''])))
      })
      .catch((err) => setError(err.response?.data?.detail || 'This link is not valid.'))
      .finally(() => setLoading(false))
  }, [token])

  const submit = async (e) => {
    e.preventDefault()
    setSending(true)
    setError('')
    try {
      const res = await apiPost(`/portal/${token}/answers`, { answers })
      setDone(res.data.message)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not send your answers. Please try again.')
    } finally {
      setSending(false)
    }
  }

  const shell = (children) => (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8 flex items-center justify-center gap-2.5"><Logo /><span className="font-semibold text-slate-900">Fictional Company</span><span className="text-sm text-slate-400">· careers</span></div>
        {children}
      </div>
    </div>
  )

  if (loading) return shell(<p className="text-center text-slate-500">Loading…</p>)
  if (done) return shell(
    <div className="card p-10 text-center">
      <p className="text-5xl mb-4"></p>
      <h1 className="text-2xl font-bold mb-2">Answers received</h1>
      <p className="text-slate-600">{done}</p>
    </div>
  )
  if (!session) return shell(
    <div className="card p-10 text-center">
      <p className="text-4xl mb-4"></p>
      <p className="text-slate-700">{error}</p>
    </div>
  )

  const allAnswered = session.questions.every((q) => (answers[q.id] || '').trim().length > 0)

  return shell(
    <form onSubmit={submit} className="card p-8">
      <h1 className="text-2xl font-bold mb-1">Hello {session.first_name} </h1>
      <p className="text-slate-600 mb-1">Written interview for <b>{session.job_title}</b></p>
      <p className="text-sm text-slate-500 mb-6">
        This link is personal, works once, and expires in about {session.token_remaining_hours} hours.
        We only look at the content of your answers — 5 to 10 sentences each is perfect.
      </p>

      {error && <div className="mb-4 rounded bg-rose-50 border border-rose-200 px-4 py-2 text-sm text-rose-800">{error}</div>}

      <div className="space-y-6">
        {session.questions.map((q, i) => (
          <div key={q.id}>
            <label className="block font-medium mb-2">{i + 1}. {q.text}</label>
            <textarea
              className="w-full border border-slate-300 rounded-lg p-3 h-36 focus:outline-none focus:ring-2 focus:ring-brand-400"
              maxLength={session.max_chars}
              value={answers[q.id] || ''}
              onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
              placeholder="Your answer…"
            />
            <p className="text-xs text-slate-400 text-right">{(answers[q.id] || '').length}/{session.max_chars}</p>
          </div>
        ))}
      </div>

      <button type="submit" disabled={!allAnswered || sending}
        className="btn-primary mt-6 w-full disabled:opacity-40">
        {sending ? 'Sending…' : 'Send my answers'}
      </button>
      <p className="text-xs text-slate-400 text-center mt-3">You can only submit once. Please check your answers before sending.</p>
    </form>
  )
}
