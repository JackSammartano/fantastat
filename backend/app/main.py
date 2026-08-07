from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from backend.app.api.v1 import router as api_v1_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fantacalcio Analysis API",
        version="0.1.0",
        description="API locale per storico e preparazione asta 2026/2027.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router)

    @app.middleware("http")
    async def shared_access_guard(request: Request, call_next) -> Response:
        password = os.getenv("FANTACALCIO_SHARE_PASSWORD")
        if password:
            authorization = request.headers.get("Authorization", "")
            authenticated = False
            if authorization.startswith("Basic "):
                try:
                    decoded = base64.b64decode(authorization[6:]).decode("utf-8")
                    username, supplied = decoded.split(":", 1)
                    authenticated = username == "fantacalcio" and secrets.compare_digest(
                        supplied, password
                    )
                except (ValueError, UnicodeDecodeError):
                    authenticated = False
            if not authenticated:
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="FantaLab"'},
                )
        if os.getenv("FANTACALCIO_READ_ONLY") == "1" and request.method not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            if not (
                request.method == "POST"
                and request.url.path == "/api/v1/rankings/calculate"
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "read_only",
                        "detail": "Condivisione in sola consultazione",
                    },
                )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": str(error),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": "http_error",
                "detail": str(error.detail),
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(
        _request: Request,
        _error: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "Errore interno non previsto",
            },
        )

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        requested = (frontend_dist / full_path).resolve()
        if (
            full_path
            and requested.is_relative_to(frontend_dist.resolve())
            and requested.is_file()
        ):
            return FileResponse(requested)
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(404, "Frontend non compilato")

    return app


app = create_app()
