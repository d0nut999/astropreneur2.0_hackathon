/**
 * Main app router.
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Approvals from './pages/Approvals'
import Audit from './pages/Audit'
import Portal from './pages/Portal'

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/portal/:token" element={<Portal />} />

        {/* Protected routes with layout */}
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/audit" element={<Audit />} />
        </Route>
      </Routes>
    </Router>
  )
}
