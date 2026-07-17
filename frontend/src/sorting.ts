import type { FeatureRequest, SortMode } from "./types";

// Mirrors the backend ranking (see app/ranking.py) so a vote can reorder the
// list client-side without a round trip. gravity matches the server default.
const GRAVITY = 1.5;

function createdDesc(a: FeatureRequest, b: FeatureRequest): number {
  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
}

function trendingScore(r: FeatureRequest, now: number): number {
  const ageHours = (now - new Date(r.created_at).getTime()) / 3_600_000;
  const base = Math.max(ageHours + 2, 1); // clamp, mirroring the backend
  return r.vote_count / Math.pow(base, GRAVITY);
}

/** Return a new array sorted the way the backend would for the given mode. */
export function sortRequests(
  items: FeatureRequest[],
  sort: SortMode,
  now: number = Date.now(),
): FeatureRequest[] {
  const copy = [...items];
  if (sort === "new") {
    copy.sort((a, b) => createdDesc(a, b) || b.id - a.id);
  } else if (sort === "trending") {
    copy.sort(
      (a, b) => trendingScore(b, now) - trendingScore(a, now) || createdDesc(a, b) || b.id - a.id,
    );
  } else {
    // top
    copy.sort((a, b) => b.vote_count - a.vote_count || createdDesc(a, b) || b.id - a.id);
  }
  return copy;
}
