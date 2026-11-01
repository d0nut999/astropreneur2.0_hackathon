/**
 * Evidence quote display (plain text only).
 */

export default function EvidenceQuote({ quote, criterion }) {
  return (
    <div className="bg-brand-50 border-l-4 border-brand-400 p-4 my-2">
      <p className="text-sm font-semibold text-brand-900 mb-1">{criterion}</p>
      <p className="text-sm text-brand-800 whitespace-pre-wrap">{quote}</p>
    </div>
  )
}
