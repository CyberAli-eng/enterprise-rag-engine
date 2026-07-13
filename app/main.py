import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_health, routes_ingest, routes_query
from app.config import get_settings
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Secure Retrieval-Augmented Generation engine for connecting "
    "unstructured corporate data to LLMs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_ingest.router)
app.include_router(routes_query.router)

if not settings.api_key_list and settings.environment == "production":
    logger.warning(
        "No API_KEYS configured while ENVIRONMENT=production — the API is running unauthenticated!"
    )


@app.get("/")
def root():
    return {"service": settings.app_name, "status": "live", "docs": "/docs"}
