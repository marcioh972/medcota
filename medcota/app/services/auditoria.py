from sqlalchemy.orm import Session

from ..models import Auditoria


def registrar(
    db: Session,
    empresa_id: int,
    usuario_id: int | None,
    acao: str,
    entidade: str,
    entidade_id: int | str = "",
    detalhe: str = "",
) -> None:
    """RF-04. Não faz commit: entra na mesma transação da operação auditada."""
    db.add(
        Auditoria(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id),
            detalhe=detalhe,
        )
    )
