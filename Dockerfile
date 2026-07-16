# syntax=docker/dockerfile:1

# ---- Stage 1: build the React frontend -------------------------------------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime serving the API + built bundle ----------------
FROM python:3.13-slim AS runtime

# uv, copied from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    APP_DATABASE_URL="sqlite:////data/app.db" \
    APP_FRONTEND_DIR="frontend/dist"

WORKDIR /app

# Install production dependencies only, pinned by the lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Directory for the SQLite file (mount a volume here in production).
RUN mkdir -p /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
