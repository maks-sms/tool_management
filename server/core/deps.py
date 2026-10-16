# server/core/deps.py
"""Общие зависимости FastAPI."""
from fastapi import Header, HTTPException

from server.core.security import decode_token


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    payload = decode_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload