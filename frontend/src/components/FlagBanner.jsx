/**
 * Security flag banner.
 */

export default function FlagBanner({ flags }) {
  if (!flags || flags.length === 0) return null

  return (
    <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
      <p className="text-sm font-semibold text-red-900 mb-2">Security Flags:</p>
      <ul className="list-disc list-inside text-sm text-red-800">
        {flags.map((flag, i) => (
          <li key={i}>{flag}</li>
        ))}
      </ul>
    </div>
  )
}
