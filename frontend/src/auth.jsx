/**
 * Who is logged in. Pages inside <RequireAuth> redirect to /login when nobody is.
 */
import { createContext, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { apiGet, apiPost } from './api'
import { setCsrfToken } from './api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    if (window.location.pathname.startsWith('/portal') || window.location.pathname.startsWith('/schedule')) {
      setChecking(false) // candidates never need an HR session
      return
    }
    apiGet('/auth/me')
      .then((res) => {
        setCsrfToken(res.data.csrf_token)
        setUser(res.data)
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  const login = async (email, password) => {
    const res = await apiPost('/auth/login', { email, password })
    setCsrfToken(res.data.csrf_token)
    setUser(res.data)
    return res.data
  }

  const logout = async () => {
    try {
      await apiPost('/auth/logout')
    } finally {
      setCsrfToken('')
      setUser(null)
    }
  }

  return <AuthContext.Provider value={{ user, checking, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

export function RequireAuth({ children }) {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return children
}
