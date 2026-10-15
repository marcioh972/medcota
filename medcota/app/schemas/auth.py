from pydantic import BaseModel

from ..enums import Perfil


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    perfil: Perfil
    nome: str
    empresa: str
