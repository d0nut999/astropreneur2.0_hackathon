/** Small date helpers (no library needed). */
export function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 60000
  if (diff < 1) return 'just now'
  if (diff < 60) return `${Math.round(diff)} min ago`
  if (diff < 60 * 24) return `${Math.round(diff / 60)} h ago`
  return new Date(iso).toLocaleDateString()
}

export function prettyDate(ymd) {
  if (!ymd) return 'No date'
  const d = new Date(`${ymd}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = Math.round((d - today) / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' })
}
