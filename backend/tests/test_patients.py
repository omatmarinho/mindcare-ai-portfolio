"""
Testes de pacientes, com foco em AUTORIZAÇÃO:
- nenhuma rota de pacientes funciona sem login;
- cada psicólogo só enxerga e altera os próprios pacientes;
- paciente de outro psicólogo se comporta como inexistente (404).
"""
import pytest


def _create_patient(client, headers, full_name="Paciente Ficticio", email=None):
    response = client.post(
        "/patients",
        json={"full_name": full_name, "email": email},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------- Sem login: tudo bloqueado ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/patients"),
    ("post", "/patients"),
    ("get", "/patients/1"),
    ("put", "/patients/1"),
    ("delete", "/patients/1"),
    ("post", "/patients/1/restore"),
])
def test_patient_routes_require_authentication(client, method, path):
    kwargs = {"json": {"full_name": "X"}} if method in ("post", "put") else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


# ---------- Fluxo normal do dono ----------

def test_owner_can_create_list_read_update_and_delete(client, auth_a):
    created = _create_patient(client, auth_a, "Paciente A1", "a1@exemplo.com")
    patient_id = created["id"]
    assert "user_id" not in created  # dado interno, não precisa sair na API

    listed = client.get("/patients", headers=auth_a).json()
    assert [p["id"] for p in listed] == [patient_id]

    read = client.get(f"/patients/{patient_id}", headers=auth_a)
    assert read.status_code == 200
    assert read.json()["full_name"] == "Paciente A1"

    updated = client.put(
        f"/patients/{patient_id}",
        json={"full_name": "Paciente A1 Editado", "email": None},
        headers=auth_a,
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Paciente A1 Editado"

    archived = client.delete(f"/patients/{patient_id}", headers=auth_a)
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/patients", headers=auth_a).json() == []


# ---------- Arquivamento (registros nunca são apagados) ----------

def test_archive_keeps_data_and_moves_to_archived_list(client, db_session, auth_a):
    patient = _create_patient(client, auth_a, "Paciente Arquivado")

    client.delete(f"/patients/{patient['id']}", headers=auth_a)

    active = client.get("/patients", headers=auth_a).json()
    archived = client.get("/patients?archived=true", headers=auth_a).json()
    assert active == []
    assert [p["id"] for p in archived] == [patient["id"]]

    # O registro continua no banco
    from app.database.models import Patient
    assert db_session.get(Patient, patient["id"]) is not None


def test_archived_patient_can_still_be_read(client, auth_a):
    patient = _create_patient(client, auth_a)
    client.delete(f"/patients/{patient['id']}", headers=auth_a)

    response = client.get(f"/patients/{patient['id']}", headers=auth_a)
    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


def test_archive_twice_keeps_original_date(client, auth_a):
    patient = _create_patient(client, auth_a)
    first = client.delete(f"/patients/{patient['id']}", headers=auth_a).json()
    second = client.delete(f"/patients/{patient['id']}", headers=auth_a)
    assert second.status_code == 200
    assert second.json()["archived_at"] == first["archived_at"]


def test_restore_returns_patient_to_active_list(client, auth_a):
    patient = _create_patient(client, auth_a)
    client.delete(f"/patients/{patient['id']}", headers=auth_a)

    restored = client.post(f"/patients/{patient['id']}/restore", headers=auth_a)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert [p["id"] for p in client.get("/patients", headers=auth_a).json()] == [patient["id"]]


def test_archived_list_is_also_isolated(client, auth_a, auth_b):
    patient = _create_patient(client, auth_a)
    client.delete(f"/patients/{patient['id']}", headers=auth_a)
    assert client.get("/patients?archived=true", headers=auth_b).json() == []


def test_other_user_cannot_restore_patient(client, auth_a, auth_b):
    patient = _create_patient(client, auth_a)
    client.delete(f"/patients/{patient['id']}", headers=auth_a)

    response = client.post(f"/patients/{patient['id']}/restore", headers=auth_b)
    assert response.status_code == 404
    # Continua arquivado para o dono
    assert client.get(f"/patients/{patient['id']}", headers=auth_a).json()["archived_at"] is not None


def test_invalid_email_returns_422(client, auth_a):
    response = client.post(
        "/patients",
        json={"full_name": "Paciente", "email": "nao-e-email"},
        headers=auth_a,
    )
    assert response.status_code == 422


# ---------- Isolamento entre psicólogos ----------

def test_list_shows_only_own_patients(client, auth_a, auth_b):
    _create_patient(client, auth_a, "Paciente do A")
    _create_patient(client, auth_b, "Paciente do B")

    names_a = [p["full_name"] for p in client.get("/patients", headers=auth_a).json()]
    names_b = [p["full_name"] for p in client.get("/patients", headers=auth_b).json()]

    assert names_a == ["Paciente do A"]
    assert names_b == ["Paciente do B"]


def test_other_user_cannot_read_patient(client, auth_a, auth_b):
    patient = _create_patient(client, auth_a, "Paciente do A")
    response = client.get(f"/patients/{patient['id']}", headers=auth_b)
    assert response.status_code == 404


def test_other_user_cannot_update_patient(client, auth_a, auth_b):
    patient = _create_patient(client, auth_a, "Paciente do A")

    response = client.put(
        f"/patients/{patient['id']}",
        json={"full_name": "Alterado pelo B", "email": None},
        headers=auth_b,
    )
    assert response.status_code == 404

    # E o dado do A continua intacto
    still = client.get(f"/patients/{patient['id']}", headers=auth_a).json()
    assert still["full_name"] == "Paciente do A"


def test_other_user_cannot_archive_patient(client, auth_a, auth_b):
    patient = _create_patient(client, auth_a, "Paciente do A")

    response = client.delete(f"/patients/{patient['id']}", headers=auth_b)
    assert response.status_code == 404

    # O paciente do A continua ativo
    still = client.get(f"/patients/{patient['id']}", headers=auth_a).json()
    assert still["archived_at"] is None


def test_foreign_patient_looks_exactly_like_missing_patient(client, auth_a, auth_b):
    """Não deve ser possível descobrir se um id existe em outra conta."""
    patient = _create_patient(client, auth_a, "Paciente do A")

    foreign = client.get(f"/patients/{patient['id']}", headers=auth_b)
    missing = client.get("/patients/999999", headers=auth_b)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_patient_is_created_for_the_logged_user_only(client, db_session, user_a, auth_a):
    """O dono vem do token, nunca do corpo da requisição."""
    response = client.post(
        "/patients",
        json={"full_name": "Paciente", "user_id": 999},  # campo extra é ignorado
        headers=auth_a,
    )
    assert response.status_code == 201

    from app.database.models import Patient
    saved = db_session.get(Patient, response.json()["id"])
    assert saved.user_id == user_a.id
