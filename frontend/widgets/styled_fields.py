# frontend/widgets/styled_fields.py
"""
Универсальные поля ввода в стиле FilterBar:
    - белый фон + серая рамка (border-color, border-width, border-radius)
    - подсветка рамки при фокусе
    - Spinner со стрелкой ▼ и разделителями в выпадающем списке
    - LabeledField — подпись сверху + поле снизу (как в FilterBar)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.metrics import dp
from kivy.graphics import Color, Line, Rectangle

from frontend.theme import C
from frontend.widgets.bordered import BorderedMixin


# ─── Текстовое поле с рамкой ────────────────────────────────

class StyledTextInput(BorderedMixin, TextInput):
    """TextInput в стиле FilterBar: белое поле, рамка, фокус-подсветка."""

    def __init__(self, **kw):
        kw.setdefault('border_color', list(C['border']))
        kw.setdefault('border_width', 1)
        kw.setdefault('border_radius', 4)
        kw.setdefault('focus_color', list(C['primary']))

        kw.setdefault('multiline', False)
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 32)
        kw.setdefault('font_size', dp(13))
        kw.setdefault('padding', [dp(8), dp(4)])
        kw.setdefault('background_normal', '')
        kw.setdefault('background_active', '')
        kw.setdefault('background_color', C['input_bg'])
        kw.setdefault('foreground_color', C['input_fg'])
        kw.setdefault('cursor_color', C['input_fg'])
        kw.setdefault('hint_text_color', C['input_hint'])
        super().__init__(**kw)


# ─── Spinner с рамкой и стрелкой ▼ ─────────────────────────

class StyledSpinnerOption(SpinnerOption):
    """Опция выпадающего списка: белая, тёмный текст, разделитель снизу."""

    def __init__(self, **kw):
        kw.setdefault('background_normal', '')
        kw.setdefault('background_down', '')
        kw.setdefault('background_color', C['input_bg'])
        kw.setdefault('color', C['input_fg'])
        kw.setdefault('font_size', dp(13))
        kw.setdefault('height', 32)
        kw.setdefault('halign', 'left')
        kw.setdefault('valign', 'middle')
        super().__init__(**kw)

        with self.canvas.after:
            self._sep_color = Color(*C['border'])
            self._sep_line = Line(width=1)
        self.bind(pos=self._sync_sep, size=self._sync_sep)

    def _sync_sep(self, *_):
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            self._sep_line.points = []
            return
        self._sep_line.points = [x + dp(8), y + 0.5, x + w - dp(8), y + 0.5]

    def on_size(self, *args):
        self.text_size = (max(0, self.width - dp(16)), self.height)


class StyledDropDown(DropDown):
    def __init__(self, **kw):
        kw.setdefault('max_height', dp(280))
        kw.setdefault('bar_width', dp(6))
        super().__init__(**kw)


class StyledSpinner(BorderedMixin, Spinner):
    """Spinner с рамкой, выравниванием влево и стрелкой ▼ через canvas."""

    def __init__(self, **kw):
        kw.setdefault('border_color', list(C['border']))
        kw.setdefault('border_width', 1)
        kw.setdefault('border_radius', 4)
        kw.setdefault('focus_color', list(C['primary']))

        kw.setdefault('halign', 'left')
        kw.setdefault('valign', 'middle')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 32)
        kw.setdefault('font_size', dp(13))
        kw.setdefault('background_normal', '')
        kw.setdefault('background_down', '')
        kw.setdefault('background_color', C['input_bg'])
        kw.setdefault('color', C['input_fg'])
        kw.setdefault('option_cls', StyledSpinnerOption)
        kw.setdefault('dropdown_cls', StyledDropDown)
        super().__init__(**kw)

        # Стрелка ▼
        with self.canvas.after:
            self._arrow_color = Color(*C['input_hint'])
            self._arrow_line = Line(width=1.4, close=True)

        self.bind(pos=self._sync_arrow, size=self._sync_arrow)
        self._sync_arrow()

    def _sync_arrow(self, *_):
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            self._arrow_line.points = []
            return
        arrow_w = dp(8)
        arrow_h = dp(5)
        cx = x + w - dp(14)
        cy = y + h / 2.0
        half_w = arrow_w / 2.0
        p1 = (cx - half_w, cy + arrow_h / 2.0)
        p2 = (cx + half_w, cy + arrow_h / 2.0)
        p3 = (cx,          cy - arrow_h / 2.0)
        self._arrow_line.points = [*p1, *p2, *p3]

    def on_size(self, *args):
        self.text_size = (max(0, self.width - dp(28)), self.height)


# ─── Обёртка «подпись + поле» ───────────────────────────────

class LabeledField(BoxLayout):
    """
    Вертикальная ячейка: подпись сверху (мелкая, серая)
    + поле снизу (StyledTextInput / StyledSpinner).

    Использование:
        LabeledField(label='Название:', widget=StyledTextInput(text='...'))
    """

    def __init__(self, label='', widget=None, field_width=None,
                 spacing=2, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('spacing', spacing)
        if field_width is not None:
            kw.setdefault('size_hint_x', None)
            kw.setdefault('width', field_width)
        super().__init__(**kw)

        self._label = Label(
            text=label,
            size_hint_y=None,
            height=dp(14),
            color=C['secondary'],
            font_size=dp(11),
            bold=True,
            halign='left',
            valign='middle',
        )
        self._label.bind(size=lambda i, *_: setattr(
            i, 'text_size', (i.width, i.height)))
        self.add_widget(self._label)

        self._field = widget
        if widget is not None:
            self.add_widget(widget)

        # высота = подпись + поле + spacing
        field_h = widget.height if widget is not None else 0
        self.height = dp(14) + spacing + field_h

    @property
    def field(self):
        return self._field

    # Удобные прокси
    @property
    def text(self):
        return self._field.text if self._field is not None else ''

    @text.setter
    def text(self, value):
        if self._field is not None:
            self._field.text = value

    def get(self):
        return self._field.text if self._field is not None else ''

    def set(self, value):
        if self._field is not None:
            self._field.text = str(value) if value is not None else ''