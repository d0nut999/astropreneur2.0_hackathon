/**
 * Main layout component with navigation.
 */
import { NavLink, Link, Outlet } from 'react-router-dom'

const LINKS = [
  { to: '/dashboard', label: 'Today' },
  { to: '/inbox', label: 'Inbox' },
  { to: '/agenda', label: 'Agenda' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/audit', label: 'Audit' },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <nav className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold text-blue-600">
            🛡️ HireGuard
          </Link>
          <ul className="flex gap-1 items-center">
            {LINKS.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
            <li>
              <Link to="/login" className="ml-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-900">
                Login
              </Link>
            </li>
          </ul>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>

      <footer className="bg-gray-100 border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          HireGuard · The agent executes, the human decides.
        </div>
      </footer>
    </div>
  )
}
