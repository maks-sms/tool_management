# frontend/views/main/chat_background.py
"""Фоновые задачи чата (Kivy)."""
from kivy.clock import Clock


class ChatBackground:
    def __init__(self, app):
        self.app = app

    def start(self):
        # Обновление бейджа каждые 30 секунд
        Clock.schedule_interval(self._tick, 30)

    def _tick(self, dt):
        try:
            count = self.app.chat_manager_extended.get_unread_count() \
                if hasattr(self.app, 'chat_manager_extended') else 0
        except Exception:
            count = 0
        try:
            self.app.main_screen.header.set_chat_badge(count)
        except Exception:
            pass