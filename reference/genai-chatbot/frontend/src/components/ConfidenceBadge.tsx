type Props = { confidence: number }

export function ConfidenceBadge({ confidence }: Props) {
  const pct = Math.round(confidence * 100)
  const tone =
    confidence >= 0.85
      ? { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'High confidence' }
      : confidence >= 0.5
        ? { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Moderate' }
        : { bg: 'bg-red-100', text: 'text-red-800', label: 'Low confidence' }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${tone.bg} ${tone.text}`}
      title={`Validator confidence: ${pct}%`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {tone.label} · {pct}%
    </span>
  )
}
