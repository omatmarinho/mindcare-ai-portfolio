"""Recuperação de senha por e-mail e revogação de tokens."""
import re
from datetime import datetime, timedelta, timezone

from app.database.models import UserToken
from app.security import hash_url_token
from tests.conftest import TEST_PASSWORD

NEW_PASSWORD = "NovaSenhaSegura456!"


def _token_from_email(message) -> str:
    return re.search(r"token=([\w-]+)", message.text).group(1)


def _request_reset(client, email):
    return client.post("/auth/password-reset/request", json={"email": email})


def test_request_sends_email_to_existing_user(client, user_a, outbox):
    response = _request_reset(client, user_a.email)
    assert response.status_code == 202
    assert len(outbox) == 1
    assert outbox[0].to == user_a.email
    assert "redefinir-senha?token=" in outbox[0].text


def test_request_for_unknown_email_has_same_response_and_sends_nothing(client, user_a, outbox):
    known = _request_reset(client, user_a.email)
    unknown = _request_reset(client, "naoexiste@psinara.com.br")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox) == 1  # só o do usuário existente


def test_request_for_inactive_user_sends_nothing(client, db_session, user_a, outbox):
    user_a.is_active = False
    db_session.commit()
    assert _request_reset(client, user_a.email).status_code == 202
    assert outbox == []


def test_only_hash_is_stored_in_database(client, db_session, user_a, outbox):
    _request_reset(client, user_a.email)
    raw = _token_from_email(outbox[0])
    stored = db_session.query(UserToken).one()
    assert stored.token_hash == hash_url_token(raw)
    assert raw not in stored.token_hash


def test_full_reset_flow(client, user_a, outbox):
    _request_reset(client, user_a.email)
    token = _token_from_email(outbox[0])

    response = client.post("/auth/password-reset/confirm", json={
        "token": token, "new_password": NEW_PASSWORD,
    })
    assert response.status_code == 200

    old = client.post("/auth/login", data={"username": user_a.email, "password": TEST_PASSWORD})
    new = client.post("/auth/login", data={"username": user_a.email, "password": NEW_PASSWORD})
    assert old.status_code == 401
    assert new.status_code == 200


def test_token_cannot_be_used_twice(client, user_a, outbox):
    _request_reset(client, user_a.email)
    token = _token_from_email(outbox[0])

    first = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD})
    second = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "OutraSenha789!"})
    assert first.status_code == 200
    assert second.status_code == 400


def test_expired_token_is_rejected(client, db_session, user_a, outbox):
    _request_reset(client, user_a.email)
    token = _token_from_email(outbox[0])

    stored = db_session.query(UserToken).one()
    stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    response = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400


def test_invalid_token_is_rejected(client, user_a):
    response = client.post("/auth/password-reset/confirm", json={
        "token": "token-inventado", "new_password": NEW_PASSWORD,
    })
    assert response.status_code == 400


def test_new_request_invalidates_previous_link(client, user_a, outbox):
    _request_reset(client, user_a.email)
    _request_reset(client, user_a.email)
    old_token = _token_from_email(outbox[0])
    new_token = _token_from_email(outbox[1])

    assert client.post("/auth/password-reset/confirm", json={
        "token": old_token, "new_password": NEW_PASSWORD}).status_code == 400
    assert client.post("/auth/password-reset/confirm", json={
        "token": new_token, "new_password": NEW_PASSWORD}).status_code == 200


def test_new_password_must_be_valid(client, user_a, outbox):
    _request_reset(client, user_a.email)
    token = _token_from_email(outbox[0])
    response = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "curta"})
    assert response.status_code == 422


def test_email_verification_token_cannot_reset_password(client, outbox):
    """Cada token só serve para a sua finalidade."""
    client.post("/auth/register", json={
        "full_name": "Novo", "email": "novo@psinara.com.br", "password": TEST_PASSWORD,
    })
    verification_token = _token_from_email(outbox[0])

    response = client.post("/auth/password-reset/confirm", json={
        "token": verification_token, "new_password": NEW_PASSWORD,
    })
    assert response.status_code == 400


# ---------- Revogação de JWT ----------

def test_password_reset_revokes_existing_jwts(client, user_a, auth_a, outbox):
    assert client.get("/auth/me", headers=auth_a).status_code == 200

    _request_reset(client, user_a.email)
    token = _token_from_email(outbox[0])
    client.post("/auth/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD})

    # O JWT obtido antes da troca de senha não vale mais
    assert client.get("/auth/me", headers=auth_a).status_code == 401
