import type { SseEvent } from './types'

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8081'

export async function createSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/chat/session`, { method: 'POST' })
  if (!res.ok) throw new Error(`createSession HTTP ${res.status}`)
  const json = (await res.json()) as { thread_id: string }
  return json.thread_id
}

export async function* streamMessage(
  threadId: string,
  userInput: string | Record<string, unknown>,
): AsyncGenerator<SseEvent, void, void> {
  const res = await fetch(`${API_BASE}/api/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, user_input: userInput }),
  })
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(`streamMessage HTTP ${res.status} ${text}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Parse one SSE event block ("event: X\ndata: Y" possibly multi-line).
  function parseBlock(rawEvent: string): SseEvent | null {
    let eventName = 'message'
    let data = ''
    for (const line of rawEvent.split('\n')) {
      // SSE comment / keepalive line — ignore (starts with ':').
      if (line.startsWith(':')) continue
      if (line.startsWith('event:')) eventName = line.slice(6).trim()
      else if (line.startsWith('data:')) data += line.slice(5).replace(/^ /, '')
    }
    if (!data) return null
    try {
      const parsed = JSON.parse(data) as Record<string, unknown>
      return { event: eventName as SseEvent['event'], data: parsed as never }
    } catch (err) {
      console.warn('Failed to parse SSE data:', data, err)
      return null
    }
  }

  function drain(): SseEvent[] {
    // Normalise CRLF -> LF so both "\n\n" and "\r\n\r\n" boundaries work.
    buffer = buffer.replace(/\r\n/g, '\n')
    const events: SseEvent[] = []
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const parsed = parseBlock(rawEvent)
      if (parsed) events.push(parsed)
    }
    return events
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    for (const ev of drain()) yield ev
  }

  // Flush any trailing event that arrived without a final blank-line boundary.
  buffer += decoder.decode()
  buffer = buffer.replace(/\r\n/g, '\n')
  const tail = parseBlock(buffer.trim())
  if (tail) yield tail
}
