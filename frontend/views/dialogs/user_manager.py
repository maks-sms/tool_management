# frontend/views/dialogs/user_manager.py
"""Управление пользователями — единый стиль с фильтром и крестиком."""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

from frontend.theme import C
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.filter_bar import FilterField
from frontend.widgets.filtered_tree_dialog import FilteredTreeDialog


class UserManagerDialog(FilteredTreeDialog):
    def __init__(self, app, **kw):
        self.app = app
        super().__init__(
            title='Управление пользователями',
            columns=[
                ('id', 'ID', 1), ('username', 'Логин', 2),
                ('full_name', 'ФИО', 3), ('role', 'Роль', 1),
                ('created_at', 'Дата', 2), ('last_login', 'Последний вход', 2),
            ],
            fields=[
                FilterField('search', 'Поиск:', 'entry', width=dp(200)),
                FilterField('role', 'Роль:', 'combo',
                            values=['Все', 'user', 'admin'],
                            default='Все', width=dp(120)),
            ],
            on_change=self._refresh_with_filter,
            buttons=[
                ('➕ Добавить', 'success', self._add),
                ('✏️ Редактировать', 'warning', self._edit),
                ('🗑️ Удалить', 'danger', self._delete),
                ('🔒 Пароль', 'info', self._reset_pwd),
            ],
            on_refresh=self._refresh_with_filter,
            size=(dp(850), dp(600)),
        )
        self._refresh_with_filter()

    def _refresh_with_filter(self):
        try:
            users = self.app.user_service.get_all() or []
        except Exception as e:
            print(f'[users] {e}')
            users = []

        f = self.filter_bar.get_values() if getattr(self, 'filter_bar', None) else {}
        search = (f.get('search') or '').lower()
        role = (f.get('role') or 'Все').strip()

        prepared = []
        for u in users:
            if search:
                uname = (u.username or '').lower()
                fname = (u.full_name or '').lower()
                if search not in uname and search not in fname:
                    continue
            if role and role != 'Все' and (u.role or '') != role:
                continue
            prepared.append({
                'id': u.id, 'username': u.username,
                'full_name': u.full_name or '', 'role': u.role,
                'created_at': str(u.created_at or ''),
                'last_login': str(u.last_login or ''),
            })
        self.tree.set_rows(prepared)

    def _refresh(self):
        self._refresh_with_filter()

    def _add(self):
        self._form(None)

    def _edit(self):
        sel = self.tree.get_selected()
        if not sel:
            return
        u = self.app.user_service.get_by_id(sel['id'])
        if u:
            self._form(u)

    def _delete(self):
        sel = self.tree.get_selected()
        if not sel:
            return
        if sel.get('username') in ('admin', self.app.current_username):
            self._info('Удаление невозможно',
                       'Нельзя удалить администратора или себя.')
            return
        try:
            if self.app.user_service.delete(sel['id']):
                self._refresh_with_filter()
        except Exception as e:
            print(f'[users.delete] {e}')

    def _reset_pwd(self):
        from frontend.widgets.styled_fields import StyledTextInput, LabeledField
        from kivy.uix.gridlayout import GridLayout

        sel = self.tree.get_selected()
        if not sel:
            return

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))
        pwd = StyledTextInput(password=True)
        grid.add_widget(LabeledField(
            label=f"Новый пароль для {sel['username']}:", widget=pwd,
        ))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        dlg = ModernDialog(title='Сброс пароля', body=bx, size=(440, 200))

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='OK', color='success', size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger', size_hint=(1, 1))
        row.add_widget(ok); row.add_widget(cancel)
        bx.add_widget(row)

        def do_reset(*_):
            if pwd.text:
                self.app.user_service.reset_password(sel['id'], pwd.text)
                dlg.dismiss()
        ok.bind(on_release=do_reset)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()

    def _form(self, user):
        from shared.models.user import UserCreate, UserUpdate
        from frontend.widgets.styled_fields import (
            StyledTextInput, StyledSpinner, LabeledField,
        )
        from kivy.uix.gridlayout import GridLayout

        # Левая колонка: логин, пароль, ФИО, роль
        left = BoxLayout(orientation='vertical', size_hint_x=0.5,
                         spacing=dp(8))
        right = BoxLayout(orientation='vertical', size_hint_x=0.5,
                          spacing=dp(8))

        username = StyledTextInput(
            text=user.username if user else '',
            disabled=bool(user),
        )
        password = StyledTextInput(
            password=True,
            hint_text='Оставьте пустым, чтобы не менять' if user else '',
        )
        full_name = StyledTextInput(
            text=(user.full_name or '') if user else '',
        )
        role = StyledSpinner(
            text=(user.role if user else 'user'),
            values=['user', 'admin'],
        )

        left.add_widget(LabeledField(label='Логин *:', widget=username))
        left.add_widget(LabeledField(label='Пароль *:', widget=password))
        left.add_widget(LabeledField(label='ФИО:', widget=full_name))
        left.add_widget(LabeledField(label='Роль:', widget=role))
        left.add_widget(BoxLayout())

        # Правая колонка: права доступа
        right.add_widget(Label(
            text='Права доступа:', size_hint_y=None, height=dp(16),
            color=C['secondary'], bold=True, font_size=dp(11),
            halign='left', valign='middle',
        ))

        tabs = ['inventory', 'machines', 'reserve', 'history',
                'tools', 'requests', 'export']
        perms_widgets = {}

        grid = GridLayout(cols=5, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter('height'))
        for h in ('Вкладка', 'Просм.', '', 'Редакт.', ''):
            grid.add_widget(Label(
                text=h, bold=True, color=C['secondary'],
                size_hint_y=None, height=dp(20),
                halign='center', valign='middle',
            ))
        for tab in tabs:
            grid.add_widget(Label(
                text=tab, size_hint_y=None, height=dp(24),
                color=C['dark'], font_size=dp(12),
                halign='left', valign='middle',
            ))
            v = CheckBox(active=True, size_hint_y=None, height=dp(24))
            grid.add_widget(v)
            grid.add_widget(BoxLayout(size_hint_x=None, width=dp(4)))
            e = CheckBox(active=True, size_hint_y=None, height=dp(24))
            grid.add_widget(e)
            grid.add_widget(BoxLayout(size_hint_x=None, width=dp(4)))
            perms_widgets[tab] = (v, e)

        from kivy.uix.scrollview import ScrollView
        scroll = ScrollView(size_hint_y=None, height=dp(220))
        scroll.add_widget(grid)
        right.add_widget(scroll)

        cols = BoxLayout(orientation='horizontal',
                         spacing=dp(12), size_hint_y=None)
        cols.add_widget(left)
        cols.add_widget(right)
        cols.bind(minimum_height=cols.setter('height'))

        bx = BoxLayout(orientation='vertical', padding=dp(14),
                       spacing=dp(10), size_hint_y=None)
        bx.bind(minimum_height=bx.setter('height'))
        bx.add_widget(cols)

        dlg = ModernDialog(
            title=('Редактирование' if user else 'Добавление пользователя'),
            body=bx, size=(760, 460),
        )

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Сохранить', color='success', size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger', size_hint=(1, 1))
        row.add_widget(ok); row.add_widget(cancel)
        bx.add_widget(row)

        def save(*_):
            permissions = {t: {'view': v.active, 'edit': e.active}
                           for t, (v, e) in perms_widgets.items()}
            try:
                if user:
                    u = UserUpdate(full_name=full_name.text.strip(),
                                   role=role.text,
                                   permissions=permissions)
                    self.app.user_service.update(user.id, u)
                    if password.text:
                        self.app.user_service.reset_password(
                            user.id, password.text,
                        )
                else:
                    u = UserCreate(
                        username=username.text.strip(),
                        password=password.text,
                        full_name=full_name.text.strip(),
                        role=role.text,
                        permissions=permissions,
                    )
                    self.app.user_service.create(u)
                self._refresh_with_filter()
                dlg.dismiss()
            except Exception as e:
                print(f'[user.save] {e}')

        ok.bind(on_release=save)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()

    def _info(self, title, msg):
        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(Label(text=msg, halign='center'))
        dlg = ModernDialog(title=title, body=bx, size=(dp(400), dp(180)))
        row = BoxLayout(size_hint_y=None, height=dp(40))
        ok = ModernButton(text='OK', color='info', size_hint=(1, 1))
        ok.bind(on_release=lambda *_: dlg.dismiss())
        row.add_widget(ok)
        bx.add_widget(row)
        dlg.open()