from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import erro
from ..models import Usuario
from ..schemas.empresas import UsuarioPatch
from . import auditoria


def listar_equipe(db: Session, empresa_id: int) -> list[Usuario]:
    return list(db.scalars(select(Usuario).where(Usuario.empresa_id == empresa_id).order_by(Usuario.nome)))


def atualizar_usuario(db: Session, gestor: Usuario, usuario_id: int, dados: UsuarioPatch) -> Usuario:
    alvo = db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.empresa_id == gestor.empresa_id))
    if alvo is None:  # inexistente OU de outra empresa: mesma resposta
        raise erro(404, "usuario_nao_encontrado", "Usuário não encontrado")
    if alvo.id == gestor.id and dados.ativo is False:
        raise erro(409, "nao_pode_desativar_a_si_mesmo", "Você não pode desativar a própria conta.")
    detalhes = []
    if dados.ativo is not None and dados.ativo != alvo.ativo:
        alvo.ativo = dados.ativo
        detalhes.append(f"ativo={dados.ativo}")
    if dados.ver_preco_custo is not None and dados.ver_preco_custo != alvo.ver_preco_custo:
        alvo.ver_preco_custo = dados.ver_preco_custo
        detalhes.append(f"ver_preco_custo={dados.ver_preco_custo}")
    if detalhes:
        auditoria.registrar(
            db, gestor.empresa_id, gestor.id, "alterou_usuario", "usuario", alvo.id, ", ".join(detalhes)
        )
    db.commit()
    return alvo
