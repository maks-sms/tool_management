# frontend/views/main/close_handler.py
"""Корректное закрытие приложения."""


class CloseHandler:
    def __init__(self, app):
        self.app = app

    def close(self):
        try:
            self.app.stop_auto_refresh()
        except Exception:
            pass
        try:
            self.app.stop()
        except Exception:
            pass