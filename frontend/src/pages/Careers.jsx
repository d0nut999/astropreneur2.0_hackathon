/**
 * Public job post page (no login). Shows only published posts. Text is rendered as plain text.
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import client from '../api/client'

export default function Careers() {
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get(`/careers/${slug}`).then((r) => setPost(r.data)).catch((e) => setError(e.response?.data?.detail || 'Not available'))
  }, [slug])

  const blocks = post ? post.text.split(/\n\s*\n/) : []
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <p className="text-sm text-slate-500 mb-4">Fictional Company · Careers</p>
        {error && <div className="card p-10 text-center text-slate-600">{error}</div>}
        {post && (
          <div className="card p-8">
            <p className="text-xs text-slate-400 mb-1">{post.code}{post.published_at && ` · published ${new Date(post.published_at).toLocaleDateString()}`}</p>
            <h1 className="page-title mb-4">{post.title}</h1>
            {blocks.slice(1).map((b, i) => {
              const lines = b.split('\n')
              const isHeading = lines.length > 1 && lines[0] === lines[0].toUpperCase() && /[A-Z]/.test(lines[0])
              const apply = lines[0] === 'HOW TO APPLY'
              return (
                <div key={i} className={`mb-5 ${apply ? 'rounded-lg bg-brand-50 border border-brand-200 p-4' : ''}`}>
                  {isHeading && <h2 className="text-sm font-semibold tracking-wide text-slate-500 mb-2">{lines[0]}</h2>}
                  {(isHeading ? lines.slice(1) : lines).map((l, j) =>
                    l.startsWith('- ') ? <p key={j} className="pl-4 -indent-3 text-slate-800">• {l.slice(2)}</p> : <p key={j} className="text-slate-800">{l}</p>)}
                </div>
              )
            })}
          </div>
        )}
        <p className="mt-6 text-center text-xs text-slate-400">Fictional company, demo data only · Powered by HR Buddy · Developed by NGZ 40</p>
      </div>
    </div>
  )
}
