import { describe, expect, it } from "vitest";

import { sortRequests } from "./sorting";
import type { FeatureRequest } from "./types";

function fr(id: number, vote_count: number, created_at: string): FeatureRequest {
  return {
    id,
    title: `t${id}`,
    description: "",
    author: "x",
    vote_count,
    has_voted: false,
    created_at,
  };
}

describe("sortRequests", () => {
  const a = fr(1, 5, "2026-07-17T10:00:00Z");
  const b = fr(2, 8, "2026-07-17T09:00:00Z");
  const c = fr(3, 8, "2026-07-17T11:00:00Z");

  it("top: votes desc, newer wins the tie", () => {
    expect(sortRequests([a, b, c], "top").map((r) => r.id)).toEqual([3, 2, 1]);
  });

  it("new: newest first, independent of votes", () => {
    expect(sortRequests([a, b, c], "new").map((r) => r.id)).toEqual([3, 1, 2]);
  });

  it("does not mutate the input array", () => {
    const input = [a, b, c];
    sortRequests(input, "top");
    expect(input.map((r) => r.id)).toEqual([1, 2, 3]);
  });
});
