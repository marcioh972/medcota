"""Tipos reutilizáveis de entrada (validação centralizada)."""

from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, StringConstraints

from ..core.cnpj import validar_cnpj
from ..core.password import validar_senha

# Texto com espaços das pontas removidos. NÃO usar em senha (não se altera a senha do usuário).
Texto = Annotated[str, StringConstraints(strip_whitespace=True)]
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Cnpj = Annotated[str, Field(min_length=14, max_length=30), AfterValidator(validar_cnpj)]
Senha = Annotated[str, Field(max_length=128), AfterValidator(validar_senha)]
