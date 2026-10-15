import logging
from datetime import timedelta
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import erro
from ..core.security import criar_token, hash_senha, verificar_senha
from ..core.timeutils import agora_utc
from ..models import Usuario
from ..schemas.auth import LoginOut

logger = logging.getLogger(__name__)


@lru_cache
def _hash_falso() -> str:
    # Usado quando o e-mail não existe, para que o tempo de resposta não revele isso.
    return hash_senha("senha-falsa-para-equalizar-tempo")


def _credenciais_invalidas():
    return erro(401, "credenciais_invalidas", "Credenciais inválidas", headers={"WWW-Authenticate": "Bearer"})


def autenticar(db: Session, email: str, senha: str) -> Usuario:
    u = db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))

    # RF-03: conta bloqueada é checada ANTES da senha
    if u and u.bloqueado_ate and u.bloqueado_ate > agora_utc():
        logger.warning("login em conta bloqueada usuario_id=%s", u.id)
        raise erro(423, "conta_bloqueada", "Conta temporariamente bloqueada. Tente mais tarde.")

    if u is None:
        verificar_senha(senha, _hash_falso())
        raise _credenciais_invalidas()

    if not verificar_senha(senha, u.senha_hash):
        u.falhas_login = (u.falhas_login or 0) + 1
        if u.falhas_login >= settings.login_max_falhas:
            u.bloqueado_ate = agora_utc() + timedelta(minutes=settings.login_bloqueio_min)
            u.falhas_login = 0
            logger.warning("conta bloqueada por tentativas usuario_id=%s", u.id)
        db.commit()
        raise _credenciais_invalidas()

    if not u.ativo:  # mesma resposta genérica: não revela que a conta existe
        raise _credenciais_invalidas()

    u.falhas_login = 0
    u.bloqueado_ate = None
    db.commit()
    return u


def emitir_login(u: Usuario) -> LoginOut:
    return LoginOut(access_token=criar_token(u.id), perfil=u.perfil, nome=u.nome, empresa=u.empresa.nome)
