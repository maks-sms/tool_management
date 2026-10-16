from kivy.uix.boxlayout import BoxLayout
from frontend.widgets.modern_button import ModernButton
from frontend.views.tabs.base_tab import BaseTab


class ReserveTab(BaseTab):
    def __init__(self, app, **kw):
        super().__init__(
            app=app,
            columns=[
                ('id_p', 'ID', 1), ('task', 'Задача', 3),
                ('inner_code', 'Код', 2), ('articul', 'Артикул', 3),
                ('type', 'Тип', 2), ('diameter', 'Диаметр', 1),
                ('length', 'Длина', 1), ('brand', 'Бренд', 2),
                ('qty', 'Кол-во', 1),
            ],
            **kw,
        )

    def _build_buttons(self):
        bar = BoxLayout(size_hint_y=None, height=42, spacing=4, padding=[4, 2])
        bar.add_widget(ModernButton(text='🔄 Обновить', color='info',
                                    on_release=lambda *_: self.refresh()))
        if self.app.has_edit_permission('reserve'):
            bar.add_widget(ModernButton(text='УПРАВЛЕНИЕ (Выдача/Возврат)', color='warning',
                                        on_release=lambda *_: self.app.action_from_place('УПРАВЛЕНИЕ', self.tree)))
        bar.add_widget(BoxLayout())
        return bar

    def refresh(self):
        svc = getattr(self.app, 'reserve_view_service', None)
        if svc is None:
            self.tree.set_rows([])
            return
        try:
            rows = svc.get_reserve_placements()
        except Exception as e:
            print(f'[reserve] ошибка: {e}')
            self.tree.set_rows([])
            return
        prepared = [{
            'id_p': r[0] if len(r) > 0 else '',
            'task': r[1] if len(r) > 1 else '',
            'inner_code': r[2] if len(r) > 2 else '',
            'articul': r[3] if len(r) > 3 else '',
            'type': r[4] if len(r) > 4 else '',
            'diameter': r[5] if len(r) > 5 else '',
            'length': r[6] if len(r) > 6 else '',
            'brand': r[7] if len(r) > 7 else '',
            'qty': r[8] if len(r) > 8 else '',
        } for r in rows or []]
        prepared = self._sort_rows(prepared)
        self.tree.set_rows(prepared)
        print(f'[reserve] загружено {len(prepared)} строк')

    def _build_context_menu(self, tree_widget):
        items = [('🔄 Обновить', self.refresh)]
        if self.app.has_edit_permission('reserve'):
            items.insert(0, ('УПРАВЛЕНИЕ (Выдача/Возврат)',
                             lambda: self.app.action_from_place(
                                 'УПРАВЛЕНИЕ', tree_widget)))
        return items