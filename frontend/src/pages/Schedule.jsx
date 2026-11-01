/**
 * Public page: an advanced candidate picks an interview time, or says none of them work.
 */
import { useEffect, useState } from 'react'
import { Logo } from '../components/Icon'
import { useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import { baseURL } from '../api/client'

const fmt = (iso) =>
  new Date(iso).toLocaleString(undefined, { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

export default function Schedule() {
  const { token } = useParams()
  const [offer, setOffer] = useState(null)
  const [error, setError] = useState('')
  const [choice, setChoice] = useState(null)
  const [declining, setDeclining] = useState(false)
  const [availability, setAvailability] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState('')

  const load = () =>
    apiGet(`/schedule/${token}`)
      .then((r) => setOffer(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'This link is not valid.'))

  useEffect(() => {
    load()
  }, [token])

  const book = async () => {
    setBusy(true)
    setError('')
    try {
      const r = await apiPost(`/schedule/${token}/book`, { start: choice })
      setDone(r.data.message)
      await load()
    } catch (e) {
      const d = e.response?.data?.detail
      if (e.response?.status === 409 && d?.alternatives) {
        setError(`${d.message} Here are the closest free times.`)
        setOffer({ ...offer, times: d.alternatives })
        setChoice(null)
      } else {
        setError(typeof d === 'string' ? d : 'Could not book this time.')
      }
    } finally {
      setBusy(false)
    }
  }

  const decline = async () => {
    setBusy(true)
    setError('')
    try {
      const r = await apiPost(`/schedule/${token}/decline`, { availability })
      setDone(r.data.message)
      setOffer({ ...offer, status: 'declined' })
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not send your message.')
    } finally {
      setBusy(false)
    }
  }

  const shell = (children) => (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 flex items-center justify-center gap-2.5"><Logo /><span className="font-semibold text-slate-900">Fictional Company</span><span className="text-sm text-slate-400">· careers</span></div>
        {children}
      </div>
    </div>
  )

  if (!offer && !error) return shell(<p className="text-center text-slate-500">Loading…</p>)
  if (!offer) return shell(<div className="card p-10 text-center"><p className="text-4xl mb-3"></p><p>{error}</p></div>)

  const booked = offer.booked
  if (offer.status === 'booked' && booked) {
    return shell(
      <div className="card p-10 text-center">
        <p className="text-5xl mb-4"></p>
        <h1 className="text-2xl font-bold mb-2">Your interview is booked</h1>
        <p className="text-lg mb-1">{fmt(booked.start)}</p>
        <p className="text-slate-600 mb-6">{offer.duration_minutes} minutes · {offer.location}</p>
        <a href={`${baseURL}/schedule/${token}/ics`} className="btn-primary inline-block">
          Add to my calendar (.ics)
        </a>
      </div>
    )
  }
  if (offer.status === 'declined') {
    return shell(
      <div className="card p-10 text-center">
        <p className="text-5xl mb-4"></p>
        <h1 className="text-2xl font-bold mb-2">Thank you</h1>
        <p className="text-slate-600">{done || 'The HR team will send you new options soon.'}</p>
      </div>
    )
  }

  return shell(
    <div className="card p-8">
      <h1 className="text-2xl font-bold mb-1">Congratulations {offer.first_name} </h1>
      <p className="text-slate-600 mb-1">Final interview for <b>{offer.job_title}</b></p>
      <p className="text-sm text-slate-500 mb-6">
        {offer.duration_minutes} minutes · {offer.location}. These are the times free right now —
        first come, first served, so we recommend booking soon.
      </p>

      {error && <div className="mb-4 rounded bg-rose-50 border border-rose-200 px-4 py-2 text-sm text-rose-800">{error}</div>}

      {!declining && (
        <>
          <div className="space-y-3 mb-6">
            {offer.times.length === 0 && (
              <p className="text-slate-600 bg-slate-50 rounded p-4">No free times at the moment. Please tell us when you are available below.</p>
            )}
            {offer.times.map((t) => (
              <label key={t} className={`flex items-center gap-3 border rounded-lg p-4 cursor-pointer ${choice === t ? 'border-brand-500 bg-brand-50' : 'hover:bg-slate-50'}`}>
                <input type="radio" name="slot" checked={choice === t} onChange={() => setChoice(t)} />
                <span className="font-medium">{fmt(t)}</span>
              </label>
            ))}
          </div>
          <button onClick={book} disabled={!choice || busy}
            className="btn-primary w-full disabled:opacity-40">
            {busy ? 'Booking…' : 'Confirm this time'}
          </button>
          <button onClick={() => { setDeclining(true); setError('') }} className="w-full mt-3 text-sm text-slate-600 hover:underline">
            None of these work for me
          </button>
        </>
      )}

      {declining && (
        <div>
          <label className="block font-medium mb-2">When are you available?</label>
          <textarea value={availability} onChange={(e) => setAvailability(e.target.value)} maxLength={500}
            placeholder="For example: Tuesday or Thursday afternoon, or any morning next week"
            className="w-full border rounded-lg p-3 h-28 mb-3 focus:outline-none focus:ring-2 focus:ring-brand-400" />
          <button onClick={decline} disabled={availability.trim().length < 5 || busy}
            className="btn-primary w-full disabled:opacity-40">
            {busy ? 'Sending…' : 'Send my availability'}
          </button>
          <button onClick={() => setDeclining(false)} className="w-full mt-3 text-sm text-slate-600 hover:underline">
            ← Back to the proposed times
          </button>
        </div>
      )}
      <p className="mt-8 text-center text-xs text-slate-400">Powered by HR Buddy · Developed by NGZ 40</p>
    </div>
  )
}
