import { useState } from 'react'
import type { Evidence } from '../types'

type Props = { evidence: Evidence | undefined }

export function EvidencePanel({ evidence }: Props) {
  const [open, setOpen] = useState(false)
  if (!evidence) return null

  const hasAny =
    !!evidence.sql?.query ||
    (evidence.citations && evidence.citations.length > 0) ||
    (evidence.hybrid_sub_results && evidence.hybrid_sub_results.length > 0)
  if (!hasAny) return null

  return (
    <div className="mt-3 border border-slate-200 rounded-lg">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg flex justify-between items-center"
      >
        <span>Evidence</span>
        <span className="text-xs text-slate-500">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs space-y-3">
          {evidence.sql?.query && (
            <div>
              <div className="font-semibold text-slate-600 mb-1">Executed SQL</div>
              <pre className="bg-slate-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                {evidence.sql.query}
              </pre>
              {evidence.sql.rows_markdown && (
                <>
                  <div className="font-semibold text-slate-600 mt-2 mb-1">Rows</div>
                  <pre className="bg-slate-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                    {evidence.sql.rows_markdown}
                  </pre>
                </>
              )}
              {evidence.sql.error && (
                <div className="text-red-700 mt-1">Error: {evidence.sql.error}</div>
              )}
            </div>
          )}
          {evidence.citations && evidence.citations.length > 0 && (
            <div>
              <div className="font-semibold text-slate-600 mb-1">Cited chunks</div>
              <ul className="list-disc pl-5 text-slate-700">
                {evidence.citations.map((c) => (
                  <li key={c.chunk_id}>
                    <code className="text-xs">{c.chunk_id}</code>
                    {c.section_title ? ` — ${c.section_title}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
