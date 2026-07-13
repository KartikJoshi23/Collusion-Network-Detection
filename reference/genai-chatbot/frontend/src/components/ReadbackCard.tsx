import { useState } from 'react'

type Props = {
  text: string
  onApprove: () => void
  onAdjust: (adjustment: string) => void
  disabled?: boolean
}

export function ReadbackCard({ text, onApprove, onAdjust, disabled }: Props) {
  const [editing, setEditing] = useState(false)
  const [adjustment, setAdjustment] = useState('')

  return (
    <div className="bg-sky-50 border border-sky-200 rounded-xl p-4 space-y-3">
      <h4 className="text-sm font-semibold text-sky-900">Read-back</h4>
      <p className="text-sm text-sky-950 whitespace-pre-wrap">{text}</p>

      {!editing ? (
        <div className="flex gap-2">
          <button
            disabled={disabled}
            onClick={onApprove}
            className="px-3 py-1.5 rounded-lg bg-sky-600 text-white text-sm disabled:opacity-50"
          >
            Yes, run
          </button>
          <button
            disabled={disabled}
            onClick={() => setEditing(true)}
            className="px-3 py-1.5 rounded-lg bg-white border border-sky-300 text-sm text-sky-900 hover:bg-sky-100 disabled:opacity-50"
          >
            Adjust
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={adjustment}
            onChange={(e) => setAdjustment(e.target.value)}
            disabled={disabled}
            placeholder="What should I change? e.g. 'Top 10 instead of 5, and include Churned accounts.'"
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-sky-300 text-sm bg-white"
          />
          <div className="flex gap-2">
            <button
              disabled={disabled || !adjustment.trim()}
              onClick={() => {
                onAdjust(adjustment.trim())
                setAdjustment('')
                setEditing(false)
              }}
              className="px-3 py-1.5 rounded-lg bg-sky-600 text-white text-sm disabled:opacity-50"
            >
              Submit correction
            </button>
            <button
              disabled={disabled}
              onClick={() => {
                setEditing(false)
                setAdjustment('')
              }}
              className="px-3 py-1.5 rounded-lg bg-white border border-sky-300 text-sm text-sky-900"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
