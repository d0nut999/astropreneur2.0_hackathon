/**
 * Demo controls: AI status, connection test, full demo reset (two-step confirm, no browser popups).
 */
import { useEffect, useState } from 'react'
import { apiGet, apiPost } from '../api'

export default function DemoControls({ onReset }) {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [msg, setMsg] = useState(null)

  const loadStatus = () => apiGet('/system/status').then((r) => setStatus(r.data)).catch(() => {})
  useEffect(() => {
    loadStatus()
  }, [])

  const testAi = async () => {
    setBusy('ai')
    setMsg(null)
    try {
      const r = await apiPost('/system/test_ai')
      setMsg({ ok: r.data.ok, text: r.data.message })
    } finally {
      setBusy('')
    }
  }

  const reset = async () => {
    if (!confirm) return setConfirm(true)
    setConfirm(false)
    setBusy('reset')
    setMsg(null)
    try {
      const r = await apiPost('/system/reset_demo')
      setMsg({ ok: true, text: r.data.message })
      await loadStatus()
      onReset?.()
    } catch (err) {
      setMsg({ ok: false, text: err.response?.data?.detail || 'Reset failed' })
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="mt-8 bg-white rounded-lg shadow p-4 flex flex-wrap items-center gap-3 text-sm">
      <span className="font-semibold text-gray-700">Demo controls</span>
      {status && (
        <span className={`rounded-full px-3 py-1 ${status.ai_configured ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'}`}>
          {status.ai_configured ? `AI: ${status.ai_model} (${status.ai_provider})` : 'AI not configured: offline rules'}
        </span>
      )}
      <button onClick={testAi} disabled={!!busy} className="px-3 py-1.5 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50">
        {busy === 'ai' ? 'Testing…' : 'Test AI connection'}
      </button>
      <button onClick={reset} disabled={!!busy}
        className={`px-3 py-1.5 rounded disabled:opacity-50 ${confirm ? 'bg-red-600 text-white hover:bg-red-700' : 'border border-red-300 text-red-700 hover:bg-red-50'}`}>
        {busy === 'reset' ? 'Resetting & reloading emails…' : confirm ? 'Click again to confirm reset' : 'Reset demo'}
      </button>
      {confirm && <button onClick={() => setConfirm(false)} className="text-gray-500 hover:underline">cancel</button>}
      {msg && <span className={msg.ok ? 'text-green-700' : 'text-red-700'}>{msg.text}</span>}
    </div>
  )
}
