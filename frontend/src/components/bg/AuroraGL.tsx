// V3 depth layer (docs/frontend_overhaul.md V3 §1): a real fragment-shader
// aurora — three fbm-driven hue blobs, domain-reactive, bright enough to feed
// every glass blur above it. Raw WebGL2, zero dependencies.
//   - WebGL unavailable → render nothing (the CSS aurora in tokens.css remains
//     underneath as the designed fallback)
//   - prefers-reduced-motion → a single static frame, no rAF loop
//   - paused while the tab is hidden
//   - re-reads its hue uniforms when the domain toggle flips data-domain
//   - renders at reduced resolution (it sits behind blur — banding-dithered)
import { useEffect, useRef } from "react";

const VERT = `#version 300 es
precision highp float;
const vec2 POS[3] = vec2[3](vec2(-1.,-1.), vec2(3.,-1.), vec2(-1.,3.));
out vec2 vUv;
void main() {
  vec2 p = POS[gl_VertexID];
  vUv = p * 0.5 + 0.5;
  gl_Position = vec4(p, 0., 1.);
}`;

const FRAG = `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 outColor;
uniform float uTime;
uniform vec2 uRes;
uniform vec3 uHueA; // dominant
uniform vec3 uHueB;
uniform vec3 uHueC;

float hash(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), u.x),
             mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0., a = 0.55;
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p = p * 2.03 + vec2(11.7, 5.3);
    a *= 0.5;
  }
  return v;
}

// one drifting nebula lobe
float lobe(vec2 uv, vec2 center, float scale, float t, float seed) {
  vec2 q = (uv - center) * scale;
  float n = fbm(q * 2.6 + vec2(t * 0.55, -t * 0.35) + seed);
  float d = length(q) - n * 0.55;
  return smoothstep(0.75, -0.25, d);
}

void main() {
  vec2 uv = vUv;
  vec2 asp = vec2(uRes.x / uRes.y, 1.);
  vec2 p = uv * asp;
  float t = uTime * 0.03;

  vec2 cA = vec2(0.16 * asp.x + 0.05 * sin(t * 1.7), 0.98 + 0.06 * cos(t * 1.3));
  vec2 cB = vec2(0.92 * asp.x + 0.06 * cos(t * 1.1), 0.86 + 0.05 * sin(t * 1.9));
  vec2 cC = vec2(0.55 * asp.x + 0.08 * sin(t * 0.9), -0.08 + 0.05 * cos(t * 1.5));

  float a = lobe(p, cA, 1.35, t, 3.1);
  float b = lobe(p, cB, 1.45, t + 7., 9.4);
  float c = lobe(p, cC, 1.15, t + 3., 17.2);

  // additive nebula over the base surface color
  vec3 base = vec3(0.039, 0.055, 0.09); // --bg-0
  vec3 col = base;
  col += uHueA * a * 0.30;
  col += uHueB * b * 0.26;
  col += uHueC * c * 0.20;

  // faint large-scale luminance ripple so the field never reads flat
  col += vec3(0.5, 0.62, 0.85) * (fbm(p * 1.4 - t * 0.4) - 0.5) * 0.05;

  // vignette keeps edges quiet under the film grain
  float vig = smoothstep(1.45, 0.35, length(uv - 0.5) * 1.9);
  col = mix(base * 0.85, col, vig);

  // ordered-ish dither kills banding under the panel blur
  col += (hash(gl_FragCoord.xy) - 0.5) / 255.0;

  outColor = vec4(col, 1.0);
}`;

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "").trim();
  const v =
    h.length === 3
      ? h.split("").map((c) => parseInt(c + c, 16))
      : [
          parseInt(h.slice(0, 2), 16),
          parseInt(h.slice(2, 4), 16),
          parseInt(h.slice(4, 6), 16),
        ];
  return [v[0] / 255, v[1] / 255, v[2] / 255];
}

function readHues(): [number, number, number][] {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fb: string) => css.getPropertyValue(name).trim() || fb;
  // dominant accent leads; the other two families are ALWAYS present (V3 §5)
  return [
    hexToRgb(v("--accent", "#22d3ee")),
    hexToRgb(v("--accent-2", "#a78bfa")),
    hexToRgb(v("--hue-magenta", "#e879f9")),
  ];
}

export function AuroraGL() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: "low-power",
    });
    if (!gl) return; // CSS aurora fallback stays visible

    const compile = (type: number, src: string) => {
      const s = gl.createShader(type);
      if (!s) return null;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        // a driver that rejects the shader falls back to the CSS aurora
        gl.deleteShader(s);
        return null;
      }
      return s;
    };
    const vs = compile(gl.VERTEX_SHADER, VERT);
    const fs = compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return;
    const prog = gl.createProgram();
    if (!prog) return;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
    gl.useProgram(prog);

    const uTime = gl.getUniformLocation(prog, "uTime");
    const uRes = gl.getUniformLocation(prog, "uRes");
    const uHues = [
      gl.getUniformLocation(prog, "uHueA"),
      gl.getUniformLocation(prog, "uHueB"),
      gl.getUniformLocation(prog, "uHueC"),
    ];
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);

    const applyHues = () => {
      const hues = readHues();
      hues.forEach((h, i) => gl.uniform3f(uHues[i], h[0], h[1], h[2]));
    };

    // behind a 16px blur, half resolution is indistinguishable and cheap
    const RES_SCALE = 0.5;
    const resize = () => {
      canvas.width = Math.max(2, Math.round(window.innerWidth * RES_SCALE));
      canvas.height = Math.max(2, Math.round(window.innerHeight * RES_SCALE));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(uRes, canvas.width, canvas.height);
    };

    let raf = 0;
    const t0 = performance.now();
    const drawFrame = (now: number) => {
      gl.uniform1f(uTime, (now - t0) / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const frame = (now: number) => {
      drawFrame(now);
      raf = requestAnimationFrame(frame);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const applyMode = () => {
      stop();
      if (reduced.matches) drawFrame(performance.now());
      else raf = requestAnimationFrame(frame);
    };
    const onVisibility = () => {
      if (document.hidden) stop();
      else applyMode();
    };
    const observer = new MutationObserver(() => {
      applyHues();
      if (reduced.matches) drawFrame(performance.now());
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-domain"],
    });

    // A GPU reset would otherwise leave a permanently-black backdrop with the
    // CSS fallback retired — hand the stage back to the CSS aurora instead.
    const onContextLost = (e: Event) => {
      e.preventDefault();
      stop();
      document.documentElement.classList.remove("gl-aurora");
    };
    canvas.addEventListener("webglcontextlost", onContextLost);

    resize();
    applyHues();
    applyMode();
    // the shader replaces the CSS aurora — retire it so the two never stack
    // (tokens.css: :root.gl-aurora body::before)
    document.documentElement.classList.add("gl-aurora");
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    reduced.addEventListener("change", applyMode);

    return () => {
      stop();
      document.documentElement.classList.remove("gl-aurora");
      observer.disconnect();
      canvas.removeEventListener("webglcontextlost", onContextLost);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
      reduced.removeEventListener("change", applyMode);
      // NOTE: no loseContext() here — StrictMode re-runs this effect on the
      // same canvas, and a deliberately-lost context cannot be re-acquired,
      // which would kill the backdrop in dev. The context lives as long as
      // the canvas; the backdrop never unmounts in practice.
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0"
      style={{ zIndex: -11, width: "100vw", height: "100vh" }}
    />
  );
}
