"""
Configuração compartilhada dos testes (o Pytest carrega este arquivo sozinho).

Os testes NÃO usam o Supabase. Cada teste recebe um banco SQLite novo,
criado na memória e descartado no final. Assim os testes:
- não sujam o banco de desenvolvimento;
- não dependem uns dos outros;
- rodam rápido e sem internet.
"""
import os

from cryptography.fernet import Fernet

# Chaves só para os testes (o .env de desenvolvimento não é necessário)
os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-" + "x" * 64)
os.environ.setdefault("NOTES_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DATABASE_URL", "sqlite://")
# Os testes não dependem do .env local: cada um liga o que precisa (monkeypatch)
os.environ["DEMO_MODE"] = "false"
os.environ["INTERNAL_API_KEY"] = ""
os.environ["AI_BACKEND"] = "local"
os.environ["APP_ENV"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database.database import Base, get_db, get_session_factory
from app.database import crud
from app.rate_limit import limiter


from app import email_service


@pytest.fixture(autouse=True)
def reset_rate_limits():
    # Zera as contagens do limitador: cada teste começa "sem tentativas"
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    """E-mails ficam em uma lista em vez de serem enviados."""
    monkeypatch.setenv("EMAIL_BACKEND", "memory")
    email_service.OUTBOX.clear()
    yield email_service.OUTBOX
    email_service.OUTBOX.clear()


@pytest.fixture
def session_factory():
    # StaticPool faz todas as conexões usarem o MESMO banco em memória
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, session_factory):
    # Troca o get_db real (Supabase) pelo banco de teste
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Tarefas em segundo plano também usam o banco de teste
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Senha usada apenas nos testes (o banco de teste é descartado ao final)
TEST_PASSWORD = "SenhaDeTeste123!"


def _create_user(db_session, email: str, full_name: str):
    """Cria um psicólogo já com e-mail confirmado (pronto para fazer login)."""
    user = crud.create_user(
        db=db_session,
        full_name=full_name,
        email=email,
        password=TEST_PASSWORD,
    )
    crud.mark_email_verified(db_session, user)
    return user


def _login(client, email: str) -> dict:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a(db_session):
    return _create_user(db_session, "psicologo.a@mindcareai.com", "Psicologo A")


@pytest.fixture
def user_b(db_session):
    return _create_user(db_session, "psicologo.b@mindcareai.com", "Psicologo B")


@pytest.fixture
def auth_a(client, user_a):
    """Cabeçalho de autenticação do Psicólogo A."""
    return _login(client, user_a.email)


@pytest.fixture
def auth_b(client, user_b):
    """Cabeçalho de autenticação do Psicólogo B."""
    return _login(client, user_b.email)
