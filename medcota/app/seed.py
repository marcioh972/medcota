"""Dados de demonstração (SOMENTE desenvolvimento).

Uso:  alembic upgrade head && python -m app.seed
Cria uma empresa de exemplo com gestor, comprador, vendedor, produtos e fornecedores, e gera o
código de validação para você testar o cadastro de funcionários.
A senha dos usuários vem de SEED_SENHA (precisa cumprir a política) ou é gerada e exibida uma vez.
"""

import os
import sys
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.config import settings
from .core.database import SessionLocal
from .core.password import gerar_senha_valida, problemas_senha
from .core.security import hash_senha
from .core.timeutils import agora_utc
from .enums import ClasseProduto, Escopo, Perfil
from .models import Empresa, Fornecedor, Produto, Usuario
from .services.empresas import formatar_codigo, gerar_codigo_aleatorio

CNPJ_DEMO = "11222333000181"  # válido (dígitos verificadores corretos); usado só na demonstração


def seed(db: Session, senha: str) -> Empresa:
    empresa = Empresa(
        nome="Distribuidora Demo",
        cnpj=CNPJ_DEMO,
        codigo_validacao=gerar_codigo_aleatorio(),
        codigo_expira_em=agora_utc() + timedelta(days=settings.codigo_validade_dias),
    )
    db.add(empresa)
    db.flush()
    eid = empresa.id
    hash_ = hash_senha(senha)
    db.add_all(
        [
            Usuario(
                empresa_id=eid,
                nome="Ana Souza",
                email="ana@medcota.com.br",
                senha_hash=hash_,
                perfil=Perfil.vendedor,
                ver_preco_custo=False,
            ),
            Usuario(
                empresa_id=eid,
                nome="Bruno Lima",
                email="bruno@medcota.com.br",
                senha_hash=hash_,
                perfil=Perfil.comprador,
                ver_preco_custo=True,
            ),
            Usuario(
                empresa_id=eid,
                nome="Carla Prado",
                email="carla@medcota.com.br",
                senha_hash=hash_,
                perfil=Perfil.gestor,
                ver_preco_custo=True,
            ),
            Produto(
                empresa_id=eid,
                nome="Dipirona Sódica 500mg · 20 comp",
                principio_ativo="Dipirona monoidratada",
                ean="7896094916010",
                classe=ClasseProduto.farma,
                origem=Escopo.local,
                ncm="30049099",
            ),
            Produto(
                empresa_id=eid,
                nome="Amoxicilina 500mg · 21 cáps",
                principio_ativo="Amoxicilina",
                ean="7896094907044",
                classe=ClasseProduto.farma,
                origem=Escopo.local,
                ncm="30041011",
            ),
            Produto(
                empresa_id=eid,
                nome="Losartana 50mg · 30 comp",
                principio_ativo="Losartana potássica",
                ean="7896641808630",
                classe=ClasseProduto.farma,
                origem=Escopo.nacional,
            ),
            Produto(
                empresa_id=eid,
                nome="Soro Fisiológico 0,9% · 500ml",
                principio_ativo="Cloreto de sódio",
                ean="7898093987441",
                classe=ClasseProduto.hospitalar,
                origem=Escopo.local,
            ),
            Produto(
                empresa_id=eid,
                nome="Insulina Glargina 100UI/ml · 3ml",
                principio_ativo="Insulina glargina",
                ean="7896094968708",
                classe=ClasseProduto.hospitalar,
                origem=Escopo.nacional,
                controlado=True,
            ),
            Fornecedor(empresa_id=eid, nome="MedDist Maceió", escopo=Escopo.local, email="vendas@meddist.com.br"),
            Fornecedor(
                empresa_id=eid,
                nome="FarmaNorte Distribuidora",
                escopo=Escopo.nacional,
                email="cotacao@farmanorte.com.br",
            ),
            Fornecedor(
                empresa_id=eid,
                nome="HospMed Brasil",
                escopo=Escopo.nacional,
                email="comercial@hospmed.com.br",
            ),
        ]
    )
    db.commit()
    return empresa


def main() -> int:
    if settings.ambiente == "producao":
        print("Recusado: seed não roda em produção.")
        return 1
    with SessionLocal() as db:
        if db.scalar(select(Empresa.id).limit(1)):
            print("Banco já possui empresas; nada a fazer.")
            return 0
        senha = os.getenv("SEED_SENHA") or gerar_senha_valida()
        if faltas := problemas_senha(senha):
            print("SEED_SENHA não cumpre a política de senha: precisa ter " + ", ".join(faltas))
            return 1
        empresa = seed(db, senha)
        codigo = formatar_codigo(empresa.codigo_validacao or "")
    print(f"Empresa: {empresa.nome} (CNPJ de demonstração 11.222.333/0001-81)")
    print("Usuários: ana@ (vendedor), bruno@ (comprador), carla@ (gestor) @medcota.com.br")
    print(f"Senha: {senha}")
    print(f"Código de validação (para cadastrar funcionários): {codigo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
