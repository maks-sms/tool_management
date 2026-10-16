# frontend/views/chat/chat_search_controller.py
"""Поиск по сообщениям в чате с подсветкой и навигацией ↑/↓."""


class ChatSearchController:
    """Ищет фрагменты в текстах сообщений, подсвечивает пузыри."""

    def __init__(self, manager):
        self.manager = manager
        self.matches = []       # список ChatBubble
        self.current_idx = -1
        self.query = ''

    def search(self, text):
        q = (text or '').strip().lower()
        if q == self.query:
            self._refresh_counter()
            return
        self.query = q
        self._recalc()

    def prev(self):
        if not self.matches:
            return
        self.current_idx = (self.current_idx - 1) % len(self.matches)
        self._highlight_current()
        self._refresh_counter()

    def next(self):
        if not self.matches:
            return
        self.current_idx = (self.current_idx + 1) % len(self.matches)
        self._highlight_current()
        self._refresh_counter()

    def clear(self):
        self.query = ''
        self.matches = []
        self.current_idx = -1
        self._refresh_counter()

    # ─── Внутреннее ───

    def _recalc(self):
        m = self.manager
        if m.ui is None:
            return

        self.matches = []
        if not self.query:
            m.ui.set_search_counter(0, 0)
            return

        for bubble in m.message_bubbles:
            if self.query in (bubble._text or '').lower():
                self.matches.append(bubble)

        self.current_idx = 0 if self.matches else -1
        self._highlight_current()
        self._refresh_counter()

        if self.matches and self.current_idx >= 0:
            self._scroll_to_bubble(self.matches[self.current_idx])

    def _highlight_current(self):
        """Подсветить текущее совпадение — рамкой вокруг пузыря."""
        from kivy.graphics import Color, Line
        for i, bubble in enumerate(self.matches):
            try:
                bubble.canvas.after.clear()
            except Exception:
                pass
            if i == self.current_idx:
                with bubble.canvas.after:
                    Color(1, 0.65, 0.15, 1)   # оранжевый
                    Line(rectangle=(bubble.x, bubble.y,
                                    bubble.width, bubble.height),
                         width=2)

    def _refresh_counter(self):
        total = len(self.matches)
        current = (self.current_idx + 1) if total and self.current_idx >= 0 else 0
        if self.manager.ui:
            self.manager.ui.set_search_counter(current, total)

    def _scroll_to_bubble(self, bubble):
        """Прокрутить ScrollView так, чтобы bubble оказался примерно в середине."""
        m = self.manager
        if m.ui is None:
            return
        box = m.ui.messages_box
        scroll = m.ui.messages_scroll
        try:
            total = box.height
            if total <= 0:
                return
            # bubble.y — относительно messages_box (снизу вверх)
            frac = 1.0 - ((bubble.y + bubble.height / 2) / total)
            scroll.scroll_y = max(0.0, min(1.0, frac))
        except Exception:
            pass