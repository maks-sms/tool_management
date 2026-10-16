"""Верхняя панель главного окна (Kivy)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.properties import StringProperty, ObjectProperty
from kivy.metrics import dp

from frontend.config import APP_NAME
from frontend.theme import C
from frontend.views.main.helpers import get_initials


class Avatar(ButtonBehavior, BoxLayout):
    initials = StringProperty('?')

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (dp(32), dp(32))
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*C['avatar_bg'])
            Ellipse(pos=self.pos, size=self.size)
        self.clear_widgets()
        self.add_widget(Label(
            text=self.initials, bold=True,
            color=(1, 1, 1, 1), font_size=dp(12),
        ))


class HeaderBar(BoxLayout):
    breadcrumb = StringProperty('Склад')
    chat_badge = StringProperty('')
    app_ref = ObjectProperty(None, allownone=True)

    def __init__(self, app, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(48))
        kw.setdefault('padding', [dp(12), dp(4)])
        kw.setdefault('spacing', dp(6))
        super().__init__(**kw)
        self.app_ref = app

        # Белый фон + нижняя граница
        with self.canvas.before:
            Color(*C['panel'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(*C['header_border'])
            self._line = Line(points=[], width=1)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._build()

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        y = self.pos[1]
        self._line.points = [self.x, y, self.x + self.width, y]

    def _build(self):
        self.add_widget(Label(text='🔧', size_hint_x=None, width=dp(28),
                              font_size=dp(18), color=C['primary']))
        self.add_widget(Label(text=APP_NAME, size_hint_x=None, width=dp(180),
                              bold=True, color=C['primary'],
                              font_size=dp(14), halign='left'))
        self.add_widget(Label(text='›', size_hint_x=None, width=dp(16),
                              color=C['gray'], font_size=dp(14)))

        self.breadcrumb_lbl = Label(
            text=self.breadcrumb, color=C['gray'],
            font_size=dp(13), halign='left',
        )
        self.add_widget(self.breadcrumb_lbl)
        self.add_widget(BoxLayout())

        app = self.app_ref

        self.refresh_lbl = Label(text='●', size_hint_x=None, width=dp(18),
                                 color=C['success'], font_size=dp(12))
        self.add_widget(self.refresh_lbl)

        av = Avatar(initials=get_initials(app.current_user_fullname))
        av.bind(on_release=self._open_user_menu)
        self.add_widget(av)
        self.add_widget(Label(
            text=app.current_user_fullname or app.current_username,
            size_hint_x=None, width=dp(180),
            bold=True, color=C['primary'],
            font_size=dp(12), halign='left',
        ))

        self.chat_btn = Button(
            text='💬', size_hint=(None, None),
            size=(dp(48), dp(36)), font_size=dp(16),
            background_normal='', background_color=(0, 0, 0, 0),
            color=C['secondary'],
            on_release=lambda *_: app.open_chat(),
        )
        self.add_widget(self.chat_btn)

        self.bell_btn = Button(
            text='🔔', size_hint=(None, None),
            size=(dp(44), dp(36)), font_size=dp(16),
            background_normal='', background_color=(0, 0, 0, 0),
            color=C['secondary'],
            on_release=lambda *_: app.show_notifications_popup(),
        )
        self.add_widget(self.bell_btn)

    def _open_user_menu(self, *_):
        app = self.app_ref
        dd = DropDown()
        items = [
            ('👤 Профиль', app.open_profile),
            ('🔒 Сменить пароль', app.change_password),
            ('🔄 Сменить пользователя', app.switch_user),
            ('🚪 Выход', app.on_close),
        ]
        for label, cb in items:
            b = Button(
                text=label, size_hint_y=None, height=dp(34),
                background_normal='', background_color=C['panel'],
                color=C['dark'],
            )
            b.bind(on_release=lambda btn, c=cb: (dd.dismiss(), c()))
            dd.add_widget(b)
        dd.open(self)

    def set_breadcrumb(self, text):
        self.breadcrumb = text
        self.breadcrumb_lbl.text = text

    def set_chat_badge(self, count):
        if count > 0:
            self.chat_btn.text = f"💬{count if count < 100 else '99+'}"
            self.chat_btn.color = C['danger']
        else:
            self.chat_btn.text = '💬'
            self.chat_btn.color = C['secondary']