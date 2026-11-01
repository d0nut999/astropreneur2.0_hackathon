/**
 * Login page.
 */
import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import Icon, { Logo } from '../components/Icon'
import { useAuth } from '../auth'

export default function Login() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { user, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const next = params.get('next')
  const target = next && next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard' // no open redirect

  if (user) return <Navigate to={target} replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(email, password)
      navigate(target, { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-slate-900 p-12 text-white lg:flex">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
        <div className="absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-brand-400/10 blur-3xl" />
        <div className="relative flex items-center gap-2.5">
          <Logo className="h-8 w-8" />
          <span className="text-lg font-semibold tracking-tight">HR Buddy</span>
        </div>
        <div className="relative max-w-md">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight text-white">Your HR assistant for hiring and for the people you already have.</h2>
          <p className="mt-4 text-slate-300">It reads the inbox, ranks CVs with evidence, plans interviews, checks leave requests and answers staff questions. Every email and every decision about a person waits for a human click.</p>
          <div className="mt-8 grid grid-cols-2 gap-3 text-sm">
            {[['briefcase', 'Recruitment', 'Job posts, CV ranking, interviews'], ['users', 'Employees', 'Leave, presence, handbook answers']].map(([i, t, d]) => (
              <div key={t} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <Icon name={i} className="h-5 w-5 text-brand-300" />
                <p className="mt-2 font-medium">{t}</p>
                <p className="text-slate-400">{d}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-slate-500">Developed by <span className="font-semibold text-slate-300">NGZ 40</span> · Fictional data only</p>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <Logo /><span className="text-lg font-semibold">HR Buddy</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-slate-500">Welcome back. Sign in to your HR workspace.</p>

          {error && <div className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username"
                className="input" placeholder="you@fictional-company.test" required />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password"
                className="input" placeholder="••••••••" required />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">{loading ? 'Signing in…' : 'Sign in'}</button>
          </form>

          <div className="mt-8 rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
            <p className="mb-2 font-semibold text-slate-700">Demo accounts (fictional)</p>
            <button type="button" onClick={() => { setEmail('recruiter@fictional-company.test'); setPassword('recruiter123') }}
              className="block w-full rounded px-2 py-1 text-left hover:bg-white">Recruiter · recruiter@fictional-company.test / recruiter123</button>
            <button type="button" onClick={() => { setEmail('admin@fictional-company.test'); setPassword('admin123') }}
              className="block w-full rounded px-2 py-1 text-left hover:bg-white">Admin · admin@fictional-company.test / admin123</button>
          </div>
        </div>
      </div>
    </div>
  )
}
