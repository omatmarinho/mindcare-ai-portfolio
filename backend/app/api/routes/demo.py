"""
POST /demo/session — entra na demonstração com uma conta temporária própria.

Só existe com DEMO_MODE=true. Limite de tentativas por IP e de contas ativas
ao mesmo tempo; contas vencidas são apagadas a cada nova entrada.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app import audit, demo
from app.api.routes.auth import _issue_tokens
from app.database.database import get_db
from app.rate_limit import limiter
from app.schemas import Token

router = APIRouter(prefix="/demo", tags=["Demonstração"])


@router.post("/session", response_model=Token)
@limiter.limit("5/minute;30/hour")
def start_demo(request: Request, db=Depends(get_db)):
    if not demo.enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    demo.purge_expired(db)
    if demo.active_count(db) >= demo.max_active():
        raise HTTPException(status_code=503, detail="Muitas demonstrações abertas agora. Tente de novo em alguns minutos.")
    user = demo.create_demo_user(db)
    audit.record(db, request, audit.DEMO_SESSION_START, user_id=user.id)
    return _issue_tokens(db, user)
