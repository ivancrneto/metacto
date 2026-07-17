FROM python:3.12-slim

# uv provides fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so the layer caches across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application code.
COPY . .

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
