"""Anonymous voter identity, derived from a client-supplied browser fingerprint.

The frontend computes a stable FingerprintJS ``visitorId`` in the browser and
sends it on every request as the ``X-Visitor-Id`` header; that value becomes the
``voter_id`` used to enforce one-vote-per-voter and to block self-votes.

This identifier is **client-provided and therefore spoofable** — exactly as the
old signed cookie was. It's anti-abuse friction, not authentication: swap for
real auth if you need trust. We hash it server-side to a fixed-width, opaque
token (so we neither trust nor store the raw client string), but we do NOT sign
it. See README.
"""

from __future__ import annotations

import hashlib

from fastapi import HTTPException, Request, status

VISITOR_ID_HEADER = "X-Visitor-Id"


def get_voter_id(request: Request) -> str:
    """Resolve the voter identity from the X-Visitor-Id header.

    Returns a normalized 64-char hex token (sha256 of the raw fingerprint) — the
    stable interface consumed by the request handlers, and a clean fit for the
    ``String(64)`` identity columns. Raises 400 when the header is absent or
    empty: the frontend always sends it, so a missing value means a non-browser
    or misbehaving client, not a legitimate first visit.
    """
    raw = request.headers.get(VISITOR_ID_HEADER, "").strip()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing visitor identity")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
