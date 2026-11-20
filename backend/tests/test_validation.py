"""Validação de entradas e normalização de e-mail."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.database import crud
from tests.conftest import TEST_PASSWORD


def _register(client, **overrides):
    payload = {
        "full_name": "Psicologo",
        "email": "valido@mindcareai.com",
        "password": TEST_PASSWORD,
       
    }
    payload.update(overrides)
    return client.post("/auth/register", json=payload)


# ---------- Cadastro de psicólogo ----------

@pytest.mark.parametrize("password", ["", "1234567"])
def test_register_rejects_short_password(client, password):
    assert _register(client, password=password).status_code == 422


def test_register_rejects_huge_password(client):
    # Senhas gigantes deixariam o Argon2 lento de propósito (ataque de negação de serviço)
    assert _register(client, password="a" * 129).status_code == 422


@pytest.mark.parametrize("full_name", ["", "   ", "x" * 151])
def test_register_rejects_invalid_full_name(client, full_name):
    assert _register(client, full_name=full_name).status_code == 422


def test_register_rejects_email_longer_than_column(client):
    long_email = "a" * 140 + "@mindcareai.com"  # 155 caracteres; a coluna aceita 150
    assert _register(client, email=long_email).status_code == 422


def test_register_strips_full_name(client, db_session):
    response = _register(client, full_name="  Psicologo Com Espacos  ")
    assert response.status_code == 202
    user = crud.get_user_by_email(db_session, "valido@mindcareai.com")
    assert user.full_name == "Psicologo Com Espacos"


# ---------- E-mail sem diferenciar maiúsculas ----------

def test_register_stores_email_in_lowercase(client, db_session):
    assert _register(client, email="Fulano@MindCareAI.com").status_code == 202
    assert crud.get_user_by_email(db_session, "fulano@mindcareai.com") is not None


def test_register_same_email_with_other_case_is_duplicate(client, db_session):
    _register(client, email="fulano@mindcareai.com")
    _register(client, email="FULANO@mindcareai.com", full_name="Outro")
    assert db_session.query(crud.User).count() == 1


def test_login_ignores_email_case_and_spaces(client, db_session):
    _register(client, email="fulano@mindcareai.com")
    crud.mark_email_verified(db_session, crud.get_user_by_email(db_session, "fulano@mindcareai.com"))

    response = client.post("/auth/login", data={
        "username": "  Fulano@MindCareAI.com ", "password": TEST_PASSWORD,
    })
    assert response.status_code == 200


# ---------- Concorrência no cadastro ----------

def test_create_user_handles_unique_violation(db_session, monkeypatch):
    """
    Simula duas requisições simultâneas com o mesmo e-mail: as duas passam
    pela verificação "e-mail já existe?" antes de qualquer uma gravar.
    A segunda esbarra na restrição UNIQUE do banco e deve virar 409, não 500.
    """
    crud.create_user(db_session, "Primeiro", "corrida@mindcareai.com", TEST_PASSWORD)

    # Faz a verificação prévia "não enxergar" o usuário já gravado
    monkeypatch.setattr(crud, "get_user_by_email", lambda db, email: None)

    result = crud.create_user(db_session, "Segundo", "corrida@mindcareai.com", TEST_PASSWORD)
    assert result is None

    # A sessão continua utilizável depois do erro (rollback foi feito)
    assert db_session.query(crud.User).count() == 1


# ---------- Pacientes ----------

@pytest.mark.parametrize("full_name", ["", "   ", "x" * 151])
def test_patient_rejects_invalid_full_name(client, auth_a, full_name):
    response = client.post("/patients", json={"full_name": full_name}, headers=auth_a)
    assert response.status_code == 422


def test_patient_email_is_normalized(client, auth_a):
    response = client.post(
        "/patients",
        json={"full_name": "Paciente", "email": "Paciente@Exemplo.COM"},
        headers=auth_a,
    )
    assert response.status_code == 201
    assert response.json()["email"] == "paciente@exemplo.com"
