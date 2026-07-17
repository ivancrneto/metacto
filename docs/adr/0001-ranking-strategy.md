# ADR-0001: Ranking strategy

**Status:** Accepted
**Date:** 2026-07-17
**Deciders:** Engineering

## Context

The board must rank requests by "popularity". The naive reading — order by raw
vote count — has a well-known failure mode on every feedback board: the earliest
requests accumulate votes forever and pin themselves to the top, so nothing new
is ever discovered. "Popularity" is really "popularity _right now_", which is a
function of both votes and age.

At the same time, a tuned decay formula as the _only_ ranking is confusing to a
first-time viewer ("why is the 8-vote item above the 10-vote one?").

## Decision

Offer three explicit, user-selectable sort modes, computed in SQL:

- **`top`** (default): `vote_count DESC, created_at DESC, id DESC` — the obvious,
  literal interpretation of "vote counts and ranking".
- **`new`**: `created_at DESC` — newest first.
- **`trending`**: time-decayed score `votes / (age_hours + 2) ^ gravity`
  (Reddit/HN-style), `gravity` configurable (default 1.5).

`id DESC` is always the final tiebreak so pagination is stable when other keys
collide.

## Options Considered

### Option A: Raw vote count only
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| UX | Familiar but stale — old items dominate |
| Signal | Doesn't show awareness of the recency problem |

### Option B: Trending/hotness only
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium (formula tuning) |
| UX | Confusing as the sole default (ordering not obviously tied to votes) |
| Risk | Bets the core UX on a tuned constant |

### Option C: Selectable modes — `top` default + `new` + `trending` (chosen)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| UX | Default is obvious; power modes are opt-in |
| Signal | Makes the recency trade-off _visible_ to the user instead of hiding it |

## Trade-off Analysis

Option C keeps the default dead-simple and correct while still demonstrating the
recency insight — and crucially it surfaces the trade-off as a UI control rather
than burying it in a formula. The cost is a little more query logic and a
`gravity` constant to reason about, which is well contained in `ranking.py`.

The `trending` formula uses Postgres time functions (`extract(epoch …)`,
`power`), so it is intentionally database-specific. That is an accepted
consequence of committing to Postgres (see ADR-0003).

## Consequences

- **Easier:** discovery of newer requests; explaining ranking to users.
- **Harder:** ranking is now Postgres-coupled; `gravity` needs occasional tuning.
- **Revisit when:** the list grows enough that `trending`'s per-row score
  computation over the full table needs a precomputed/materialized score column
  or a scheduled refresh.
