# server/config.py
"""
Конфиг серверной части.
Импортирует только из shared — ничего из client_desktop.*.
"""
import os
import sys

# Убедимся, что корень проекта в sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Общие настройки (путь к БД, константы)
from shared.config import get_db_path, LOCATION_MACHINE_PREFIX, LOCATION_RESERVE

# ─── API ────────────────────────────────────────────────
API_HOST = os.environ.get("TM_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("TM_API_PORT", "8000"))

# ─── JWT ────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "TM_SECRET_KEY",
    "CHANGE_ME_на_длинную_случайную_строку",
)
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12

# ─── CORS ───────────────────────────────────────────────
CORS_ORIGINS = ["*"]


def get_current_db_path() -> str:
    """Актуальный путь к БД (читается каждый раз из общего конфига)."""
    return get_db_path()