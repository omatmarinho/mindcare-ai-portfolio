"""Rate limiting: bloqueia tentativas em excesso (força bruta)."""
from app.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT
from tests.conftest import TEST_PASSWORD


def _limit_count(limit: str) -> int:
    return int(limit.split("/")[0])


def test_login_is_blocked_after_too_many_attempts(client, user_a):
    max_attempts = _limit_count(LOGIN_LIMIT)

    for _ in range(max_attempts):
        response = client.post("/auth/login", data={
            "username": user_a.email, "password": "SenhaErrada123!",
        })
        assert response.status_code == 401

    blocked = client.post("/auth/login", data={
        "username": user_a.email, "password": "SenhaErrada123!",
    })
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_correct_password_is_also_blocked_while_limited(client, user_a):
    """Mesmo acertando a senha, o atacante não ganha nada durante o bloqueio."""
    for _ in range(_limit_count(LOGIN_LIMIT)):
        client.post("/auth/login", data={"username": user_a.email, "password": "x" * 8})

    response = client.post("/auth/login", data={
        "username": user_a.email, "password": TEST_PASSWORD,
    })
    assert response.status_code == 429


def test_register_is_rate_limited(client):
    for i in range(_limit_count(REGISTER_LIMIT)):
        response = client.post("/auth/register", json={
            "full_name": "Psicologo", "email": f"p{i}@psinara.com.br", "password": TEST_PASSWORD,
        })
        assert response.status_code == 202

    blocked = client.post("/auth/register", json={
        "full_name": "Psicologo", "email": "extra@psinara.com.br", "password": TEST_PASSWORD,
    })
    assert blocked.status_code == 429
