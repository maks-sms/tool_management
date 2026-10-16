# frontend/widgets/dialog_header.py
"""Верхняя панель диалога с крестиком — единый стиль с окном чата."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from frontend.theme import C


class DialogHeader(BoxLayout):
    """Полоса `#2c3e50` с заголовком слева и ✖ справа."""

    def __init__(self, title='', on_close=None, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 42)          # ← БЕЗ dp()
        kw.setdefault('spacing', 6)
        kw.setdefault('padding', [12, 6])
        super().__init__(orientation='horizontal', **kw)

        with self.canvas.before:
            Color(*C['primary'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        self.title_lbl = Label(
            text=title, bold=True, color=C['white'],
            font_size=dp(15), halign='left', valign='middle',
        )
        self.title_lbl.bind(
            size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        self.add_widget(self.title_lbl)
        self.add_widget(BoxLayout())

        self._closing = False

        def _safe_close(*_):
            if self._closing:
                return
            self._closing = True
            if on_close:
                try:
                    on_close()
                except Exception as e:
                    print(f'[DialogHeader.on_close] {e}')

        close_btn = Button(
            text='✖', size_hint=(None, None), size=(32, 32),  # ← БЕЗ dp()
            background_normal='', background_down='',
            background_color=(0, 0, 0, 0),
            color=C['white'], font_size=dp(16), bold=True,
        )
        close_btn.bind(on_release=_safe_close)
        self.add_widget(close_btn)

    def set_title(self, text):
        self.title_lbl.text = text