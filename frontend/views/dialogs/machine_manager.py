# frontend/views/dialogs/machine_manager.py
"""Управление станками — единый стиль с фильтром и крестиком."""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.filter_bar import FilterField
from frontend.widgets.filtered_tree_dialog import FilteredTreeDialog


class MachineManagerDialog(FilteredTreeDialog):
    def __init__(self, app, **kw):
        self.app = app
        super().__init__(
            title='Управление станками',
            columns=[
                ('id', 'ID', 1), ('name', 'Название', 4),
                ('placements_count', 'Позиций', 1),
                ('total_qty', 'Всего шт.', 1),
            ],
            fields=[
                FilterField('search', 'Поиск:', 'entry', width=dp(200)),
            ],
            on_change=self._refresh_with_filter,
            buttons=[
                ('➕ Добавить', 'success', self._add),
                ('✏️ Переименовать', 'warning', self._rename),
                ('🗑️ Удалить', 'danger', self._delete),
            ],
            on_refresh=self._refresh_with_filter,
            size=(dp(700), dp(500)),
        )
        self._refresh_with_filter()

    def _refresh_with_filter(self):
        try:
            rows = self.app.machine_service.get_all_with_counts() or []
        except Exception as e:
            print(f'[machines] {e}')
            rows = []

        f = self.filter_bar.get_values() if getattr(self, 'filter_bar', None) else {}
        search = (f.get('search') or '').lower()

        prepared = []
        for r in rows:
            name = (r[1] or '')
            if search and search not in name.lower():
                continue
            prepared.append({'id': r[0], 'name': name,
                             'placements_count': r[2] or 0,
                             'total_qty': r[3] or 0})
        self.tree.set_rows(prepared)

    def _refresh(self):
        self._refresh_with_filter()

    def _add(self):
        from frontend.widgets.styled_fields import StyledTextInput, LabeledField
        from kivy.uix.gridlayout import GridLayout

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        inp = StyledTextInput(hint_text='Например: CNC-01')
        grid.add_widget(LabeledField(label='Название нового станка:', widget=inp))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        dlg = ModernDialog(title='Добавление станка', body=bx, size=(440, 200))

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Добавить', color='success', size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger', size_hint=(1, 1))
        row.add_widget(ok); row.add_widget(cancel)
        bx.add_widget(row)

        def save(*_):
            name = inp.text.strip()
            if not name:
                return
            if self.app.machine_service.add(name):
                self._refresh_with_filter()
                dlg.dismiss()
        ok.bind(on_release=save)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()

    def _rename(self):
        from frontend.widgets.styled_fields import StyledTextInput, LabeledField
        from kivy.uix.gridlayout import GridLayout

        sel = self.tree.get_selected()
        if not sel:
            return

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        inp = StyledTextInput(text=sel['name'])
        grid.add_widget(LabeledField(
            label=f"Переименовать: {sel['name']}", widget=inp,
        ))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        dlg = ModernDialog(title='Переименование станка', body=bx,
                           size=(460, 200))

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Сохранить', color='success', size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger', size_hint=(1, 1))
        row.add_widget(ok); row.add_widget(cancel)
        bx.add_widget(row)

        def save(*_):
            name = inp.text.strip()
            if name and self.app.machine_service.rename(sel['id'], name):
                self._refresh_with_filter()
                dlg.dismiss()
        ok.bind(on_release=save)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()

    def _delete(self):
        sel = self.tree.get_selected()
        if not sel:
            return
        if sel.get('placements_count', 0) > 0:
            self._info('Удаление невозможно',
                       'На станке есть инструмент. Сначала освободите.')
            return
        try:
            if self.app.machine_service.delete_by_id(sel['id']):
                self._refresh_with_filter()
        except Exception as e:
            print(f'[machine.delete] {e}')

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