import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createSession, streamMessage } from './api'
import { ClarificationChips } from './components/ClarificationChips'
import { ComposerInput } from './components/ComposerInput'
import { MessageBubble } from './components/MessageBubble'
import { ReadbackCard } from './components/ReadbackCard'
import type { ChatMessage, ClarificationOption } from './types'

type PendingInterrupt =
  | { kind: 'clarification'; question: string; options: ClarificationOption[]; round: number }
  | { kind: 'readback'; text: string }
  | null

function uid() {
  return Math.random().toString(36).slice(2, 10)
}

export default function App() {
  const [threadId, setThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState<PendingInterrupt>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [liveTrace, setLiveTrace] = useState<string[]>([])
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    createSession()
      .then(setThreadId)
      .catch((e) => setError(`Could not start session: ${(e as Error).message}`))
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pending, liveTrace])

  const send = useCallback(
    async (userInput: string | Record<string, unknown>, displayText?: string) => {
      if (!threadId) {
        setError('Session not ready yet.')
        return
      }
      setError(null)
      setBusy(true)
      setPending(null)
      setLiveTrace([])

      const visibleText =
        displayText !== undefined
          ? displayText
          : typeof userInput === 'string'
            ? userInput
            : JSON.stringify(userInput)

      setMessages((m) => [...m, { id: uid(), role: 'user', text: visibleText }])

      try {
        for await (const ev of streamMessage(threadId, userInput)) {
          if (ev.event === 'trace') {
            setLiveTrace((t) => [...t, `${ev.data.phase}: ${ev.data.text}`])
          } else if (ev.event === 'clarification') {
            setPending({
              kind: 'clarification',
              question: ev.data.question,
              options: ev.data.options ?? [],
              round: ev.data.round,
            })
          } else if (ev.event === 'readback') {
            setPending({ kind: 'readback', text: ev.data.readback })
          } else if (ev.event === 'final') {
            setMessages((m) => [
              ...m,
              {
                id: uid(),
                role: 'assistant',
                text: ev.data.answer,
                confidence: ev.data.confidence,
                evidence: ev.data.evidence,
                trace: ev.data.trace,
              },
            ])
            setLiveTrace([])
          } else if (ev.event === 'error') {
            setError(ev.data.message)
          }
        }
      } catch (err) {
        setError((err as Error).message)
      } finally {
        setBusy(false)
      }
    },
    [threadId],
  )

  const handleNewMessage = useCallback((text: string) => send(text), [send])

  const handleClarification = useCallback(
    (answer: string) => send(answer, `(clarification) ${answer}`),
    [send],
  )

  const handleReadbackApprove = useCallback(
    () => send({ approved: true }, '(approved read-back)'),
    [send],
  )

  const handleReadbackAdjust = useCallback(
    (adjustment: string) =>
      send({ approved: false, adjustment }, `(adjust) ${adjustment}`),
    [send],
  )

  const composerDisabled = busy || !!pending

  const examples = useMemo(
    () => [
      'How many employees are there in total?',
      'How many customers are in Tier 1?',
      'Top 5 Tier-1 APAC customers by ARR with their account managers.',
      "What's the maximum counter-offer percentage for retention?",
      'Which customers were affected by INC-2025-0847, and what did the board say?',
      'Show me the expensive vendors.',
    ],
    [],
  )

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">TechNova Chatbot</h1>
            <p className="text-xs text-slate-500">
              Hybrid agentic RAG + Text-to-SQL · 10 agents · local-only
            </p>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            session: {threadId ? threadId.slice(0, 8) : '…'}
          </span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {messages.length === 0 && !busy && (
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-2">Try an example</h2>
            <div className="flex flex-wrap gap-2">
              {examples.map((q) => (
                <button
                  key={q}
                  onClick={() => handleNewMessage(q)}
                  disabled={composerDisabled}
                  className="text-left text-xs px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {busy && (
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
              <span className="inline-block w-2 h-2 rounded-full bg-slate-400 animate-pulse" />
              Working…
            </div>
            {liveTrace.length > 0 ? (
              <ul className="text-xs font-mono text-slate-500 space-y-0.5">
                {liveTrace.slice(-6).map((l, i) => (
                  <li key={i}>· {l}</li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-slate-400 italic">
                Spinning up agents (first request also loads embedding + reranker models —
                can take up to 30s)…
              </div>
            )}
          </div>
        )}

        {pending?.kind === 'clarification' && (
          <ClarificationChips
            question={pending.question}
            options={pending.options}
            round={pending.round}
            onAnswer={handleClarification}
            disabled={busy}
          />
        )}

        {pending?.kind === 'readback' && (
          <ReadbackCard
            text={pending.text}
            onApprove={handleReadbackApprove}
            onAdjust={handleReadbackAdjust}
            disabled={busy}
          />
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-900 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}

        <div ref={endRef} />
      </main>

      <footer className="sticky bottom-0 bg-slate-100 border-t border-slate-200">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <ComposerInput
            onSubmit={handleNewMessage}
            disabled={composerDisabled}
            placeholder={
              pending
                ? 'Respond to the card above first…'
                : 'Ask about TechNova — structured data, policies, or both'
            }
          />
        </div>
      </footer>
    </div>
  )
}
