import { useState } from 'react'

type Props = { trace: string[] | undefined }

export function TraceTimeline({ trace }: Props) {
  const [open, setOpen] = useState(false)
  if (!trace || trace.length === 0) return null
  return (
    <div className="mt-2 border border-slate-200 rounded-lg">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 rounded-lg flex justify-between items-center"
      >
        <span>Agent trace · {trace.length} steps</span>
        <span className="text-[10px] text-slate-400">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <ol className="px-4 pb-2 text-[11px] text-slate-600 list-decimal list-inside space-y-0.5">
          {trace.map((t, i) => (
            <li key={i} className="font-mono">
              {t}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
