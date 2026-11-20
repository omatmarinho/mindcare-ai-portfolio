
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração do hash de senhas
password_hash = PasswordHash.recommended()

# Configurações do JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Tipos de token ("typ"): impede usar um refresh token como access token
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY não encontrada no arquivo .env")


# Gera o hash da senha
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# Hash "falso", usado no login quando o e-mail não existe.
# Assim a resposta demora o mesmo tempo, exista o e-mail ou não.
DUMMY_PASSWORD_HASH = hash_password("senha-ficticia-apenas-para-tempo")


# Verifica a senha
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def _create_token(data: dict, token_type: str, expires_in: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.now(timezone.utc) + expires_in,
        "typ": token_type,
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# Gera um token de acesso JWT (curto: usado em cada requisição)
def create_access_token(data: dict) -> str:
    return _create_token(
        data, ACCESS_TOKEN_TYPE, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


# Gera um refresh token (longo: serve APENAS para obter novos tokens)
def create_refresh_token(data: dict) -> str:
    return _create_token(
        data, REFRESH_TOKEN_TYPE, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


# Valida um token JWT e retorna seu conteúdo (payload)
# Retorna None se o token for inválido, adulterado ou expirado
def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp"]}
        )

        return payload

    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------------
# Tokens de uso único enviados por e-mail
# ---------------------------------------------------------------------

def generate_url_token() -> str:
    """Token aleatório e imprevisível para colocar em um link (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_url_token(token: str) -> str:
    """
    Hash SHA-256 do token, que é o que fica guardado no banco.

    Por que SHA-256 aqui e Argon2 nas senhas? Senhas são escolhidas por
    pessoas e podem ser adivinhadas; o Argon2 é lento justamente para
    dificultar tentativas. Este token é totalmente aleatório (256 bits):
    não há como adivinhá-lo, então um hash rápido basta.
    """
    return hashlib.sha256(token.encode()).hexdigest()
