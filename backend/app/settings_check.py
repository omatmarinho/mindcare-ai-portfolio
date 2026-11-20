"""
Verificações de configuração feitas ao iniciar a API.

Em produção (APP_ENV=production) a API SE RECUSA A INICIAR se alguma
configuração insegura for detectada. É melhor não subir do que subir
vulnerável. Em desenvolvimento, os problemas viram apenas avisos.
"""
import logging
import os

logger = logging.getLogger("mindcare.settings")

MIN_JWT_SECRET_LENGTH = 32


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def find_problems() -> list[str]:
    problems = []

    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < MIN_JWT_SECRET_LENGTH:
        problems.append(
            f"JWT_SECRET_KEY tem menos de {MIN_JWT_SECRET_LENGTH} caracteres. Gere uma com: "
            'python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )

    demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")
    if is_production():
        if not demo_mode and os.getenv("EMAIL_BACKEND", "console").lower() != "resend":
            problems.append("EMAIL_BACKEND precisa ser 'resend' em produção.")
        if demo_mode and len(os.getenv("INTERNAL_API_KEY", "")) < 32:
            problems.append("A demonstração pública precisa de INTERNAL_API_KEY com 32+ caracteres.")
        if not os.getenv("NOTES_ENCRYPTION_KEY"):
            problems.append("NOTES_ENCRYPTION_KEY precisa ser definida.")

        for var in ("FRONTEND_URL", "CORS_ORIGINS"):
            values = [v.strip() for v in os.getenv(var, "").split(",") if v.strip()]
            if not values or any(not v.startswith("https://") for v in values):
                problems.append(f"{var} precisa ser definida e usar https:// em produção.")

    return problems


def check_settings() -> None:
    problems = find_problems()
    if not problems:
        return

    if is_production():
        raise RuntimeError(
            "Configuração insegura para produção:\n- " + "\n- ".join(problems)
        )

    for problem in problems:
        logger.warning("Configuração: %s", problem)
