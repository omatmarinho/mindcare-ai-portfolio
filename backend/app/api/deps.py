from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import crud
from app.database.models import User
from app.security import ACCESS_TOKEN_TYPE, decode_access_token

# Diz ao FastAPI que o token vem no cabeçalho "Authorization: Bearer <token>"
# e que ele é obtido na rota /auth/login (isso cria o botão "Authorize" no /docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

EMAIL_NOT_VERIFIED_DETAIL = (
    "Confirme seu e-mail antes de entrar. "
    "Se não recebeu o link, solicite um novo."
)


# Dependência que identifica o psicólogo autenticado.
# Qualquer rota que a utilizar passa a exigir um token válido.
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    # 1) O token é autêntico e está dentro da validade?
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 1b) É um token de ACESSO? (um refresh token não abre rotas)
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise credentials_exception

    # 2) O token diz de quem ele é? ("sub" guarda o id como texto)
    user_id = payload.get("sub")
    if user_id is None or not str(user_id).isdigit():
        raise credentials_exception

    # 3) Esse usuário ainda existe e está ativo?
    user = crud.get_user_by_id(db, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    # 4) O token foi emitido depois da última troca de senha?
    #    (tokens sem "ver" são de antes desse recurso e contam como versão 0)
    if payload.get("ver", 0) != user.token_version:
        raise credentials_exception

    # 5) O e-mail está confirmado? (o login já exige; esta checagem cobre
    #    tokens emitidos antes de a regra existir)
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_NOT_VERIFIED_DETAIL
        )

    return user
