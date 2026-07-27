// Count-up numerals for KPI first paint (§5.2 motion principles). Uses the
// imperative animate() so no re-renders happen per frame; collapses to a
// static value under prefers-reduced-motion.
import { animate, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

export function CountUp({
  value,
  format = (n: number) => Math.round(n).toLocaleString("en-US"),
  duration = 0.9,
}: {
  value: number;
  format?: (n: number) => string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Paint the true value FIRST, so the number is right even if nothing below
    // ever runs.
    el.textContent = format(value);
    if (reduced) return;

    const controls = animate(0, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        el.textContent = format(v);
      },
      onComplete: () => {
        el.textContent = format(value); // exact, never a rounded tween frame
      },
    });

    // Animation frames can stall — a background tab, a low-power mode, an
    // embedded browser view. Measured 2026-07-27: a stalled count-up left the
    // KPI reading 9 where the queue held 50, and 0 where two datasets were
    // loaded. A decorative tween must never be able to publish a WRONG number
    // in a screening console, so settle the true value unconditionally.
    const settle = window.setTimeout(
      () => {
        el.textContent = format(value);
      },
      duration * 1000 + 300,
    );

    return () => {
      controls.stop();
      window.clearTimeout(settle);
    };
    // format is intentionally not a dependency: inline lambdas would restart
    // the animation every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration, reduced]);

  // The true value is rendered in the markup, NOT only written by the
  // animation callback. If animate() never runs — a throttled background tab,
  // a low-power mode, a browser that suspends frames — an empty span left the
  // KPI showing no number at all. Painting the value first and animating over
  // it means the worst case is "the number did not count up", never "the
  // number is missing".
  return (
    <span ref={ref} className="tnum">
      {format(value)}
    </span>
  );
}
