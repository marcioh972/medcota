from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import settings


def _bytes_senha(senha: str) -> bytes:
    b = senha.encode("utf-8")
    if len(b) > 72:  # limite do bcrypt
        raise ValueError("Senha excede 72 bytes (limite do bcrypt)")
    return b


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_bytes_senha(senha), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")


def verificar_senha(senha: str, hash_salvo: str) -> bool:
    try:
        return bcrypt.checkpw(_bytes_senha(senha), hash_salvo.encode("utf-8"))
    except ValueError:  # senha longa demais ou hash malformado
        return False


def criar_token(usuario_id: int) -> str:
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),  # 'sub' precisa ser string
        "iat": agora,
        "exp": agora + timedelta(hours=settings.jwt_expira_horas),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


def decodificar_token(token: str) -> int:
    """Levanta jwt.PyJWTError ou ValueError se o token for inválido."""
    dados = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo], options={"require": ["exp", "sub"]}
    )
    return int(dados["sub"])
