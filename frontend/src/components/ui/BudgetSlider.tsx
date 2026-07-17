import { useConsole } from "../../state/console";

// Budget k control (§5.3): adjusting it re-queries the alert queue and animates
// the precision readout. Range mirrors the API cap (1..500).
export function BudgetSlider() {
  const budget = useConsole((s) => s.budget);
  const setBudget = useConsole((s) => s.setBudget);
  return (
    <label className="flex items-center gap-2 text-xs text-text-1">
      <span className="text-text-2">budget k</span>
      <input
        type="range"
        min={10}
        max={500}
        step={5}
        value={budget}
        onChange={(e) => setBudget(Number(e.target.value))}
        className="h-1 w-40 cursor-pointer appearance-none rounded-full bg-bg-3 accent-[var(--accent)]"
      />
      <span className="mono w-8 text-right text-text-0">{budget}</span>
    </label>
  );
}
