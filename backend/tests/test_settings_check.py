"""A API deve se recusar a iniciar em produção com configuração insegura."""
import pytest

from app import settings_check

SAFE_SECRET = "x" * 64


def _production(monkeypatch, **overrides):
    env = {
        "APP_ENV": "production",
        "JWT_SECRET_KEY": SAFE_SECRET,
        "EMAIL_BACKEND": "resend",
        "FRONTEND_URL": "https://app.mindcare.example",
        "CORS_ORIGINS": "https://app.mindcare.example",
    }
    env.update(overrides)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_safe_production_config_starts(monkeypatch):
    _production(monkeypatch)
    settings_check.check_settings()  # não lança erro


@pytest.mark.parametrize("override", [
    {"JWT_SECRET_KEY": "curta"},
    {"EMAIL_BACKEND": "console"},
    {"FRONTEND_URL": "http://app.mindcare.example"},
    {"CORS_ORIGINS": "https://ok.example,http://inseguro.example"},
])
def test_unsafe_production_config_refuses_to_start(monkeypatch, override):
    _production(monkeypatch, **override)
    with pytest.raises(RuntimeError):
        settings_check.check_settings()


def test_development_only_warns(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "curta")
    settings_check.check_settings()  # apenas aviso, não lança erro
