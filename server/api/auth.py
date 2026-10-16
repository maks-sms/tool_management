# server/api/auth.py
"""Эндпоинты авторизации."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.core.security import create_token
from server.config import get_current_db_path
from server.services.user_service import UserService

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str
    role: str
    full_name: str
    permissions: dict


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    service = UserService(get_current_db_path())
    user = service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.id, user.username, user.role)
    return LoginResponse(
        token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name or "",
        permissions=user.permissions or {},
    )