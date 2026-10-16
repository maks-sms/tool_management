# frontend/views/main/notifications.py
"""Профиль пользователя и заглушка уведомлений."""
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from frontend.widgets.modern_button import ModernButton


class Notifications:
    def __init__(self, app):
        self.app = app

    def open_profile(self):
        box = BoxLayout(orientation='vertical', padding=16, spacing=8)
        box.add_widget(Label(
            text=f"{self.app.current_user_fullname}\n{self.app.current_username}",
            halign='center',
        ))
        btn = ModernButton(text='OK', color='info',
                           size_hint=(None, None), size=(120, 40))
        btn.pos_hint = {'center_x': 0.5}
        box.add_widget(btn)
        popup = Popup(title='Профиль', content=box,
                      size_hint=(None, None), size=(400, 200))
        btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def show_notifications_popup(self):
        box = BoxLayout(orientation='vertical', padding=16, spacing=8)
        box.add_widget(Label(text='Пока нет уведомлений', halign='center'))
        btn = ModernButton(text='OK', color='info',
                           size_hint=(None, None), size=(120, 40))
        btn.pos_hint = {'center_x': 0.5}
        box.add_widget(btn)
        popup = Popup(title='Уведомления', content=box,
                      size_hint=(None, None), size=(360, 180))
        btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()