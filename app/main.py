import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, profile
from app.core.config import settings
from app.core.logging_config import LoggingMiddleware
from app.utils.constants import APP_TITLE, APP_VERSION, DOCS_URL

logger = logging.getLogger(__name__)

app = FastAPI(title=APP_TITLE, version=APP_VERSION, docs_url=DOCS_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(profile.router, prefix="/api", tags=["Profile"])


@app.get("/health")
def health_check():
    logger.info("Health check pinged")
    return {"status": "ok"}
