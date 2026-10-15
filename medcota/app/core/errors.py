"""Formato único de erro de negócio: {"detail": {"codigo": ..., "mensagem": ..., ...}}."""

from fastapi import HTTPException


def erro(status_code: int, codigo: str, mensagem: str, *, headers: dict | None = None, **extra) -> HTTPException:
    return HTTPException(status_code, detail={"codigo": codigo, "mensagem": mensagem, **extra}, headers=headers)
