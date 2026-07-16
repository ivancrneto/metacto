"""FastAPI application entrypoint.

In production this single process also serves the built React bundle, so the API
and UI share one origin (first-party SameSite=Lax cookies, one deploy target).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.requests import router as requests_router
from app.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Feature Request Board", version="0.1.0", lifespan=lifespan)
app.include_router(requests_router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Serve the built frontend (production, single-origin) --------------------
# Skipped in local dev where Vite serves the app and proxies /api to this server.
_frontend = Path(settings.frontend_dir)
if (_frontend / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_frontend / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        # Unknown /api/* routes must 404, not fall through to the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(_frontend / "index.html")
