/**
 * Security flag banner.
 */

export default function FlagBanner({ flags }) {
  if (!flags || flags.length === 0) return null

  return (
    <div className="bg-rose-50 border border-rose-200 rounded-md p-4 mb-4">
      <p className="text-sm font-semibold text-rose-900 mb-2">Security Flags:</p>
      <ul className="list-disc list-inside text-sm text-rose-800">
        {flags.map((flag, i) => (
          <li key={i}>{flag}</li>
        ))}
      </ul>
    </div>
  )
}
