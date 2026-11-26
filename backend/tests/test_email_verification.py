"""Verificação de e-mail (obrigatória para entrar)."""
import re

from app.security import create_access_token
from tests.conftest import TEST_PASSWORD

EMAIL = "novo@psinara.com.br"


def _token_from_email(message) -> str:
    return re.search(r"token=([\w-]+)", message.text).group(1)


def _register(client, email=EMAIL):
    return client.post("/auth/register", json={
        "full_name": "Novo Psicologo", "email": email, "password": TEST_PASSWORD,
    })


def _login(client, email=EMAIL):
    return client.post("/auth/login", data={"username": email, "password": TEST_PASSWORD})


def _resend(client, email=EMAIL):
    return client.post("/auth/verify-email/request", json={"email": email})


# ---------- Cadastro e confirmação ----------

def test_password_reset_also_confirms_email(client, outbox):
    """O link de redefinição chega pela caixa de entrada: isso comprova o e-mail."""
    _register(client)
    assert _login(client).status_code == 403  # ainda não confirmado

    client.post("/auth/password-reset/request", json={"email": EMAIL})
    reset_mail = next(m for m in outbox if "redefinir-senha?token=" in m.text)
    token = _token_from_email(reset_mail)
    new_password = "OutraSenhaSegura789!"
    assert client.post("/auth/password-reset/confirm",
                       json={"token": token, "new_password": new_password}).status_code == 200

    login = client.post("/auth/login", data={"username": EMAIL, "password": new_password})
    assert login.status_code == 200

def test_register_sends_verification_email(client, outbox):
    response = _register(client)
    assert response.status_code == 202
    assert len(outbox) == 1
    assert "verificar-email?token=" in outbox[0].text


def test_confirm_marks_email_as_verified(client, outbox):
    _register(client)
    token = _token_from_email(outbox[0])

    assert client.post("/auth/verify-email/confirm", json={"token": token}).status_code == 200

    access = _login(client).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).json()
    assert me["email_verified_at"] is not None


def test_verification_token_is_single_use(client, outbox):
    _register(client)
    token = _token_from_email(outbox[0])
    assert client.post("/auth/verify-email/confirm", json={"token": token}).status_code == 200
    assert client.post("/auth/verify-email/confirm", json={"token": token}).status_code == 400


def test_invalid_verification_token_is_rejected(client):
    assert client.post("/auth/verify-email/confirm", json={"token": "inventado"}).status_code == 400


# ---------- Bloqueio de quem não confirmou ----------

def test_unverified_user_cannot_login(client, outbox):
    _register(client)
    response = _login(client)
    assert response.status_code == 403
    assert "Confirme seu e-mail" in response.json()["detail"]


def test_unverified_user_with_wrong_password_gets_generic_401(client, outbox):
    """Sem a senha certa, não se descobre nada sobre a confirmação do e-mail."""
    _register(client)
    response = client.post("/auth/login", data={"username": EMAIL, "password": "SenhaErrada123!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha incorretos."


def test_user_can_login_after_confirming(client, outbox):
    _register(client)
    assert _login(client).status_code == 403

    client.post("/auth/verify-email/confirm", json={"token": _token_from_email(outbox[0])})
    assert _login(client).status_code == 200


def test_token_of_unverified_user_is_rejected(client, db_session, outbox):
    """Cobre tokens emitidos antes de a regra existir."""
    from app.database import crud
    _register(client)
    user_id = crud.get_user_by_email(db_session, EMAIL).id
    old_token = create_access_token({"sub": str(user_id), "ver": 0})

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert response.status_code == 403


# ---------- Reenvio do link (não exige login) ----------

def test_resend_sends_new_link_and_invalidates_old(client, outbox):
    _register(client)

    response = _resend(client)
    assert response.status_code == 202
    assert len(outbox) == 2

    old_token = _token_from_email(outbox[0])
    new_token = _token_from_email(outbox[1])
    assert client.post("/auth/verify-email/confirm", json={"token": old_token}).status_code == 400
    assert client.post("/auth/verify-email/confirm", json={"token": new_token}).status_code == 200


def test_resend_has_same_response_for_unknown_and_verified_emails(client, user_a, outbox):
    _register(client)
    pending = _resend(client, EMAIL)                         # cadastrado, não confirmado
    verified = _resend(client, user_a.email)                 # já confirmado
    unknown = _resend(client, "naoexiste@psinara.com.br")    # não existe

    assert pending.status_code == verified.status_code == unknown.status_code == 202
    assert pending.json() == verified.json() == unknown.json()

    # Só o cadastro pendente recebe e-mail (1 do cadastro + 1 do reenvio)
    assert [m.to for m in outbox] == [EMAIL, EMAIL]
