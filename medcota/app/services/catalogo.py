"""Catálogo da empresa: produtos e fornecedores (isolados por empresa)."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.errors import erro
from ..models import Fornecedor, Produto, Usuario
from ..schemas.fornecedores import FornecedorIn, FornecedorPatch
from ..schemas.produtos import ProdutoIn
from . import auditoria


def buscar_produtos(db: Session, empresa_id: int, q: str, limit: int) -> list[Produto]:
    stmt = select(Produto).where(Produto.empresa_id == empresa_id).order_by(Produto.nome).limit(limit)
    termo = q.strip()
    if termo:
        stmt = stmt.where(
            or_(
                Produto.nome.icontains(termo, autoescape=True),
                Produto.principio_ativo.icontains(termo, autoescape=True),
                Produto.ean.startswith(termo, autoescape=True),
            )
        )
    return list(db.scalars(stmt))


def criar_produto(db: Session, usuario: Usuario, dados: ProdutoIn) -> Produto:
    if dados.ean and db.scalar(
        select(Produto.id).where(Produto.empresa_id == usuario.empresa_id, Produto.ean == dados.ean)
    ):
        raise erro(409, "ean_em_uso", "Já existe um produto com este EAN.", campo="ean")
    produto = Produto(empresa_id=usuario.empresa_id, **dados.model_dump())
    db.add(produto)
    db.flush()
    auditoria.registrar(db, usuario.empresa_id, usuario.id, "criou_produto", "produto", produto.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise erro(409, "ean_em_uso", "Já existe um produto com este EAN.", campo="ean") from None
    return produto


def listar_fornecedores(db: Session, empresa_id: int) -> list[Fornecedor]:
    return list(db.scalars(select(Fornecedor).where(Fornecedor.empresa_id == empresa_id).order_by(Fornecedor.nome)))


def _cnpj_em_uso(db: Session, empresa_id: int, cnpj: str, ignorar_id: int | None = None) -> bool:
    q = select(Fornecedor.id).where(Fornecedor.empresa_id == empresa_id, Fornecedor.cnpj == cnpj)
    if ignorar_id is not None:
        q = q.where(Fornecedor.id != ignorar_id)
    return db.scalar(q) is not None


def _erro_cnpj():
    return erro(409, "cnpj_em_uso", "Já existe um fornecedor com este CNPJ.", campo="cnpj")


def criar_fornecedor(db: Session, usuario: Usuario, dados: FornecedorIn) -> Fornecedor:
    if dados.cnpj and _cnpj_em_uso(db, usuario.empresa_id, dados.cnpj):
        raise _erro_cnpj()
    fornecedor = Fornecedor(
        empresa_id=usuario.empresa_id,
        nome=dados.nome,
        escopo=dados.escopo,
        email=dados.email or "",
        cnpj=dados.cnpj,
        credenciado_72101=dados.credenciado_72101,
    )
    db.add(fornecedor)
    db.flush()
    auditoria.registrar(db, usuario.empresa_id, usuario.id, "criou_fornecedor", "fornecedor", fornecedor.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _erro_cnpj() from None
    return fornecedor


def atualizar_fornecedor(db: Session, usuario: Usuario, fornecedor_id: int, dados: FornecedorPatch) -> Fornecedor:
    f = db.scalar(select(Fornecedor).where(Fornecedor.id == fornecedor_id, Fornecedor.empresa_id == usuario.empresa_id))
    if f is None:  # inexistente OU de outra empresa
        raise erro(404, "fornecedor_nao_encontrado", "Fornecedor não encontrado")
    enviados = dados.model_fields_set
    mudancas = []
    if "cnpj" in enviados and dados.cnpj != f.cnpj:
        if dados.cnpj and _cnpj_em_uso(db, usuario.empresa_id, dados.cnpj, ignorar_id=f.id):
            raise _erro_cnpj()
        f.cnpj = dados.cnpj
        mudancas.append("cnpj")
    if "email" in enviados and (dados.email or "") != f.email:
        f.email = dados.email or ""
        mudancas.append("email")
    if dados.credenciado_72101 is not None and dados.credenciado_72101 != f.credenciado_72101:
        f.credenciado_72101 = dados.credenciado_72101
        mudancas.append(f"credenciado_72101={dados.credenciado_72101}")
    if mudancas:
        auditoria.registrar(
            db,
            usuario.empresa_id,
            usuario.id,
            "atualizou_fornecedor",
            "fornecedor",
            f.id,
            ", ".join(mudancas),
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise _erro_cnpj() from None
    return f
