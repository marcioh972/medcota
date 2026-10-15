"""Configuração central (12-factor): tudo vem de variáveis de ambiente ou do arquivo .env."""

from datetime import time
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ambiente: Literal["desenvolvimento", "teste", "producao"] = "desenvolvimento"
    database_url: str = "sqlite:///./medcota.db"

    # Sem valor padrão de propósito: a aplicação não sobe sem segredo.
    jwt_secret: str = Field(min_length=32)
    jwt_algoritmo: str = "HS256"
    jwt_expira_horas: int = 8
    bcrypt_rounds: int = Field(12, ge=4, le=16)  # custo do hash de senha

    cors_origens: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    alcada_aprovacao: Decimal = Decimal("5000")  # RN-06
    validade_cotacao_h: int = 48  # RN-01
    frete_padrao: Decimal = Decimal("45")
    horario_corte: time = time(17, 0)  # RF-09
    fuso_horario: str = "America/Maceio"

    login_max_falhas: int = 5  # RF-03
    login_bloqueio_min: int = 30
    rate_limit_ativo: bool = True
    rate_limit_login: str = "10/minute"
    rate_limit_cadastro: str = "5/minute"  # cadastro de empresa e de funcionário
    rate_limit_publico: str = "60/minute"

    codigo_validade_dias: int = Field(7, ge=1, le=365)  # validade do código de cadastro de funcionários

    nfe_max_bytes: int = Field(2_000_000, ge=10_000, le=20_000_000)  # tamanho máximo do XML da NF-e

    log_nivel: str = "INFO"

    @model_validator(mode="after")
    def _regras_de_producao(self):
        if self.ambiente == "producao" and "*" in self.cors_origens:
            raise ValueError("CORS_ORIGENS não pode conter '*' em produção")
        return self


settings = Settings()
