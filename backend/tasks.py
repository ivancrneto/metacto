"""Developer task runner (pyinvoke).

Run `invoke --list` to see everything. Common flows:

    invoke install        # sync deps (incl. dev)
    invoke check          # lint + typecheck + test (CI gate)
    invoke run            # start the API with reload
    invoke migrate        # apply Alembic migrations
    invoke seed           # load demo data
"""

from invoke import task
from invoke.context import Context

# All backend commands run through `uv` so the pinned venv is always used.
UV = "uv run"


@task
def install(c: Context) -> None:
    """Sync dependencies (including the dev group)."""
    c.run("uv sync", pty=True)


@task
def fmt(c: Context) -> None:
    """Auto-format and apply safe lint fixes."""
    c.run(f"{UV} ruff format .", pty=True)
    c.run(f"{UV} ruff check --fix .", pty=True)


@task
def lint(c: Context) -> None:
    """Lint and check formatting (no writes)."""
    c.run(f"{UV} ruff check .", pty=True)
    c.run(f"{UV} ruff format --check .", pty=True)


@task
def typecheck(c: Context) -> None:
    """Static type checking with mypy."""
    c.run(f"{UV} mypy app", pty=True)


@task
def test(c: Context) -> None:
    """Run the test suite (spins up the Postgres test DB via compose)."""
    c.run("docker compose -f ../docker-compose.yml up -d db", pty=True)
    c.run(f"{UV} pytest -q", pty=True)


@task(pre=[lint, typecheck, test])
def check(c: Context) -> None:
    """CI gate: lint + typecheck + test."""


@task
def migrate(c: Context) -> None:
    """Apply Alembic migrations to the latest revision."""
    c.run(f"{UV} alembic upgrade head", pty=True)


@task(help={"message": "Revision message"})
def makemigration(c: Context, message: str) -> None:
    """Autogenerate a new Alembic revision from model changes."""
    c.run(f'{UV} alembic revision --autogenerate -m "{message}"', pty=True)


@task
def seed(c: Context) -> None:
    """Load demo feature requests, users, and votes."""
    c.run(f"{UV} python -m app.seed", pty=True)


@task
def run(c: Context) -> None:
    """Run the API locally with autoreload."""
    c.run(f"{UV} uvicorn app.main:app --reload --port 8000", pty=True)


@task(help={"tag": "Image tag to build (default: latest)"})
def deploy(c: Context, tag: str = "latest") -> None:
    """Build the production Docker image (push step is environment-specific)."""
    c.run(f"docker build -t feature-board-api:{tag} .", pty=True)
    print(f"Built feature-board-api:{tag}. Push/apply is environment-specific.")
