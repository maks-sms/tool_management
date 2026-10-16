# frontend/widgets/filtered_tree_dialog.py
"""Универсальный CRUD-диалог: шапка + FilterBar + таблица + кнопки."""
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from frontend.widgets.modern_window import ModernWindow
from frontend.widgets.filter_bar import FilterBar
from frontend.widgets.modern_tree import ModernTree
from frontend.widgets.modern_button import ModernButton


class FilteredTreeDialog(ModernWindow):
    def __init__(self, title, columns, fields, on_change,
                 buttons=None, on_refresh=None, **kw):
        body = BoxLayout(orientation='vertical', spacing=4,
                         padding=[8, 6])

        self.filter_bar = FilterBar(fields=fields, on_change=on_change)
        body.add_widget(self.filter_bar)

        self.tree = ModernTree(columns=list(columns))
        self.tree.size_hint_y = 1
        body.add_widget(self.tree)

        bottom = BoxLayout(size_hint_y=None, height=42,
                           spacing=4, padding=[0, 2])
        if buttons:
            for text, color, cb in buttons:
                btn = ModernButton(text=text, color=color, size_hint=(1, 1))
                btn.bind(on_release=lambda *_a, f=cb: f())
                bottom.add_widget(btn)
        if on_refresh:
            bottom.add_widget(BoxLayout())
            ref = ModernButton(text='🔄 Обновить', color='info',
                               size_hint=(None, None), size=(120, 38))
            ref.bind(on_release=lambda *_: on_refresh())
            bottom.add_widget(ref)
        body.add_widget(bottom)

        kw.pop('size_hint', None)
        kw.setdefault('size', (900, 600))    # ← БЕЗ dp()
        super().__init__(title=title, body=body, **kw)