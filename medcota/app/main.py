"""MedCota — API de compras e cotações.

Rodar:  uvicorn app.main:app --reload
Docs:   /docs (Swagger)
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from .core.config import settings
from .core.database import SessionLocal
from .core.logging import configurar_logging, request_id_var
from .core.ratelimit import limiter
from .routers import (
    auth,
    cadastro,
    comparativo,
    cotacoes,
    dashboard,
    empresa,
    faltas,
    fornecedores,
    pedidos,
    produtos,
    publico,
    recebimento,
)

configurar_logging()
logger = logging.getLogger("medcota")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("MedCota iniciada ambiente=%s", settings.ambiente)
    yield


app = FastAPI(title="MedCota — Compras e Cotações", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origens,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
async def _limite_excedido(_request: Request, _exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": "60"},
        content={
            "detail": {
                "codigo": "limite_requisicoes",
                "mensagem": "Muitas requisições. Tente novamente em instantes.",
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def _validacao(_request: Request, exc: RequestValidationError):
    """Erros de validação no mesmo formato dos demais: {"detail": {"codigo", "mensagem", "campos"}}."""
    campos: dict[str, str] = {}
    for e in exc.errors():
        campo = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path", "form"))
        msg = str(e["msg"]).removeprefix("Value error, ")
        campos.setdefault(campo or "_", msg)
    return JSONResponse(
        status_code=422,
        content={"detail": {"codigo": "validacao", "mensagem": "Dados inválidos", "campos": campos}},
    )


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(rid)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/saude", tags=["infra"])
def saude():
    """Healthcheck: confirma que a API responde e o banco está acessível."""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}


for r in (
    auth,
    cadastro,
    empresa,
    produtos,
    fornecedores,
    faltas,
    cotacoes,
    publico,
    comparativo,
    pedidos,
    dashboard,
    recebimento,
):
    app.include_router(r.router)

app.include_router(recebimento.fiscal)
