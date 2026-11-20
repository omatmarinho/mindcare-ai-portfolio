from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import audit, email_service
from app.api.deps import EMAIL_NOT_VERIFIED_DETAIL, get_current_user
from app.database.database import get_db
from app.database import crud
from app.database.models import User
from app.rate_limit import (
    EMAIL_VERIFICATION_LIMIT,
    LOGIN_LIMIT,
    PASSWORD_RESET_LIMIT,
    REGISTER_LIMIT,
    limiter,
)
from app.schemas import (
    EmailVerificationConfirm,
    EmailVerificationRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    generate_url_token,
    hash_password,
)

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)

# Validade dos links enviados por e-mail
PASSWORD_RESET_VALID_MINUTES = 30
EMAIL_VERIFICATION_VALID_HOURS = 24

INVALID_LINK = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Link inválido ou expirado. Solicite um novo."
)


def _queue_verification_email(db: Session, user: User, background_tasks: BackgroundTasks):
    token = crud.create_user_token(
        db, user, crud.EMAIL_VERIFICATION,
        timedelta(hours=EMAIL_VERIFICATION_VALID_HOURS)
    )
    # Envia DEPOIS de responder: o usuário não espera o provedor de e-mail
    background_tasks.add_task(
        email_service.send_email_verification_email,
        user.email, token, EMAIL_VERIFICATION_VALID_HOURS
    )


# ---------------------------------------------------------------------
# Cadastro, login e usuário atual
# ---------------------------------------------------------------------

