// Designed loading / error / empty states (§5.1: first-class UI, never blank).
import type { ReactNode } from "react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-32 items-center justify-center gap-3 text-text-2">
      <span
        className="inline-block h-3 w-3 animate-pulse rounded-full"
        style={{ background: "var(--accent)" }}
      />
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
    <div className="flex h-full min-h-32 flex-col items-center justify-center gap-1 p-6 text-center">
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
      <div className="text-sm text-text-1">{title}</div>
      {hint && <div className="max-w-md text-xs text-text-2">{hint}</div>}
      {children}
    </div>
  );
}
