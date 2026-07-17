from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import feature_requests, votes


def create_app() -> FastAPI:
    app = FastAPI(title="Feature Request Board", version="0.1.0")

    # The SPA is served from a separate origin (Vite dev server / static host).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(feature_requests.router)
    app.include_router(votes.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
