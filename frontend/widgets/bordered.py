# frontend/widgets/bordered.py
"""Миксин, рисующий рамку вокруг виджета через canvas.after."""
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty

from frontend.theme import C


# Берём цвета напрямую из темы — единый источник правды
DEFAULT_BORDER = tuple(C['border'])       # #d1d5db — светло-серая
FOCUS_BORDER   = tuple(C['primary'])      # #2c3e50 — тёмно-синяя


class BorderedMixin:
    """Добавляет виджету прямоугольную рамку по его границам.

    Атрибуты:
        border_color   — цвет рамки (RGBA)
        border_width   — толщина в пикселях
        border_radius  — радиус скругления (0 = прямые углы)
        focus_color    — цвет при фокусе (если у виджета есть focus)
    """
    border_color = ListProperty(list(DEFAULT_BORDER))
    border_width = NumericProperty(1)
    border_radius = NumericProperty(0)
    focus_color = ListProperty(list(FOCUS_BORDER))

    _base_border_color = ListProperty(list(DEFAULT_BORDER))

    def __init__(self, **kw):
        bc = kw.pop('border_color', None)
        bw = kw.pop('border_width', None)
        br = kw.pop('border_radius', None)
        fc = kw.pop('focus_color', None)

        super().__init__(**kw)

        # Запоминаем «базовый» цвет — тот, что возвращается после снятия фокуса
        if bc is not None:
            self.border_color = list(bc)
            self._base_border_color = list(bc)
        else:
            self._base_border_color = list(self.border_color)

        if bw is not None:
            self.border_width = bw
        if br is not None:
            self.border_radius = br
        if fc is not None:
            self.focus_color = list(fc)

        # Рисуем рамку поверх содержимого виджета
        with self.canvas.after:
            self._border_color_instr = Color(*self.border_color)
            self._border_line = Line(width=self.border_width)

        self.bind(
            pos=self._sync_border,
            size=self._sync_border,
            border_color=self._sync_border_color,
            border_width=self._sync_border_width,
        )

        # Фокусная подсветка — только если у виджета есть свойство focus
        if hasattr(self, 'focus'):
            self.bind(focus=self._on_focus_change)

        self._sync_border()

    # ─── реакции на изменения ───

    def _sync_border_color(self, *_):
        self._border_color_instr.rgba = self.border_color

    def _sync_border_width(self, *_):
        self._border_line.width = self.border_width

    def _sync_border(self, *_):
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            self._border_line.points = []
            return
        r = float(self.border_radius or 0)
        self._border_line.rounded_rectangle = (
            x + 0.5, y + 0.5, w - 1, h - 1, r
        )

    def _on_focus_change(self, _, focused):
        if focused:
            self.border_color = list(self.focus_color)
        else:
            self.border_color = list(self._base_border_color)