from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    return app


app = create_app()

