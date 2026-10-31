/**
 * Inbox: every email with its category, urgency (+ why), and a short AI summary.
 * Email content is always rendered as PLAIN TEXT (never HTML) for security.
 */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import UrgencyBadge from '../components/UrgencyBadge'
import CategoryTag from '../components/CategoryTag'
import { timeAgo, prettyDate } from '../utils/format'

const FILTERS = [
  { key: 'all', label: 'All', params: '' },
  { key: 'urgent', label: 'Urgent', params: '?urgency=urgent' },
  { key: 'candidates', label: 'Candidates', match: (e) => e.category.startsWith('candidate') },
  { key: 'work', label: 'Work', match: (e) => e.category.startsWith('work') },
  { key: 'flagged', label: 'Suspicious', params: '?urgency=flagged' },
]

export default function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [emails, setEmails] = useState([])
  const [filter, setFilter] = useState('all')
  const [selectedId, setSelectedId] = useState(Number(searchParams.get('id')) || null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const [showSim, setShowSim] = useState(false)
  const [sim, setSim] = useState({ from_name: 'Leila Haddad (Director)', from_addr: 'director@fictional-company.test', subject: 'Meeting request', body: 'Hi, can we meet on Tuesday at 14:00 to discuss the hiring budget?' })

  const load = async () => {
    const f = FILTERS.find((x) => x.key === filter)
    try {
      const res = await apiGet(`/emails${f.params || ''}`)
      setEmails(f.match ? res.data.filter(f.match) : res.data)
    } catch (err) {
      setNotice('Could not load emails. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [filter])

  useEffect(() => {
    if (!selectedId) return setDetail(null)
    apiGet(`/emails/${selectedId}`)
      .then((res) => setDetail(res.data))
      .catch(() => setDetail(null))
  }, [selectedId])

  const select = (id) => {
    setSelectedId(id)
    setSearchParams({ id })
  }

  const run = async (label, fn) => {
    setBusy(label)
    setNotice('')
    try {
      await fn()
    } catch (err) {
      setNotice(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setBusy('')
    }
  }

  const loadDemo = () =>
    run('demo', async () => {
      const res = await apiPost('/emails/load_demo')
      setNotice(`${res.data.imported} demo email(s) analyzed${res.data.already_had ? `, ${res.data.already_had} already in inbox` : ''}.`)
      await load()
    })

  const sync = () =>
    run('sync', async () => {
      const res = await apiPost('/emails/sync')
      setNotice(`${res.data.imported} new email(s) from ${res.data.source}.`)
      await load()
    })

  const simulate = () =>
    run('sim', async () => {
      const res = await apiPost('/emails/simulate', sim)
      setShowSim(false)
      setNotice(`Email received and analyzed: ${res.data.urgency} — ${res.data.urgency_reasons?.[0] || ''}`)
      await load()
      select(res.data.id)
    })

  const draftReply = () =>
    run('draft', async () => {
      await apiPost(`/emails/${selectedId}/draft_reply`)
      setNotice('Reply drafted. It is waiting in Approvals — nothing has been sent.')
      const res = await apiGet(`/emails/${selectedId}`)
      setDetail(res.data)
    })

  const markHandled = () =>
    run('handled', async () => {
      await apiPost(`/emails/${selectedId}/handled`)
      setNotice('Marked as handled.')
      await load()
      setDetail({ ...detail, status: 'handled' })
    })

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-3xl font-bold">Inbox</h1>
          <p className="text-gray-500 text-sm">Sorted by the AI, urgency decided by clear rules. You decide what happens.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowSim(!showSim)}
            className="px-4 py-2 rounded-lg border border-dashed border-gray-400 bg-white hover:bg-gray-50 text-sm">
            ✉ Simulate an incoming email
          </button>
          <button onClick={sync} disabled={!!busy}
            className="px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-medium disabled:opacity-50">
            {busy === 'sync' ? 'Syncing…' : 'Sync inbox'}
          </button>
          <button onClick={loadDemo} disabled={!!busy}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium disabled:opacity-50">
            {busy === 'demo' ? 'Analyzing…' : 'Load demo emails'}
          </button>
        </div>
      </div>

      {showSim && (
        <div className="mb-4 bg-white rounded-lg shadow p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border rounded p-2 text-sm" placeholder="Sender name" value={sim.from_name} onChange={(e) => setSim({ ...sim, from_name: e.target.value })} />
          <input className="border rounded p-2 text-sm" placeholder="Sender email" value={sim.from_addr} onChange={(e) => setSim({ ...sim, from_addr: e.target.value })} />
          <input className="border rounded p-2 text-sm md:col-span-2" placeholder="Subject" value={sim.subject} onChange={(e) => setSim({ ...sim, subject: e.target.value })} />
          <textarea className="border rounded p-2 text-sm md:col-span-2 h-24" value={sim.body} onChange={(e) => setSim({ ...sim, body: e.target.value })} />
          <div className="md:col-span-2 flex gap-2">
            <button onClick={simulate} disabled={!!busy} className="px-4 py-2 rounded-lg bg-gray-800 text-white text-sm disabled:opacity-50">
              {busy === 'sim' ? 'Analyzing…' : 'Receive this email'}
            </button>
            <span className="text-xs text-gray-500 self-center">Demo tool: the email goes through the same security checks and AI analysis as a real one.</span>
          </div>
        </div>
      )}

      {notice && <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-900">{notice}</div>}

      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium ${
              filter === f.key ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* List */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow divide-y max-h-[75vh] overflow-y-auto">
          {loading && <p className="p-6 text-gray-500">Loading…</p>}
          {!loading && emails.length === 0 && (
            <div className="p-6 text-gray-500 text-sm">
              No emails here. Click <b>Load demo emails</b> to try HireGuard with fictional data.
            </div>
          )}
          {emails.map((e) => (
            <button key={e.id} onClick={() => select(e.id)}
              className={`w-full text-left p-4 hover:bg-gray-50 ${selectedId === e.id ? 'bg-blue-50' : ''} ${
                e.status === 'handled' ? 'opacity-50' : ''
              }`}>
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-semibold text-sm truncate">{e.from_name || e.from_addr}</span>
                <span className="text-xs text-gray-400 whitespace-nowrap">{timeAgo(e.received_at)}</span>
              </div>
              <div className="text-sm text-gray-900 truncate mb-1">{e.subject}</div>
              <div className="text-xs text-gray-500 line-clamp-2 mb-2">{e.summary}</div>
              <div className="flex items-center gap-2 flex-wrap">
                <UrgencyBadge urgency={e.urgency} small />
                <CategoryTag category={e.category} />
                {e.has_attachments && <span className="text-xs text-gray-400">📎</span>}
                {e.urgency_reasons?.[0] && <span className="text-xs text-gray-500 truncate">· {e.urgency_reasons[0]}</span>}
              </div>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-3 bg-white rounded-lg shadow p-6 min-h-[300px]">
          {!detail && <p className="text-gray-400">Select an email to see the details.</p>}
          {detail && (
            <div>
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h2 className="text-xl font-semibold">{detail.subject}</h2>
                  <p className="text-sm text-gray-500">
                    {detail.from_name} &lt;{detail.from_addr}&gt; · {new Date(detail.received_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <UrgencyBadge urgency={detail.urgency} />
                  <CategoryTag category={detail.category} />
                </div>
              </div>

              {/* Why */}
              <div className={`rounded-lg p-4 mb-4 ${detail.urgency === 'flagged' ? 'bg-amber-50 border border-amber-200' : 'bg-gray-50'}`}>
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                  AI summary {detail.analysis_source === 'rules' && '(offline rules)'}
                </p>
                <p className="text-gray-900 mb-3">{detail.summary}</p>
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Why this priority</p>
                <ul className="text-sm text-gray-800 list-disc list-inside">
                  {detail.urgency_reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>

              {/* Security */}
              {(detail.injection_text || detail.security_flags?.length > 0) && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 mb-4 text-sm text-red-900">
                  <p className="font-semibold mb-1">🛡️ Security gate</p>
                  {detail.injection_text && (
                    <p className="mb-1">Manipulation attempt detected: <span className="italic">"{detail.injection_text}"</span></p>
                  )}
                  {detail.security_flags?.map((f, i) => <p key={i}>• {f}</p>)}
                  <p className="mt-2 text-red-700">HireGuard did not follow these instructions and will not reply automatically.</p>
                </div>
              )}

              {/* Attachments */}
              {detail.attachments?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Attachments</p>
                  {detail.attachments.map((a, i) => (
                    <div key={i} className={`rounded border p-3 mb-2 text-sm ${a.safe ? 'border-gray-200' : 'border-red-300 bg-red-50'}`}>
                      <div className="flex justify-between">
                        <span>📎 {a.filename}</span>
                        <span className={a.safe ? 'text-green-700' : 'text-red-700 font-medium'}>
                          {a.safe ? '✓ passed security checks' : `✗ blocked: ${a.flags.join(', ')}`}
                        </span>
                      </div>
                      {a.hidden_text?.length > 0 && (
                        <p className="mt-2 text-red-800">Hidden text found (invisible to a human reader): <span className="italic">"{a.hidden_text[0]}"</span></p>
                      )}
                    </div>
                  ))}
                  {detail.application_id && (
                    <Link to={`/candidates/${detail.application_id}`} className="text-sm text-blue-600 hover:underline">→ Open candidate profile and score</Link>
                  )}
                </div>
              )}

              {/* Events found */}
              {detail.events?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Found in this email</p>
                  {detail.events.map((ev) => (
                    <div key={ev.id} className="text-sm rounded border border-emerald-200 bg-emerald-50 p-3 mb-2 flex justify-between">
                      <span>{ev.type === 'meeting' ? '📅' : '⏰'} {ev.title} — {prettyDate(ev.date)} {ev.time || ''} {ev.location && `· ${ev.location}`}</span>
                      <Link to="/agenda" className="text-emerald-800 font-medium hover:underline">{ev.status}</Link>
                    </div>
                  ))}
                </div>
              )}

              {/* Original email, plain text */}
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Original email</p>
              <div className="rounded border border-gray-200 p-4 text-sm text-gray-800 whitespace-pre-wrap max-h-64 overflow-y-auto mb-4">
                {detail.body}
              </div>

              {/* Actions */}
              <div className="flex gap-2 flex-wrap">
                {detail.urgency !== 'flagged' && (
                  <button onClick={draftReply} disabled={!!busy}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium disabled:opacity-50">
                    {busy === 'draft' ? 'Drafting…' : '✍️ Draft a reply'}
                  </button>
                )}
                {detail.status !== 'handled' && (
                  <button onClick={markHandled} disabled={!!busy}
                    className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 text-sm font-medium disabled:opacity-50">
                    ✓ Mark as handled
                  </button>
                )}
                {detail.drafts?.length > 0 && (
                  <Link to="/approvals" className="px-4 py-2 text-sm text-blue-700 hover:underline">
                    {detail.drafts.length} draft(s) in Approvals →
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
