/**
 * Main app router.
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import { AuthProvider, RequireAuth } from './auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Inbox from './pages/Inbox'
import Calendar from './pages/Calendar'
import Jobs from './pages/Jobs'
import JobCandidates from './pages/JobCandidates'
import Candidate from './pages/Candidate'
import Approvals from './pages/Approvals'
import Audit from './pages/Audit'
import Portal from './pages/Portal'
import Schedule from './pages/Schedule'

export default function App() {
  return (
    <Router>
      <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/portal/:token" element={<Portal />} />
        <Route path="/schedule/:token" element={<Schedule />} />

        {/* Protected routes with layout */}
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/agenda" element={<Calendar />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobCandidates />} />
          <Route path="/candidates/:id" element={<Candidate />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/audit" element={<Audit />} />
        </Route>
      </Routes>
      </AuthProvider>
    </Router>
  )
}
