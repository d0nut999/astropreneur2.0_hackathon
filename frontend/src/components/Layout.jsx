/**
 * Main layout component with navigation.
 */
import { Link, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <nav className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold text-blue-600">
            HireGuard
          </Link>
          <ul className="flex gap-6">
            <li>
              <Link to="/login" className="text-gray-600 hover:text-gray-900">
                Login
              </Link>
            </li>
            <li>
              <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
                Dashboard
              </Link>
            </li>
            <li>
              <Link to="/jobs" className="text-gray-600 hover:text-gray-900">
                Jobs
              </Link>
            </li>
            <li>
              <Link to="/approvals" className="text-gray-600 hover:text-gray-900">
                Approvals
              </Link>
            </li>
            <li>
              <Link to="/audit" className="text-gray-600 hover:text-gray-900">
                Audit
              </Link>
            </li>
          </ul>
        </nav>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          HireGuard © 2024 | Secure AI Recruiting Assistant
        </div>
      </footer>
    </div>
  )
}
