from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

# Atrás de proxy/Nginx, configure o uvicorn com --proxy-headers para o IP real do cliente.
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_ativo)
