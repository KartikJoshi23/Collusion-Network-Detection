export type MessageRole = 'user' | 'assistant' | 'clarification' | 'readback' | 'system'

export type ClarificationOption = {
  label: string
  value: string
}

export type Evidence = {
  sql?: {
    query?: string | null
    rows_markdown?: string | null
    error?: string | null
  } | null
  citations?: { chunk_id: string; section_num?: number; section_title?: string }[] | null
  chunks_seen?: { chunk_id: string }[] | null
  hybrid_sub_results?: unknown[] | null
}

export type ChatMessage = {
  id: string
  role: MessageRole
  text: string
  // optional payload for special messages
  clarificationOptions?: ClarificationOption[]
  clarificationRound?: number
  readbackText?: string
  confidence?: number
  evidence?: Evidence
  trace?: string[]
}

export type SseEvent =
  | { event: 'trace'; data: { phase: string; text: string } }
  | { event: 'clarification'; data: { question: string; options: ClarificationOption[]; round: number } }
  | { event: 'readback'; data: { readback: string } }
  | { event: 'final'; data: { answer: string; confidence: number; evidence: Evidence; trace: string[] } }
  | { event: 'error'; data: { message: string } }
