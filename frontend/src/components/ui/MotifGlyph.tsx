// One small SVG glyph per motif family (§5.3: motif chips on alert rows and
// the case dossier). Geometry is schematic — nodes and flows, not icons from
// a generic set — so the chips read as graph patterns. Stroke follows
// currentColor; size in px.
import { isMotifId, type MotifId } from "../../lib/motifs";

const S = 1.4; // stroke width

const GLYPHS: Record<MotifId, React.ReactNode> = {
  // three nodes on a ring, arrowed circulation
  cycle: (
    <>
      <circle cx="8" cy="3.2" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="3.4" cy="11" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="12.6" cy="11" r="1.6" fill="currentColor" stroke="none" />
      <path d="M6.6 4.4 4 9.4M4.9 12.2h6.2M12 9.6 9.4 4.5" />
      <path d="M10.2 3.6 9.4 4.5l1.2.5" fill="none" />
    </>
  ),
  // many sources converge on one sink
  fan_in: (
    <>
      <circle cx="3" cy="3" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="3" cy="8" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="3" cy="13" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="13" cy="8" r="1.9" fill="currentColor" stroke="none" />
      <path d="M4.4 3.6 11 7.2M4.6 8h6.2M4.4 12.4 11 8.8" />
    </>
  ),
  // one source sprays to many sinks
  fan_out: (
    <>
      <circle cx="3" cy="8" r="1.9" fill="currentColor" stroke="none" />
      <circle cx="13" cy="3" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="13" cy="8" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="13" cy="13" r="1.3" fill="currentColor" stroke="none" />
      <path d="M5 7.2 11.6 3.6M5.2 8h6.2M5 8.8l6.6 3.6" />
    </>
  ),
  // one controller above a row of controlled entities
  common_control: (
    <>
      <circle cx="8" cy="3" r="1.9" fill="currentColor" stroke="none" />
      <circle cx="3" cy="13" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="8" cy="13" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="13" cy="13" r="1.3" fill="currentColor" stroke="none" />
      <path d="M7 4.6 3.5 11.6M8 5.2v6.4M9 4.6l3.5 7" />
    </>
  ),
  // a chain, value entering one side and leaving the other
  pass_through: (
    <>
      <circle cx="2.6" cy="8" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="8" cy="8" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="13.4" cy="8" r="1.4" fill="currentColor" stroke="none" />
      <path d="M4.2 8h2.2M9.6 8h2.2" />
      <path d="M5.6 6.9 6.4 8l-.8 1.1M11 6.9l.8 1.1-.8 1.1" fill="none" />
    </>
  ),
  // winners taking turns around a ring
  rotation: (
    <>
      <path d="M8 2.8a5.2 5.2 0 1 1-5 4" fill="none" />
      <path d="M2.6 3.6l.4 3.2 3-1.2" fill="none" />
      <circle cx="8" cy="2.8" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="13.2" cy="8" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="8" cy="13.2" r="1.4" fill="currentColor" stroke="none" />
    </>
  ),
  // deliberately-high cover bids shielding a designated low winner
  cover_bid: (
    <>
      <path d="M3 13.5V6.5M8 13.5V3.5M13 13.5V5.5" />
      <circle cx="3" cy="13.5" r="1.6" fill="currentColor" stroke="none" />
      <path d="M1.5 15h13" />
    </>
  ),
  // a market split into exclusive territories
  partition: (
    <>
      <circle cx="8" cy="8" r="5.8" fill="none" />
      <path d="M8 2.2V8l4.6 3.4M8 8 3.4 11.4" />
      <circle cx="5.6" cy="5.6" r="1" fill="currentColor" stroke="none" />
      <circle cx="10.6" cy="5.8" r="1" fill="currentColor" stroke="none" />
      <circle cx="8" cy="11.6" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  // K4 — everyone linked to everyone
  clique: (
    <>
      <circle cx="3.4" cy="3.4" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12.6" cy="3.4" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="3.4" cy="12.6" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12.6" cy="12.6" r="1.4" fill="currentColor" stroke="none" />
      <path d="M3.4 3.4h9.2M3.4 12.6h9.2M3.4 3.4v9.2M12.6 3.4v9.2M3.4 3.4l9.2 9.2M12.6 3.4l-9.2 9.2" />
    </>
  ),
};

export function MotifGlyph({
  motif,
  size = 16,
  className,
}: {
  motif: string;
  size?: number;
  className?: string;
}) {
  if (!isMotifId(motif)) return null;
  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      className={className}
      stroke="currentColor"
      strokeWidth={S}
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
      aria-hidden
    >
      {GLYPHS[motif]}
    </svg>
  );
}
