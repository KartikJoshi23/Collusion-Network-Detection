import { AnimatePresence, motion } from "motion/react";
import { lazy, Suspense } from "react";
import { Loading } from "../components/ui/States";
import { useConsole } from "../state/console";
import { AlertQueue } from "../views/alert-queue/AlertQueue";
import { CaseDetail } from "../views/case-detail/CaseDetail";
import { GraphExplorer } from "../views/graph-explorer/GraphExplorer";
import { ModelLab } from "../views/model-lab/ModelLab";
import { Overview } from "../views/overview/Overview";

// The About story is ScrollTrigger-heavy and rarely the first view — split it
// out of the main chunk.
const About = lazy(() =>
  import("../views/about/About").then((m) => ({ default: m.About })),
);

function content(view: string) {
  switch (view) {
    case "overview":
      return <Overview />;
    case "queue":
      return <AlertQueue />;
    case "explorer":
      return <GraphExplorer />;
    case "case":
      return <CaseDetail />;
    case "about":
      return (
        <Suspense fallback={<Loading label="Loading methodology…" />}>
          <About />
        </Suspense>
      );
    default:
      return <ModelLab />;
  }
}

// View switches animate (§5.2: animation communicates state) — a short
// rise+fade via Motion; MotionConfig reducedMotion="user" collapses it.
export function ViewRouter() {
  const view = useConsole((s) => s.view);
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={view}
        className="h-full min-h-0"
        initial={{ opacity: 0, y: 12, scale: 0.995 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.995 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      >
        {content(view)}
      </motion.div>
    </AnimatePresence>
  );
}
