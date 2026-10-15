"""Onboarding SaaS: cadastro da empresa (gestor), código de validação e cadastro de funcionários."""

import logging
import re
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import erro
from ..core.security import hash_senha
from ..core.timeutils import agora_utc
from ..enums import Perfil
from ..models import Empresa, Usuario
from ..schemas.empresas import CadastroEmpresaIn, CadastroFuncionarioIn, EmpresaOut
from . import auditoria

logger = logging.getLogger(__name__)

# 32 símbolos, sem 0/O/1/I (evita confusão ao digitar). 12 posições = 60 bits de entropia.
_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TAMANHO_CODIGO = 12


def gerar_codigo_aleatorio() -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_TAMANHO_CODIGO))


def normalizar_codigo(valor: str) -> str:
    """Aceita 'abcd-efgh-jklm', 'ABCD EFGH JKLM' etc."""
    return re.sub(r"[\s\-]", "", valor).upper()


def formatar_codigo(codigo: str) -> str:
    return "-".join(codigo[i : i + 4] for i in range(0, len(codigo), 4))


def empresa_out(e: Empresa) -> EmpresaOut:
    ativo = bool(e.codigo_validacao and e.codigo_expira_em and e.codigo_expira_em > agora_utc())
    return EmpresaOut(
        id=e.id,
        nome=e.nome,
        cnpj=e.cnpj,
        codigo_validacao=formatar_codigo(e.codigo_validacao) if e.codigo_validacao else None,
        codigo_expira_em=e.codigo_expira_em,
        codigo_ativo=ativo,
    )


def _email_em_uso(db: Session, email: str) -> bool:
    return db.scalar(select(Usuario.id).where(Usuario.email == email)) is not None


def cadastrar_empresa(db: Session, dados: CadastroEmpresaIn) -> Usuario:
    """Cria a empresa (tenant) e o gestor. Devolve o gestor já com a empresa associada."""
    if db.scalar(select(Empresa.id).where(Empresa.cnpj == dados.cnpj)):
        raise erro(409, "cnpj_em_uso", "Já existe uma empresa cadastrada com este CNPJ.", campo="cnpj")
    if _email_em_uso(db, dados.email):
        raise erro(409, "email_em_uso", "Este e-mail já está cadastrado.", campo="email")

    empresa = Empresa(nome=dados.empresa_nome, cnpj=dados.cnpj)
    db.add(empresa)
    db.flush()
    gestor = Usuario(
        empresa_id=empresa.id,
        nome=dados.gestor_nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        perfil=Perfil.gestor,
        ver_preco_custo=True,
    )
    db.add(gestor)
    db.flush()
    auditoria.registrar(db, empresa.id, gestor.id, "cadastrou_empresa", "empresa", empresa.id)
    try:
        db.commit()
    except IntegrityError:  # corrida: outro cadastro idêntico terminou primeiro
        db.rollback()
        raise erro(409, "cadastro_duplicado", "CNPJ ou e-mail já cadastrados.") from None
    logger.info("empresa cadastrada empresa_id=%s", empresa.id)
    return gestor


def _empresa_do_gestor(db: Session, gestor: Usuario, *, bloquear: bool = False) -> Empresa:
    return db.get(Empresa, gestor.empresa_id, with_for_update=bloquear)  # type: ignore[return-value]


def obter_empresa(db: Session, gestor: Usuario) -> Empresa:
    return _empresa_do_gestor(db, gestor)


def gerar_codigo(db: Session, gestor: Usuario) -> Empresa:
    """Gera (ou rotaciona) o código de validação. O anterior deixa de valer imediatamente."""
    empresa = _empresa_do_gestor(db, gestor, bloquear=True)
    for _ in range(5):  # colisão é astronomicamente improvável; a constraint única é a garantia final
        codigo = gerar_codigo_aleatorio()
        if not db.scalar(select(Empresa.id).where(Empresa.codigo_validacao == codigo)):
            break
    empresa.codigo_validacao = codigo
    empresa.codigo_expira_em = agora_utc() + timedelta(days=settings.codigo_validade_dias)
    auditoria.registrar(db, empresa.id, gestor.id, "gerou_codigo_validacao", "empresa", empresa.id)
    db.commit()
    logger.info("codigo de validacao gerado empresa_id=%s", empresa.id)
    return empresa


def revogar_codigo(db: Session, gestor: Usuario) -> Empresa:
    empresa = _empresa_do_gestor(db, gestor, bloquear=True)
    empresa.codigo_validacao = None
    empresa.codigo_expira_em = None
    auditoria.registrar(db, empresa.id, gestor.id, "revogou_codigo_validacao", "empresa", empresa.id)
    db.commit()
    return empresa


def cadastrar_funcionario(db: Session, dados: CadastroFuncionarioIn) -> Usuario:
    """Cadastro de comprador/vendedor: o código de validação define a empresa de destino."""
    codigo = normalizar_codigo(dados.codigo)
    empresa = db.scalar(select(Empresa).where(Empresa.codigo_validacao == codigo))
    if not empresa or not empresa.codigo_expira_em or empresa.codigo_expira_em < agora_utc():
        # mesma mensagem para "não existe", "revogado" e "expirado": não revela nada a quem tenta adivinhar
        raise erro(
            422,
            "codigo_invalido",
            "Código de validação inválido ou expirado. Peça um novo ao gestor.",
            campo="codigo",
        )
    if _email_em_uso(db, dados.email):
        raise erro(409, "email_em_uso", "Este e-mail já está cadastrado.", campo="email")

    perfil = Perfil(dados.perfil)
    user = Usuario(
        empresa_id=empresa.id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        perfil=perfil,
        ver_preco_custo=perfil == Perfil.comprador,  # o gestor pode alterar em Empresa > Equipe
    )
    db.add(user)
    db.flush()
    auditoria.registrar(db, empresa.id, user.id, "cadastrou_funcionario", "usuario", user.id, f"perfil {perfil.value}")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise erro(409, "email_em_uso", "Este e-mail já está cadastrado.", campo="email") from None
    return user
