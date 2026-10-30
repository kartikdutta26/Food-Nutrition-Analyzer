import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import certifi
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import (
    ConfigurationError,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from app.api.food import router as food_router
from app.api.meals import router as meals_router
from app.api.nutrition import router as nutrition_router
from app.api.photos import router as photos_router
from app.api.profile import router as profile_router
from app.database import initialize_database
from app.schemas.nutrition import (
    DatabaseHealthResponse,
    HealthResponse,
    RootResponse,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
_LOGGER = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "nutriai_db")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
for origin in ("http://127.0.0.1:5174", "http://localhost:5174"):
    if origin not in CORS_ORIGINS:
        CORS_ORIGINS.append(origin)


def _validation_message(error: dict) -> str:
    location = error.get("loc", ())
    source = location[0] if location else None
    path = location[1:] if source in {"body", "query", "path"} else location
    field = ".".join(str(part) for part in path)
    error_type = error.get("type", "")
    context = error.get("ctx") or {}

    if error_type == "missing":
        if source == "query":
            if field == "date":
                return "Query parameter 'date' is required. Add ?date=YYYY-MM-DD."
            return f"Query parameter '{field}' is required. Add it to the URL."
        if source == "path":
            return f"Path parameter '{field}' is required. Use the documented URL format."
        if not field:
            return "Request body is required. Send the documented JSON object."
        if field.startswith("nutrition."):
            return (
                f"Required field '{field}' is missing. Include a non-negative number; "
                "calories use kcal and macros use grams."
            )
        return f"Required field '{field}' is missing. Include it in the request."

    if source == "query" and field == "date":
        return "Use ISO date format YYYY-MM-DD for 'date' (for example, 2026-10-15)."
    if source == "body" and field == "consumed_at" and "datetime" in error_type:
        return (
            "Use an ISO 8601 datetime for 'consumed_at', "
            "for example 2026-10-15T13:30:00Z."
        )
    if error_type == "json_invalid":
        return "Request body is not valid JSON. Check commas, quotes, and brackets."
    if error_type == "extra_forbidden":
        return f"Field '{field}' is not supported here. Remove it or use a documented field."
    if error_type == "literal_error":
        expected = context.get("expected", "the documented values")
        return f"'{field}' must be one of: {expected}."
    if error_type == "string_pattern_mismatch" and source == "path" and field == "meal_id":
        return (
            "'meal_id' must be a 24-character hexadecimal MongoDB ID. "
            "Use the id returned when the meal was created."
        )
    if error_type in {"int_parsing", "int_type"}:
        return f"'{field}' must be an integer."
    if error_type in {"float_parsing", "float_type"}:
        return f"'{field}' must be a number."
    if error_type == "list_type":
        return f"'{field}' must be a JSON array."
    if error_type == "model_type":
        return f"'{field}' must be a JSON object with the documented fields."
    if error_type in {"greater_than_equal", "greater_than"}:
        minimum = context.get("ge", context.get("gt"))
        relation = "at least" if error_type == "greater_than_equal" else "greater than"
        return f"'{field}' must be {relation} {minimum}."
    if error_type in {"less_than_equal", "less_than"}:
        maximum = context.get("le", context.get("lt"))
        relation = "at most" if error_type == "less_than_equal" else "less than"
        return f"'{field}' must be {relation} {maximum}."
    if error_type in {"string_too_short", "too_short"}:
        minimum = context.get("min_length", 0)
        unit = "item" if error_type == "too_short" and minimum == 1 else "items"
        if error_type == "string_too_short":
            unit = "character" if minimum == 1 else "characters"
        return f"'{field}' is too short; provide at least {minimum} {unit}."
    if error_type in {"string_too_long", "too_long"}:
        maximum = context.get("max_length", 0)
        unit = "item" if error_type == "too_long" and maximum == 1 else "items"
        if error_type == "string_too_long":
            unit = "character" if maximum == 1 else "characters"
        return f"'{field}' is too long; use no more than {maximum} {unit}."

    message = error.get("msg", "Invalid value")
    if message.startswith("Value error, "):
        message = message.removeprefix("Value error, ")
    if field:
        return f"Invalid '{field}': {message}"
    return message


def _mongodb_startup_diagnostic(error: PyMongoError) -> str:
    """Return a useful startup diagnosis without exposing URI or credential text."""
    message = str(error).lower()

    if isinstance(error, ConfigurationError):
        if any(
            marker in message
            for marker in ("dns", "srv", "resolution", "nameserver")
        ):
            return (
                "DNS SRV/TXT resolution failed or timed out. Check the machine's DNS "
                "resolver and network access to the Atlas cluster."
            )
        return (
            "MongoDB connection string configuration is invalid. Check its scheme, "
            "Atlas hostname, and DNS records."
        )

    if isinstance(error, ServerSelectionTimeoutError):
        return (
            "No Atlas server became reachable before the selection timeout. Check "
            "DNS/network access and the Atlas IP access list."
        )

    if any(marker in message for marker in ("certificate", "tls", "ssl")):
        return (
            "TLS connection setup failed. Check system CA certificates and Atlas "
            "TLS connectivity."
        )

    if any(marker in message for marker in ("authentication failed", "auth failed")):
        return (
            "MongoDB authentication failed. Check the configured database user's "
            "credentials and role."
        )

    if any(marker in message for marker in ("timeout", "timed out")):
        return (
            "The MongoDB connection timed out. Check network access and the Atlas "
            "IP access list."
        )

    return (
        "MongoDB reported a startup configuration or connection error. Check Atlas "
        "connectivity and configuration."
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is missing from the .env file")

    client = None
    try:
        # mongodb+srv URI parsing performs DNS SRV/TXT lookups in the constructor,
        # so construction must be inside this startup error boundary as well.
        client = MongoClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            # PyMongo also uses connectTimeoutMS as the SRV/TXT lookup lifetime.
            # A 30s window accommodates the slow DNS responses observed here.
            connectTimeoutMS=30000,
            serverSelectionTimeoutMS=5000,
        )
        app.state.mongodb_client = client
        app.state.database = client[MONGODB_DATABASE]
        client.admin.command("ping")
        initialize_database(app.state.database)
    except PyMongoError as exc:
        diagnostic = _mongodb_startup_diagnostic(exc)
        _LOGGER.error(
            "MongoDB startup failed (exception_type=%s): %s",
            type(exc).__name__,
            diagnostic,
        )
        if client is not None:
            client.close()
        raise RuntimeError(
            f"MongoDB startup failed ({type(exc).__name__}): {diagnostic}"
        ) from None

    _LOGGER.info("MongoDB Atlas connected successfully")
    try:
        yield
    finally:
        if client is not None:
            client.close()
        _LOGGER.info("MongoDB connection closed")


def create_app(*, lifespan_context=lifespan) -> FastAPI:
    application = FastAPI(
        title="NutriAI Backend",
        description="Backend API for the NutriAI Food Nutrition Analyser",
        version="1.0.0",
        lifespan=lifespan_context,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @application.exception_handler(PyMongoError)
    async def mongo_error_handler(
        request: Request,
        exc: PyMongoError,
    ) -> JSONResponse:
        # Do not log exception text: driver errors can include database details.
        _LOGGER.error(
            "MongoDB operation failed for %s (%s)",
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "MongoDB operation failed"},
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": error.get("loc", ()),
                        "msg": _validation_message(error),
                        "type": error.get("type", "value_error"),
                    }
                    for error in exc.errors()
                ]
            },
        )

    @application.get("/", response_model=RootResponse)
    def root():
        return {"message": "NutriAI Backend is running!"}

    @application.get("/api/health", response_model=HealthResponse)
    def health_check():
        return {"status": "healthy", "service": "NutriAI Backend"}

    @application.get("/api/db-health", response_model=DatabaseHealthResponse)
    def database_health_check(request: Request):
        try:
            request.app.state.mongodb_client.admin.command("ping")
            return {
                "status": "connected",
                "database": MONGODB_DATABASE,
            }
        except PyMongoError:
            raise HTTPException(
                status_code=503,
                detail="MongoDB connection failed",
            )

    application.include_router(food_router)
    application.include_router(photos_router)
    application.include_router(meals_router)
    application.include_router(nutrition_router)
    application.include_router(profile_router)
    return application


app = create_app()
