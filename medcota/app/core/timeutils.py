"""Datas e horas. Banco em UTC 'ingênuo'; 'hoje' e horário de corte no fuso do negócio."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from .config import settings

TZ = ZoneInfo(settings.fuso_horario)


def agora_utc() -> datetime:
    """UTC sem tzinfo (compatível com as colunas DateTime)."""
    return datetime.now(UTC).replace(tzinfo=None)


def agora_local() -> datetime:
    return datetime.now(TZ)


def hoje() -> date:
    """Dia corrente no fuso do negócio (Maceió), não no do servidor."""
    return agora_local().date()


def inicio_do_dia_utc() -> datetime:
    """00:00 de hoje (fuso do negócio) convertido para UTC ingênuo."""
    inicio = datetime.combine(hoje(), time.min, tzinfo=TZ)
    return inicio.astimezone(UTC).replace(tzinfo=None)