REGISTER_MESSAGE = (
    "Cadastro recebido. Enviamos um e-mail para o endereço informado: "
    "siga as instruções para ativar sua conta."
)


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit(REGISTER_LIMIT)
def register_user(
    request: Request,  # exigido pelo limitador (de onde ele lê o IP)
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    A resposta é SEMPRE a mesma, exista o e-mail ou não. Assim ninguém usa
    o cadastro para descobrir quem tem conta no Psinara. Quem precisa
    saber (o dono do e-mail) é avisado por e-mail.
    """
    existing_user = crud.get_user_by_email(db, user.email)

    if existing_user is None:
        new_user = crud.create_user(
            db=db,
            full_name=user.full_name,
            email=user.email,
            password=user.password
        )
        if new_user is not None:
            _queue_verification_email(db, new_user, background_tasks)
            audit.record(db, request, audit.REGISTER, user_id=new_user.id)
            return MessageResponse(message=REGISTER_MESSAGE)

        # Outra requisição criou o mesmo e-mail ao mesmo tempo
        existing_user = crud.get_user_by_email(db, user.email)
    else:
        # Gasta o mesmo tempo do caminho de cadastro novo (hash Argon2),
        # para que a demora da resposta não revele que o e-mail existe
        hash_password(user.password)

    if existing_user is not None and existing_user.is_active:
        if existing_user.email_verified_at is None:
            # Ainda não confirmou: o mais útil é mandar um novo link
            _queue_verification_email(db, existing_user, background_tasks)
        else:
            background_tasks.add_task(
                email_service.send_account_exists_email, existing_user.email
            )

    audit.record(
        db, request, audit.REGISTER_EXISTING_EMAIL,
        user_id=existing_user.id if existing_user else None
    )
    return MessageResponse(message=REGISTER_MESSAGE)


@router.post("/login", response_model=Token)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,  # exigido pelo limitador (de onde ele lê o IP)
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # No padrão OAuth2 o campo se chama "username", mas aqui ele recebe o e-mail
    user = crud.authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password
    )

    if user is None:
        # Não registramos o e-mail digitado: pode ser de um terceiro
        audit.record(db, request, audit.LOGIN_FAILED)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Só chega aqui quem acertou a senha: dizer "confirme o e-mail"
    # não ajuda um atacante, que precisaria já saber a senha.
    if user.email_verified_at is None:
        audit.record(db, request, audit.LOGIN_BLOCKED_UNVERIFIED, user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_NOT_VERIFIED_DETAIL
        )

    audit.record(db, request, audit.LOGIN_SUCCESS, user_id=user.id)

    return _issue_tokens(db, user)


def _issue_tokens(db: Session, user: User) -> Token:
    # "sub" identifica o dono do token: usamos o id (como texto), não o e-mail.
    # "ver" permite invalidar todos os tokens do usuário (logout, troca de senha).
    claims = {"sub": str(user.id), "ver": user.token_version}

    # O refresh token é de uso único: o "jti" o identifica no banco
    jti = generate_url_token()
    crud.store_refresh_token(
        db, user, jti, datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return Token(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token({**claims, "jti": jti}),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
@limiter.limit(LOGIN_LIMIT)
def refresh_tokens(
    request: Request,
    data: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Troca um refresh token válido por um par novo (access + refresh)."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão expirada. Entre novamente.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    payload = decode_access_token(data.refresh_token)
    if payload is None or payload.get("typ") != REFRESH_TOKEN_TYPE:
        raise invalid

    user_id = str(payload.get("sub", ""))
    user = crud.get_user_by_id(db, int(user_id)) if user_id.isdigit() else None

    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
        or payload.get("ver", 0) != user.token_version
        or not payload.get("jti")
    ):
        raise invalid

    outcome = crud.use_refresh_token(db, user, str(payload["jti"]))

    if outcome == "reused":
        # Um token já gasto voltou: alguém pode ter copiado a sessão.
        # Encerra TODAS as sessões; o dono entra de novo com a senha.
        crud.revoke_all_tokens(db, user)
        audit.record(db, request, audit.TOKEN_REUSE_DETECTED, user_id=user.id)
        raise invalid

    if outcome == "invalid":
        raise invalid

    audit.record(db, request, audit.TOKEN_REFRESH, user_id=user.id)
    return _issue_tokens(db, user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Encerra TODAS as sessões do usuário, em todos os dispositivos:
    a versão aumenta e todo access/refresh token emitido antes deixa de valer.
    """
    crud.revoke_all_tokens(db, current_user)
    audit.record(db, request, audit.LOGOUT, user_id=current_user.id)
    return MessageResponse(message="Sessão encerrada em todos os dispositivos.")


# Rota protegida: devolve os dados do psicólogo dono do token
@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user


# ---------------------------------------------------------------------
# Recuperação de senha
# ---------------------------------------------------------------------

@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit(PASSWORD_RESET_LIMIT)
def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, data.email)

    if user is not None and user.is_active:
        token = crud.create_user_token(
            db, user, crud.PASSWORD_RESET,
            timedelta(minutes=PASSWORD_RESET_VALID_MINUTES)
        )
        background_tasks.add_task(
            email_service.send_password_reset_email,
            user.email, token, PASSWORD_RESET_VALID_MINUTES
        )

    # Registrado nos dois casos (com ou sem conta), para não criar
    # diferença de tempo entre eles
    audit.record(
        db, request, audit.PASSWORD_RESET_REQUESTED,
        user_id=user.id if user else None
    )

    # Mesma resposta exista o e-mail ou não (evita enumeração de usuários)
    return MessageResponse(
        message="Se este e-mail estiver cadastrado, enviaremos um link para redefinir a senha."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit(PASSWORD_RESET_LIMIT)
def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    user = crud.consume_user_token(db, data.token, crud.PASSWORD_RESET)

    if user is None:
        audit.record(db, request, audit.PASSWORD_RESET_INVALID_TOKEN)
        raise INVALID_LINK

    crud.reset_password(db, user, data.new_password)
    audit.record(db, request, audit.PASSWORD_RESET_COMPLETED, user_id=user.id)

    # O link de redefinição só chega a quem controla a caixa de entrada:
    # isso já comprova o e-mail, então a conta fica confirmada também.
    if user.email_verified_at is None:
        crud.mark_email_verified(db, user)
        audit.record(db, request, audit.EMAIL_VERIFIED, user_id=user.id)

    return MessageResponse(
        message="Senha redefinida com sucesso. Entre novamente com a nova senha."
    )


# ---------------------------------------------------------------------
# Verificação de e-mail
# ---------------------------------------------------------------------

# Não exige login: quem ainda não confirmou o e-mail não consegue entrar.
@router.post(
    "/verify-email/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit(EMAIL_VERIFICATION_LIMIT)
def request_email_verification(
    request: Request,
    data: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, data.email)

    if user is not None and user.is_active and user.email_verified_at is None:
        _queue_verification_email(db, user, background_tasks)

    # Mesma resposta em todos os casos (evita enumeração de usuários)
    return MessageResponse(
        message="Se este e-mail estiver cadastrado e ainda não confirmado, "
                "enviaremos um novo link de confirmação."
    )


@router.post("/verify-email/confirm", response_model=MessageResponse)
@limiter.limit(EMAIL_VERIFICATION_LIMIT)
def confirm_email_verification(
    request: Request,
    data: EmailVerificationConfirm,
    db: Session = Depends(get_db)
):
    user = crud.consume_user_token(db, data.token, crud.EMAIL_VERIFICATION)

    if user is None:
        raise INVALID_LINK

    crud.mark_email_verified(db, user)
    audit.record(db, request, audit.EMAIL_VERIFIED, user_id=user.id)

    return MessageResponse(message="E-mail confirmado com sucesso.")
