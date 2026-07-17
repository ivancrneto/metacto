# ADR-0004: Device-fingerprint identity

**Status:** Accepted — supersedes the *mechanism* of [ADR-0002](0002-auth-identity.md) (the DI seam it established is unchanged)
**Date:** 2026-07-17
**Deciders:** Engineering

## Context

[ADR-0002](0002-auth-identity.md) identified users by a self-chosen username
sent in `X-User`. That is trivial to game for the one product invariant that
matters here — **one vote per user**: a single person just types a different
name and votes again. We want *better uniqueness* without standing up real
accounts.

## Decision

Identify the user by a **device fingerprint** (FingerprintJS open-source
`visitorId`) instead of a typed name.

- The SPA resolves the `visitorId` once on load (`identity.ts`), and sends it in
  the **same `X-User` header** the seam already expects — so the **backend is
  unchanged**: the fingerprint is lowercased and passes the existing username
  validation, and becomes the user's identity key.
- There is no username input anymore; a readable display name is derived from
  the fingerprint (`anon-<6 chars>`).
- If fingerprinting is blocked or fails, we fall back to a random id persisted in
  `localStorage`, so the app still works (unique per browser).

## Options Considered

### Option A: Keep typed usernames (ADR-0002 status quo)
| Dimension | Assessment |
|-----------|------------|
| Uniqueness | Weak — rename and re-vote |
| Friction | Low |
| Privacy | None collected |

### Option B: Device fingerprint replaces the username (chosen)
| Dimension | Assessment |
|-----------|------------|
| Uniqueness | Better — tied to device/browser signals, not a free-text name |
| Friction | Zero (auto-identify) |
| Privacy | Fingerprinting is privacy-sensitive; must be disclosed in a real deployment |
| Cost | New client dep; no backend change |

### Option C: Fingerprint **and** username both required
| Dimension | Assessment |
|-----------|------------|
| Uniqueness | Strong, but two identity inputs to reconcile |
| Friction | Higher; more moving parts than this app needs |

## Trade-off Analysis

Option B raises the bar on multi-voting for effectively zero friction and no
backend change — the identity seam from ADR-0002 paid off exactly here. The
honest limitations, which is why this is a **deterrent, not a guarantee**:

- **Accuracy.** The open-source library (not Fingerprint Pro) is roughly
  ~40–60% accurate; fingerprints can **drift** (browser updates) or **collide**
  (identical devices), so the same person may occasionally get a new identity or
  two people may share one.
- **Trust boundary.** The server still trusts the header — a determined actor can
  forge or rotate it. Real anti-abuse needs server-side signals (IP/velocity),
  rate limiting, and ideally Fingerprint Pro or authenticated accounts.
- **Privacy.** Device fingerprinting is regulated in some jurisdictions and
  should be disclosed to users (and ideally consented) before shipping.

## Consequences

- **Easier:** discourages trivial ballot-stuffing; no login friction.
- **Harder / accepted:** privacy disclosure obligation; identity can drift;
  header remains forgeable (not a security boundary).
- **Revisit when:** abuse justifies it → Fingerprint Pro or real accounts,
  plus server-side rate limiting (see the README's Production Considerations).
