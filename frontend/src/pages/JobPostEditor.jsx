/**
 * Job post: HR enters the key facts -> AI draft -> fairness & fact checks -> HR edits -> HR publishes.
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { apiGet, apiPost, apiPut } from '../api'

const EMPTY = {
  title: '', team: '', location: '', work_mode: 'hybrid', contract_type: 'permanent', contract_length: '',
  start_date: '', hours: '40 h/week', salary_min: '', salary_max: '', currency: 'TND', experience: '',
  must_haves: '', nice_to_haves: '', tasks: '', benefits: '', about: '',
}
const EXAMPLE = {
  ...EMPTY, title: 'Customer Support Specialist', team: 'Customer Support', location: 'Tunis', work_mode: 'hybrid',
  contract_type: 'fixed_term', contract_length: '12 months', start_date: '1 December 2026', salary_min: 1800,
  salary_max: 2300, experience: '1-3 years',
  must_haves: 'Fluent French and English (written and spoken)\nExperience answering customers by email or phone\nYoung and dynamic',
  nice_to_haves: 'A ticketing tool such as Zendesk or Freshdesk', tasks: 'Answer customer emails, chats and calls\nWrite and update help-center articles\nReport recurring problems to the product team',
  benefits: 'Health insurance from day one\nYearly training budget\n2 remote days per week',
}

const toForm = (d) => ({ ...EMPTY, ...d, must_haves: (d.must_haves || []).join('\n'), nice_to_haves: (d.nice_to_haves || []).join('\n'),
  tasks: (d.tasks || []).join('\n'), benefits: (d.benefits || []).join('\n'), salary_min: d.salary_min || '', salary_max: d.salary_max || '' })

function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-slate-400 mt-0.5">{hint}</span>}
    </label>
  )
}
const input = 'input mt-1'

export default function JobPostEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [post, setPost] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [note, setNote] = useState('')
  const [copied, setCopied] = useState(false)
  const [demoMsg, setDemoMsg] = useState('')

  useEffect(() => {
    if (!id) return
    apiGet(`/jobs/${id}/post`).then((r) => { setPost(r.data); setText(r.data.text); setForm(toForm(r.data.details)) })
  }, [id])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const run = async (label, fn) => {
    setBusy(label)
    setErr('')
    try {
      const r = await fn()
      setPost(r.data)
      setText(r.data.text)
      return r.data
    } catch (e) {
      setErr(e.response?.data?.detail || 'Something went wrong')
    } finally {
      setBusy('')
    }
  }
  const generate = async () => {
    const p = await run('generate', () => (post ? apiPost(`/jobs/${post.job_id}/post/generate`, { details: form }) : apiPost('/jobs/posts/generate', { details: form })))
    if (p && !id) navigate(`/jobs/${p.job_id}/post`, { replace: true })
  }
  const save = () => run('save', () => apiPut(`/jobs/${post.job_id}/post`, { text }))
  const publish = async () => {
    if (text !== post.text) await apiPut(`/jobs/${post.job_id}/post`, { text })
    await run('publish', () => apiPost(`/jobs/${post.job_id}/post/publish`, { note }))
  }
  const applySuggestion = (issue) => {
    let s = issue.suggestion.startsWith('(') ? '' : issue.suggestion
    if (s && issue.phrase[0] === issue.phrase[0].toUpperCase()) s = s[0].toUpperCase() + s.slice(1)
    setText(text.split(issue.phrase).join(s).replace(/ {2,}/g, ' '))
  }
  const sendDemo = async () => {
    setBusy('demo')
    setErr('')
    setDemoMsg('')
    try {
      const r = await apiPost(`/jobs/${post.job_id}/post/demo_applications`)
      setDemoMsg(r.data.message)
    } catch (e) {
      setErr(e.response?.data?.detail || 'Could not send demo applications')
    } finally {
      setBusy('')
    }
  }
  const publicUrl = post?.public_slug ? `${window.location.origin}/careers/${post.public_slug}` : ''
  const published = post?.status === 'published'
  const dirty = post && text !== post.text
  const c = post?.checks

  return (
    <div>
      <Link to="/jobs" className="text-sm text-brand-600 hover:underline">← Jobs</Link>
      <div className="flex flex-wrap items-end justify-between gap-3 mt-2 mb-6">
        <div>
          <h1 className="page-title">{post ? post.title : 'New job post'}</h1>
          <p className="text-slate-600 mt-1">
            You give the facts, the AI writes the text, HR Buddy checks it, you publish. Contract details, salary and
            how to apply are written by code from your input, so they are always exact.
          </p>
        </div>
        {post && (
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${published ? 'bg-emerald-100 text-emerald-800' : post.status === 'closed' ? 'bg-slate-200 text-slate-700' : 'bg-amber-100 text-amber-800'}`}>
            {post.code} · {published ? 'Published' : post.status === 'closed' ? 'Closed' : 'Draft — not public'}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Key facts */}
        <div className="card lg:col-span-2 p-5 space-y-3 h-fit">
          <div className="flex justify-between items-center">
            <h2 className="font-semibold text-slate-900">1. Key facts</h2>
            {!post && <button onClick={() => setForm(EXAMPLE)} className="text-xs text-brand-600 hover:underline">Fill an example</button>}
          </div>
          <fieldset disabled={published} className="space-y-3">
            <Field label="Job title *"><input className={input} value={form.title} onChange={set('title')} /></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Team"><input className={input} value={form.team} onChange={set('team')} /></Field>
              <Field label="Location"><input className={input} value={form.location} onChange={set('location')} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Work mode">
                <select className={input} value={form.work_mode} onChange={set('work_mode')}>
                  <option value="onsite">On-site</option><option value="hybrid">Hybrid</option><option value="remote">Remote</option>
                </select>
              </Field>
              <Field label="Contract">
                <select className={input} value={form.contract_type} onChange={set('contract_type')}>
                  <option value="permanent">Permanent</option><option value="fixed_term">Fixed-term</option>
                  <option value="internship">Internship</option><option value="freelance">Freelance</option>
                </select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field label={`Contract length${['fixed_term', 'internship'].includes(form.contract_type) ? ' *' : ''}`}>
                <input className={input} value={form.contract_length} onChange={set('contract_length')} placeholder="e.g. 12 months" />
              </Field>
              <Field label="Start date"><input className={input} value={form.start_date} onChange={set('start_date')} placeholder="e.g. 1 December 2026" /></Field>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Working hours"><input className={input} value={form.hours} onChange={set('hours')} /></Field>
              <Field label="Experience"><input className={input} value={form.experience} onChange={set('experience')} placeholder="e.g. 1-3 years" /></Field>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Field label="Salary min / month"><input type="number" className={input} value={form.salary_min} onChange={set('salary_min')} /></Field>
              <Field label="Salary max / month"><input type="number" className={input} value={form.salary_max} onChange={set('salary_max')} /></Field>
              <Field label="Currency"><input className={input} value={form.currency} onChange={set('currency')} /></Field>
            </div>
            <Field label="Must-have skills * (one per line)" hint="They become the CV scoring criteria (70%).">
              <textarea rows={3} className={input} value={form.must_haves} onChange={set('must_haves')} />
            </Field>
            <Field label="Nice to have (one per line)"><textarea rows={2} className={input} value={form.nice_to_haves} onChange={set('nice_to_haves')} /></Field>
            <Field label="Main tasks (one per line)"><textarea rows={3} className={input} value={form.tasks} onChange={set('tasks')} /></Field>
            <Field label="Benefits (one per line)"><textarea rows={2} className={input} value={form.benefits} onChange={set('benefits')} /></Field>
            <Field label="About the team (optional)"><textarea rows={2} className={input} value={form.about} onChange={set('about')} /></Field>
          </fieldset>
          {!published && (
            <button onClick={generate} disabled={!!busy} className="btn-primary w-full">
              {busy === 'generate' ? 'Writing…' : post ? '↻ Rewrite from these facts' : 'Write the job post'}
            </button>
          )}
          {err && !post && <p className="text-sm text-rose-700">{err}</p>}
        </div>

        {/* Draft, checks, publish */}
        <div className="lg:col-span-3 space-y-4">
          {!post ? (
            <div className="card p-10 text-center text-slate-500">
              Fill the key facts and click <b>Write the job post</b>. Nothing is public until you click Publish.
            </div>
          ) : (
            <>
              <div className="card p-5">
                <div className="flex justify-between items-center mb-2">
                  <h2 className="font-semibold text-slate-900">2. The post <span className="text-xs font-normal text-slate-500">· written by {post.generated_by === 'ai' ? 'AI (fact-checked)' : 'template (offline)'}</span></h2>
                  {!published && dirty && <button onClick={save} disabled={!!busy} className="btn-secondary">{busy === 'save' ? 'Saving…' : 'Save & re-check'}</button>}
                </div>
                <textarea value={text} onChange={(e) => setText(e.target.value)} readOnly={published} rows={22}
                  className="w-full border rounded p-3 text-sm font-mono leading-relaxed" />
              </div>

              <div className="card p-5 space-y-3">
                <h2 className="font-semibold text-slate-900">3. Checks {dirty && <span className="text-xs font-normal text-amber-700">(save to re-check your edits)</span>}</h2>
                {c.fairness.length === 0 ? (
                  <p className="text-sm text-emerald-700">✓ Inclusive wording: no age, gender, origin, family or appearance criteria found.</p>
                ) : (
                  <div className="rounded border border-amber-300 bg-amber-50 p-3">
                    <p className="text-sm font-semibold text-amber-900 mb-2">{c.fairness.length} wording issue{c.fairness.length > 1 ? 's' : ''} that could exclude candidates</p>
                    {c.fairness.map((f, i) => (
                      <div key={i} className="text-sm flex flex-wrap items-center gap-2 py-1">
                        <span className="font-mono bg-white border px-1.5 rounded">“{f.phrase}”</span>
                        <span className="text-slate-700">{f.why} Suggestion: <i>{f.suggestion}</i></span>
                        {!published && <button onClick={() => applySuggestion(f)} className="text-xs px-2 py-0.5 rounded bg-white border border-amber-400 hover:bg-amber-100">Apply</button>}
                      </div>
                    ))}
                  </div>
                )}
                {c.excluded_from_scoring.length > 0 && (
                  <p className="text-sm text-slate-700">Not used to score CVs: {c.excluded_from_scoring.map((e) => `“${e.point}”`).join(', ')} (fails the fairness check).</p>
                )}
                {c.removed_by_fact_check.length > 0 && (
                  <p className="text-sm text-slate-700">Removed from the AI text because it contained numbers you did not give: {c.removed_by_fact_check.map((x) => `“${x}”`).join(', ')}</p>
                )}
                <p className={`text-sm ${c.contact_ok ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {c.contact_ok ? '✓' : '✗'} How to apply: {post.contact_email} with code {post.code} (written by code; applications with this code go to this job).
                </p>
                <p className={`text-sm ${c.facts_ok ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {c.facts_ok ? '✓ Contract, salary and dates exactly as you entered them.' : 'The details block was edited by hand: double-check contract, salary and dates.'}
                </p>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500 mb-1 mt-2">CV scoring criteria from your key points</p>
                  <div className="flex flex-wrap gap-2">
                    {post.rubric.map((r) => (
                      <span key={r.key} className="text-xs bg-slate-100 text-slate-700 rounded px-2 py-1">{r.label} · {Math.round(r.weight)}%{r.must_have ? ' · must-have' : ''}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card p-5">
                <h2 className="font-semibold text-slate-900 mb-2">4. Publish</h2>
                {published ? (
                  <div className="space-y-2">
                    <p className="text-sm text-emerald-800">✓ Published. Candidates apply to {post.contact_email}; their CVs arrive in the Inbox and are scored for this job.</p>
                    <div className="flex flex-wrap gap-2 items-center">
                      <a href={publicUrl} target="_blank" rel="noreferrer" className="text-sm text-brand-600 hover:underline break-all">{publicUrl} ↗</a>
                      <button onClick={() => { navigator.clipboard?.writeText(post.text); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
                        className="btn-secondary">{copied ? 'Copied ✓' : 'Copy text (LinkedIn, job boards)'}</button>
                      <Link to={`/jobs/${post.job_id}`} className="btn-secondary">Candidates →</Link>
                      <button onClick={() => run('close', () => apiPost(`/jobs/${post.job_id}/post/close`))} className="btn-danger">Close the post</button>
                    </div>
                    {post.dev && (
                      <div className="mt-3 p-3 rounded-lg border border-dashed border-purple-300 bg-purple-50">
                        <p className="text-sm text-purple-900 mb-2">
                          <b>Demo:</b> 4 fictional candidates (strong → weak, CVs built from your key points) email their
                          application with code {post.code}. They go through the real pipeline: security check, anonymization, scoring.
                        </p>
                        <div className="flex flex-wrap gap-2 items-center">
                          <button onClick={sendDemo} disabled={!!busy}
                            className="px-3 py-1.5 text-sm rounded-lg bg-purple-600 text-white font-medium hover:bg-purple-700 disabled:opacity-50">
                            {busy === 'demo' ? 'Candidates are applying…' : 'Send 4 demo applications'}
                          </button>
                          {demoMsg && (
                            <>
                              <span className="text-sm text-purple-900">✓ {demoMsg}</span>
                              <Link to={`/jobs/${post.job_id}`} className="text-sm font-medium text-brand-700 hover:underline">See the ranking →</Link>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-slate-600">Publishing makes the post public and approves the scoring criteria above. Only you can do this.</p>
                    {c.fairness.length > 0 && (
                      <input value={note} onChange={(e) => setNote(e.target.value)} className="w-full border rounded px-2 py-1.5 text-sm"
                        placeholder="Publishing with open wording issues? Write why (saved in the audit log)" />
                    )}
                    <button onClick={publish} disabled={!!busy} className="btn-success">
                      {busy === 'publish' ? 'Publishing…' : 'Publish'}
                    </button>
                  </div>
                )}
                {err && <p className="text-sm text-rose-700 mt-2">{err}</p>}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
