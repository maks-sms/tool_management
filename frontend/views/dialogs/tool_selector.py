# frontend/views/dialogs/tool_selector.py
"""Универсальный диалог выбора инструмента с фильтрами."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp

from frontend.widgets.modern_window import ModernWindow
from frontend.widgets.filter_bar import FilterBar, FilterField
from frontend.widgets.modern_tree import ModernTree
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import StyledTextInput, LabeledField


class ToolSelectorDialog(ModernWindow):
    """Диалог выбора инструмента.

    :param app:             WarehouseApp
    :param on_select:       callback(tool_dict, qty) при выборе
    :param current_tools:   список уже добавленных inner_code (для пометки ✓)
    :param title:           заголовок окна
    """

    def __init__(self, app, on_select, current_tools=None,
                 title='Выбор инструмента', **kw):
        self.app = app
        self.on_select = on_select
        self.current_tools = current_tools or []

        body = BoxLayout(orientation='vertical', padding=dp(10),
                         spacing=dp(8))

        # ─── Фильтры ───
        self.filter_bar = FilterBar(
            fields=[
                FilterField('search', 'Код/Артикул:', 'entry',
                            width=dp(160)),
                FilterField('type', 'Тип:', 'combo',
                            values_provider=self._get_types,
                            width=dp(160)),
                FilterField('brand', 'Пр-ль:', 'combo',
                            values_provider=self._get_brands,
                            width=dp(160)),
                FilterField('diameter', 'Диаметр:', 'entry',
                            width=dp(100)),
            ],
            on_change=self._refresh_list,
        )
        body.add_widget(self.filter_bar)

        # ─── Таблица инструментов ───
        cols = [
            ('inner_code', 'Код', 2),
            ('articul', 'Артикул', 3),
            ('type', 'Тип', 2),
            ('diameter', 'Диаметр', 1),
            ('brand', 'Пр-ль', 2),
            ('qty_total', 'Остаток', 1),
        ]
        self.tree = ModernTree(columns=cols)
        self.tree.size_hint_y = 1
        self.tree.on_double_click = lambda row: self._select()
        body.add_widget(self.tree)

        # ─── Количество + выбранный ───
        bottom = BoxLayout(size_hint_y=None, height=dp(60),
                           spacing=dp(8))
        self.qty_input = StyledTextInput(
            text='1', input_filter='int',
            size_hint_y=None, height=dp(32),
        )
        qty_field = LabeledField(
            label='Количество для закупки:',
            widget=self.qty_input,
            size_hint_x=None, width=dp(220),
        )
        bottom.add_widget(qty_field)
        self.info_lbl = Label(
            text='Выберите инструмент из списка',
            color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
            halign='left', valign='middle',
        )
        self.info_lbl.bind(size=lambda i, *_: setattr(
            i, 'text_size', (i.width, i.height)))
        bottom.add_widget(self.info_lbl)
        body.add_widget(bottom)

        # ─── Кнопки ───
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='✅ Выбрать', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._select(),
        ))
        row.add_widget(ModernButton(
            text='❌ Отмена', color='danger', size_hint=(1, 1),
            on_release=lambda *_: self.dismiss(),
        ))
        body.add_widget(row)

        self.tree.on_select = self._on_row_selected
        self.tree.on_double_click = self._on_row_dbl_click

        kw.pop('size_hint', None)
        kw.setdefault('size', (850, 600))
        super().__init__(title=title, body=body, **kw)

        # Загружаем данные
        self._refresh_list()

    # ─── Данные ────────────────────────────────────────────────

    def _get_types(self):
        try:
            return self.app.tool_service.get_unique_types() or []
        except Exception:
            return []

    def _get_brands(self):
        try:
            return self.app.tool_service.get_unique_brands() or []
        except Exception:
            return []

    def _refresh_list(self):
        svc = getattr(self.app, 'inventory_view_service', None)
        if svc is None:
            return

        f = self.filter_bar.get_values() if self.filter_bar else {}

        try:
            tools = svc.get_tools_with_filters(
                search_art=f.get('search', ''),
                tool_type=f.get('type', ''),
                brand=f.get('brand', ''),
                diameter=f.get('diameter', ''),
            )
        except TypeError:
            tools = svc.get_tools_with_filters() or []

        prepared = []
        for t in tools or []:
            code = getattr(t, 'inner_code', '') or ''
            already = code in self.current_tools
            prefix = '✓ ' if already else ''
            prepared.append({
                'inner_code': prefix + code,
                'articul': getattr(t, 'articul', '') or '',
                'type': getattr(t, 'type', '') or '',
                'diameter': getattr(t, 'diameter', '') or '',
                'brand': getattr(t, 'brand', '') or '',
                'qty_total': getattr(t, 'qty_total', 0),
            })

        self.tree.set_rows(prepared)
        self.info_lbl.text = f'Найдено инструментов: {len(prepared)}'

    # ─── Выделение ─────────────────────────────────────────────

    def _on_row_selected(self, row):
        if not row:
            self.info_lbl.text = 'Выберите инструмент из списка'
            return

        code = str(row.get('inner_code', '')).lstrip('✓ ').strip()
        already = code in self.current_tools
        if already:
            self.info_lbl.text = f'⚠ {code} уже добавлен в заявку'
        else:
            self.info_lbl.text = (
                f'✅ {code} — {row.get("articul", "")} '
                f'(остаток: {row.get("qty_total", 0)})'
            )

    def _on_row_dbl_click(self, row):
        self._select()

    def _select(self):
        sel = self.tree.get_selected()
        if not sel:
            return
        code = str(sel.get('inner_code', '')).lstrip('✓ ').strip()

        if code in self.current_tools:
            self.info_lbl.text = f'⚠ {code} уже добавлен в заявку'
            return

        try:
            qty = int(self.qty_input.text or '1')
        except ValueError:
            qty = 1
        if qty <= 0:
            qty = 1

        # Находим полный tool
        tool = self.app.tool_service.get_by_code(code)
        if not tool:
            self.info_lbl.text = '⚠ Инструмент не найден'
            return

        tool_info = {
            'tool_id': tool.id,
            'inner_code': tool.inner_code,
            'articul': tool.articul or '',
            'type': tool.type or '',
            'diameter': tool.diameter or '',
            'brand': tool.brand or '',
            'current_qty': tool.qty_total or 0,
        }

        try:
            self.on_select(tool_info, qty)
        except Exception as e:
            print(f'[ToolSelectorDialog.on_select] {e}')

        self.dismiss()