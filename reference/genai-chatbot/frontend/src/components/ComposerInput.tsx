import { useState, type KeyboardEvent } from 'react'

type Props = {
  onSubmit: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ComposerInput({ onSubmit, disabled, placeholder }: Props) {
  const [text, setText] = useState('')

  function send() {
    const trimmed = text.trim()
    if (!trimmed) return
    onSubmit(trimmed)
    setText('')
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex gap-2 border border-slate-300 bg-white rounded-2xl p-2 shadow-sm">
      <textarea
        value={text}
        disabled={disabled}
        rows={1}
        placeholder={placeholder ?? 'Ask about TechNova — e.g. "Top 5 Tier-1 APAC customers by ARR"'}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
        className="flex-1 resize-none px-2 py-1.5 text-sm outline-none disabled:opacity-50 min-h-[38px] max-h-40"
      />
      <button
        onClick={send}
        disabled={disabled || !text.trim()}
        className="px-4 py-1.5 rounded-xl bg-slate-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-slate-800"
      >
        Send
      </button>
    </div>
  )
}
