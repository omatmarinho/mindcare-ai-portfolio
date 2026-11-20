from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Patient, RefreshToken, User, UserToken
from app.security import (
    hash_password,
    verify_password,
    generate_url_token,
    hash_url_token,
    DUMMY_PASSWORD_HASH
)

# Finalidades dos tokens enviados por e-mail
PASSWORD_RESET = "password_reset"
EMAIL_VERIFICATION = "email_verification"


# ---------------------------------------------------------------------
# Pacientes
#
# REGRA DE SEGURANÇA: toda função recebe "owner_id" (o id do psicólogo
# autenticado) e SEMPRE filtra por ele. Um paciente de outro psicólogo
# é tratado exatamente como um paciente inexistente.
# ---------------------------------------------------------------------

def create_patient(
    db: Session,
    owner_id: int,
    full_name: str,
    email: str | None = None,
    phone: str | None = None
):
    new_patient = Patient(
        full_name=full_name,
        email=email,
        user_id=owner_id,
        phone=phone,
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient


def get_patients(db: Session, owner_id: int, archived: bool = False):
    query = db.query(Patient).filter(Patient.user_id == owner_id)

    if archived:
        query = query.filter(Patient.archived_at.is_not(None))
    else:
        query = query.filter(Patient.archived_at.is_(None))

    return query.order_by(Patient.id).all()


def get_patient(db: Session, owner_id: int, patient_id: int):
    return db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.user_id == owner_id
    ).first()


def update_patient(
    db: Session,
    owner_id: int,
    patient_id: int,
    full_name: str,
    email: str | None = None,
    phone: str | None = None
):
    patient = get_patient(db, owner_id, patient_id)

    if patient is None:
        return None

    patient.full_name = full_name
    patient.email = email
    patient.phone = phone

    db.commit()
    db.refresh(patient)

    return patient


# Arquivar em vez de apagar: os registros precisam ser guardados
# (Resolução CFP nº 001/2009, mínimo de 5 anos). Os dados permanecem no banco.
def archive_patient(db: Session, owner_id: int, patient_id: int):
    patient = get_patient(db, owner_id, patient_id)

    if patient is None:
        return None

    if patient.archived_at is None:
        patient.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patient)

    return patient


def restore_patient(db: Session, owner_id: int, patient_id: int):
    patient = get_patient(db, owner_id, patient_id)

    if patient is None:
        return None

    if patient.archived_at is not None:
        patient.archived_at = None
        db.commit()
        db.refresh(patient)

    return patient


def create_user(
    db: Session,
    full_name: str,
    email: str,
    password: str
):
    existing_user = get_user_by_email(db, email)

    if existing_user:
        return None

    hashed_password = hash_password(password)

    new_user = User(
        full_name=full_name,
        email=email,
        hashed_password=hashed_password,
    )

    db.add(new_user)

    # A verificação acima não basta quando duas requisições com o mesmo
    # e-mail chegam ao mesmo tempo: as duas passam por ela antes de gravar.
    # A restrição UNIQUE do banco é a garantia final; aqui tratamos a recusa.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    db.refresh(new_user)

    return new_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(
        User.email == email
    ).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id
    ).first()


# Verifica as credenciais de login.
# Retorna o usuário se e-mail e senha estiverem corretos e a conta ativa.
# Retorna None em qualquer outro caso, sem revelar o motivo.
def authenticate_user(db: Session, email: str, password: str):
    # O formulário de login não passa pelos schemas, então normalizamos aqui
    email = email.strip().lower()
    user = get_user_by_email(db, email)

    if user is None:
        # Executa uma verificação "de mentira" para gastar o mesmo tempo
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


# ---------------------------------------------------------------------
# Tokens de uso único (links enviados por e-mail)
# ---------------------------------------------------------------------

