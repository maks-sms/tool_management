# frontend/views/chat_screen.py
"""Фасад чата для WarehouseApp.open_chat()."""
from frontend.views.chat.chat_manager import ChatManager

_chat_manager_instance = None


def get_chat_manager(app):
    """Один ChatManager на всё приложение."""
    global _chat_manager_instance
    if _chat_manager_instance is None:
        _chat_manager_instance = ChatManager(app)
    return _chat_manager_instance


def open_chat(app):
    get_chat_manager(app).open_chat()