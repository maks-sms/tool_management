# server/main.py
"""
FastAPI-сервер Tool Management.

Запуск:
    uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api import auth, tools
from server.config import CORS_ORIGINS, get_current_db_path

app = FastAPI(title="Tool Management API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,  prefix="/api/auth",  tags=["auth"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_path": get_current_db_path()}


# Раздача веб-клиента
_web_dir = os.path.join(_ROOT, "client_web")
if os.path.isdir(_web_dir):
    app.mount("/", StaticFiles(directory=_web_dir, html=True), name="web")