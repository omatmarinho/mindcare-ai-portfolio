"""Endereços do banco: aceitar o formato copiado do Supabase."""
from app.database.database import normalize_database_url


def test_plain_postgresql_url_uses_psycopg2():
    url = "postgresql://user:pw@host.pooler.supabase.com:5432/postgres"
    assert normalize_database_url(url) == "postgresql+psycopg2://user:pw@host.pooler.supabase.com:5432/postgres"


def test_postgres_alias_uses_psycopg2():
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"


def test_explicit_driver_is_kept():
    url = "postgresql+psycopg2://u:p@h/db"
    assert normalize_database_url(url) == url
