"""Testes da autenticação: cadastro, login e rota protegida /auth/me."""
from datetime import datetime, timedelta, timezone

import jwt

from app.security import JWT_ALGORITHM, JWT_SECRET_KEY, create_access_token
from tests.conftest import TEST_PASSWORD


# ---------- Cadastro ----------

def _register(client, email, full_name="Novo Psicologo"):
    return client.post("/auth/register", json={
        "full_name": full_name, "email": email, "password": TEST_PASSWORD,
    })


def test_register_creates_user_and_returns_generic_message(client, db_session):
    response = _register(client, "novo@mindcareai.com")
    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"message"}  # nenhum dado da conta na resposta

    from app.database import crud
    user = crud.get_user_by_email(db_session, "novo@mindcareai.com")
    assert user is not None
    assert user.hashed_password != TEST_PASSWORD  # guardada como hash


def test_register_existing_email_has_identical_response(client, user_a):
    """O cadastro não pode ser usado para descobrir quem tem conta."""
    new = _register(client, "outro@mindcareai.com")
    existing = _register(client, user_a.email, full_name="Copia")
    assert new.status_code == existing.status_code == 202
    assert new.json() == existing.json()


def test_register_existing_verified_email_notifies_owner(client, db_session, user_a, outbox):
    _register(client, user_a.email, full_name="Impostor")

    assert len(outbox) == 1
    assert outbox[0].to == user_a.email
    assert "já possui uma conta" in outbox[0].text

    # A conta original não foi alterada
    db_session.refresh(user_a)
    assert user_a.full_name == "Psicologo A"


def test_register_existing_unverified_email_resends_verification(client, outbox):
    _register(client, "pendente@mindcareai.com")
    _register(client, "pendente@mindcareai.com")
    assert len(outbox) == 2
    assert all("verificar-email?token=" in m.text for m in outbox)


def test_register_existing_inactive_email_sends_nothing(client, db_session, user_a, outbox):
    user_a.is_active = False
    db_session.commit()
    assert _register(client, user_a.email).status_code == 202
    assert outbox == []


# ---------- Login ----------

def test_login_success_returns_bearer_token(client, user_a):
    response = client.post("/auth/login", data={
        "username": user_a.email, "password": TEST_PASSWORD,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401(client, user_a):
    response = client.post("/auth/login", data={
        "username": user_a.email, "password": "SenhaErrada123!",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha incorretos."


def test_login_unknown_email_has_same_message_as_wrong_password(client):
    response = client.post("/auth/login", data={
        "username": "naoexiste@mindcareai.com", "password": TEST_PASSWORD,
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha incorretos."


def test_login_inactive_user_returns_401(client, db_session, user_a):
    user_a.is_active = False
    db_session.commit()
    response = client.post("/auth/login", data={
        "username": user_a.email, "password": TEST_PASSWORD,
    })
    assert response.status_code == 401


# ---------- Rota protegida /auth/me ----------

def test_me_with_valid_token_returns_own_user(client, user_a, auth_a):
    response = client.get("/auth/me", headers=auth_a)
    assert response.status_code == 200
    assert response.json()["id"] == user_a.id
    assert response.json()["email"] == user_a.email


def test_me_without_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer isso-nao-e-um-token"})
    assert response.status_code == 401


def test_me_with_tampered_token_returns_401(client, user_a):
    token = create_access_token({"sub": str(user_a.id)})
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401


def test_me_with_expired_token_returns_401(client, user_a):
    # Token que "já nasceu vencido": expirou 1 minuto atrás
    expired = jwt.encode(
        {"sub": str(user_a.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_me_with_token_without_exp_returns_401(client, user_a):
    # Token sem data de expiração seria eterno: deve ser recusado
    no_exp = jwt.encode({"sub": str(user_a.id)}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {no_exp}"})
    assert response.status_code == 401


def test_me_with_token_signed_by_other_key_returns_401(client, user_a):
    forged = jwt.encode(
        {"sub": str(user_a.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "chave-falsa-de-um-atacante-com-32-bytes!!",
        algorithm=JWT_ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_me_for_deleted_user_returns_401(client, user_a):
    # Token válido, mas de um id que não existe no banco
    token = create_access_token({"sub": "999999"})
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_for_deactivated_user_returns_401(client, db_session, user_a, auth_a):
    # Conta desativada depois do login: o token antigo deve parar de funcionar
    user_a.is_active = False
    db_session.commit()
    response = client.get("/auth/me", headers=auth_a)
    assert response.status_code == 401
