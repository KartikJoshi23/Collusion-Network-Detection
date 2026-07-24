import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { CHART_SERIES, MOTIF_HUE, STATUS, UI_HUES } from "./palette";
import { MOTIF_TYPES } from "./motifs";

describe("V2 palette system", () => {
  it("assigns a fixed hue to every motif family", () => {
    for (const m of MOTIF_TYPES) {
      expect(MOTIF_HUE[m], m).toBeTruthy();
    }
  });

  it("keeps coral exclusive to flagged status — never a series color", () => {
    expect(STATUS.flagged).toBe(UI_HUES.coral);
    expect(CHART_SERIES).not.toContain(UI_HUES.coral);
    expect(Object.values(MOTIF_HUE)).not.toContain(UI_HUES.coral);
  });

  it("has five fixed-order categorical series", () => {
    expect(CHART_SERIES).toHaveLength(5);
    expect(new Set(CHART_SERIES).size).toBe(5);
  });
});

describe("V4 neutral-chrome theme", () => {
  // vitest runs from frontend/ (import.meta.url is not a file: URL here)
  const tokens = readFileSync(resolve("src/styles/tokens.css"), "utf-8");
  const token = (name: string): string => {
    const m = tokens.match(new RegExp(`\\s${name}:\\s*(#[0-9a-fA-F]{6});`));
    if (!m) throw new Error(`token ${name} not found in tokens.css`);
    return m[1];
  };
  const rgb = (hex: string): [number, number, number] => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
  /** Channel spread — 0 is perfectly achromatic. A blue cast shows up as a
      large B−R gap (V3's --bg-3 #1c2440 spread 36, blue-dominant). */
  const spread = (hex: string): number => {
    const c = rgb(hex);
    return Math.max(...c) - Math.min(...c);
  };

  it("keeps every surface and text token achromatic — no blue cast", () => {
    for (const name of [
      "--bg-0",
      "--bg-1",
      "--bg-2",
      "--bg-3",
      "--hairline",
      "--text-0",
      "--text-1",
      "--text-2",
    ]) {
      expect(spread(token(name)), `${name} must be neutral`).toBeLessThanOrEqual(8);
    }
  });

  it("keeps --bg-0 a true near-black ground", () => {
    const [r, g, b] = rgb(token("--bg-0"));
    expect(Math.max(r, g, b)).toBeLessThanOrEqual(16);
  });

  it("keeps CHART_SERIES in sync with the --chart-* tokens", () => {
    const fromCss = [1, 2, 3, 4, 5].map((i) => token(`--chart-${i}`));
    expect(fromCss).toEqual([...CHART_SERIES]);
  });

  it("clears contrast floors against the bare --bg-0 ground", () => {
    const lum = (hex: string): number => {
      const ch = rgb(hex).map((v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
    };
    const ratio = (a: string, b: string): number => {
      const [l1, l2] = [lum(a), lum(b)];
      return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    };
    const ground = token("--bg-0");
    // body + secondary text must clear AA for normal text
    for (const t of ["--text-0", "--text-1", "--text-2"]) {
      expect(ratio(token(t), ground), `${t} on --bg-0`).toBeGreaterThanOrEqual(4.5);
    }
    // chart ink must clear the 3:1 non-text floor
    for (const i of [1, 2, 3, 4, 5]) {
      expect(
        ratio(token(`--chart-${i}`), ground),
        `--chart-${i} on --bg-0`,
      ).toBeGreaterThanOrEqual(3);
    }
  });
});
