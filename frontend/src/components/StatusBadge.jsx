/**
 * Status badge component.
 */

const statusColors = {
  RECEIVED: 'bg-blue-100 text-blue-800',
  SCREENED: 'bg-green-100 text-green-800',
  SCORED: 'bg-purple-100 text-purple-800',
  SHORTLISTED: 'bg-yellow-100 text-yellow-800',
  INVITED: 'bg-indigo-100 text-indigo-800',
  VIDEO_SUBMITTED: 'bg-cyan-100 text-cyan-800',
  EVALUATED: 'bg-orange-100 text-orange-800',
  DECIDED: 'bg-gray-100 text-gray-800',
  QUARANTINED: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  sent: 'bg-blue-100 text-blue-800',
}

export default function StatusBadge({ status }) {
  const color = statusColors[status] || 'bg-gray-100 text-gray-800'
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${color}`}>
      {status}
    </span>
  )
}
