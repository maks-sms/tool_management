# frontend/theme.py
"""
Единая тема Kivy-клиента.
Повторяет логику client_desktop.config: COLORS, dialog_bg, dialog_bg_soft,
но добавляет RGBA-версии и цвета для нативных Kivy-виджетов.
"""
from kivy.metrics import dp


def _hex(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255,
            int(h[2:4], 16) / 255,
            int(h[4:6], 16) / 255, a)


# ─── Hex-палитра (как в client_desktop.config.COLORS) ───
HEX = {
    'primary':   '#2c3e50',
    'secondary': '#34495e',
    'success':   '#27ae60',
    'danger':    '#e74c3c',
    'warning':   '#f39c12',
    'info':      '#3498db',
    'light':     '#ecf0f1',
    'dark':      '#2c3e50',
    'white':     '#ffffff',
    'gray':      '#95a5a6',
    'hover':     '#e67e22',

    # Специфика client_desktop
    'header':        '#ffffff',
    'header_border': '#e5e7eb',
    'avatar_bg':     '#3b82f6',

    # Фоны — как в client_desktop (dialog_bg / dialog_bg_soft)
    'bg':      '#f5f6f8',   # фон приложения
    'panel':   '#ffffff',   # фон панелей / форм
    'soft':    '#ecf0f1',   # мягкий фон (поля, фреймы)
    'border':  '#d1d5db',   # границы

    # Цвета для Kivy-виджетов, которых не было в desktop
    'input_bg':    '#ffffff',
    'input_fg':    '#2c3e50',
    'input_hint':  '#95a5a6',
    'input_border':'#d1d5db',

    'popup_bg':    '#ffffff',
    'popup_title': '#2c3e50',

    'tab_bg':      '#ecf0f1',
    'tab_active':  '#ffffff',
    'tab_text':    '#2c3e50',
    'tab_text_active': '#2c3e50',

    'spinner_bg':  '#ffffff',
    'spinner_fg':  '#2c3e50',

    'checkbox_fg': '#3498db',
    'slider_fg':   '#3498db',

    'scrollbar_bg':   '#e5e7eb',
    'scrollbar_grip': '#95a5a6',

    'row_alt':      '#f9fafb',
    'row_selected': '#3498db',
}

# ─── RGBA-версии (для виджетов, которые принимают color) ───
C = {k: _hex(v) for k, v in HEX.items()}


def dialog_bg():
    """Аналог client_desktop.config.dialog_bg()."""
    return HEX['panel']


def dialog_bg_soft():
    """Аналог client_desktop.config.dialog_bg_soft()."""
    return HEX['soft']


def bg():
    """Фон приложения — f5f6f8 (как в Kivy Config.set background_color)."""
    return HEX['bg']


# ─── Общие размеры (как в client_desktop.config.WINDOW_SIZES) ───
WINDOW = {
    'main':      (1100, 720),
    'auth':      (420, 400),
    'db_config': (640, 260),
    'chat':      (1000, 650),
    'tool_manager': (900, 600),
    'user_manager': (760, 620),
    'tool_edit': (480, 600),
    'user_edit': (480, 620),
    'license':   (600, 620),
}

WINDOW_MIN = (900, 600)

# Имя зарегистрированного шрифта (см. frontend/main.py::_setup_fonts)
FONT_NAME = 'AppFont'