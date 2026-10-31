/**
 * Login page.
 */
import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <p className="text-center text-3xl font-bold text-blue-600 mb-2">🛡️ HireGuard</p>
        <p className="text-center text-gray-500 mb-6">The agent executes, the human decides.</p>
        <div className="bg-white p-8 rounded-lg shadow">
          <h1 className="text-xl font-semibold mb-6">Sign in to the HR workspace</h1>

          {error && <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-800 text-sm">{error}</div>}

          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username"
              className="w-full px-4 py-2 border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="recruiter@fictional-company.test" required />

            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password"
              className="w-full px-4 py-2 border rounded-lg mb-6 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Password" required />

            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 p-4 bg-blue-50 rounded text-sm text-blue-800">
            <p className="font-semibold mb-1">Demo accounts (fictional)</p>
            <p>Recruiter: recruiter@fictional-company.test / recruiter123</p>
            <p>Admin: admin@fictional-company.test / admin123</p>
          </div>
        </div>
      </div>
    </div>
  )
}
