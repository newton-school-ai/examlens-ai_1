"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import auth, papers, upload, users

app = FastAPI(
    title="ExamLens AI",
    description="PYQ analysis, answer generation, and exam preparation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "examlens-ai"}


@app.get("/api/health")
def api_health():
    """Milestone-compatible health endpoint under the API prefix."""
    return health()


# Register endpoints
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
