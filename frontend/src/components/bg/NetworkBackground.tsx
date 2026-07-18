// Live animated backdrop (overhaul brief §3): a drifting network of nodes and
// proximity edges with occasional coral "flagged" pulses travelling along
// edges — the project's subject matter as ambience. Constraints honored:
//   - prefers-reduced-motion → a single static frame, no rAF loop
//   - node count capped by viewport area (perf budget §9.2)
//   - paused while the tab is hidden
//   - recolors live when the domain toggle flips data-domain on <html>
import { useEffect, useRef } from "react";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

interface Pulse {
  a: number; // node indices
  b: number;
  t: number; // 0..1 along the edge
  speed: number;
}

const LINK_DIST = 150;
const MAX_NODES = 80;
const MAX_PULSES = 4;
const PULSE_EVERY_MS = 1400;

function accentColor(): string {
  return (
    getComputedStyle(document.documentElement)
      .getPropertyValue("--accent")
      .trim() || "#2dd4bf"
  );
}

export function NetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;
    let last = performance.now();
    let sinceSpawn = 0;
    let accent = accentColor();
    const coral = "#ff5a5f";
    const nodes: Node[] = [];
    const pulses: Pulse[] = [];
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    };

    const seed = () => {
      const target = Math.min(MAX_NODES, Math.floor((w * h) / 24000));
      nodes.length = 0;
      pulses.length = 0;
      for (let i = 0; i < target; i++) {
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 14, // px/s — a slow drift
          vy: (Math.random() - 0.5) * 14,
          r: 1 + Math.random() * 1.8,
        });
      }
    };

    const links = (): [number, number, number][] => {
      const out: [number, number, number][] = [];
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const d2 = dx * dx + dy * dy;
          if (d2 < LINK_DIST * LINK_DIST) out.push([i, j, Math.sqrt(d2)]);
        }
      }
      return out;
    };

    const draw = (dt: number) => {
      ctx.clearRect(0, 0, w, h);
      const edges = links();

      // edges — hairline strokes fading with distance
      for (const [i, j, d] of edges) {
        const alpha = 0.16 * (1 - d / LINK_DIST);
        ctx.strokeStyle = accent;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }

      // nodes
      for (const n of nodes) {
        ctx.globalAlpha = 0.4;
        ctx.fillStyle = accent;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // flagged pulses — coral dots travelling along a live edge
      for (let p = pulses.length - 1; p >= 0; p--) {
        const pulse = pulses[p];
        pulse.t += pulse.speed * dt;
        if (pulse.t >= 1) {
          pulses.splice(p, 1);
          continue;
        }
        const a = nodes[pulse.a];
        const b = nodes[pulse.b];
        const x = a.x + (b.x - a.x) * pulse.t;
        const y = a.y + (b.y - a.y) * pulse.t;
        ctx.globalAlpha = 0.5;
        ctx.strokeStyle = coral;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        const glow = ctx.createRadialGradient(x, y, 0, x, y, 9);
        glow.addColorStop(0, coral);
        glow.addColorStop(1, "transparent");
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, 9, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // spawn the next pulse on a random current edge
      sinceSpawn += dt * 1000;
      if (sinceSpawn > PULSE_EVERY_MS && pulses.length < MAX_PULSES && edges.length > 0) {
        sinceSpawn = 0;
        const [i, j] = edges[Math.floor(Math.random() * edges.length)];
        pulses.push({ a: i, b: j, t: 0, speed: 0.5 + Math.random() * 0.4 });
      }
    };

    const physics = (dt: number) => {
      for (const n of nodes) {
        n.x += n.vx * dt;
        n.y += n.vy * dt;
        if (n.x < -20) n.x = w + 20;
        if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h + 20;
        if (n.y > h + 20) n.y = -20;
      }
    };

    const frame = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      physics(dt);
      draw(dt);
      raf = requestAnimationFrame(frame);
    };

    const start = () => {
      if (raf) return;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };

    const applyMode = () => {
      if (reduced.matches) {
        stop();
        draw(0); // one static frame
      } else {
        start();
      }
    };

    const onVisibility = () => {
      if (document.hidden) stop();
      else applyMode();
    };

    // domain toggle flips data-domain on <html>; re-read the accent token
    const observer = new MutationObserver(() => {
      accent = accentColor();
      if (reduced.matches) draw(0);
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-domain"],
    });

    resize();
    applyMode();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    reduced.addEventListener("change", applyMode);

    return () => {
      stop();
      observer.disconnect();
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
      reduced.removeEventListener("change", applyMode);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10"
      style={{ opacity: 0.55 }}
    />
  );
}
