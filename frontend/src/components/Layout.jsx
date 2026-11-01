/**
 * App shell: two areas at the top (Recruitment = future employees, Employees = current staff),
 * a sidebar with the pages of the current area plus the shared workspace (Today, Inbox, Calendar, Approvals).
 */
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { apiGet } from '../api'
import Icon, { Logo } from './Icon'

const AREAS = {
  recruitment: {
    label: 'Recruitment', home: '/jobs', hint: 'Future employees',
    items: [
      { to: '/jobs', label: 'Job posts', icon: 'briefcase', match: ['/jobs', '/candidates'] },
      { to: '/followups', label: 'Follow-ups', icon: 'clock', badge: 'followups' },
    ],
  },
  employees: {
    label: 'Employees', home: '/employees', hint: 'Current staff',
    items: [
      { to: '/employees', label: 'Overview', icon: 'chart', exact: true },
      { to: '/employees/leave', label: 'Leave requests', icon: 'clipboard', badge: 'leave' },
      { to: '/employees/handbook', label: 'Questions & handbook', icon: 'book' },
      { to: '/employees/directory', label: 'Directory', icon: 'list' },
    ],
  },
}
const WORKSPACE = [
  { to: '/dashboard', label: 'Today', icon: 'home', match: ['/dashboard'], exact: true },
  { to: '/inbox', label: 'Inbox', icon: 'inbox' },
  { to: '/calendar', label: 'Calendar', icon: 'calendar', match: ['/calendar', '/agenda'] },
  { to: '/approvals', label: 'Approvals', icon: 'checkCircle', badge: 'approvals' },
  { to: '/audit', label: 'Audit log', icon: 'shield', adminOnly: true },
]

function areaOf(path) {
  if (path.startsWith('/employees')) return 'employees'
  if (path.startsWith('/jobs') || path.startsWith('/candidates') || path.startsWith('/followups')) return 'recruitment'
  return null
}

function isActive(item, path) {
  if (item.exact) return path === item.to || (item.to === '/dashboard' && path === '/')
  return (item.match || [item.to]).some((m) => path === m || path.startsWith(m + '/'))
}

function NavItem({ item, path, count }) {
  const active = isActive(item, path)
  return (
    <NavLink to={item.to}
      className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors ${
        active ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}>
      <Icon name={item.icon} className={`h-4 w-4 ${active ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
      <span className="flex-1">{item.label}</span>
      {count > 0 && (
        <span className={`min-w-[20px] rounded-full px-1.5 text-center text-[11px] font-semibold leading-5 ${
          active ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-700'}`}>{count}</span>
      )}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [area, setArea] = useState(() => {
    try { return localStorage.getItem('hrb-area') || 'recruitment' } catch { return 'recruitment' }
  })
  const [counts, setCounts] = useState({})

  useEffect(() => {
    const a = areaOf(pathname)
    if (a && a !== area) {
      setArea(a)
      try { localStorage.setItem('hrb-area', a) } catch { /* private mode */ }
    }
  }, [pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    apiGet('/digest/today').then((r) => setCounts({
      approvals: r.data.pending_approvals_count,
      followups: (r.data.followups_due_count || 0) + (r.data.followups_your_call_count || 0),
      leave: r.data.leave_pending_count,
    })).catch(() => {})
  }, [pathname])

  const switchArea = (a) => {
    setArea(a)
    try { localStorage.setItem('hrb-area', a) } catch { /* private mode */ }
    navigate(AREAS[a].home)
  }
  const signOut = async () => {
    await logout()
    navigate('/login')
  }
  const current = AREAS[area]
  const initials = (user?.email || '?').slice(0, 2).toUpperCase()

  return (
    <div className="min-h-screen">
      {/* Top bar: the two worlds of HR */}
      <header className="fixed inset-x-0 top-0 z-30 h-14 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="flex h-full items-center gap-6 px-5">
          <Link to="/dashboard" className="flex w-52 items-center gap-2.5">
            <Logo />
            <span className="text-[15px] font-semibold tracking-tight text-slate-900">HR Buddy</span>
          </Link>
          <nav className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
            {Object.entries(AREAS).map(([key, a]) => (
              <button key={key} onClick={() => switchArea(key)}
                className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-sm font-medium transition ${
                  area === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}>
                <Icon name={key === 'recruitment' ? 'briefcase' : 'users'} className="h-4 w-4" />
                {a.label}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <Link to="/approvals" title="Emails waiting for your approval"
              className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800">
              <Icon name="checkCircle" className="h-5 w-5" />
              {counts.approvals > 0 && (
                <span className="absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full bg-rose-500 px-1 text-center text-[10px] font-semibold leading-[18px] text-white">
                  {counts.approvals}
                </span>
              )}
            </Link>
            <div className="flex items-center gap-2.5 border-l border-slate-200 pl-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">{initials}</div>
              <div className="hidden text-xs leading-tight md:block">
                <p className="font-medium text-slate-800">{user?.email}</p>
                <p className="capitalize text-slate-500">{user?.role}</p>
              </div>
              <button onClick={signOut} title="Log out" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800">
                <Icon name="logout" className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar: pages of the current area + shared workspace */}
      <aside className="fixed bottom-0 left-0 top-14 z-20 flex w-60 flex-col border-r border-slate-200 bg-white">
        <div className="flex-1 overflow-y-auto px-3 py-5">
          <p className="eyebrow px-2.5">{current.label}</p>
          <p className="mb-2 px-2.5 text-xs text-slate-400">{current.hint}</p>
          <div className="space-y-0.5">
            {current.items.map((i) => <NavItem key={i.to} item={i} path={pathname} count={counts[i.badge]} />)}
          </div>
          <p className="eyebrow mb-2 mt-7 px-2.5">Workspace</p>
          <div className="space-y-0.5">
            {WORKSPACE.filter((i) => !i.adminOnly || user?.role === 'admin')
              .map((i) => <NavItem key={i.to} item={i} path={pathname} count={counts[i.badge]} />)}
          </div>
        </div>
        <div className="border-t border-slate-200 px-5 py-4 text-[11px] leading-relaxed text-slate-400">
          <p>The AI suggests, you decide.</p>
          <p>Developed by <span className="font-semibold text-slate-500">NGZ 40</span></p>
        </div>
      </aside>

      <main className="pl-60 pt-14">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
