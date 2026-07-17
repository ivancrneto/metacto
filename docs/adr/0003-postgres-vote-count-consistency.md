# ADR-0003: Postgres & vote-count consistency

**Status:** Accepted
**Date:** 2026-07-17
**Deciders:** Engineering

## Context

Ranking reads dominate this workload — every page load sorts by vote count.
Meanwhile the central correctness requirement is **one vote per user per
request**, which must hold even under concurrent requests. We need both fast
reads and a tally that can never drift or be double-counted.

## Decision

**Postgres**, with:

1. **A `votes` row per vote** plus a **`UNIQUE(user_id, request_id)`** constraint.
   Double-voting is impossible at the database level — a second insert raises an
   `IntegrityError` regardless of timing — so integrity does not depend on
   application-level checks winning a race.
2. **A denormalized `feature_requests.vote_count`**, updated with an **atomic
   `SET vote_count = vote_count ± 1`** inside the **same transaction** as the
   vote insert/delete. Ranking reads a single indexed column instead of a
   `COUNT(*)` join, and the counter can never diverge from the row count because
   both mutations commit or roll back together.

Postgres also underpins the `trending` SQL in ADR-0001.

## Options Considered

### Option A: Derive count on read — `COUNT(*)` / join
| Dimension | Assessment |
|-----------|------------|
| Correctness | Always exact (single source of truth) |
| Read cost | Aggregation/join on every list request |
| Verdict | Correct but pays on the hot path |

### Option B: Denormalized counter, atomic in-transaction update (chosen)
| Dimension | Assessment |
|-----------|------------|
| Correctness | Exact — counter and rows commit atomically |
| Read cost | Single indexed column read |
| Cost | Must be disciplined: never mutate votes without the paired update |

### Option C: Trigger-maintained counter
| Dimension | Assessment |
|-----------|------------|
| Correctness | Strong (DB-enforced) |
| Cost | Logic hidden in DB triggers; harder to test in the app suite |
| Verdict | Good at larger scale; heavier than needed here |

## Trade-off Analysis

Option B keeps the fast-read benefit of a cached counter while eliminating the
usual downside (drift) by binding the counter mutation to the vote mutation in
one transaction. The `UNIQUE` constraint is what makes the whole thing safe under
concurrency — the atomic `± 1` handles the tally, the constraint handles
identity. The discipline required (always pair the two writes) is localized to
two functions in `services.py` and is covered by a concurrent-vote test.

## Consequences

- **Easier:** ranking queries; reasoning about correctness (DB enforces the
  invariant).
- **Harder / accepted:** all vote mutations must go through `services.py`; ad-hoc
  writes could desync the counter. Ranking is Postgres-specific.
- **Revisit when:** write volume is high enough that the per-row counter update
  becomes a contention point → consider a trigger (Option C), sharded counters,
  or an async projection.
