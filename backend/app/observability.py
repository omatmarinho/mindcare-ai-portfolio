"""
Logs da aplicação (diferentes da auditoria).

- Auditoria (app/audit.py): QUEM fez O QUÊ com qual paciente. Fica no
  banco, é imutável e serve para prestação de contas (LGPD).
- Logs da aplicação (este arquivo): o que aconteceu TECNICAMENTE em cada
  requisição (rota, status, tempo, erros). Vão para a saída do servidor
  e servem para encontrar problemas.

Cada requisição recebe um "request id", devolvido no cabeçalho
X-Request-ID. Se um usuário relatar um erro, esse id permite achar
exatamente a linha correspondente no log.

REGRA: nunca registrar corpo de requisição, cabeçalho Authorization,
query string ou qualquer dado pessoal. Só método, caminho, status e tempo.
"""
import logging
import os
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mindcare.http")


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_logging_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "request_id=%s method=%s path=%s status=500 duration_ms=%.0f",
            request_id, request.method, request.url.path, duration_ms,
        )
        # Resposta genérica: detalhes do erro ficam só no log do servidor
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno. Informe o código ao suporte.", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.0f",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response
