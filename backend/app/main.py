import sentry_sdk
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, league, match, prediction, admin
from app.routers import notifications, dugout, tournament_picks
from app.services.scheduler import start_scheduler, stop_scheduler

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


# Initialize FastAPI app
app = FastAPI(
    title="Lazy Fantasy",
    description="Backend API for Lazy Fantasy — Cricket predictions",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve uploaded images
_uploads_dir = Path("uploads")
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# CORS configuration (configurable via environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(league.router)
app.include_router(match.router)
app.include_router(prediction.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(dugout.router)
app.include_router(tournament_picks.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Lazy Fantasy API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
