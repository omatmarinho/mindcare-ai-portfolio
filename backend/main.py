import hmac
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

load_dotenv()

from app.api.routes import (  # noqa: E402
    agenda, audit_logs, auth, dashboard, demo, health, notes, patient_export, patient_overview, patients,
)
from app import demo as demo_mode  # noqa: E402
from app.observability import configure_logging, request_logging_middleware  # noqa: E402
from app.rate_limit import limiter, rate_limit_exceeded_handler  # noqa: E402
from app.settings_check import check_settings, is_production  # noqa: E402

# Logs e verificação de configuração (em produção, recusa iniciar se inseguro)
configure_logging()
check_settings()

# Criando a aplicação.
# Em produção a documentação interativa (/docs) fica desligada:
# não há motivo para expor o mapa da API publicamente.
app = FastAPI(
    title="MindCare AI API",
    description="API da plataforma MindCare AI",
    version="0.1.0",
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
    openapi_url=None if is_production() else "/openapi.json",
)

# Log de cada requisição com um "request id" (ver app/observability.py)
app.middleware("http")(request_logging_middleware)

# Chave interna: quando a API fica exposta na internet (hospedagem gratuita da
# demonstração), só o frontend, que conhece a chave, consegue chamá-la.
# Também é o que torna seguro confiar no IP repassado pelo frontend (X-Forwarded-For).
# Na demonstração não há e-mail de verdade: cadastro e recuperação de senha ficam fechados
DEMO_CLOSED_PATHS = ("/auth/register", "/auth/password-reset", "/auth/verify-email")


@app.middleware("http")
async def gatekeeper(request: Request, call_next):
    path = request.url.path
    internal_key = os.getenv("INTERNAL_API_KEY", "")
    if internal_key and path != "/health":
        sent = request.headers.get("x-internal-key", "")
        if not hmac.compare_digest(sent.encode(), internal_key.encode()):
            return JSONResponse(status_code=401, content={"detail": "Não autorizado"})
    if demo_mode.enabled() and path.startswith(DEMO_CLOSED_PATHS):
        return JSONResponse(status_code=403, content={"detail": "Indisponível na demonstração."})
    return await call_next(request)

# Limite de requisições (ver app/rate_limit.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS: quais sites (origens) o navegador deixa chamar esta API.
# Lista separada por vírgulas na variável CORS_ORIGINS do .env.
# Padrão: o frontend Next.js rodando localmente.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,  # usamos token no cabeçalho, não cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Key"],
    expose_headers=["X-Request-ID"],
)

# As tabelas NÃO são criadas aqui.
# A estrutura do banco é gerenciada pelo Alembic (pasta alembic/):
#     alembic upgrade head

# Registrando as rotas
app.include_router(health.router)
app.include_router(patients.router)
app.include_router(auth.router)
app.include_router(audit_logs.router)
app.include_router(notes.router)
app.include_router(agenda.router)
app.include_router(dashboard.router)
app.include_router(patient_export.router)
app.include_router(patient_overview.router)


@app.get("/")
def home():
    return {
        "message": "Bem-vindo à API do MindCare AI!",
        "status": "online"
    }
app.include_router(demo.router)
