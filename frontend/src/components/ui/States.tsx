// Designed loading / error / empty states (§5.1: first-class UI, never blank).
import type { ReactNode } from "react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-32 flex-col items-center justify-center gap-3 text-text-2">
      <span className="radar" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({
  message,
  detail,
}: {
  message: string;
  detail?: string;
}) {
  return (
    <div className="flex h-full min-h-32 flex-col items-center justify-center gap-2 p-6 text-center">
      <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden>
        <path
          d="M12 3 22 20H2L12 3Z"
          fill="none"
          stroke="var(--risk-high)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path d="M12 10v4.5" stroke="var(--risk-high)" strokeWidth="1.5" />
        <circle cx="12" cy="17" r="0.9" fill="var(--risk-high)" />
      </svg>
      <div className="text-sm font-medium text-risk-high">{message}</div>
      {detail && <div className="mono text-xs text-text-2">{detail}</div>}
    </div>
  );
}

export function Empty({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex h-full min-h-32 flex-col items-center justify-center gap-2 p-6 text-center">
      <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden opacity="0.5">
        <g fill="none" stroke="var(--text-2)" strokeWidth="1.4" strokeDasharray="2.5 3">
          <circle cx="8" cy="24" r="3" />
          <circle cx="16" cy="8" r="3" />
          <circle cx="25" cy="21" r="3" />
          <path d="M10 21.5 14.4 10.6M18.6 10 23.4 18.6M11 24.5 22 21.8" />
        </g>
      </svg>
      <div className="text-sm text-text-1">{title}</div>
      {hint && <div className="max-w-md text-xs text-text-2">{hint}</div>}
      {children}
    </div>
  );
}
