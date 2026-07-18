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
    if (reduced) {
      el.textContent = format(value);
      return;
    }
    const controls = animate(0, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        el.textContent = format(v);
      },
    });
    return () => controls.stop();
    // format is intentionally not a dependency: inline lambdas would restart
    // the animation every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration, reduced]);

  return <span ref={ref} className="tnum" />;
}
