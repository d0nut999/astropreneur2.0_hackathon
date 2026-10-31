/**
 * HR calendar: week view (default) or list view.
 * Shows interviews, meetings (confirmed / to confirm), deadlines, interview blocks, lunch, free interview spots.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api'
import { baseURL } from '../api/client'
import Agenda from './Agenda'

const HOUR_PX = 56
const iso = (d) => d.toISOString().slice(0, 10)
const hm = (s) => new Date(s).toTimeString().slice(0, 5)
const minutesOf = (s) => {
  const d = new Date(s)
  return d.getHours() * 60 + d.getMinutes()
}

const STYLE = {
  interview: 'bg-indigo-600 text-white border-indigo-700',
  confirmed: 'bg-emerald-500 text-white border-emerald-600',
  suggested: 'bg-white text-emerald-900 border-emerald-500 border-dashed',
}

function lanes(items) {
  // place overlapping items side by side
  const sorted = [...items].sort((a, b) => minutesOf(a.start) - minutesOf(b.start))
  const ends = []
  return sorted.map((it) => {
    let lane = ends.findIndex((end) => end <= minutesOf(it.start))
    if (lane === -1) lane = ends.length
    ends[lane] = minutesOf(it.end)
    return { ...it, lane }
  }).map((it, _, all) => ({ ...it, laneCount: Math.max(...all.filter((o) => minutesOf(o.start) < minutesOf(it.end) && minutesOf(it.start) < minutesOf(o.end)).map((o) => o.lane)) + 1 }))
}

export default function Calendar() {
  const [view, setView] = useState('week')
  const [day, setDay] = useState(iso(new Date()))
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [msg, setMsg] = useState('')
  const [clash, setClash] = useState('')

  const load = () => apiGet(`/calendar?day=${day}`).then((r) => setData(r.data)).catch(() => setMsg('Could not load the calendar.'))
  useEffect(() => {
    load()
  }, [day])

  const shift = (n) => {
    const d = new Date(`${day}T12:00:00`)
    d.setDate(d.getDate() + n * 7)
    setDay(iso(d))
    setSelected(null)
  }

  const decide = async (eventId, action, force = false) => {
    setClash('')
    try {
      await apiPost(`/events/${eventId}/${action}${force ? '?force=true' : ''}`)
      setSelected(null)
      await load()
    } catch (e) {
      if (e.response?.status === 409) setClash(e.response.data.detail)
      else setMsg(e.response?.data?.detail || 'Action failed')
    }
  }

  if (view === 'list') {
    return (
      <div>
        <Header view={view} setView={setView} />
        <Agenda embedded />
      </div>
    )
  }
  if (!data) return <div className="text-center text-gray-500">{msg || 'Loading…'}</div>

  const { hours, lunch } = data
  const height = (hours.end - hours.start) * HOUR_PX
  const top = (min) => ((min - hours.start * 60) / 60) * HOUR_PX
  const visibleDays = data.days.filter((d) => d.is_work_day || d.is_today ||
    data.items.some((i) => i.start.startsWith(d.date)) || data.all_day.some((a) => a.date === d.date))
  const now = new Date(data.now)
  const weekLabel = `${new Date(`${data.week_start}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long' })} – ${new Date(`${data.days[6].date}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}`
  const s = data.summary

  return (
    <div className="relative">
      <Header view={view} setView={setView} />

      {/* Week navigation + summary */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <button onClick={() => shift(-1)} className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50">◀</button>
          <button onClick={() => setDay(iso(new Date()))} className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50 text-sm">Today</button>
          <button onClick={() => shift(1)} className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50">▶</button>
          <span className="ml-2 font-semibold">{weekLabel}</span>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <Chip color="bg-indigo-100 text-indigo-800">🤝 {s.interviews} interview{s.interviews !== 1 && 's'}</Chip>
          <Chip color="bg-emerald-100 text-emerald-800">📅 {s.meetings} meeting{s.meetings !== 1 && 's'}</Chip>
          <Chip color="bg-yellow-100 text-yellow-800">{s.to_confirm} to confirm</Chip>
          <Chip color="bg-orange-100 text-orange-800">⏰ {s.deadlines} deadline{s.deadlines !== 1 && 's'}</Chip>
          <Chip color="bg-green-50 text-green-800 ring-1 ring-green-200">{s.free_interview_spots} free interview spot{s.free_interview_spots !== 1 && 's'}</Chip>
          {s.clashes > 0 && <Chip color="bg-red-100 text-red-800">⚠ {s.clashes} clash{s.clashes > 1 && 'es'}</Chip>}
        </div>
      </div>

      {msg && <div className="mb-3 rounded bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">{msg}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {/* Day headers */}
        <div className="grid border-b" style={{ gridTemplateColumns: `56px repeat(${visibleDays.length}, 1fr)` }}>
          <div />
          {visibleDays.map((d) => (
            <div key={d.date} className={`px-2 py-2 text-center border-l ${d.is_today ? 'bg-blue-50' : ''}`}>
              <div className="text-xs uppercase text-gray-500">{d.weekday.slice(0, 3)}</div>
              <div className={`text-lg font-semibold ${d.is_today ? 'text-blue-700' : ''}`}>{Number(d.date.slice(8))}</div>
            </div>
          ))}
        </div>

        {/* All-day row (deadlines, meetings without time) */}
        <div className="grid border-b bg-gray-50" style={{ gridTemplateColumns: `56px repeat(${visibleDays.length}, 1fr)` }}>
          <div className="text-[10px] text-gray-400 px-1 py-1">all day</div>
          {visibleDays.map((d) => (
            <div key={d.date} className="border-l p-1 min-h-[30px] space-y-1">
              {data.all_day.filter((a) => a.date === d.date).map((a) => (
                <button key={a.id} onClick={() => setSelected({ ...a })}
                  className={`block w-full text-left text-xs rounded px-1.5 py-0.5 truncate border ${a.status === 'confirmed' ? 'bg-orange-500 text-white border-orange-600' : 'bg-white text-orange-800 border-orange-400 border-dashed'}`}>
                  ⏰ {a.title}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Time grid */}
        <div className="grid relative" style={{ gridTemplateColumns: `56px repeat(${visibleDays.length}, 1fr)` }}>
          <div className="relative" style={{ height }}>
            {Array.from({ length: hours.end - hours.start }, (_, i) => (
              <div key={i} className="absolute right-1 text-[11px] text-gray-400" style={{ top: i * HOUR_PX - 6 }}>
                {String(hours.start + i).padStart(2, '0')}:00
              </div>
            ))}
          </div>
          {visibleDays.map((d) => {
            const dayItems = lanes(data.items.filter((i) => i.start.startsWith(d.date)))
            const free = data.free_spots.filter((f) => f.startsWith(d.date))
            const isNowDay = d.date === iso(now)
            const nowMin = now.getHours() * 60 + now.getMinutes()
            return (
              <div key={d.date} className={`relative border-l ${d.is_work_day ? '' : 'bg-gray-50'}`} style={{ height }}>
                {/* hour lines */}
                {Array.from({ length: hours.end - hours.start }, (_, i) => (
                  <div key={i} className="absolute left-0 right-0 border-t border-gray-100" style={{ top: i * HOUR_PX }} />
                ))}
                {/* interview blocks */}
                {d.blocks.map((b, i) => {
                  const t = top(Number(b.start.slice(0, 2)) * 60)
                  const h = top(Number(b.end.slice(0, 2)) * 60) - t
                  return (
                    <div key={i} className="absolute left-0 right-0 bg-green-50 border-y border-green-200" style={{ top: t, height: h }}>
                      <span className="absolute top-0.5 right-1 text-[10px] text-green-700">interview block</span>
                    </div>
                  )
                })}
                {/* lunch */}
                {d.is_work_day && (
                  <div className="absolute left-0 right-0 bg-gray-100/80 flex items-center justify-center text-[10px] text-gray-400"
                    style={{ top: top(lunch.start * 60), height: (lunch.end - lunch.start) * HOUR_PX }}>lunch</div>
                )}
                {/* free interview spots */}
                {free.map((f) => (
                  <button key={f} onClick={() => setSelected({ kind: 'free', start: f })}
                    className="absolute left-1 right-1 rounded border border-dashed border-green-400 text-[10px] text-green-700 hover:bg-green-100"
                    style={{ top: top(minutesOf(f)) + 2, height: HOUR_PX - 4 }}>
                    free · {hm(f)}
                  </button>
                ))}
                {/* events */}
                {dayItems.map((it) => {
                  const cls = it.kind === 'interview' ? STYLE.interview : STYLE[it.status] || STYLE.suggested
                  const w = 100 / it.laneCount
                  return (
                    <button key={it.id} onClick={() => { setSelected(it); setClash('') }}
                      className={`absolute rounded-md border-2 px-1.5 py-1 text-left overflow-hidden shadow-sm hover:shadow ${cls} ${it.conflict ? 'ring-2 ring-red-500' : ''}`}
                      style={{ top: top(minutesOf(it.start)) + 1, height: Math.max(26, ((minutesOf(it.end) - minutesOf(it.start)) / 60) * HOUR_PX - 3),
                               left: `calc(${it.lane * w}% + 3px)`, width: `calc(${w}% - 6px)` }}>
                      <div className="text-[11px] font-semibold leading-tight truncate">
                        {it.conflict && '⚠ '}{hm(it.start)} {it.kind === 'interview' ? '🤝' : '📅'} {it.title}
                      </div>
                      <div className="text-[10px] leading-tight truncate opacity-90">{it.who}</div>
                    </button>
                  )
                })}
                {/* now line */}
                {isNowDay && nowMin >= hours.start * 60 && nowMin <= hours.end * 60 && (
                  <div className="absolute left-0 right-0 border-t-2 border-red-500 z-10" style={{ top: top(nowMin) }}>
                    <span className="absolute -left-1 -top-1.5 h-3 w-3 rounded-full bg-red-500" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-600">
        <span><span className="inline-block w-3 h-3 rounded bg-indigo-600 align-middle mr-1" />Interview booked</span>
        <span><span className="inline-block w-3 h-3 rounded bg-emerald-500 align-middle mr-1" />Meeting confirmed</span>
        <span><span className="inline-block w-3 h-3 rounded border-2 border-dashed border-emerald-500 align-middle mr-1" />Meeting to confirm (from an email)</span>
        <span><span className="inline-block w-3 h-3 rounded bg-green-50 border border-green-300 align-middle mr-1" />Interview block (free spots dashed)</span>
        <span><span className="inline-block w-3 h-3 rounded ring-2 ring-red-500 align-middle mr-1" />Clash</span>
        <span className="text-gray-400">Interview blocks: {data.settings.blocks_text} · max {data.settings.max_interviews_per_day} interviews/day</span>
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="fixed top-0 right-0 h-full w-96 max-w-full bg-white shadow-2xl z-30 p-6 overflow-y-auto border-l">
          <button onClick={() => setSelected(null)} className="absolute top-3 right-4 text-gray-400 hover:text-gray-700 text-xl">×</button>
          <Detail item={selected} decide={decide} clash={clash} />
        </div>
      )}
    </div>
  )
}

function Header({ view, setView }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h1 className="text-3xl font-bold">Calendar</h1>
        <p className="text-gray-500 text-sm">Interviews, meetings found in emails, deadlines, and free interview spots.</p>
      </div>
      <div className="flex rounded-lg border bg-white overflow-hidden text-sm">
        {['week', 'list'].map((v) => (
          <button key={v} onClick={() => setView(v)}
            className={`px-4 py-2 capitalize ${view === v ? 'bg-gray-900 text-white' : 'hover:bg-gray-50'}`}>{v}</button>
        ))}
      </div>
    </div>
  )
}

function Chip({ color, children }) {
  return <span className={`rounded-full px-3 py-1 ${color}`}>{children}</span>
}

function Detail({ item, decide, clash }) {
  const when = item.start
    ? `${new Date(item.start).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}, ${hm(item.start)}`
    : new Date(`${item.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  if (item.kind === 'free') {
    return (
      <div>
        <p className="text-xs uppercase text-green-700 mb-1">Free interview spot</p>
        <h2 className="text-xl font-semibold mb-2">{when}</h2>
        <p className="text-sm text-gray-600">Inside an interview block and free. Candidates with a scheduling link can book it — first come, first served.</p>
      </div>
    )
  }
  return (
    <div>
      <p className="text-xs uppercase text-gray-500 mb-1">
        {item.kind === 'interview' ? '🤝 Interview · booked' : item.kind === 'deadline' ? `⏰ Deadline · ${item.status}` : `📅 Meeting · ${item.status === 'suggested' ? 'to confirm' : item.status}`}
      </p>
      <h2 className="text-xl font-semibold mb-1">{item.title}</h2>
      <p className="text-gray-700 mb-4">{when}{item.end && ` – ${hm(item.end)}`}</p>

      {item.conflict && <p className="text-sm bg-red-50 text-red-800 rounded p-2 mb-3">⚠ {item.conflict}</p>}

      <dl className="text-sm space-y-2 mb-5">
        {item.who && <div><dt className="text-gray-500 text-xs">With</dt><dd>{item.who}</dd></div>}
        {item.job && <div><dt className="text-gray-500 text-xs">Position</dt><dd>{item.job}</dd></div>}
        {item.location && <div><dt className="text-gray-500 text-xs">Where</dt><dd>{item.location}</dd></div>}
        {item.email_subject && <div><dt className="text-gray-500 text-xs">Found in the email</dt><dd>"{item.email_subject}" — {item.email_from}</dd></div>}
      </dl>

      <div className="flex flex-col gap-2">
        {item.kind === 'interview' && (
          <>
            <Link to={`/candidates/${item.application_id}`} className="px-3 py-2 rounded bg-indigo-600 text-white text-sm text-center hover:bg-indigo-700">Open candidate</Link>
            <a href={`${baseURL}/candidates/${item.application_id}/interview.ics`} className="px-3 py-2 rounded border text-sm text-center hover:bg-gray-50">Download calendar file (.ics)</a>
          </>
        )}
        {item.event_id && item.status === 'suggested' && (
          <>
            <button onClick={() => decide(item.event_id, 'confirm')} className="px-3 py-2 rounded bg-green-600 text-white text-sm hover:bg-green-700">Confirm</button>
            <button onClick={() => decide(item.event_id, 'dismiss')} className="px-3 py-2 rounded border text-sm hover:bg-gray-50">Dismiss</button>
          </>
        )}
        {clash && (
          <div className="text-sm bg-red-50 border border-red-200 rounded p-2 text-red-800">
            {clash}
            <button onClick={() => decide(item.event_id, 'confirm', true)} className="block mt-1 underline">Confirm anyway</button>
          </div>
        )}
        {item.email_id && <Link to={`/inbox?id=${item.email_id}`} className="px-3 py-2 rounded border text-sm text-center hover:bg-gray-50">Open the email</Link>}
      </div>
    </div>
  )
}
