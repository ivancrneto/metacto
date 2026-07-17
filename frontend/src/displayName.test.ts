import { describe, expect, it } from "vitest";

import { displayName } from "./displayName";

describe("displayName", () => {
  it("humanizes a long fingerprint hash", () => {
    expect(displayName("a1b2c3d4e5f6a7b8c9")).toBe("anon-a1b2c3");
  });

  it("passes through short human handles", () => {
    expect(displayName("ada")).toBe("ada");
  });
});
