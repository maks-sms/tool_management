# frontend/views/chat/chat_group_manager.py
"""Создание и управление группами чата."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from frontend.theme import C
from frontend.widgets.modern_button import ModernButton


class ChatGroupManager:
    def __init__(self, manager):
        self.manager = manager

    def create_group_dialog(self):
        """Диалог создания группы."""
        m = self.manager
        box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))

        box.add_widget(Label(text='Название группы *:',
                             size_hint_y=None, height=dp(20),
                             color=C['secondary'], bold=True,
                             halign='left'))
        name_input = TextInput(multiline=False, size_hint_y=None,
                               height=dp(32),
                               background_normal='', background_active='',
                               background_color=C['input_bg'],
                               foreground_color=C['input_fg'])
        box.add_widget(name_input)

        box.add_widget(Label(text='Участники:',
                             size_hint_y=None, height=dp(20),
                             color=C['secondary'], bold=True,
                             halign='left'))

        users = m.chat_service.get_users_except(m.current_user[0]) or []
        users_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        users_grid.bind(minimum_height=users_grid.setter('height'))
        user_vars = []
        for u in users:
            uid, username, full_name, _t = u[:4]
            display = full_name or username
            row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(4))
            row.add_widget(Label(text=display, color=C['dark']))
            cb = CheckBox(size_hint_x=None, width=dp(28), color=C['info'])
            row.add_widget(cb)
            users_grid.add_widget(row)
            user_vars.append((uid, cb))

        scroll = ScrollView()
        scroll.add_widget(users_grid)
        box.add_widget(scroll)

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        ok_btn = ModernButton(text='Создать', color='success',
                              size_hint=(1, 1), height=dp(38))
        cancel_btn = ModernButton(text='Отмена', color='danger',
                                  size_hint=(1, 1), height=dp(38))
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)

        popup = Popup(title='Создание группы', content=box,
                      size_hint=(None, None), size=(dp(420), dp(520)),
                      background_color=C['panel'],
                      separator_color=C['border'])

        def do_create(*_):
            name = name_input.text.strip()
            if not name:
                return
            members = [uid for uid, cb in user_vars if cb.active]
            try:
                m.chat_service.create_group(
                    name=name, description='',
                    created_by=m.current_user[0],
                    members=members,
                )
            except Exception as e:
                print(f'[chat.group] {e}')
            popup.dismiss()
            m.list_controller.update()

        ok_btn.bind(on_release=do_create)
        cancel_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def show_group_info(self):
        """Информация о группе."""
        m = self.manager
        if not m.current_group:
            return

        box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(6))
        box.add_widget(Label(text=m.current_group['name'],
                             bold=True, size_hint_y=None, height=dp(24),
                             color=C['primary']))
        box.add_widget(Label(text=f"Участников: {m.current_group.get('member_count', 0)}",
                             size_hint_y=None, height=dp(20),
                             color=C['secondary']))

        try:
            members = m.chat_service.get_group_members(m.current_group['id']) or []
        except Exception:
            members = []

        members_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        members_grid.bind(minimum_height=members_grid.setter('height'))
        for member in members:
            uid, username, full_name, is_creator = member
            display = full_name or username
            if is_creator:
                display += '  👑'
            members_grid.add_widget(Label(text=display,
                                          size_hint_y=None,
                                          height=dp(22),
                                          color=C['dark']))
        scroll = ScrollView()
        scroll.add_widget(members_grid)
        box.add_widget(scroll)

        close = ModernButton(text='Закрыть', color='info',
                             size_hint=(None, None), size=(dp(120), dp(38)))
        close.pos_hint = {'center_x': 0.5}
        box.add_widget(close)

        popup = Popup(title='Информация о группе', content=box,
                      size_hint=(None, None), size=(dp(400), dp(480)),
                      background_color=C['panel'],
                      separator_color=C['border'])
        close.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def leave_current_group(self):
        """Покинуть текущую группу."""
        m = self.manager
        if not m.current_group:
            return
        try:
            m.chat_service.remove_group_member(
                m.current_group['id'], m.current_user[0]
            )
        except Exception as e:
            print(f'[chat.leave] {e}')
        m.current_group = None
        m.select_general()
        m.list_controller.update()