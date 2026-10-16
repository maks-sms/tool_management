"""Верхняя панель — лого, крошки, чат, колокольчик, аватар, индикатор."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Ellipse
from kivy.properties import StringProperty, ObjectProperty
from frontend.config import COLORS, APP_NAME
from frontend.views.main.helpers import get_initials  # см. ниже


class Avatar(ButtonBehavior, BoxLayout):
    initials = StringProperty('?')

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (32, 32)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*COLORS['avatar_bg'])
            Ellipse(pos=self.pos, size=self.size)
        self.clear_widgets()
        self.add_widget(Label(text=self.initials, bold=True,
                              color=(1,1,1,1), font_size=12))


class HeaderBar(BoxLayout):
    breadcrumb = StringProperty('Склад')
    chat_badge = StringProperty('')
    app_ref = ObjectProperty(None, allownone=True)

    def __init__(self, app, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 48)
        kw.setdefault('padding', [12, 4])
        kw.setdefault('spacing', 6)
        super().__init__(**kw)
        self.app_ref = app
        self._build()

    def _build(self):
        # Левая часть
        self.add_widget(Label(text='🔧', size_hint_x=None, width=28,
                              font_size=18, color=COLORS['primary']))
        self.add_widget(Label(text=APP_NAME, size_hint_x=None, width=140,
                              bold=True, color=COLORS['primary'],
                              font_size=14, halign='left'))
        self.add_widget(Label(text='›', size_hint_x=None, width=16,
                              color=COLORS['gray'], font_size=14))
        self.breadcrumb_lbl = Label(text=self.breadcrumb, color=COLORS['gray'],
                                    font_size=13, halign='left')
        self.bind(breadcrumb=lambda *_: setattr(self.breadcrumb_lbl, 'text', self.breadcrumb))
        self.add_widget(self.breadcrumb_lbl)
        self.add_widget(BoxLayout())

        # Правая часть
        app = self.app_ref

        self.refresh_lbl = Label(text='●', size_hint_x=None, width=18,
                                 color=COLORS['success'], font_size=12)
        self.add_widget(self.refresh_lbl)

        # Аватар + меню
        av = Avatar(initials=get_initials(app.current_user_fullname))
        av.bind(on_release=self._open_user_menu)
        self.add_widget(av)
        self.add_widget(Label(text=app.current_user_fullname,
                              size_hint_x=None, width=180,
                              bold=True, color=COLORS['primary'],
                              font_size=12, halign='left'))

        self.chat_btn = Button(text='💬', size_hint=(None, None),
                               size=(48, 36), font_size=16,
                               background_normal='',
                               background_color=(0,0,0,0),
                               color=COLORS['secondary'],
                               on_release=lambda *_: app.open_chat())
        self.add_widget(self.chat_btn)

        self.bell_btn = Button(text='🔔', size_hint=(None, None),
                               size=(44, 36), font_size=16,
                               background_normal='',
                               background_color=(0,0,0,0),
                               color=COLORS['secondary'],
                               on_release=lambda *_: app.show_notifications())
        self.add_widget(self.bell_btn)

    def _open_user_menu(self, *_):
        app = self.app_ref
        dd = DropDown()
        for label, cb in [
            ('👤 Профиль', app.open_profile),
            ('🔒 Сменить пароль', app.change_password),
            (None, None),
            ('🔄 Сменить пользователя', app.switch_user),
            (None, None),
            ('🚪 Выход', app.on_close),
        ]:
            if label is None:
                continue
            b = Button(text=label, size_hint_y=None, height=34)
            b.bind(on_release=lambda btn, c=cb: (dd.dismiss(), c()))
            dd.add_widget(b)
        dd.open(self)

    def set_breadcrumb(self, text):
        self.breadcrumb = text
        self.breadcrumb_lbl.text = text

    def set_chat_badge(self, count):
        if count > 0:
            txt = f"💬{count if count < 100 else '99+'}"
            self.chat_btn.text = txt
            self.chat_btn.color = COLORS['danger']
        else:
            self.chat_btn.text = '💬'
            self.chat_btn.color = COLORS['secondary']