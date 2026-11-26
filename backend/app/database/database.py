
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carrega as variáveis do arquivo .env
load_dotenv()

# URL do banco (PostgreSQL/Supabase ou sqlite:///arquivo.db)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise ValueError("DATABASE_URL não foi encontrada no arquivo .env")
    # Para rodar localmente sem configurar nada: um arquivo SQLite na pasta do backend
    DATABASE_URL = "sqlite:///./psinara.db"


def normalize_database_url(url: str) -> str:
    """Usa o driver instalado (psycopg2) mesmo quando a URL vem sem driver.

    O Supabase fornece endereços "postgresql://..."; o SQLAlchemy 2.1 associa
    esse formato ao psycopg 3, que não usamos.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_database_url(DATABASE_URL)

# PostgreSQL em produção; SQLite serve para rodar localmente e para a demonstração.
# No SQLite, o processamento da IA (em outra thread) precisa poder usar a conexão.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

# Configura as sessões do banco
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para criação dos modelos
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory():
    """
    Entrega a "fábrica" de sessões para tarefas em segundo plano (que rodam
    depois da resposta e precisam abrir a própria sessão). Os testes
    substituem esta dependência pelo banco de teste.
    """
    return SessionLocal