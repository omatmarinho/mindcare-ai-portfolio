"""CORS: só o frontend autorizado pode chamar a API pelo navegador."""


def _preflight(client, origin):
    return client.options(
        "/patients",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )


def test_allowed_origin_gets_cors_headers(client):
    response = _preflight(client, "http://localhost:3000")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unknown_origin_is_not_allowed(client):
    response = _preflight(client, "https://site-malicioso.example")
    assert "access-control-allow-origin" not in response.headers
