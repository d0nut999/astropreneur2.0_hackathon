/**
 * AI recommendation badge (Advance / Hold / Not recommended) or human decision.
 */
const STYLES = {
  Advance: 'bg-green-100 text-green-800 ring-green-300',
  Hold: 'bg-yellow-100 text-yellow-900 ring-yellow-300',
  'Not recommended': 'bg-red-100 text-red-800 ring-red-300',
  advance: 'bg-green-600 text-white ring-green-700',
  reject: 'bg-gray-700 text-white ring-gray-800',
}
const LABELS = { advance: 'Advanced by HR', reject: 'Rejected by HR' }

export default function RecommendationBadge({ value, large = false }) {
  if (!value) return null
  return (
    <span className={`inline-block rounded-full ring-1 font-semibold ${STYLES[value] || 'bg-gray-100'} ${
      large ? 'px-4 py-1.5 text-base' : 'px-2.5 py-0.5 text-xs'}`}>
      {LABELS[value] || value}
    </span>
  )
}
