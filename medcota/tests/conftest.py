import os

# Precisa vir ANTES de importar a aplicação.
os.environ.update(
    {
        "AMBIENTE": "teste",
        "JWT_SECRET": "segredo-de-teste-com-mais-de-32-caracteres-ok",
        "DATABASE_URL": "sqlite://",
        "RATE_LIMIT_ATIVO": "false",
        "HORARIO_CORTE": "23:59",
        "BCRYPT_ROUNDS": "4",  # hash rápido só nos testes
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_senha  # noqa: E402
from app.enums import ClasseProduto, Escopo, Perfil  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Empresa, Fornecedor, Produto, Usuario  # noqa: E402

SENHA = "Senha-teste-123"  # cumpre a política (8+, maiúscula, minúscula, número)
CNPJ_A = "11222333000181"
CNPJ_B = "11444777000161"

_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
_Session = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db():
    Base.metadata.create_all(_engine)
    s = _Session()
    yield s
    s.close()
    Base.metadata.drop_all(_engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- helpers
def criar_empresa(db, nome="Empresa A", cnpj=CNPJ_A) -> Empresa:
    e = Empresa(nome=nome, cnpj=cnpj)
    db.add(e)
    db.commit()
    return e


def empresa_padrao(db) -> Empresa:
    """Empresa 'A' dos testes (cria na primeira chamada)."""
    return db.scalar(select(Empresa).where(Empresa.cnpj == CNPJ_A)) or criar_empresa(db)


def criar_usuario(db, email, perfil, ver_preco_custo=True, ativo=True, empresa=None) -> Usuario:
    empresa = empresa or empresa_padrao(db)
    u = Usuario(
        empresa_id=empresa.id,
        nome=email.split("@")[0].title(),
        email=email,
        senha_hash=hash_senha(SENHA),
        perfil=perfil,
        ver_preco_custo=ver_preco_custo,
        ativo=ativo,
    )
    db.add(u)
    db.commit()
    return u


def criar_produto(db, empresa=None, nome="Dipirona 500mg", ean="7896094916010", origem=Escopo.local):
    empresa = empresa or empresa_padrao(db)
    p = Produto(empresa_id=empresa.id, nome=nome, ean=ean, classe=ClasseProduto.farma, origem=origem)
    db.add(p)
    db.commit()
    return p


def criar_fornecedores(db, empresa=None, nomes=("Forn A", "Forn B")):
    empresa = empresa or empresa_padrao(db)
    fs = [Fornecedor(empresa_id=empresa.id, nome=n, escopo=Escopo.local) for n in nomes]
    db.add_all(fs)
    db.commit()
    return fs


def login(client, email, senha=SENHA):
    return client.post("/auth/login", data={"username": email, "password": senha})


def auth(client, email):
    r = login(client, email)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- fixtures (empresa A)
@pytest.fixture
def empresa(db):
    return empresa_padrao(db)


@pytest.fixture
def vendedor(db):
    return criar_usuario(db, "ana@t.com", Perfil.vendedor, ver_preco_custo=False)


@pytest.fixture
def comprador(db):
    return criar_usuario(db, "bruno@t.com", Perfil.comprador)


@pytest.fixture
def gestor(db):
    return criar_usuario(db, "carla@t.com", Perfil.gestor)


@pytest.fixture
def produto(db):
    return criar_produto(db)


@pytest.fixture
def fornecedores(db):
    a, b = criar_fornecedores(db)
    return a, b
