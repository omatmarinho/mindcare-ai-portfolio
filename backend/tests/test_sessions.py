"""Refresh tokens, logout e consulta da auditoria."""
from app import audit
from app.security import create_refresh_token
from tests.conftest import TEST_PASSWORD


def _login_pair(client, email):
    response = client.post("/auth/login", data={"username": email, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return response.json()


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Refresh ----------

def test_login_returns_access_and_refresh_tokens(client, user_a):
    body = _login_pair(client, user_a.email)
    assert body["access_token"] and body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]
    assert body["expires_in"] == 30 * 60


def test_refresh_returns_new_working_pair(client, user_a):
    pair = _login_pair(client, user_a.email)
    response = client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert response.status_code == 200
    new_access = response.json()["access_token"]
    assert client.get("/auth/me", headers=_bearer(new_access)).status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(client, user_a):
    pair = _login_pair(client, user_a.email)
    assert client.get("/auth/me", headers=_bearer(pair["refresh_token"])).status_code == 401


def test_access_token_cannot_be_used_to_refresh(client, user_a):
    pair = _login_pair(client, user_a.email)
    response = client.post("/auth/refresh", json={"refresh_token": pair["access_token"]})
    assert response.status_code == 401


def test_refresh_with_garbage_is_rejected(client):
    assert client.post("/auth/refresh", json={"refresh_token": "lixo"}).status_code == 401


def test_refresh_for_deactivated_user_is_rejected(client, db_session, user_a):
    pair = _login_pair(client, user_a.email)
    user_a.is_active = False
    db_session.commit()
    assert client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401


def _refresh(client, token):
    return client.post("/auth/refresh", json={"refresh_token": token})


def test_refresh_token_is_single_use_with_short_grace(client, user_a):
    pair = _login_pair(client, user_a.email)
    assert _refresh(client, pair["refresh_token"]).status_code == 200
    # Segundo pedido logo em seguida (ex.: duas abas): tolerado
    assert _refresh(client, pair["refresh_token"]).status_code == 200


def test_reused_refresh_token_revokes_every_session(client, db_session, user_a):
    from datetime import datetime, timedelta, timezone

    from app.database.models import AuditLog, RefreshToken

    pair = _login_pair(client, user_a.email)
    rotated = _refresh(client, pair["refresh_token"]).json()

    # Simula o token antigo reaparecendo bem depois de ter sido usado
    db_session.query(RefreshToken).filter(RefreshToken.used_at.isnot(None)).update(
        {"used_at": datetime.now(timezone.utc) - timedelta(minutes=5)}
    )
    db_session.commit()

    assert _refresh(client, pair["refresh_token"]).status_code == 401
    # Todas as sessões caíram, inclusive a do par novo
    assert client.get("/auth/me", headers=_bearer(rotated["access_token"])).status_code == 401
    assert _refresh(client, rotated["refresh_token"]).status_code == 401
    assert db_session.query(AuditLog).filter(AuditLog.action == audit.TOKEN_REUSE_DETECTED).count() == 1


def test_refresh_token_without_jti_is_rejected(client, user_a):
    legacy = create_refresh_token({"sub": str(user_a.id), "ver": user_a.token_version})
    assert _refresh(client, legacy).status_code == 401


def test_refresh_token_of_another_user_jti_is_rejected(client, user_a, user_b):
    pair_b = _login_pair(client, user_b.email)
    from app.security import decode_access_token
    jti_b = decode_access_token(pair_b["refresh_token"])["jti"]
    forged = create_refresh_token({"sub": str(user_a.id), "ver": user_a.token_version, "jti": jti_b})
    assert _refresh(client, forged).status_code == 401


def test_refresh_with_old_version_is_rejected(client, user_a):
    stale = create_refresh_token({"sub": str(user_a.id), "ver": user_a.token_version + 5})
    assert client.post("/auth/refresh", json={"refresh_token": stale}).status_code == 401


# ---------- Logout ----------

def test_logout_revokes_access_and_refresh_tokens(client, user_a):
    pair = _login_pair(client, user_a.email)
    other_device = _login_pair(client, user_a.email)

    response = client.post("/auth/logout", headers=_bearer(pair["access_token"]))
    assert response.status_code == 200

    # Tudo o que foi emitido antes do logout para de funcionar, em qualquer dispositivo
    assert client.get("/auth/me", headers=_bearer(pair["access_token"])).status_code == 401
    assert client.get("/auth/me", headers=_bearer(other_device["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401

    # Um login novo volta a funcionar
    fresh = _login_pair(client, user_a.email)
    assert client.get("/auth/me", headers=_bearer(fresh["access_token"])).status_code == 200


def test_logout_requires_login(client):
    assert client.post("/auth/logout").status_code == 401


# ---------- Consulta da auditoria ----------

def test_audit_logs_show_only_own_actions(client, auth_a, auth_b, user_a):
    patient = client.post("/patients", json={"full_name": "Paciente A"}, headers=auth_a).json()
    client.get(f"/patients/{patient['id']}", headers=auth_b)  # tentativa do B

    logs_a = client.get("/audit-logs", headers=auth_a).json()
    logs_b = client.get("/audit-logs", headers=auth_b).json()

    actions_a = [log["action"] for log in logs_a]
    actions_b = [log["action"] for log in logs_b]
    assert audit.PATIENT_CREATE in actions_a
    assert audit.PATIENT_ACCESS_DENIED not in actions_a
    assert audit.PATIENT_ACCESS_DENIED in actions_b
    assert audit.PATIENT_CREATE not in actions_b


def test_audit_logs_filter_by_patient_newest_first(client, auth_a):
    p1 = client.post("/patients", json={"full_name": "P1"}, headers=auth_a).json()
    p2 = client.post("/patients", json={"full_name": "P2"}, headers=auth_a).json()
    client.get(f"/patients/{p1['id']}", headers=auth_a)
    client.put(f"/patients/{p1['id']}", json={"full_name": "P1b"}, headers=auth_a)

    logs = client.get(f"/audit-logs?patient_id={p1['id']}", headers=auth_a).json()
    assert [log["action"] for log in logs] == [
        audit.PATIENT_UPDATE, audit.PATIENT_READ, audit.PATIENT_CREATE,
    ]
    assert all(log["resource_id"] == p1["id"] for log in logs)
    assert p2["id"] not in [log["resource_id"] for log in logs]


def test_audit_logs_pagination_limits(client, auth_a):
    assert client.get("/audit-logs?limit=0", headers=auth_a).status_code == 422
    assert client.get("/audit-logs?limit=201", headers=auth_a).status_code == 422
    assert len(client.get("/audit-logs?limit=1", headers=auth_a).json()) == 1


def test_audit_logs_require_login(client):
    assert client.get("/audit-logs").status_code == 401


# ---------- Logs da aplicação ----------

def test_every_response_has_request_id(client):
    response = client.get("/health")
    assert len(response.headers["X-Request-ID"]) == 16
