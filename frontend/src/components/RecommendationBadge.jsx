/**
 * AI recommendation badge (Advance / Hold / Not recommended) or human decision.
 */
const STYLES = {
  Advance: 'bg-emerald-100 text-emerald-800 ring-emerald-300',
  Hold: 'bg-amber-100 text-amber-900 ring-amber-300',
  'Not recommended': 'bg-rose-100 text-rose-800 ring-rose-300',
  advance: 'bg-emerald-600 text-white ring-emerald-700',
  reject: 'bg-slate-700 text-white ring-slate-800',
}
const LABELS = { advance: 'Advanced by HR', reject: 'Rejected by HR' }

export default function RecommendationBadge({ value, large = false }) {
  if (!value) return null
  return (
    <span className={`inline-block rounded-full ring-1 font-semibold ${STYLES[value] || 'bg-slate-100'} ${
      large ? 'px-4 py-1.5 text-base' : 'px-2.5 py-0.5 text-xs'}`}>
      {LABELS[value] || value}
    </span>
  )
}
