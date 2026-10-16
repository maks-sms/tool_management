# frontend/widgets/modern_window.py
"""Универсальное модальное окно — как окно чата."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from frontend.theme import C
from frontend.widgets.dialog_header import DialogHeader


class ModernWindow(ModalView):
    """Модальное окно с шапкой `#2c3e50` и ✖ справа.

    API:
        w = ModernWindow(title='Заголовок', body=some_layout,
                         size=(600, 500))
        w.open()
        w.dismiss()
    """

    _opening_in_progress = False

    def __init__(self, title='', body=None, header=True, **kw):
        if ModernWindow._opening_in_progress:
            raise RuntimeError(
                'ModernWindow: рекурсивное создание заблокировано'
            )
        ModernWindow._opening_in_progress = True
        try:
            # ─── Убираем все параметры, которых НЕТ у ModalView ───
            for k in (
                'title_size', 'title_color', 'title_align',
                'separator_height', 'separator_color',
                'content', 'background_opacity',   # ← ЭТОТ БЫЛ ЛИШНИМ
                'title',                            # передаётся отдельно
            ):
                kw.pop(k, None)

            # ─── Только валидные для ModalView параметры ───
            kw.setdefault('size_hint', (None, None))
            kw.setdefault('size', (600, 500))
            kw.setdefault('auto_dismiss', False)
            kw.setdefault('background', '')
            kw.setdefault('background_color', C['panel'])
            kw.setdefault('overlay_color', (0, 0, 0, 0.35))

            super().__init__(**kw)

            # ─── Содержимое окна ───
            root = BoxLayout(orientation='vertical', spacing=0)
            with root.canvas.before:
                Color(*C['panel'])
                root._bg = Rectangle(pos=root.pos, size=root.size)
            root.bind(
                pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                size=lambda i, *_: setattr(i._bg, 'size', i.size),
            )

            self._header = None
            if header:
                self._header = DialogHeader(
                    title=title, on_close=self.dismiss,
                )
                root.add_widget(self._header)

            if body is not None:
                root.add_widget(body)

            self.add_widget(root)
        finally:
            ModernWindow._opening_in_progress = False

    def set_title(self, text):
        if self._header is not None:
            self._header.set_title(text)