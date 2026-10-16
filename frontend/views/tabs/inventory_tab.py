# frontend/views/tabs/inventory_tab.py
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from frontend.widgets.filter_bar import FilterBar, FilterField
from frontend.widgets.modern_button import ModernButton
from frontend.views.tabs.base_tab import BaseTab


class InventoryTab(BaseTab):
    def __init__(self, app, **kw):
        self.filter_bar = None
        super().__init__(
            app=app,
            columns=[
                ('inner_code', 'Код', 2),
                ('articul', 'Артикул', 3),
                ('type', 'Тип', 2),
                ('diameter', 'Диаметр', 1),
                ('length', 'Длина', 1),
                ('brand', 'Пр-ль', 2),
                ('analog', 'Аналоги', 3),
                ('qty_total', 'Остаток', 1),
            ],
            **kw,
        )

    def _build_top(self):
        self.filter_bar = FilterBar(
            fields=[
                FilterField('search_art', 'Код/Артикул:', 'entry', width=dp(160)),
                FilterField('type', 'Тип:', 'combo',
                            values_provider=self._get_types, width=dp(160)),
                FilterField('brand', 'Производитель:', 'combo',
                            values_provider=self._get_brands, width=dp(160)),
                FilterField('diameter', 'Диаметр:', 'entry', width=dp(100)),
            ],
            on_change=self.refresh,
        )
        return self.filter_bar

    def _get_types(self):
        try:
            return self.app.inventory_view_service.get_unique_types() or []
        except Exception:
            return []

    def _get_brands(self):
        try:
            return self.app.inventory_view_service.get_unique_brands() or []
        except Exception:
            return []

    def _build_buttons(self):
        bar = BoxLayout(size_hint_y=None, height=dp(42),
                        spacing=dp(4), padding=[dp(4), dp(2)])

        def _btn(text, color, cb):
            b = ModernButton(text=text, color=color, size_hint=(1, 1))
            b.bind(on_release=lambda *_: cb())
            return b

        if self.app.has_edit_permission('inventory'):
            bar.add_widget(_btn('📦 Поступления', 'success',
                                self.app.win_add_qty))
            bar.add_widget(_btn('⚙ На станок', 'info',
                                lambda: self.app.win_move('СТАНОК')))
        if self.app.has_edit_permission('reserve'):
            bar.add_widget(_btn('⏳ В резерв', 'warning',
                                lambda: self.app.win_move('РЕЗЕРВ')))
        if self.app.has_view_permission('requests'):
            bar.add_widget(_btn('📋 Заявка на закупку', 'warning',
                                self.app.create_request_from_selected))
        bar.add_widget(_btn('➕ Новый станок', 'warning',
                            self.app.win_add_machine))
        if self.app.has_edit_permission('tools'):
            bar.add_widget(_btn('⚙ Управление инструментами', 'info',
                                self.app.open_tool_manager))
        return bar

    def refresh(self):
        svc = getattr(self.app, 'inventory_view_service', None)
        if svc is None:
            return

        f = self.filter_bar.get_values() if self.filter_bar else {}

        try:
            tools = svc.get_tools_with_filters(
                search_art=f.get('search_art', ''),
                tool_type=f.get('type', ''),
                brand=f.get('brand', ''),
                diameter=f.get('diameter', ''),
            )
        except TypeError:
            tools = svc.get_tools_with_filters()
            search = (f.get('search_art') or '').lower()
            ttype = (f.get('type') or '').lower()
            brand = (f.get('brand') or '').lower()
            diam = (f.get('diameter') or '').lower()
            filtered = []
            for t in tools:
                inner = (getattr(t, 'inner_code', '') or '').lower()
                art = (getattr(t, 'articul', '') or '').lower()
                if search and search not in inner and search not in art:
                    continue
                if ttype and ttype != (getattr(t, 'type', '') or '').lower():
                    continue
                if brand and brand != (getattr(t, 'brand', '') or '').lower():
                    continue
                if diam and diam not in (getattr(t, 'diameter', '') or '').lower():
                    continue
                filtered.append(t)
            tools = filtered

        prepared = [{
            'inner_code': getattr(t, 'inner_code', '') or '',
            'articul':    getattr(t, 'articul', '') or '',
            'type':       getattr(t, 'type', '') or '',
            'diameter':   getattr(t, 'diameter', '') or '',
            'length':     getattr(t, 'length', '') or '',
            'brand':      getattr(t, 'brand', '') or '',
            'analog':     getattr(t, 'analog', '') or '',
            'qty_total':  getattr(t, 'qty_total', 0),
        } for t in (tools or [])]

        prepared = self._sort_rows(prepared)
        self.tree.set_rows(prepared)
        self.tree.on_double_click = self._on_dbl
        print(f'[inventory] загружено {len(prepared)}')

    # ─── Контекстное меню ───

    def _build_context_menu(self, tree_widget):
        """Меню для правого клика. Строим по аналогии с кнопками."""
        sel = tree_widget.get_selected_all()
        n = len(sel)
        if n == 0:
            return []

        app = self.app
        items = []

        if n == 1:
            if app.has_edit_permission('inventory'):
                items.append(('📦 Поступление',
                              app.win_add_qty))
                items.append(('⚙ На станок',
                              lambda: app.win_move('СТАНОК')))
            if app.has_edit_permission('reserve'):
                items.append(('⏳ В резерв',
                              lambda: app.win_move('РЕЗЕРВ')))
            items.append((None, None))
            if app.has_view_permission('requests'):
                items.append(('📋 Заявка на закупку',
                              app.create_request_from_selected))
            if app.has_edit_permission('tools'):
                items.append(('⚙ Управление инструментами',
                              app.open_tool_manager))
        else:
            # Мультивыделение
            items.append((f'📦 Поступление ({n})',
                          app.win_add_qty))
            if app.has_edit_permission('inventory'):
                items.append((f'⚙ На станок ({n})',
                              lambda: app.win_move('СТАНОК')))
            if app.has_edit_permission('reserve'):
                items.append((f'⏳ В резерв ({n})',
                              lambda: app.win_move('РЕЗЕРВ')))
            if app.has_view_permission('requests'):
                items.append((None, None))
                items.append((f'📋 Создать групповую заявку ({n})',
                              app.create_group_request_from_selected))

        items.append((None, None))
        items.append(('🔄 Обновить', self.refresh))
        return items

    def _on_dbl(self, row):
        if not row:
            return
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout as BX
        from kivy.uix.label import Label
        from frontend.widgets.modern_button import ModernButton
        txt = '\n'.join(f'{k}: {v}' for k, v in row.items())
        bx = BX(orientation='vertical', padding=dp(14), spacing=dp(8))
        bx.add_widget(Label(text=txt, halign='left'))
        btn = ModernButton(text='OK', color='info',
                           size_hint=(None, None), size=(dp(120), dp(40)))
        btn.pos_hint = {'center_x': 0.5}
        bx.add_widget(btn)
        popup = Popup(title='Инструмент', content=bx,
                      size_hint=(None, None), size=(dp(420), dp(280)))
        btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()