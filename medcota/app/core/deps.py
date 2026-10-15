"""Dependências de autenticação/autorização, no estilo Annotated (FastAPI moderno)."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..enums import Perfil
from ..models import Usuario
from .database import get_db
from .errors import erro
from .security import decodificar_token

oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def usuario_atual(db: DbSession, token: Annotated[str, Depends(oauth2)]) -> Usuario:
    try:
        uid = decodificar_token(token)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise erro(
            401, "token_invalido", "Token inválido ou expirado", headers={"WWW-Authenticate": "Bearer"}
        ) from None
    u = db.get(Usuario, uid)
    if not u or not u.ativo:
        raise erro(401, "usuario_invalido", "Usuário inválido", headers={"WWW-Authenticate": "Bearer"})
    return u


def exigir_perfil(*perfis: Perfil):
    def dep(u: Annotated[Usuario, Depends(usuario_atual)]) -> Usuario:
        if u.perfil not in perfis:
            raise erro(403, "perfil_sem_permissao", "Perfil sem permissão para esta operação")
        return u

    return dep


UsuarioLogado = Annotated[Usuario, Depends(usuario_atual)]
Vendedor = Annotated[Usuario, Depends(exigir_perfil(Perfil.vendedor))]
Comprador = Annotated[Usuario, Depends(exigir_perfil(Perfil.comprador))]
Gestor = Annotated[Usuario, Depends(exigir_perfil(Perfil.gestor))]
CompradorOuGestor = Annotated[Usuario, Depends(exigir_perfil(Perfil.comprador, Perfil.gestor))]


def exigir_conferencia(
    u: Annotated[Usuario, Depends(exigir_perfil(Perfil.comprador, Perfil.gestor))],
) -> Usuario:
    """Módulo de recebimento/conferência fiscal: só comprador e gestor, e só com permissão de ver preços
    (RN-04), porque a conferência exibe preços, custos e impostos."""
    if not u.ver_preco_custo:
        raise erro(403, "sem_permissao_precos", "Seu usuário não tem permissão para ver preços e custos.")
    return u


ConferenciaFiscal = Annotated[Usuario, Depends(exigir_conferencia)]
