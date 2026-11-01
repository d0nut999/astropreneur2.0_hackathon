/**
 * Audit log page.
 */
import { useEffect, useState } from 'react'
import { apiGet } from '../api'

export default function Audit() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiGet('/audit')
        setLogs(res.data)
      } catch (err) {
        if (err.response?.status === 403) setForbidden(true)
        else console.error('Failed to load audit logs:', err)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  if (loading) return <div className="text-center text-gray-500">Loading...</div>
  if (forbidden) {
    return (
      <div className="max-w-xl mx-auto bg-white rounded-lg shadow p-8 text-center">
        <p className="text-4xl mb-2">🔒</p>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Admins only</h1>
        <p className="text-gray-600">
          The audit log records every action, including yours. To keep it independent, only an administrator can read it.
          Your actions are still recorded.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Audit Log</h1>

      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Timestamp
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Actor
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Action
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Entity
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Hash
              </th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 text-sm">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm font-medium">{log.actor}</td>
                <td className="px-4 py-3 text-sm">{log.action}</td>
                <td className="px-4 py-3 text-sm">
                  {log.entity} (ID: {log.entity_id})
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 font-mono text-xs">
                  {log.payload_hash.substring(0, 12)}...
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logs.length === 0 && (
        <p className="text-gray-500 mt-4">No audit logs.</p>
      )}
    </div>
  )
}
