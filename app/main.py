from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.status import HTTP_200_OK

from app.common.auth import check_token
from app.config import get_settings
from app.controller.offers import offer_router
from app.controller.places import place_router
from app.exceptions import NotFoundError, ConflictError
from app.schemas.rest.rest_responses import HealthCheck

settings = get_settings()

origins = ["http://localhost", "http://localhost:8080", "*"]


def create_application() -> FastAPI:
    """
    Create base FastAPI app with CORS middlewares and routes loaded
    Returns:
        FastAPI: [description]
    """
    app = FastAPI(debug=settings.APP_DEBUG, openapi_url=settings.APP_API_DOCS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
        max_age=86400,
    )

    app.include_router(offer_router, prefix="/offers", tags=["OFFERS"], dependencies=[Depends(check_token)])
    app.include_router(place_router, prefix="/places", tags=["PLACE"], dependencies=[Depends(check_token)])

    return app


app = create_application()


def traces_sampler(sampling_context: dict[str, Any]) -> float:
    """Function to dynamically set Sentry sampling rates"""

    if settings.APP_ENV != "PROD":
        return 0.0

    request_path = sampling_context.get("asgi_scope", {}).get("path")
    if request_path in {"/health", "/metrics", "/docs", "/openapi.json"}:
        return 0.0
    return 0.1


if settings.APP_ENV == "PROD":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        send_default_pii=True,
        traces_sampler=traces_sampler,
        profiles_sample_rate=0.1,
        integrations=[SqlalchemyIntegration()],
    )
    app.add_middleware(SentryAsgiMiddleware)

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"
@app.get("/")
async def read_root():
    return {"Hello": "World!", "Env": settings.APP_ENV, "timestamp": datetime.now(tz=ZoneInfo("UTC"))}


@app.get("/health",
         status_code=HTTP_200_OK,
         tags=["healthcheck"],
         summary="Perform a Health Check",
         response_description="Return HTTP Status Code 200 (OK)"
         )
async def health_check() -> HealthCheck:
    return HealthCheck(status="OK")


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
