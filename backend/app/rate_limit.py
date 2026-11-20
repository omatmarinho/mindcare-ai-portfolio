"""
Limite de requisições (rate limiting).

Impede que alguém tente milhares de senhas por minuto (ataque de força
bruta) ou dispare e-mails de recuperação sem parar.

As contagens ficam na memória do servidor. Isso basta enquanto houver
UM processo da API. Com vários servidores/processos, cada um contaria
separado: aí será preciso um armazenamento compartilhado (ex.: Redis),
configurando "storage_uri" abaixo.

ATENÇÃO NO DEPLOY: atrás de um proxy/load balancer, o IP visto pela API
é o do proxy. Será preciso confiar no cabeçalho X-Forwarded-For
(uvicorn --proxy-headers --forwarded-allow-ips=...) para limitar por
cliente real.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Limites usados nas rotas
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/minute"
PASSWORD_RESET_LIMIT = "5/minute"
EMAIL_VERIFICATION_LIMIT = "5/minute"

# Contagem por endereço IP de quem faz a requisição
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas. Aguarde um minuto e tente novamente."},
        headers={"Retry-After": "60"},
    )
