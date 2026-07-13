# Fix: TechNova Chatbot frontend never shows a response

**Give this file to Claude Code (or any developer) along with the project. Follow it top to bottom.**

## Symptom

You open the chat UI at `http://localhost:8080`, type a query, see a "Working…" spinner
for a moment, then it disappears and **no answer ever appears**.

There are **two independent causes**. Fix both.

---

## Cause 1 — Frontend SSE parser bug (code fix, do this first)

The backend streams Server-Sent Events with **CRLF** (`\r\n\r\n`) line endings, but the
frontend splits the stream on `\n\n` (LF only). Because `\r\n\r\n` contains no `\n\n`
substring, the browser never detects an event boundary, so events are never rendered.

### Fix

Replace the **entire contents** of `frontend/src/api.ts` with the code below:

```ts
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
```

After saving, the Vite dev server hot-reloads automatically. **Hard-refresh the browser
tab** (`Ctrl + Shift + R`) so it loads the new bundle.

---

## Cause 2 — Invalid or missing OpenAI API key (config fix)

The pushed code does **not** contain an API key (it's intentionally excluded for security),
and any key that was shared earlier may be revoked. Every query fails silently at the first
LLM call with `HTTP 401 - Incorrect API key`. **Each user needs their own key.**

### Fix

1. Get a valid OpenAI API key that has access to the model in `.env`
   (`OPENAI_MODEL_NAME`, e.g. `gpt-5.4`). Get one at
   <https://platform.openai.com/api-keys>.

2. In the project root, create/edit the file named `.env` (copy from `.env.example` if it
   doesn't exist):

   ```
   OPENAI_API_KEY=sk-your-key-here   # [REDACTED during §4.6 triage — original doc embedded a live key; rotate it]
   OPENAI_MODEL_NAME=gpt-5.4
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   ```

3. **Force-recreate the backend so it re-reads `.env`.** A plain `restart` does NOT reload
   `.env` — you must recreate the container:

   ```bash
   docker compose up -d --force-recreate backend
   ```

> ⚠️ Never paste the key into any tracked file or commit it. `.env` is gitignored — keep it
> that way. Do not share your key in chat or push it.

---

## Verify it works

1. Backend healthy:
   ```bash
   curl http://localhost:8081/health
   # -> {"status":"ok","model":"gpt-5.4",...}
   ```

2. Key is valid (should print `OK`):
   ```bash
   docker compose exec -T backend python -c "from openai import OpenAI, os; \
   print(OpenAI(api_key=os.environ['OPENAI_API_KEY']).chat.completions.create(\
   model=os.environ['OPENAI_MODEL_NAME'], messages=[{'role':'user','content':'say OK'}], \
   max_completion_tokens=5).choices[0].message.content)"
   ```

3. In the browser (`http://localhost:8080`, hard-refreshed), type
   *"How many departments are there?"* You should see:
   - a **"Working…"** spinner with a live agent trace, then
   - a **read-back** or **clarification** card (click a chip / "Yes, run"), then
   - the **final answer** with a confidence badge.

## Expected timing (this is normal — it is NOT frozen)

- Simple queries: **~20–40 seconds**
- Complex multi-agent queries: **1–10 minutes** (the full 11-agent pipeline runs
  clarification → read-back → SQL/RAG → validation → completeness check).

The spinner + live trace means it is working. Give it time before assuming it hung.
