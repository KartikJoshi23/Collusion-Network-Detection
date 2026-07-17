import { useConsole } from "../state/console";
import { Empty } from "../components/ui/States";

// Views are filled in Week 8B; the router + placeholders keep the shell
// buildable and navigable now (Week 8A scaffold).
export function ViewRouter() {
  const view = useConsole((s) => s.view);
  const dataset = useConsole((s) => s.dataset);

  const soon = (title: string) => (
    <Empty
      title={title}
      hint={`Wired to ${dataset ?? "—"}. This view lands in Week 8B (§7 step 24).`}
    />
  );

  switch (view) {
    case "overview":
      return soon("Overview / Command deck");
    case "queue":
      return soon("Alert Queue");
    case "explorer":
      return soon("Graph Explorer");
    case "case":
      return soon("Case Detail");
    case "lab":
      return soon("Model Lab");
  }
}
