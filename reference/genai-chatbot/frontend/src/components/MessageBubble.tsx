import type { ChatMessage } from '../types'
import { ConfidenceBadge } from './ConfidenceBadge'
import { EvidencePanel } from './EvidencePanel'
import { TraceTimeline } from './TraceTimeline'

type Props = { message: ChatMessage }

export function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl px-4 py-2 bg-slate-900 text-white rounded-2xl rounded-br-sm shadow-sm whitespace-pre-wrap">
          {message.text}
        </div>
      </div>
    )
  }

  if (message.role === 'system') {
    return (
      <div className="text-center text-xs text-slate-500 italic">{message.text}</div>
    )
  }

  // Assistant / final answer
  return (
    <div className="flex justify-start">
      <div className="max-w-2xl w-full px-4 py-3 bg-white border border-slate-200 rounded-2xl rounded-bl-sm shadow-sm">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-slate-700">TechNova Assistant</span>
          {message.confidence !== undefined && <ConfidenceBadge confidence={message.confidence} />}
        </div>
        <div className="text-sm text-slate-900 whitespace-pre-wrap leading-relaxed">
          {message.text}
        </div>
        <EvidencePanel evidence={message.evidence} />
        <TraceTimeline trace={message.trace} />
      </div>
    </div>
  )
}
