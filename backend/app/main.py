import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import AuditReport, AuditRequest
from app.scanner import _run_audit_sync
# Windows: uvicorn + Playwright work better with Proactor event loop
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# This variable is what uvicorn looks for:  uvicorn app.main:app
app = FastAPI(
    title="Web Privacy Auditor API",
    description="Scans URLs for third-party tags, trackers, and cookies.",
    version="1.0.0",
)

# Which frontends may call this API (comma-separated in env var CORS_ORIGINS)
_default_cors = (
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:3000,"
    "https://privacy-web-869322756604.asia-south1.run.app"
)
_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _default_cors).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Simple check that the API is running."""
    return {"status": "ok"}


@app.post("/audit", response_model=AuditReport)
def audit(body: AuditRequest):
    """
    Run a privacy scan on the given URL.
    Sync route = FastAPI runs Playwright in a thread pool (fixes Windows + uvicorn).

    Frontend sends:  { "url": "https://example.com" }
    """
    url = str(body.url)

    try:
        return _run_audit_sync(url)
    except Exception as e:
        msg = str(e).strip() or type(e).__name__
        raise HTTPException(status_code=400, detail=f"Scan failed: {msg}")
