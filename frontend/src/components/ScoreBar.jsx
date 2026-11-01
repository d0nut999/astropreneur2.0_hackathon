/**
 * Horizontal score bar (0-100 or 0-5).
 */
export default function ScoreBar({ value, max = 100, small = false }) {
  if (value === null || value === undefined) return <span className="text-slate-400 text-sm">not scored</span>
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 45 ? 'bg-amber-500' : 'bg-rose-400'
  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 bg-slate-100 rounded-full overflow-hidden ${small ? 'h-1.5' : 'h-2.5'}`}>
        <div className={`${color} h-full rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      {!small && (
        <span className="text-sm font-semibold w-12 text-right">
          {Math.round(value)}
          <span className="text-slate-400 font-normal">/{max}</span>
        </span>
      )}
    </div>
  )
}
