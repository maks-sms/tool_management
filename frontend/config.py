"""Конфиг клиента Kivy. Общие настройки — из shared.config."""
import os, sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shared.config import (
    APP_NAME, COMPANY, VERSION,
    LOCATION_WAREHOUSE, LOCATION_RESERVE, LOCATION_MACHINE_PREFIX,
    HISTORY_LIMIT, CHAT_MESSAGE_LIMIT,
    CHAT_USER_STATUS_MINUTES, CHAT_UNREAD_BADGE_MAX,
    ROLE_ADMIN, ROLE_USER,
    REFRESH_INTERVAL_DEFAULT, REFRESH_INTERVAL_OPTIONS,
    get_db_path, save_db_path,
    get_saved_username, save_username,
    get_column_widths_config, save_column_widths,
    get_column_alignment_config, save_column_alignment,
    get_remember_password, save_remember_password,
    get_saved_password, save_password, get_decrypted_password,
    get_app_dir,
)

def hex_to_rgba(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255, a)

COLORS_HEX = {
    'primary': '#2c3e50', 'secondary': '#34495e',
    'success': '#27ae60', 'danger': '#e74c3c',
    'warning': '#f39c12', 'info': '#3498db',
    'light': '#ecf0f1', 'dark': '#2c3e50',
    'white': '#ffffff', 'gray': '#95a5a6',
    'hover': '#e67e22',
    'header': '#ffffff', 'header_border': '#e5e7eb',
    'avatar_bg': '#3b82f6',
    'bg': '#f5f6f8',        # ← фон приложения
    'panel': '#ffffff',      # ← фон панелей
    'border': '#d1d5db',     # ← границы полей
}

# RGBA — оставляем для тех виджетов, которые понимают color
COLORS = {k: hex_to_rgba(v) for k, v in COLORS_HEX.items()}

# Hex — для тех, где Kivy ждёт строку
COLORS_STR = dict(COLORS_HEX)

# Размеры окна
WINDOW_SIZE = (1100, 720)
WINDOW_MIN = (900, 600)

# Шрифты
from frontend.theme import FONT_NAME as _FONT_NAME

FONT_BOLD = _FONT_NAME
FONT_SIZE = 14
FONT_SIZE_SMALL = 12
FONT_SIZE_TITLE = 18