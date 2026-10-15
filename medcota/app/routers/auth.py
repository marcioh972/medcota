from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..core.config import settings
from ..core.deps import DbSession
from ..core.ratelimit import limiter
from ..schemas.auth import LoginOut
from ..services.auth import autenticar, emitir_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
@limiter.limit(settings.rate_limit_login)
def login(request: Request, form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    u = autenticar(db, form.username, form.password)
    return emitir_login(u)
