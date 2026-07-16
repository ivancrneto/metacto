# Feature Request Board

Submit feature requests, browse them, and upvote the ones you want most. Requests
are ranked by popularity. Built as a **modular monolith**: a FastAPI backend with a
framework-free domain core, a React (Vite + TypeScript) frontend, served same-origin
in production.

> Scoped as a ~2-hour take-home. The guiding principle: build a tight vertical slice
> _well_, keep the interesting logic (voting integrity, ranking) clean and tested, and
> be explicit about what was intentionally deferred. See
> [Design decisions](#design-decisions--trade-offs) and [What I'd do next](#what-id-do-next-at-scale).

---

## Features

**Core**
- Submit a feature request (title + description)
- Browse all requests
- Upvote requests from other users
- Vote counts and popularity ranking

**Added for a more production-like product**
- **Vote integrity** — one vote per person per request, enforced by a DB unique
  constraint; anonymous identity via a client-side [FingerprintJS](https://github.com/fingerprintjs/fingerprintjs)
  browser fingerprint. Self-votes are blocked.
- **Idempotent voting** — upvote/un-vote toggle that's safe to retry and survives the
  concurrent-vote race.
- **Two ranking modes** — `Top` (by votes, with a stable tie-break) and `New`.
- **Input validation** — length limits + whitespace handling at the API edge.
- **Polished UI** — optimistic voting with rollback, loading skeletons, empty and error
  states, live character counters, light/dark themes.
- **Tooling** — `uv`, Ruff (lint + format), mypy (strict), pytest, a `Makefile`, a
  multi-stage `Dockerfile`, `fly.toml`, and GitHub Actions CI.

## Tech stack

| Layer | Choice |
|------|--------|
| Backend | FastAPI, SQLAlchemy 2.0 (typed), Pydantic v2 |
| Frontend | React 18 + TypeScript, Vite |
| Database | SQLite (dev/demo) → Postgres (production) |
| Tooling | uv, Ruff, mypy, pytest, Docker, GitHub Actions |

## Architecture

```
Browser · React (Vite + TS)          optimistic vote w/ rollback
   │  dev:  Vite proxies /api → :8000   (single origin; identity via X-Visitor-Id header)
   │  prod: FastAPI serves the built bundle from the same origin
   ▼
FastAPI (Uvicorn)
   api/      thin HTTP edge: validate → delegate → shape response
   core/     framework-free domain: voting rules + ranking (unit-tested directly)
   db/       SQLAlchemy models + session
   ▼
SQLAlchemy → SQLite / Postgres
   feature_requests · votes  [UNIQUE(voter_id, request_id)]
```

**Why this shape:**
- **Modular monolith, not layers-for-their-own-sake.** One process, one deploy — but
  the domain logic (`app/core`) has no web-framework imports, so the tricky parts (the
  one-vote rule, ranking) are testable in isolation and reusable. One clean seam, no
  ceremony.
- **DB models are separate from API schemas.** `app/db/models.py` (SQLAlchemy) and
  `app/schemas.py` (Pydantic) are deliberately distinct, so the storage shape and the
  HTTP contract can evolve independently.
- **Same-origin in every environment.** In dev, Vite proxies `/api` to the backend; in
  prod, FastAPI serves the built React bundle. Voter identity travels in an `X-Visitor-Id`
  request header (a FingerprintJS `visitorId` computed in the browser), so there's no
  cross-site cookie or CORS-with-credentials complexity, and one thing to deploy.

## Project structure

```
backend/
  app/
    main.py            FastAPI app; serves the SPA in production
    config.py          settings (env-overridable, APP_ prefix)
    api/               HTTP layer: routes + the fingerprint-identity dependency
    core/              framework-free domain: voting.py, ranking.py
    db/                SQLAlchemy base, models, session
    schemas.py         Pydantic request/response models (validation)
  tests/               pytest: voting, ranking, and an API integration flow
frontend/
  src/                 App.tsx, api.ts, types.ts, styles.css
Dockerfile · fly.toml · .github/workflows/ci.yml · Makefile · pyproject.toml
```

## Getting started

**Prerequisites:** Python 3.13, Node 22, and [uv](https://docs.astral.sh/uv/).

```bash
make install          # uv sync + npm install
```

Run the two dev servers in separate terminals:

```bash
make api               # FastAPI on http://localhost:8000
make web               # Vite on  http://localhost:5173  (proxies /api → :8000)
```

Open **http://localhost:5173**.

Or run the whole thing as the production image (API + built UI on one port):

```bash
make docker-build
make docker-run        # http://localhost:8000
```

## Testing & code quality

```bash
make check   # ruff lint + format check + mypy (strict)
make test    # pytest
make cov     # pytest with coverage
make fmt     # auto-format + auto-fix
```

`make help` lists all targets. CI (`.github/workflows/ci.yml`) runs the same backend
checks plus a frontend type-check and build on every push/PR.

## API reference

All endpoints are under `/api`. Every request must carry an `X-Visitor-Id` header (the
browser fingerprint); the frontend attaches it automatically. Requests without it get a
`400 Missing visitor identity`.

| Method | Path | Body / Query | Description |
|--------|------|--------------|-------------|
| `POST` | `/api/requests` | `{title, description}` | Create a request (title 3–120, description 1–5000 chars) |
| `GET` | `/api/requests` | `?sort=top\|new&limit=1..200` | List requests with `vote_count`, `has_voted`, `is_author` |
| `POST` | `/api/requests/{id}/vote` | — | Upvote (idempotent). `403` on self-vote, `404` if missing |
| `DELETE` | `/api/requests/{id}/vote` | — | Remove your vote (idempotent) |
| `GET` | `/api/health` | — | Health check |

Interactive docs at `/docs` when the server is running.

## Data model

| Table | Columns | Notes |
|-------|---------|-------|
| `feature_requests` | id, title, description, author_id, created_at | `author_id` = hashed fingerprint → blocks self-votes |
| `votes` | id, request_id → fr, voter_id, created_at | **`UNIQUE(voter_id, request_id)`** = one-vote invariant |

Vote counts are **computed from the `votes` table** (the source of truth) rather than
stored in a denormalized counter, so they can never drift out of sync.

## Design decisions & trade-offs

| Decision | Choice | Why | Deferred alternative |
|----------|--------|-----|----------------------|
| **Identity** | Client-side FingerprintJS `visitorId` (sha256-hashed server-side) | Honest votes without a 45-min auth build; no cookie/CORS-credentials plumbing | Magic-link / OAuth |
| **One-vote rule** | DB `UNIQUE` constraint | An invariant, not app logic you can forget; also wins the concurrent-vote race | — |
| **Vote count** | Computed aggregate | Correct, can't drift; fast at this scale | Tx-maintained counter |
| **Ranking** | `votes DESC, created_at ASC, id ASC`; isolated in `ranking.py` | Matches the brief, deterministic, and pluggable | Time-decay "trending" score |
| **Schema mgmt** | `create_all()` on startup | Enough for a take-home | Alembic migrations |
| **ORM vs schema** | SQLAlchemy models ≠ Pydantic schemas | Storage and HTTP contract evolve independently | — |
| **Deployment** | FastAPI serves the React build (single origin) | One deploy target, no cross-origin plumbing | Split static CDN + API |

**On identity.** A browser fingerprint is a stable-ish anonymous id, but it is
**client-provided and therefore spoofable** — a determined user can forge the
`X-Visitor-Id` header (or clear browser state) and vote again, exactly as they could with
the old signed cookie. It's anti-abuse friction, not authentication. The server hashes the
raw fingerprint (sha256) into an opaque, fixed-width token before storing it, so it never
trusts or persists the raw client string, but it does **not** sign it. That's an acceptable
trade for a take-home and the standard bar for a public "upvote without signup" board; the
honest next step is real accounts (below). Everything downstream (the `voter_id`, the unique
constraint) is unchanged when you swap the identity source.

**On ranking.** Raw vote count means the earliest popular request can dominate forever.
The ordering lives behind a single function (`app/core/ranking.py`), so a Hacker
News / Reddit-style time-decay score is a localized change, not a refactor.

## Security & integrity notes

- **XSS:** user content is rendered through React (auto-escaped); no `dangerouslySetInnerHTML`.
- **Input validation:** enforced server-side via Pydantic — the client limits are a UX nicety, not the guard.
- **Identity:** the client-supplied `X-Visitor-Id` is hashed server-side before use/storage; treated as spoofable friction, not a trust boundary.
- **SQL:** all access goes through SQLAlchemy's parameterized queries.

## What I'd do next (at scale)

Explicitly out of scope for the timebox, roughly in priority order:

1. **Real authentication** (magic-link or OAuth) + basic abuse/rate-limiting on submit and vote.
2. **Time-decay ranking** so fresh requests can surface; make sort strategy configurable.
3. **Postgres + Alembic** migrations; drop SQLite for anything beyond a single-node demo.
4. **Read scaling** — denormalized vote counters maintained transactionally, plus caching for the hot list.
5. **Pagination** (cursor-based) once the list outgrows a single fetch.
6. **Moderation / lifecycle** — request status (planned / in-progress / shipped), dedupe/merge, admin view.
7. **Observability** — structured logs, request metrics, and vote-latency tracking.
8. **Frontend tests** (Vitest + Testing Library) and an end-to-end smoke test in CI.

## Deployment

The included `Dockerfile` builds the frontend and serves it from FastAPI in one image.
`fly.toml` is preconfigured for [Fly.io](https://fly.io):

```bash
fly apps create feature-request-board
fly volumes create frb_data --size 1
fly deploy            # or: make deploy
```

The same image runs on any Docker host (Render, Railway, a VM). For real traffic, point
`APP_DATABASE_URL` at managed Postgres instead of the bundled SQLite volume.

## Configuration

All settings are environment variables with the `APP_` prefix (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_DATABASE_URL` | `sqlite:///./app.db` | SQLAlchemy database URL |
| `APP_FRONTEND_DIR` | `frontend/dist` | Built bundle to serve in production |