def create_user_token(db: Session, user: User, purpose: str, valid_for: timedelta) -> str:
    """
    Cria um token novo e devolve o token "puro" (para ir no e-mail).
    No banco fica só o hash. Pedidos anteriores ainda não usados, da mesma
    finalidade, são descartados: só o link mais recente funciona.
    """
    db.query(UserToken).filter(
        UserToken.user_id == user.id,
        UserToken.purpose == purpose,
        UserToken.used_at.is_(None)
    ).delete(synchronize_session=False)

    raw_token = generate_url_token()
    db.add(UserToken(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_url_token(raw_token),
        expires_at=datetime.now(timezone.utc) + valid_for
    ))
    db.commit()

    return raw_token


def consume_user_token(db: Session, raw_token: str, purpose: str) -> User | None:
    """
    Valida e "gasta" um token. Devolve o usuário ou None se o token não
    existir, já tiver sido usado, estiver vencido ou a conta estiver inativa.
    """
    now = datetime.now(timezone.utc)

    token = db.query(UserToken).filter(
        UserToken.token_hash == hash_url_token(raw_token),
        UserToken.purpose == purpose,
        UserToken.used_at.is_(None),
        UserToken.expires_at > now
    ).first()

    if token is None:
        return None

    user = get_user_by_id(db, token.user_id)
    if user is None or not user.is_active:
        return None

    token.used_at = now
    # Envia a marcação ao banco já (sem confirmar a transação). Sem isso,
    # uma consulta seguinte por "tokens não usados" ainda o enxergaria
    # como não usado, porque a sessão usa autoflush=False.
    db.flush()

    return user  # quem chamou faz o commit junto com a alteração no usuário


def reset_password(db: Session, user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)

    # Invalida todos os JWTs emitidos antes da troca de senha
    user.token_version = (user.token_version or 0) + 1

    # Outros links de redefinição pendentes deixam de valer
    db.query(UserToken).filter(
        UserToken.user_id == user.id,
        UserToken.purpose == PASSWORD_RESET,
        UserToken.used_at.is_(None)
    ).delete(synchronize_session=False)

    db.commit()


# ---------------------------------------------------------------------
# Refresh tokens (uso único, com detecção de reuso)
# ---------------------------------------------------------------------

# Tolerância para o próprio navegador pedir duas renovações ao mesmo tempo
# (várias abas ou requisições paralelas) sem que isso pareça um roubo.
REFRESH_REUSE_GRACE = timedelta(seconds=30)


def store_refresh_token(db: Session, user: User, jti: str, expires_at: datetime) -> None:
    now = datetime.now(timezone.utc)
    # Limpeza: tokens vencidos do usuário não servem para mais nada
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.expires_at < now
    ).delete(synchronize_session=False)
    db.add(RefreshToken(user_id=user.id, jti_hash=hash_url_token(jti), expires_at=expires_at))
    db.commit()


def use_refresh_token(db: Session, user: User, jti: str) -> str:
    """
    Gasta um refresh token. Resultados:
    - "ok": primeiro uso.
    - "grace": já usado há menos de REFRESH_REUSE_GRACE (pedidos simultâneos).
    - "reused": já usado antes disso. Sinal de roubo.
    - "invalid": desconhecido ou vencido.
    """
    now = datetime.now(timezone.utc)
    token = db.query(RefreshToken).filter(
        RefreshToken.jti_hash == hash_url_token(jti),
        RefreshToken.user_id == user.id,
        RefreshToken.expires_at > now,
    ).first()
    if token is None:
        return "invalid"

    if token.used_at is None:
        token.used_at = now
        db.commit()
        return "ok"

    recently_used = db.query(RefreshToken.id).filter(
        RefreshToken.id == token.id, RefreshToken.used_at > now - REFRESH_REUSE_GRACE
    ).first()
    return "grace" if recently_used else "reused"


def revoke_all_tokens(db: Session, user: User) -> None:
    """Invalida todos os JWTs (access e refresh) já emitidos para o usuário."""
    user.token_version = (user.token_version or 0) + 1
    db.commit()


def mark_email_verified(db: Session, user: User) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    db.commit()   