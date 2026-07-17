# ADR-0002: Authentication & identity

**Status:** Accepted — the DI seam stands; the identity *mechanism* (typed username) is superseded by [ADR-0004](0004-device-fingerprint-identity.md)
**Date:** 2026-07-17
**Deciders:** Engineering

## Context

Two core requirements imply a notion of "who is acting":

1. **One vote per user per request.**
2. **You may only upvote requests submitted by _other_ users.**

Both need a stable identity. But full authentication (password hashing, email
verification, sessions/JWT, refresh tokens, reset flows) is a large piece of work
that would crowd out the domain logic this exercise is actually about — and it is
a solved, boilerplate problem. We need identity without building an auth system.

## Decision

Use a **pseudo-identity** seam: the client sends an `X-User` header; the server
normalizes/validates it and lazily creates the user on first sight. All
request-handling code depends only on two dependencies —
`get_current_user` (required) and `get_optional_user` (reads) — so the identity
mechanism is a **single swap point**.

Replacing this with real auth means reimplementing those two dependencies to
validate a session cookie or JWT and load the user; **no route, service, or model
changes.**

## Options Considered

### Option A: Full auth (password + JWT)
| Dimension | Assessment |
|-----------|------------|
| Complexity | High |
| Time cost | Dominates the budget |
| Value to this exercise | Low — it's boilerplate, not the domain |

### Option B: Signed session cookie (no passwords)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| Realism | Feels more real in a demo |
| Value | Still not the domain; middling cost/benefit |

### Option C: `X-User` pseudo-identity behind a DI seam (chosen)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Realism | Honestly labelled as a stand-in |
| Swap cost | One file (`deps.py`) |

## Trade-off Analysis

Option C spends the identity budget on the _seam_ (clean injection point,
validation, concurrent-first-request handling) rather than on auth mechanics.
The important production property — that identity is centralized and swappable —
is present and tested; the mechanism behind it is deliberately trivial and
documented as such.

## Consequences

- **Easier:** multi-user demos (`X-User: alice`); testing (headers, no token
  minting); a clean path to real auth.
- **Harder / accepted risk:** the demo trusts the header — it is **not** a
  security boundary and must not ship to production as-is.
- **Revisit when:** the app is exposed beyond a trusted demo → implement real
  auth inside `get_current_user` / `get_optional_user`; add rate limiting
  (see the README's Production Considerations).
