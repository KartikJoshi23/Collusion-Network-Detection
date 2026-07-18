import { describe, expect, it } from "vitest";
import { drainSseBuffer, parseSseBlock } from "./copilot";

describe("copilot SSE parser (the archive's CRLF fix)", () => {
  it("parses CRLF-framed blocks — the backend's actual framing", () => {
    const raw =
      'event: trace\r\ndata: {"step": "run_sql({})"}\r\n\r\n' +
      'event: final\r\ndata: {"answer": "ok", "ai_generated": true}\r\n\r\n';
    const { events, rest } = drainSseBuffer(raw);
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: "trace", data: { step: "run_sql({})" } });
    expect(events[1].event).toBe("final");
    expect(rest).toBe("");
  });

  it("parses LF framing identically", () => {
    const { events } = drainSseBuffer('event: trace\ndata: {"step": "x"}\n\n');
    expect(events).toHaveLength(1);
  });

  it("keeps an incomplete block in the buffer", () => {
    const { events, rest } = drainSseBuffer('event: trace\r\ndata: {"st');
    expect(events).toHaveLength(0);
    expect(rest).toContain('{"st');
  });

  it("joins multi-line data and ignores comment lines", () => {
    const ev = parseSseBlock(': keepalive\nevent: final\ndata: {"answer":\ndata:  "two lines"}');
    expect(ev?.event).toBe("final");
    expect((ev?.data as { answer: string }).answer).toBe("two lines");
  });

  it("drops malformed JSON instead of throwing", () => {
    expect(parseSseBlock("event: x\ndata: {nope")).toBeNull();
    expect(parseSseBlock(": only a comment")).toBeNull();
  });
});
