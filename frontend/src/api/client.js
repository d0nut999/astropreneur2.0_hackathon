/**
 * API client: sends the session cookie (withCredentials) and the CSRF token on every change.
 * The session cookie itself is HttpOnly: JavaScript can never read it.
 */
import axios from 'axios'

export const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let csrfToken = ''
export function setCsrfToken(token) {
  csrfToken = token || ''
}

const client = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const method = (config.method || 'get').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  (error) => {
    const path = window.location.pathname
    const url = error.config?.url || ''
    // Session expired -> back to login (but never on the public candidate portal)
    if (error.response?.status === 401 && !path.startsWith('/login') && !path.startsWith('/portal') && !path.startsWith('/schedule') && !url.includes('/auth/')) {
      window.location.href = `/login?next=${encodeURIComponent(path)}`
    }
    return Promise.reject(error)
  }
)

export default client
