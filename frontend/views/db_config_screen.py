# frontend/views/db_config_screen.py
"""Выбор пути к БД. Обычный виджет, без своего App."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from frontend.config import APP_NAME, get_db_path, save_db_path
from frontend.theme import C
from frontend.widgets.modern_button import ModernButton


class DBConfigScreen(BoxLayout):
    def __init__(self, on_done=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', dp(24))
        kw.setdefault('spacing', dp(10))
        super().__init__(**kw)

        self._on_done = on_done

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build()

    def _build(self):
        self.add_widget(Label(
            text=APP_NAME, bold=True, font_size=dp(20),
            color=C['primary'], size_hint_y=None, height=dp(34),
        ))
        self.add_widget(Label(
            text='Путь к базе данных склада:',
            color=C['secondary'], bold=True,
            size_hint_y=None, height=dp(20),
        ))
        self.path_inp = TextInput(
            text=get_db_path() or '', multiline=False,
            size_hint_y=None, height=dp(36), font_size=dp(13),
            background_normal='', background_active='',
            background_color=C['input_bg'],
            foreground_color=C['input_fg'],
            cursor_color=C['input_fg'],
            padding=[dp(8), dp(6)],
        )
        self.add_widget(self.path_inp)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        row.add_widget(ModernButton(
            text='Продолжить', color='success',
            on_release=lambda *_: self._save(),
        ))
        row.add_widget(ModernButton(
            text='Выход', color='danger',
            on_release=lambda *_: self._finish(None),
        ))
        self.add_widget(row)

    def _save(self):
        from shared.services.database import init_db, create_default_db
        p = self.path_inp.text.strip()
        result_path = None
        if p:
            save_db_path(p)
            if not init_db(p):
                new = create_default_db()
                if not new:
                    return
                result_path = new
            else:
                result_path = p
        else:
            new = create_default_db()
            if not new:
                return
            result_path = new
        self._finish(result_path)

    def _finish(self, path):
        if self._on_done:
            self._on_done(path)