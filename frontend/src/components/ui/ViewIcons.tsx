// V3 tab iconography (docs/frontend_overhaul.md V3 §2): one inline-SVG glyph
// per view, drawn on a shared 20×20 grid, stroke-only so the tab hue inks them.
import type { ViewId } from "../../state/console";

const STROKE = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

export function ViewIcon({ view, size = 15 }: { view: ViewId; size?: number }) {
  const body = GLYPHS[view];
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden>
      <g {...STROKE}>{body}</g>
    </svg>
  );
}

const GLYPHS: Record<ViewId, React.ReactNode> = {
  // command deck — radar crosshair with a contact
  overview: (
    <>
      <circle cx="10" cy="10" r="6.5" />
      <path d="M10 1.8v3M10 15.2v3M1.8 10h3M15.2 10h3" />
      <circle cx="12.6" cy="7.6" r="1.5" fill="currentColor" stroke="none" />
    </>
  ),
  // alert queue — ranked bars with a flagged head
  queue: (
    <>
      <path d="M4 5h9M4 10h12M4 15h7" />
      <circle cx="16.6" cy="5" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  // graph explorer — ego network
  explorer: (
    <>
      <circle cx="10" cy="10" r="2.2" />
      <circle cx="4" cy="5" r="1.5" />
      <circle cx="16" cy="4.6" r="1.5" />
      <circle cx="16.4" cy="15" r="1.5" />
      <circle cx="4.4" cy="15.4" r="1.5" />
      <path d="M8.4 8.6 5.2 6M11.7 8.5l3-2.7M11.8 11.4l3.3 2.6M8.3 11.5l-2.7 2.8" />
    </>
  ),
  // case detail — dossier with the seal
  case: (
    <>
      <path d="M6 2.8h6.4L16 6.4V17.2H6z" />
      <path d="M12.4 2.8v3.6H16" />
      <path d="M8.4 10h4.8M8.4 13h4.8" />
    </>
  ),
  // model lab — flask with a sample
  lab: (
    <>
      <path d="M8.2 2.8h3.6M9.4 2.8v4.2L4.6 15a2.4 2.4 0 0 0 2.1 3.6h6.6a2.4 2.4 0 0 0 2.1-3.6l-4.8-8V2.8" />
      <path d="M6.4 12.6h7.2" />
      <circle cx="11.4" cy="15.2" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  // about — the mission mark
  about: (
    <>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 9v4.6" />
      <circle cx="10" cy="6.2" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
};
