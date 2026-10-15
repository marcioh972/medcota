import pytest

from app.core.cnpj import cnpj_valido, normalizar_cnpj, validar_cnpj
from app.core.password import gerar_senha_valida, problemas_senha, validar_senha
from app.services.empresas import formatar_codigo, gerar_codigo_aleatorio, normalizar_codigo
from tests.conftest import CNPJ_A, CNPJ_B


class TestSenha:
    @pytest.mark.parametrize("senha", ["Abcdef1x", "Senha-teste-123", "ÁguaClara9", "A1" + "b" * 60])
    def test_aceita(self, senha):
        assert problemas_senha(senha) == []
        assert validar_senha(senha) == senha

    @pytest.mark.parametrize(
        ("senha", "falta"),
        [
            ("Ab1", "pelo menos 8 caracteres"),
            ("abcdefg1", "uma letra maiúscula"),
            ("ABCDEFG1", "uma letra minúscula"),
            ("Abcdefgh", "um número"),
            ("A1" + "b" * 80, "no máximo 72 bytes"),
            ("", "pelo menos 8 caracteres"),
        ],
    )
    def test_rejeita_e_diz_o_que_falta(self, senha, falta):
        assert falta in problemas_senha(senha)
        with pytest.raises(ValueError, match="A senha precisa ter"):
            validar_senha(senha)

    def test_so_digitos_ascii_contam_como_numero(self):
        assert "um número" in problemas_senha("Abcdefg٣")  # dígito arábico-índico

    def test_gerador_sempre_cumpre_a_politica(self):
        for _ in range(200):
            assert problemas_senha(gerar_senha_valida()) == []


class TestCnpj:
    @pytest.mark.parametrize(
        "cnpj",
        [
            CNPJ_A,
            CNPJ_B,
            "12.ABC.345/01DE-35",  # exemplo oficial da Receita (alfanumérico)
            "00.000.000/E08G-12",  # primeiro CNPJ alfanumérico emitido (31/07/2026)
            "11.222.333/0001-81",
        ],
    )
    def test_valido(self, cnpj):
        assert cnpj_valido(normalizar_cnpj(cnpj))

    @pytest.mark.parametrize(
        "cnpj",
        [
            "11222333000182",
            "00000000000000",
            "11111111111111",
            "1122233300018",
            "12ABC34501DE3A",
            "12abc34501de36",
            "",
            "abc",
        ],
    )
    def test_invalido(self, cnpj):
        assert not cnpj_valido(normalizar_cnpj(cnpj))

    def test_normaliza_mascara_e_caixa(self):
        assert normalizar_cnpj(" 12.abc.345/01de-35 ") == "12ABC34501DE35"
        assert validar_cnpj("11.222.333/0001-81") == CNPJ_A

    def test_validar_levanta_erro(self):
        with pytest.raises(ValueError, match="CNPJ inválido"):
            validar_cnpj("11.222.333/0001-80")


class TestCodigo:
    def test_formato_e_alfabeto(self):
        for _ in range(200):
            c = gerar_codigo_aleatorio()
            assert len(c) == 12 and not set(c) & set("01OI")

    def test_normaliza_e_formata(self):
        assert normalizar_codigo(" abcd-efgh jklm ") == "ABCDEFGHJKLM"
        assert formatar_codigo("ABCDEFGHJKLM") == "ABCD-EFGH-JKLM"

    def test_sem_colisoes_em_amostra(self):
        assert len({gerar_codigo_aleatorio() for _ in range(5000)}) == 5000


class TestCors:
    """O navegador faz preflight antes de PATCH/DELETE; sem liberar o método o front não funciona."""

    @pytest.mark.parametrize(("metodo", "rota"), [("PATCH", "/empresa/equipe/1"), ("DELETE", "/empresa/codigo")])
    def test_preflight_libera_metodos_da_area_do_gestor(self, client, metodo, rota):
        r = client.options(
            rota,
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": metodo,
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert r.status_code == 200
        assert metodo in r.headers["access-control-allow-methods"]

    def test_origem_desconhecida_nao_e_liberada(self, client):
        r = client.options(
            "/empresa/codigo",
            headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "DELETE"},
        )
        assert "access-control-allow-origin" not in r.headers
