# frontend/widgets/modern_button.py
from kivy.uix.button import Button
from kivy.properties import ListProperty
from kivy.metrics import dp
from frontend.theme import C


def _shade(color, factor=0.85):
    r, g, b, a = color
    return (r * factor, g * factor, b * factor, a)


class ModernButton(Button):
    bg_color = ListProperty(C['info'])
    hover_color = ListProperty(_shade(C['info']))
    text_color = ListProperty((1, 1, 1, 1))

    def __init__(self, color='info', compact=False, **kw):
        kw.setdefault('background_normal', '')
        kw.setdefault('background_down', '')
        kw.setdefault('background_color', (0, 0, 0, 0))
        kw.setdefault('font_size', dp(12) if compact else dp(14))
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(28) if compact else dp(38))
        kw.setdefault('color', (1, 1, 1, 1))
        super().__init__(**kw)
        self.bg_color = C.get(color, C['info'])
        self.hover_color = _shade(self.bg_color, 0.85)
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw)

    def _redraw(self, *a):
        self.canvas.before.clear()
        from kivy.graphics import Color, RoundedRectangle
        with self.canvas.before:
            c = self.hover_color if self.state == 'down' else self.bg_color
            Color(*c)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])