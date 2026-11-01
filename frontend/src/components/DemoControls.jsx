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
    <div className="mt-8 flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white/60 px-4 py-3 text-sm">
      <span className="eyebrow">Demo controls</span>
      {status && (
        <span className={`chip ${status.ai_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${status.ai_configured ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          {status.ai_configured ? `AI: ${status.ai_model} (${status.ai_provider})` : 'AI not configured: offline rules'}
        </span>
      )}
      <button onClick={testAi} disabled={!!busy} className="btn-secondary btn-sm">{busy === 'ai' ? 'Testing…' : 'Test AI connection'}</button>
      <button onClick={reset} disabled={!!busy} className={confirm ? 'btn btn-sm bg-rose-600 text-white hover:bg-rose-700' : 'btn-danger btn-sm'}>
        {busy === 'reset' ? 'Resetting & reloading emails…' : confirm ? 'Click again to confirm reset' : 'Reset demo'}
      </button>
      {confirm && <button onClick={() => setConfirm(false)} className="btn-ghost btn-sm">Cancel</button>}
      {msg && <span className={msg.ok ? 'text-emerald-700' : 'text-rose-700'}>{msg.text}</span>}
    </div>
  )
}
