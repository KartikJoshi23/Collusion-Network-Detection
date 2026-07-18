// Copilot client (§4.6 / §5.3 view 7). The SSE parser is the archive's FIXED
// implementation (reference/genai-chatbot + FIX_FRONTEND.md): CRLF→LF
// normalisation before splitting event blocks — the backend deliberately
// frames with CRLF so the fix stays exercised end-to-end. Parsing helpers are
// pure and unit-tested (lib-style, no fetch inside).

export interface CopilotEvidence {
  tool: string;
  args: string;
  result: string;
}

export interface CopilotPayload {
  answer: string;
  confidence: number;
  numbers_grounded: boolean;
  corpus_grounded: boolean;
  /** the guard's rewritten-phrase list (measured live: a string array) */
  guard_rewrites: string[];
  evidence: CopilotEvidence[];
  trace: string[];
  model: string;
  caveat: string;
  ai_generated: boolean;
}

export type CopilotEvent =
  | { event: "trace"; data: { step: string } }
  | { event: "final"; data: CopilotPayload }
  | { event: "error"; data: { detail: string } };

export interface CopilotHealth {
  configured: boolean;
  provider: string;
  model: string;
  caveat: string;
}

/** Parse one SSE block ("event: X\ndata: Y", possibly multi-line data). */
export function parseSseBlock(rawEvent: string): CopilotEvent | null {
  let eventName = "message";
  let data = "";
  for (const line of rawEvent.split("\n")) {
    if (line.startsWith(":")) continue; // comment / keepalive
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).replace(/^ /, "");
  }
  if (!data) return null;
  try {
    return { event: eventName, data: JSON.parse(data) } as CopilotEvent;
  } catch {
    return null;
  }
}

/** Drain complete event blocks from a buffer; returns events + the remainder.
    Normalises CRLF→LF so both "\n\n" and "\r\n\r\n" boundaries work (the fix). */
export function drainSseBuffer(buffer: string): {
  events: CopilotEvent[];
  rest: string;
} {
  let rest = buffer.replace(/\r\n/g, "\n");
  const events: CopilotEvent[] = [];
  let idx: number;
  while ((idx = rest.indexOf("\n\n")) !== -1) {
    const parsed = parseSseBlock(rest.slice(0, idx));
    rest = rest.slice(idx + 2);
    if (parsed) events.push(parsed);
  }
  return { events, rest };
}

export async function copilotHealth(): Promise<CopilotHealth> {
  const res = await fetch("/api/v1/copilot/health");
  if (!res.ok) throw new Error(`health HTTP ${res.status}`);
  return (await res.json()) as CopilotHealth;
}

export async function* streamChat(
  question: string,
  contextAlertId?: string,
): AsyncGenerator<CopilotEvent, void, void> {
  const res = await fetch("/api/v1/copilot/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      context_alert_id: contextAlertId ?? null,
    }),
  });
  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = drainSseBuffer(buffer);
    buffer = rest;
    for (const ev of events) yield ev;
  }
  // flush a trailing event that arrived without a final blank-line boundary
  buffer += decoder.decode();
  const tail = parseSseBlock(buffer.replace(/\r\n/g, "\n").trim());
  if (tail) yield tail;
}
