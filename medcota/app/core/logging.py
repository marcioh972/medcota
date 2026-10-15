"""Logging com ID de requisição para rastrear uma chamada de ponta a ponta."""

import logging
from contextvars import ContextVar

from .config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configurar_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(settings.log_nivel.upper())
