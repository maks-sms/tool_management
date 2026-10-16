# server/api/tools.py
"""Эндпоинты склада."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.config import get_current_db_path
from server.core.deps import get_current_user
from server.services.tool_service import ToolService
from shared.models.tool import ToolCreate, ToolUpdate

router = APIRouter()


def _tool_to_dict(t) -> dict:
    return {
        "id": t.id,
        "inner_code": t.inner_code,
        "articul": t.articul,
        "type": t.type or "",
        "diameter": t.diameter or "",
        "length": t.length or "",
        "brand": t.brand or "",
        "analog": t.analog or "",
        "qty_total": t.qty_total,
        "min_qty": t.min_qty or 0,
    }


@router.get("")
async def list_tools(
    search: Optional[str] = None,
    type: Optional[str] = None,
    brand: Optional[str] = None,
    diameter: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    filters = {}
    if search:   filters["search"] = search
    if type:     filters["type"] = type
    if brand:    filters["brand"] = brand
    if diameter: filters["diameter"] = diameter

    service = ToolService(get_current_db_path())
    return [_tool_to_dict(t) for t in service.get_all(filters)]


@router.get("/types")
async def list_types(user: dict = Depends(get_current_user)):
    service = ToolService(get_current_db_path())
    return {"types": service.get_unique_types()}


@router.get("/brands")
async def list_brands(user: dict = Depends(get_current_user)):
    service = ToolService(get_current_db_path())
    return {"brands": service.get_unique_brands()}


@router.get("/{tool_id}")
async def get_tool(tool_id: int, user: dict = Depends(get_current_user)):
    service = ToolService(get_current_db_path())
    tool = service.get_by_id(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    return _tool_to_dict(tool)


class CreateToolRequest(BaseModel):
    inner_code: str
    articul: str
    type: str = ""
    diameter: str = ""
    length: str = ""
    brand: str = ""
    analog: str = ""
    qty_total: int = 0


@router.post("")
async def create_tool(req: CreateToolRequest,
                      user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admin can create tools")
    service = ToolService(get_current_db_path())
    try:
        tool = service.create(ToolCreate(**req.dict()))
    except Exception as e:
        raise HTTPException(400, str(e))
    return _tool_to_dict(tool)