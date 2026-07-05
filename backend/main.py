from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.api import auth_routes, product_routes, insight_routes, advisor_routes, user_routes
from backend.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Verdict API",
    description="AI-powered Shopping Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(product_routes.router, prefix="/api/v1")
app.include_router(insight_routes.router, prefix="/api/v1")
app.include_router(advisor_routes.router, prefix="/api/v1")
app.include_router(user_routes.router, prefix="/api/v1")


@app.get("/api")
def api_root():
    return {"service": "Verdict API", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ── Serve the SPA ────────────────────────────────────────────────────────
# frontend/index.html is a self-contained single-page app that talks to
# /api/v1/... on the same origin, so no BACKEND_URL / CORS juggling is
# needed when the two are deployed together (see render.yaml).
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Any non-API path falls back to the SPA shell (client-side routing).
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
