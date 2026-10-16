from kivy.uix.boxlayout import BoxLayout
from frontend.widgets.modern_button import ModernButton
from frontend.views.tabs.base_tab import BaseTab


class HistoryTab(BaseTab):
    def __init__(self, app, **kw):
        super().__init__(
            app=app,
            columns=[
                ('date', 'Дата', 2), ('code', 'Код', 2),
                ('act', 'Действие', 3), ('qty', 'Кол-во', 1),
                ('targ', 'Куда', 3), ('work', 'Фамилия', 2),
            ],
            **kw,
        )

    def _build_buttons(self):
        bar = BoxLayout(size_hint_y=None, height=42, spacing=4, padding=[4, 2])
        bar.add_widget(ModernButton(text='🔄 Обновить', color='info',
                                    on_release=lambda *_: self.refresh()))
        bar.add_widget(BoxLayout())
        return bar

    def refresh(self):
        svc = getattr(self.app, 'history_view_service', None)
        if svc is None:
            self.tree.set_rows([])
            return
        try:
            records = svc.get_history_records()
        except Exception as e:
            print(f'[history] ошибка: {e}')
            self.tree.set_rows([])
            return
        prepared = [{
            'date': getattr(r, 'date', ''),
            'code': getattr(r, 'articul', ''),
            'act':  getattr(r, 'action', ''),
            'qty':  getattr(r, 'qty', ''),
            'targ': getattr(r, 'target', ''),
            'work': getattr(r, 'worker', ''),
        } for r in records or []]
        prepared = self._sort_rows(prepared)
        self.tree.set_rows(prepared)
        print(f'[history] загружено {len(prepared)} строк')

    def _build_context_menu(self, tree_widget):
        return [('🔄 Обновить', self.refresh)]