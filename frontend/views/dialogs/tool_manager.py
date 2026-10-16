# frontend/views/dialogs/tool_manager.py
"""Управление инструментами — единый стиль с фильтром и крестиком."""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from frontend.theme import C
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.filter_bar import FilterField
from frontend.widgets.filtered_tree_dialog import FilteredTreeDialog


class ToolManagerDialog(FilteredTreeDialog):
    def __init__(self, app, **kw):
        self.app = app
        super().__init__(
            title='Управление инструментами',
            columns=[
                ('id', 'ID', 1), ('inner_code', 'Код', 2),
                ('articul', 'Артикул', 3), ('qty_total', 'Остаток', 1),
                ('type', 'Тип', 2), ('diameter', 'Диаметр', 1),
                ('length', 'Длина', 1), ('brand', 'Пр-ль', 2),
                ('analog', 'Аналоги', 3),
            ],
            fields=[
                FilterField('search', 'Поиск:', 'entry', width=180),
                FilterField('type', 'Тип:', 'combo',
                            values_provider=self._get_types, width=150),
                FilterField('brand', 'Пр-ль:', 'combo',
                            values_provider=self._get_brands, width=150),
            ],
            on_change=self._refresh_with_filter,
            buttons=[
                ('➕ Добавить', 'success', self._add),
                ('✏️ Редактировать', 'warning', self._edit),
                ('🗑️ Удалить', 'danger', self._delete),
            ],
            on_refresh=self._refresh_with_filter,
            size=(950, 620),
        )
        self._refresh_with_filter()

    def _get_types(self):
        """Возвращает список уникальных типов инструментов."""
        try:
            tools = self.app.tool_service.get_all() or []
            return sorted({(t.type or '').strip()
                           for t in tools if (t.type or '').strip()})
        except Exception as e:
            print(f'[tool_manager._get_types] {e}')
            return []

    def _get_brands(self):
        """Возвращает список уникальных производителей."""
        try:
            tools = self.app.tool_service.get_all() or []
            return sorted({(t.brand or '').strip()
                           for t in tools if (t.brand or '').strip()})
        except Exception as e:
            print(f'[tool_manager._get_brands] {e}')
            return []

    def _refresh_with_filter(self):
        try:
            tools = self.app.tool_service.get_all() or []
        except Exception as e:
            print(f'[tools] {e}')
            tools = []

        f = self.filter_bar.get_values() if getattr(self, 'filter_bar', None) else {}
        search = (f.get('search') or '').lower()
        ttype = (f.get('type') or '').strip()
        brand = (f.get('brand') or '').strip()

        prepared = []
        for t in tools:
            if search:
                code = (t.inner_code or '').lower()
                art = (t.articul or '').lower()
                if search not in code and search not in art:
                    continue
            if ttype and (t.type or '').strip() != ttype:
                continue
            if brand and (t.brand or '').strip() != brand:
                continue
            prepared.append({
                'id': t.id, 'inner_code': t.inner_code, 'articul': t.articul,
                'qty_total': t.qty_total, 'type': t.type or '',
                'diameter': t.diameter or '', 'length': t.length or '',
                'brand': t.brand or '', 'analog': t.analog or '',
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
        tool = self.app.tool_service.get_by_id(sel['id'])
        if tool:
            self._form(tool)

    def _delete(self):
        sel = self.tree.get_selected()
        if not sel:
            return
        try:
            if self.app.tool_service.delete(sel['id']):
                self.app.history_service.add_record(
                    sel.get('articul', ''), 'УДАЛЕНИЕ',
                    sel.get('qty_total', 0), 'Удален из системы',
                    self.app.get_current_worker_name(),
                )
                self._refresh_with_filter()
        except Exception as e:
            print(f'[tools.delete] {e}')

    def _form(self, tool):
        from shared.models.tool import ToolCreate, ToolUpdate
        from kivy.uix.gridlayout import GridLayout
        from frontend.widgets.styled_fields import (
            StyledTextInput, LabeledField,
        )

        # Сетка 2×4 — поля в два столбца, все ровные
        grid = GridLayout(
            cols=2,
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(4), dp(4)],
        )
        grid.bind(minimum_height=grid.setter('height'))

        def add_field(label, widget):
            # LabeledField: подпись + поле
            grid.add_widget(LabeledField(
                label=label,
                widget=widget,
                size_hint_y=None,
            ))

        code = StyledTextInput(
            text=tool.inner_code if tool else '',
        )
        art = StyledTextInput(
            text=tool.articul if tool else '',
        )
        ttype = StyledTextInput(
            text=(tool.type or '') if tool else '',
        )
        diam = StyledTextInput(
            text=(tool.diameter or '') if tool else '',
        )
        length = StyledTextInput(
            text=(tool.length or '') if tool else '',
        )
        brand = StyledTextInput(
            text=(tool.brand or '') if tool else '',
        )
        analog = StyledTextInput(
            text=(tool.analog or '') if tool else '',
        )
        qty = StyledTextInput(
            text=str(tool.qty_total) if tool else '0',
            input_filter='int',
        )

        for label, w in [
            ('Код *:', code), ('Артикул *:', art),
            ('Тип:', ttype), ('Диаметр:', diam),
            ('Длина:', length), ('Производитель:', brand),
            ('Аналоги:', analog), ('Кол-во:', qty),
        ]:
            add_field(label, w)

        # Обёртка фиксированной высоты = minimum_height сетки
        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        dlg = ModernDialog(
            title=('Редактирование' if tool else 'Добавление инструмента'),
            body=bx,
            size=(640, 500),
        )

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Сохранить', color='success', size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger', size_hint=(1, 1))
        row.add_widget(ok)
        row.add_widget(cancel)
        bx.add_widget(row)

        def save(*_):
            try:
                new_qty = int(qty.text or '0')
            except ValueError:
                return
            try:
                if tool:
                    u = ToolUpdate(
                        inner_code=code.text.strip(), articul=art.text.strip(),
                        type=ttype.text.strip(), diameter=diam.text.strip(),
                        length=length.text.strip(), brand=brand.text.strip(),
                        analog=analog.text.strip(), qty_total=new_qty,
                    )
                    self.app.tool_service.update(tool.id, u)
                else:
                    c = ToolCreate(
                        inner_code=code.text.strip(), articul=art.text.strip(),
                        type=ttype.text.strip(), diameter=diam.text.strip(),
                        length=length.text.strip(), brand=brand.text.strip(),
                        analog=analog.text.strip(), qty_total=new_qty,
                    )
                    self.app.tool_service.create(c)
                self._refresh_with_filter()
                dlg.dismiss()
            except Exception as e:
                print(f'[tool.save] {e}')

        ok.bind(on_release=save)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()