# frontend/views/auth_screen.py
"""Экран авторизации. Виджет, без своего App."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

from frontend.config import get_saved_username, save_username
from frontend.theme import C
from frontend.widgets.modern_entry import ModernEntry
from frontend.widgets.modern_button import ModernButton


class AuthScreen(BoxLayout):
    def __init__(self, on_done=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', [dp(30), dp(20)])
        kw.setdefault('spacing', dp(8))
        super().__init__(**kw)

        self._on_done = on_done
        self.result = None

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._build()

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _build(self):
        self.add_widget(Label(
            text='Tool Management', bold=True,
            font_size=dp(22), color=C['primary'],
            size_hint_y=None, height=dp(38),
        ))
        self.add_widget(Label(
            text='Система учета инструмента',
            font_size=dp(13), color=C['gray'],
            size_hint_y=None, height=dp(22),
        ))
        self.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        self.username = ModernEntry(
            label_text='Логин', placeholder='Введите логин',
        )
        self.username.set(get_saved_username())
        self.add_widget(self.username)

        self.password = ModernEntry(
            label_text='Пароль', placeholder='Введите пароль',
        )
        self.password.entry.password = True
        self.add_widget(self.password)

        self.username.entry.bind(
            on_text_validate=lambda *_: self.password.entry.focus_set()
        )
        self.password.entry.bind(
            on_text_validate=lambda *_: self._do_login()
        )

        row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        row.add_widget(Label(
            text='Запомнить меня', size_hint_x=None, width=dp(150),
            color=C['dark'], halign='left',
        ))
        self.remember = CheckBox(
            active=bool(get_saved_username()),
            size_hint_x=None, width=dp(28),
            color=C['info'],
        )
        row.add_widget(self.remember)
        row.add_widget(BoxLayout())
        self.add_widget(row)

        self.error_lbl = Label(
            text='', color=C['danger'],
            size_hint_y=None, height=dp(20), font_size=dp(12),
        )
        self.add_widget(self.error_lbl)

        self.login_btn = ModernButton(
            text='ВОЙТИ', color='success',
            size_hint=(None, None), size=(dp(200), dp(42)),
        )
        self.login_btn.pos_hint = {'center_x': 0.5}
        self.login_btn.bind(on_release=lambda *_: self._do_login())
        self.add_widget(self.login_btn)

        Clock.schedule_once(self._focus_first, 0.3)

    def _focus_first(self, *_):
        try:
            if get_saved_username():
                self.password.entry.focus = True
            else:
                self.username.entry.focus = True
        except Exception:
            pass

    def _do_login(self):
        from shared.services.user_service import UserService
        u = self.username.get().strip()
        p = self.password.get()
        if not u or not p:
            self.error_lbl.text = 'Введите логин и пароль'
            return
        try:
            svc = UserService()
            user = svc.authenticate(u, p)
        except Exception as e:
            self.error_lbl.text = f'Ошибка: {e}'
            return
        if user:
            save_username(u if self.remember.active else '')
            self.result = (user.id, user.username, user.role,
                           user.full_name, user.permissions)
            if self._on_done:
                self._on_done(self.result)
        else:
            self.error_lbl.text = 'Неверный логин или пароль'