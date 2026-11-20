"""Modo demonstração: conta temporária por visitante, dados fictícios, limpeza e proteções."""
from datetime import timedelta

import pytest

from app import demo
from app.ai import demo as demo_ai
from app.database.models import Appointment, ClinicalNote, Patient, User
from app.timeutils import now_utc


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")


def _start(client):
    response = client.post("/demo/session")
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_demo_is_off_by_default(client):
    assert client.post("/demo/session").status_code == 404


def test_demo_session_comes_with_fictitious_data(client, demo_on):
    headers = _start(client)
    me = client.get("/auth/me", headers=headers).json()
    assert me["email"].startswith("demo-")

    patients = client.get("/patients", headers=headers).json()
    assert len(patients) == len(demo.PATIENTS)
    dashboard = client.get("/dashboard", headers=headers).json()
    assert len(dashboard["notes_to_review"]) == 1
    assert sum(m["completed"] for m in dashboard["insights"]["months"]) > 0


def test_each_visitor_gets_an_isolated_account(client, demo_on):
    first, second = _start(client), _start(client)
    mine = client.get("/patients", headers=first).json()[0]
    client.put(f"/patients/{mine['id']}", json={"full_name": "Alterado Pelo Visitante"}, headers=first)

    other_names = [p["full_name"] for p in client.get("/patients", headers=second).json()]
    assert "Alterado Pelo Visitante" not in other_names
    assert client.get(f"/patients/{mine['id']}", headers=second).status_code == 404


def test_expired_demo_accounts_are_deleted_completely(client, db_session, demo_on):
    _start(client)
    user = db_session.query(User).one()
    user.demo_expires_at = now_utc() - timedelta(minutes=1)
    db_session.commit()

    assert demo.purge_expired(db_session) == 1
    for model in (User, Patient, Appointment, ClinicalNote):
        assert db_session.query(model).count() == 0


def test_demo_closes_signup_and_password_reset(client, demo_on):
    assert client.post("/auth/register", json={"full_name": "X", "email": "x@exemplo.com",
                                               "password": "SenhaFicticia123!"}).status_code == 403
    assert client.post("/auth/password-reset/request", json={"email": "x@exemplo.com"}).status_code == 403


def test_demo_has_a_cap_on_active_accounts(client, demo_on, monkeypatch):
    monkeypatch.setenv("DEMO_MAX_ACTIVE", "1")
    _start(client)
    assert client.post("/demo/session").status_code == 503


def test_internal_key_blocks_direct_calls(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "k" * 40)
    assert client.get("/health").status_code == 200  # monitoramento continua aberto
    assert client.post("/auth/login", data={"username": "a@b.com", "password": "x"}).status_code == 401
    ok = client.post("/auth/login", data={"username": "a@b.com", "password": "x"},
                     headers={"X-Internal-Key": "k" * 40})
    assert ok.status_code != 401 or ok.json()["detail"] != "Não autorizado"


def test_demo_ai_only_organizes_the_given_text():
    text = ("Paciente falou sobre o trabalho e sobre o sono. "
            "Combinamos retomar o assunto na próxima sessão. Talvez mude de emprego?")
    summary = demo_ai.summarize(text)
    assert "Trabalho" in summary.topicos and "Sono" in summary.topicos
    assert summary.pontos_de_acompanhamento == ["Combinamos retomar o assunto na próxima sessão."]
    assert summary.trechos_para_revisao == ["Talvez mude de emprego?"]
    # Nada além do que estava no texto
    assert all(part in text for part in summary.pontos_de_acompanhamento + summary.trechos_para_revisao)
