import { useConsole } from "../../state/console";

const MIN = 10;
const MAX = 500;

// Budget k control (§5.3): adjusting it re-queries the alert queue and animates
// the precision readout. Range mirrors the API cap (1..500). The track fill
// tracks the value via the --fill custom property (styled in tokens.css).
export function BudgetSlider() {
  const budget = useConsole((s) => s.budget);
  const setBudget = useConsole((s) => s.setBudget);
  const fill = `${(100 * (budget - MIN)) / (MAX - MIN)}%`;
  return (
    <label className="flex items-center gap-2 text-xs text-text-1">
      <span className="text-text-2">budget k</span>
      <input
        type="range"
        min={MIN}
        max={MAX}
        step={5}
        value={budget}
        onChange={(e) => setBudget(Number(e.target.value))}
        className="budget w-40 cursor-pointer"
        style={{ "--fill": fill } as React.CSSProperties}
      />
      <span className="mono w-8 text-right text-text-0">{budget}</span>
    </label>
  );
}
