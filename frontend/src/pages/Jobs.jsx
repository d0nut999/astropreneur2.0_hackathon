/**
 * Recruitment > Job posts: every job with its pipeline.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../api'
import Icon from '../components/Icon'

const STATUS = {
  published: 'bg-emerald-50 text-emerald-700',
  draft: 'bg-amber-50 text-amber-700',
  closed: 'bg-slate-100 text-slate-600',
}

function Stat({ value, label, tone = 'text-slate-900' }) {
  return (
    <div className="text-right">
      <p className={`text-lg font-semibold tabular-nums ${value ? tone : 'text-slate-300'}`}>{value || 0}</p>
      <p className="text-[11px] text-slate-500">{label}</p>
    </div>
  )
}

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet('/jobs')
      .then((res) => setJobs(res.data))
      .catch((err) => console.error('Failed to load jobs:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Job posts</h1>
          <p className="page-sub">Candidates who apply by email are screened, anonymized and scored against each job's criteria.</p>
        </div>
        <Link to="/jobs/new" className="btn-primary"><Icon name="plus" /> New job post</Link>
      </div>

      <div className="space-y-3">
        {jobs.map((job) => {
          const c = job.status_counts || {}
          const scored = (c.SCORED || 0) + (c.SHORTLISTED || 0)
          const inProcess = (c.INVITED || 0) + (c.VIDEO_SUBMITTED || 0) + (c.EVALUATED || 0)
          const post = job.post
          return (
            <div key={job.id} className="card transition hover:border-slate-300">
              <Link to={post?.status === 'draft' ? `/jobs/${job.id}/post` : `/jobs/${job.id}`} className="flex items-start gap-6 p-5">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                  <Icon name="briefcase" className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-slate-900">{job.title}</h2>
                    {post && <span className={`chip ${STATUS[post.status]}`}>{post.code} · {post.status}</span>}
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">{job.description.replace(/^[A-Z0-9 ()&/-]+\n+/, '')}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {job.rubric?.map((r) => (
                      <span key={r.key} className="chip bg-slate-100 font-normal text-slate-600">
                        {r.label} · {Math.round(r.weight)}%{r.must_have ? ' · must-have' : ''}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex shrink-0 gap-6">
                  <Stat value={job.applications} label="applications" />
                  <Stat value={scored} label="to review" tone="text-brand-700" />
                  <Stat value={inProcess} label="interviewing" tone="text-brand-700" />
                  <Stat value={job.quarantined} label="blocked" tone="text-rose-600" />
                </div>
              </Link>
              {post && (
                <div className="flex gap-4 border-t border-slate-100 px-5 py-2.5 text-sm">
                  <Link to={`/jobs/${job.id}/post`} className="link">Edit job post</Link>
                  <Link to={`/jobs/${job.id}`} className="link">Candidates</Link>
                  {post.public_slug && (
                    <a href={`/careers/${post.public_slug}`} target="_blank" rel="noreferrer" className="link inline-flex items-center gap-1">
                      Public page <Icon name="external" className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
      {jobs.length === 0 && <div className="card p-10 text-center text-sm text-slate-500">No jobs yet. Create your first job post.</div>}
    </div>
  )
}
