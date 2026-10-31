/**
 * HR view of a candidate's final-interview scheduling: link status, live free times,
 * time requests received by email (book it / propose alternatives), demo "simulate a reply".
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiPost } from '../api'
import { baseURL } from '../api/client'

const fmt = (iso) => new Date(iso).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const fmtLong = (iso) => new Date(iso).toLocaleString(undefined, { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

export default function SchedulingPanel({ c, id, busy, act, reload, setNotice }) {
  const s = c.scheduling || { status: 'none', requests: [], live_times: [] }
  const [sim, setSim] = useState(false)
  const [simText, setSimText] = useState('')
  const [reqError, setReqError] = useState('')

  const bookRequest = async (reqId) => {
    setReqError('')
    try {
      const r = await apiPost(`/candidates/${id}/schedule/requests/${reqId}/book`)
      setNotice(r.data.message)
      await reload()
    } catch (e) {
      const d = e.response?.data?.detail
      setReqError(d?.message ? `${d.message} Closest free times: ${d.alternatives.map(fmt).join(', ')}` : 'Could not book')
      await reload()
    }
  }

  const simulate = async () => {
    await apiPost('/emails/simulate', { from_name: c.name, from_addr: c.email, subject: 'Re: interview time', body: simText })
    setSim(false)
    setSimText('')
    setNotice('Email received and analyzed (simulated).')
    await reload()
  }

  const suggestion = s.live_times?.[0]
    ? `Hello, would ${new Date(s.live_times[0]).toLocaleDateString('en-US', { weekday: 'long' })} at ${new Date(s.live_times[0]).toTimeString().slice(0, 5)} work for the interview?`
    : 'Hello, would Tuesday at 14:00 work for the interview?'

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex justify-between items-start mb-3">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          Final interview scheduling {s.round > 1 ? `· round ${s.round}` : ''}
        </p>
        {s.status !== 'booked' && (
          <button onClick={() => { setSim(!sim); setSimText(suggestion) }} className="text-xs text-gray-500 hover:underline">
            ✉ Simulate an email reply from this candidate (demo)
          </button>
        )}
      </div>

      {sim && (
        <div className="mb-4 rounded border border-dashed border-gray-300 p-3">
          <p className="text-xs text-gray-500 mb-1">As if {c.email} wrote to HR:</p>
          <textarea value={simText} onChange={(e) => setSimText(e.target.value)} className="w-full border rounded p-2 text-sm h-20 mb-2" />
          <button onClick={simulate} disabled={simText.trim().length < 5} className="px-3 py-1.5 rounded bg-gray-800 text-white text-sm disabled:opacity-40">Receive this email</button>
        </div>
      )}

      {s.status === 'booked' && s.booked && (
        <div className="flex flex-wrap items-center gap-4">
          <p className="text-lg">🤝 Booked: <b>{fmtLong(s.booked.start)}</b></p>
          <a href={`${baseURL}/candidates/${id}/interview.ics`} className="px-3 py-1.5 rounded border border-gray-300 text-sm hover:bg-gray-50">Download calendar file (.ics)</a>
          <Link to="/agenda" className="text-sm text-blue-600 hover:underline">See it in the calendar →</Link>
        </div>
      )}

      {s.status === 'draft' && (
        <p className="text-sm text-gray-700">
          The email inviting the candidate to pick a time is ready. <Link to="/approvals" className="text-blue-600 hover:underline">Approve it in Approvals →</Link>
          <span className="block text-xs text-gray-500 mt-1">Nothing is reserved: the candidate will see the times that are free when they open the link.</span>
        </p>
      )}

      {s.status === 'pending' && (
        <div>
          <p className="text-sm text-gray-700 mb-2">
            Link sent — the candidate sees live free times (first come, first served).
            {s.link && <a href={new URL(s.link).pathname} target="_blank" rel="noreferrer" className="ml-2 text-blue-600 hover:underline">Open the candidate's link (demo) ↗</a>}
          </p>
          <div className="flex flex-wrap gap-2">
            {s.live_times.map((t) => <span key={t} className="text-sm bg-green-50 text-green-900 rounded px-3 py-1">{fmt(t)}</span>)}
            {s.live_times.length === 0 && <span className="text-sm text-amber-700">No free interview times in the coming weeks — add interview blocks in the settings.</span>}
          </div>
        </div>
      )}

      {['declined', 'expired', 'cancelled', 'none'].includes(s.status) && (
        <div>
          {s.status === 'declined' && (
            <p className="text-sm text-amber-900 bg-amber-50 rounded p-3 mb-3">
              None of the times worked. The candidate wrote: <i>"{s.availability_note}"</i>
            </p>
          )}
          {s.status === 'expired' && <p className="text-sm text-gray-700 mb-3">The candidate did not use the link in time.</p>}
          {s.status === 'cancelled' && <p className="text-sm text-gray-700 mb-3">The scheduling email was cancelled.</p>}
          <button onClick={() => act('reschedule', `/candidates/${id}/schedule/new`, 'New scheduling email drafted. Approve it in Approvals to send it.')}
            disabled={!!busy} className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50">
            {busy === 'reschedule' ? 'Preparing…' : s.status === 'declined' ? 'Send times matching their availability' : 'Send a scheduling link'}
          </button>
        </div>
      )}

      {s.requests?.length > 0 && s.status !== 'booked' && (
        <div className="mt-5 border-t pt-4">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Time requests received by email</p>
          {reqError && <p className="text-sm text-red-700 mb-2">{reqError}</p>}
          {s.requests.map((r) => (
            <div key={r.id} className="rounded border p-3 mb-2">
              <p className="text-sm italic text-gray-700 mb-2">"{r.text.slice(0, 200)}"</p>
              {r.requested_start ? (
                r.free ? (
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-green-800">✓ {fmtLong(r.requested_start)} is free</span>
                    <button onClick={() => bookRequest(r.id)} className="px-3 py-1.5 rounded bg-green-600 text-white text-sm hover:bg-green-700">
                      Book it &amp; draft confirmation
                    </button>
                  </div>
                ) : (
                  <div className="text-sm">
                    <span className="text-red-700">✗ {fmtLong(r.requested_start)} is not available.</span>
                    <span className="text-gray-600"> Closest free: {r.alternatives.map(fmt).join(' · ') || 'none'}</span>
                    <button onClick={() => act('propose', `/candidates/${id}/schedule/requests/${r.id}/propose`, 'A new scheduling email with the closest times is waiting in Approvals.')}
                      className="ml-3 px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-700">Propose these</button>
                  </div>
                )
              ) : (
                <div className="text-sm">
                  <span className="text-gray-700">No exact time given. Matching free times: {r.alternatives.map(fmt).join(' · ') || 'none'}</span>
                  <button onClick={() => act('propose', `/candidates/${id}/schedule/requests/${r.id}/propose`, 'A new scheduling email with matching times is waiting in Approvals.')}
                    className="ml-3 px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-700">Propose these</button>
                </div>
              )}
              <Link to={`/inbox?id=${r.email_id}`} className="text-xs text-blue-600 hover:underline">Open the email →</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
