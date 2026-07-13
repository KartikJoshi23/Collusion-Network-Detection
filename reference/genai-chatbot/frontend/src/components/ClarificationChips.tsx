import { useState } from 'react'
import type { ClarificationOption } from '../types'

type Props = {
  question: string
  options: ClarificationOption[]
  round: number
  onAnswer: (answer: string) => void
  disabled?: boolean
}

export function ClarificationChips({ question, options, round, onAnswer, disabled }: Props) {
  const [freeText, setFreeText] = useState('')

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-indigo-900">Quick clarification</h4>
        <span className="text-xs text-indigo-700">round {round} / 3</span>
      </div>
      <p className="text-sm text-indigo-950">{question}</p>

      {options.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {options.map((opt) => (
            <button
              key={opt.value}
              disabled={disabled}
              onClick={() => onAnswer(opt.label)}
              className="px-3 py-1.5 rounded-full bg-white border border-indigo-300 text-sm text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          disabled={disabled}
          placeholder="Or type your own…"
          className="flex-1 px-3 py-1.5 rounded-lg border border-indigo-300 text-sm bg-white"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && freeText.trim()) {
              onAnswer(freeText.trim())
              setFreeText('')
            }
          }}
        />
        <button
          disabled={disabled || !freeText.trim()}
          onClick={() => {
            onAnswer(freeText.trim())
            setFreeText('')
          }}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}
