# frontend/widgets/modern_entry.py
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, BooleanProperty
from kivy.metrics import dp

from frontend.theme import C
from frontend.widgets.styled_fields import StyledTextInput


class ModernEntry(BoxLayout):
    label_text = StringProperty('')
    placeholder = StringProperty('')
    numeric = BooleanProperty(False)
    integer = BooleanProperty(False)

    def __init__(self, label_text='', placeholder='', numeric=False,
                 integer=False, allow_negative=False, max_length=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(62) if label_text else dp(40))
        kw.setdefault('spacing', dp(2))
        super().__init__(**kw)
        self.label_text = label_text
        self.placeholder = placeholder
        self.numeric = numeric or integer
        self.integer = integer
        self._max_length = max_length

        if label_text:
            self.add_widget(Label(
                text=label_text, size_hint_y=None, height=dp(18),
                color=C['secondary'], halign='left', valign='middle',
                font_size=dp(11), bold=True,
            ))

        # Используем общий StyledTextInput — тот же, что в FilterBar
        self.entry = StyledTextInput(
            hint_text=placeholder,
            size_hint_y=None,
            height=dp(34),
            write_tab=False,
        )
        if self.numeric:
            self.entry.input_filter = 'int' if integer else 'float'
        if max_length:
            self.entry.input_filter = lambda s, from_undo: len(s) <= max_length

        self.add_widget(self.entry)

    def get(self):
        return self.entry.text

    def set(self, value):
        self.entry.text = str(value) if value is not None else ''

    def delete(self, start, end=None):
        self.entry.text = ''