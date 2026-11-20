"""
Datas e fusos horários.

Regra do projeto: no banco, todo horário fica em UTC. A conversão para o
horário local (padrão: America/Sao_Paulo) acontece só nas bordas: ao
receber dados sem fuso, ao calcular horários livres e ao exibir.

Assim, horário de verão, servidores em outro país ou psicólogos em outro
fuso no futuro não bagunçam a agenda.
"""
import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def local_tz() -> ZoneInfo:
    return ZoneInfo(os.getenv("APP_TIMEZONE", "America/Sao_Paulo"))


def to_utc(value: datetime) -> datetime:
    """Converte para UTC. Sem fuso informado, assume o horário local."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=local_tz())
    return value.astimezone(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Datas lidas do SQLite (testes) vêm sem fuso, mas estão em UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def local_date(value: datetime) -> date:
    return as_utc(value).astimezone(local_tz()).date()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
