import { describe, expect, it } from "vitest";

import { timeAgo } from "./format";

describe("timeAgo", () => {
  const now = new Date("2026-07-17T12:00:00Z");

  it("shows 'just now' under a minute", () => {
    expect(timeAgo("2026-07-17T11:59:30Z", now)).toBe("just now");
  });

  it("shows minutes", () => {
    expect(timeAgo("2026-07-17T11:30:00Z", now)).toBe("30m ago");
  });

  it("shows hours", () => {
    expect(timeAgo("2026-07-17T09:00:00Z", now)).toBe("3h ago");
  });

  it("shows days", () => {
    expect(timeAgo("2026-07-15T12:00:00Z", now)).toBe("2d ago");
  });
});
