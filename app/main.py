"""FastAPI application entry point for the Automated Multi-Platform Posting System."""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import Settings, get_settings
from app.platforms import ALL_PLATFORMS
from app.schemas import ErrorResponse, PostingRequest, PostingResponse, ValidationErrorDetail
from app.services.posting_service import PostingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dxora.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup and shutdown."""
    settings = get_settings()
    logger.info("Starting %s v%s on port %d...", settings.app_name, __version__, settings.port)
    logger.info(
        "Loaded %d platform integrations: %s",
        len(ALL_PLATFORMS),
        ", ".join([p.__name__.replace("Platform", "") for p in ALL_PLATFORMS]),
    )
    if settings.simulation_mode:
        logger.warning(
            "*** SIMULATION_MODE IS ENABLED: Platforms without live credentials will simulate posts. ***"
        )
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "Production-grade REST API that publishes short marketing messages and CTA links "
        "across multiple third-party social media networks, developer communities, and messaging platforms."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats Pydantic and FastAPI validation errors into a clean, developer-friendly response."""
    errors = []
    for err in exc.errors():
        location = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        message = err.get("msg", "Invalid input")
        # Clean Pydantic prefix "Value error, " if present
        if message.startswith("Value error, "):
            message = message[len("Value error, "):]
        errors.append(ValidationErrorDetail(field=location or "body", message=message))

    logger.warning("Validation rejected request to %s: %s", request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error="Input validation failed. Please check the requirements.",
            details=errors,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches and handles unexpected internal server errors."""
    logger.exception("Unhandled server exception on %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error occurred",
            "detail": str(exc),
        },
    )


def get_posting_service(settings: Settings = Depends(get_settings)) -> PostingService:
    """Dependency injector for PostingService."""
    return PostingService(settings=settings)


@app.get("/", tags=["General"])
async def root(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Root status endpoint providing service metadata and documentation links."""
    return {
        "service": settings.app_name,
        "version": __version__,
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "post_message": "POST /posting",
            "health_check": "GET /health",
        },
    }


@app.get("/health", tags=["General"])
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Health check endpoint displaying configuration and integrated platforms status."""
    service = PostingService(settings=settings)
    platform_status = [
        {
            "platform": p.name,
            "configured": p.is_configured(),
            "public_access_default": p.default_public_access,
        }
        for p in service.platforms
    ]
    return {
        "status": "healthy",
        "simulation_mode": settings.simulation_mode,
        "platforms_count": len(platform_status),
        "platforms": platform_status,
    }


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish message across multiple platforms",
    description=(
        "Validates that the input message is <= 200 characters and contains exactly one valid CTA link, "
        "then asynchronously and concurrently publishes it across all integrated third-party platforms."
    ),
    tags=["Posting"],
    responses={
        200: {
            "description": "Multi-platform posting execution results",
            "model": PostingResponse,
        },
        422: {
            "description": "Validation error (message > 200 chars, no link, multiple links, or invalid URL)",
            "model": ErrorResponse,
        },
    },
)
async def post_to_platforms(
    request: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    """Endpoint to trigger automated posting across multiple third-party platforms."""
    return await service.publish_message(request)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
