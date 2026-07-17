# Feature Request Board

A small, production-shaped feature-request board: users submit requests, browse a
ranked list, and upvote _other people's_ requests. Built as a take-home to show
how the system is reasoned about — the interesting decisions are written up as
[ADRs](docs/adr) and summarized under [Design decisions](#design-decisions) and
[Production considerations](#production-considerations).

- **Backend:** Python 3.12 · FastAPI · async SQLAlchemy · Postgres · Alembic
- **Frontend:** React · Vite · TypeScript
- **Tooling:** `uv` + `invoke` (backend), `pnpm` (frontend), Docker Compose
- **Tests:** `pytest` against a real Postgres; `vitest` on the frontend

## Features

- Submit a feature request (title + description, server-validated).
- Browse a ranked, paginated list.
- Upvote / un-vote — **one vote per user per request**, enforced by the database.
- **Can't vote on your own request.**
- Three ranking modes: **Top** (votes), **New** (recency), **Trending**
  (time-decayed popularity).
- Live vote counts with optimistic UI updates.

## Architecture

```
┌─────────────────┐      HTTP (JSON, X-User header)     ┌──────────────────────┐
│  React + Vite   │  ──────────────────────────────────▶│   FastAPI (async)    │
│  SPA (:5173)    │◀──────────────────────────────────  │   (:8010)            │
└─────────────────┘                                      │  routers → services  │
                                                         │  ranking · identity  │
                                                         └──────────┬───────────┘
                                                                    │ async SQLAlchemy
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │   Postgres (:5433)   │
                                                         │  users ·             │
                                                         │  feature_requests ·  │
                                                         │  votes UNIQUE(u,r)   │
                                                         └──────────────────────┘
```

Data model:

```
users(id, username UNIQUE, created_at)
feature_requests(id, title, description, author_id → users, vote_count, created_at)
votes(id, user_id → users, request_id → feature_requests, created_at,
      UNIQUE(user_id, request_id))
```

`vote_count` is a denormalized cache kept in lockstep with the `votes` table
inside one transaction — see [ADR-0003](docs/adr/0003-postgres-vote-count-consistency.md).

## Quick start (Docker Compose)

Requires Docker. Brings up Postgres, the API, and the built SPA:

```bash
docker compose up --build           # db + api + web
docker compose exec api uv run python -m app.seed   # optional: demo data
```

- SPA → http://localhost:5173
- API docs (Swagger) → http://localhost:8010/docs

> **Ports:** this project uses **5433** (db), **8010** (api), **5173** (web) to
> avoid colliding with other local services on the standard 5432/8000. Override in
> `docker-compose.yml` / `.env` if needed.

## Local development

### Backend (`uv` + `invoke`)

```bash
cd backend
uv sync                 # create venv (Python 3.12) + install
docker compose up -d db # Postgres only
invoke migrate          # apply Alembic migrations
invoke seed             # demo data
invoke run              # API with autoreload on :8010
```

Task runner (`invoke --list`):

| Task | Description |
|------|-------------|
| `invoke check` | CI gate: **lint + typecheck + test** |
| `invoke fmt` / `invoke lint` | ruff format / lint |
| `invoke typecheck` | mypy (strict) |
| `invoke test` | pytest (starts the Postgres test DB) |
| `invoke migrate` / `invoke makemigration -m "…"` | Alembic |
| `invoke seed` | load demo data |
| `invoke run` | run the API locally |
| `invoke deploy [--tag …]` | build the production image |

### Frontend (`pnpm`)

```bash
cd frontend
pnpm install
pnpm dev            # Vite dev server on :5173 (proxies to API via VITE_API_BASE_URL)
```

Scripts: `pnpm dev | build | preview | typecheck | lint | format | test`.

## API reference

Identity is passed via the `X-User` header (see
[ADR-0002](docs/adr/0002-auth-identity.md)).

| Method | Path | Body / Query | Success | Errors |
|--------|------|--------------|---------|--------|
| `POST` | `/feature-requests` | `{title, description}` | `201` | `401` no identity · `422` invalid |
| `GET` | `/feature-requests` | `?sort=top\|new\|trending&page=&page_size=` | `200` | — |
| `GET` | `/feature-requests/{id}` | — | `200` | `404` |
| `POST` | `/feature-requests/{id}/votes` | — | `201` | `403` self-vote · `404` · `409` duplicate |
| `DELETE` | `/feature-requests/{id}/votes` | — | `200` | `404` no vote |

List responses are paginated: `{ items, total, page, page_size, has_next }`.
Each request carries `has_voted` for the current viewer.

## Testing

```bash
cd backend && invoke test     # 18 tests vs. a real Postgres (metacto_test)
cd frontend && pnpm test      # vitest
```

Backend tests target **invariants**, not coverage theater: one-vote-per-user
(including a concurrent-request race), self-vote rejection, un-vote, the three
ranking orders, pagination, and input/identity validation.

## Design decisions

Full write-ups in [`docs/adr`](docs/adr):

- **[ADR-0001](docs/adr/0001-ranking-strategy.md) — Ranking:** selectable
  `top`/`new`/`trending`; default is the obvious votes-desc, trending is
  time-decayed. Makes the recency trade-off a visible control, not a hidden
  formula.
- **[ADR-0002](docs/adr/0002-auth-identity.md) — Identity:** `X-User`
  pseudo-identity behind a single `get_current_user` seam; real auth is a
  one-file swap.
- **[ADR-0003](docs/adr/0003-postgres-vote-count-consistency.md) — Consistency:**
  DB `UNIQUE` constraint for vote integrity + a denormalized `vote_count` updated
  atomically in the same transaction.

## Production considerations

What a real deployment needs beyond this exercise, and where it would slot in:

- **Real authentication & sessions** — replace the `X-User` seam
  ([ADR-0002](docs/adr/0002-auth-identity.md)) with OAuth/JWT + sessions; the
  header trust boundary is demo-only.
- **Rate limiting & abuse prevention** — per-user/IP limits on submit and vote
  (e.g. Redis token bucket), plus spam/duplicate-request detection and CAPTCHA on
  submission.
- **Caching hot lists** — the ranked first page is read-heavy and cacheable
  (short-TTL Redis, keyed by sort+page) with invalidation on vote/create.
- **Ranking at scale** — precompute/materialize a `trending` score column on a
  schedule instead of computing it per-row per-request; add covering indexes for
  each sort.
- **Observability** — structured logging, request tracing, RED metrics
  (rate/errors/duration), and DB slow-query monitoring.
- **Moderation & lifecycle** — admin roles, request status workflow
  (Planned/In-Progress/Done/Declined), merge duplicates, soft-delete/audit trail.
- **Product depth** — comments, tags/categories, search, notifications,
  full user profiles.
- **Data & migrations** — connection pooling (PgBouncer), read replicas for the
  read-dominated list, backup/restore and zero-downtime migration process.
- **Delivery** — CI running `invoke check` + `pnpm` gates on every PR, image
  scanning, secrets management, and infra-as-code for the compose stack.

## Project layout

```
backend/
  app/            config, db, models, schemas, deps (identity),
                  ranking, services (vote logic), routers/
  migrations/     Alembic (async)
  tests/          pytest (invariants)
  tasks.py        invoke task runner
frontend/
  src/            App, api client, components, timeAgo util (+ test)
docs/adr/         architecture decision records
docker-compose.yml
```
