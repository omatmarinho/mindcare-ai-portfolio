from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Reaproveita a configuração da aplicação: carrega o .env e lê DATABASE_URL.
# Assim a URL do banco nunca precisa ser escrita no alembic.ini.
from app.database.database import DATABASE_URL, Base

# Importar os modelos registra as tabelas em Base.metadata
# (necessário para o "alembic revision --autogenerate" enxergá-las)
from app.database import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem conectar ao banco (alembic upgrade --sql)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta ao banco e aplica as migrações."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
