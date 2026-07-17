import { useConsole } from "../state/console";
import { AlertQueue } from "../views/alert-queue/AlertQueue";
import { CaseDetail } from "../views/case-detail/CaseDetail";
import { GraphExplorer } from "../views/graph-explorer/GraphExplorer";
import { ModelLab } from "../views/model-lab/ModelLab";
import { Overview } from "../views/overview/Overview";

export function ViewRouter() {
  const view = useConsole((s) => s.view);
  switch (view) {
    case "overview":
      return <Overview />;
    case "queue":
      return <AlertQueue />;
    case "explorer":
      return <GraphExplorer />;
    case "case":
      return <CaseDetail />;
    case "lab":
      return <ModelLab />;
  }
}
