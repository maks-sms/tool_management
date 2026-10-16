# frontend/views/tabs/base_tab.py
"""Базовый класс вкладки.

Ключевая идея:
    - refresh() переопределяется в наследниках;
    - BaseTab предоставляет _sort_rows() и _on_sort_clicked();
    - сортировка делается в памяти (без обращения к сервису);
    - tree.set_rows() вызывается ровно один раз — из refresh();
    - повторный вызов refresh() с теми же данными не мигает
      (это обеспечивает сам ModernTree.set_rows).
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from frontend.theme import C
from frontend.widgets.modern_tree import ModernTree


class BaseTab(BoxLayout):
    def __init__(self, app, columns, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('spacing', 4)
        kw.setdefault('padding', [6, 4])
        kw.setdefault('size_hint_y', 1)
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.app = app
        self.columns = columns
        self.tree = None

        # Текущая сортировка
        self._sort_key = None
        self._sort_desc = False

        # Флаги, которые читает app.refresh_all()
        self._dirty = False
        self._busy = False

        self._build()

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _build(self):
        top = self._build_top()
        if top is not None:
            self.add_widget(top)

        buttons = self._build_buttons()
        if buttons is not None:
            self.add_widget(buttons)

        self.tree = ModernTree(columns=self.columns)
        self.tree.size_hint_y = 1

        # Правый клик
        if hasattr(self, '_build_context_menu'):
            def on_right_click(tree_widget):
                items = self._build_context_menu(tree_widget)
                if not items:
                    return
                from kivy.core.window import Window
                from frontend.widgets.context_menu import show_context_menu
                x, y = Window.mouse_pos
                show_context_menu(items, (x, y))
            self.tree.on_right_click = on_right_click

        # Сортировка по клику на заголовок
        self.tree.on_sort = self._on_sort_clicked

        self.add_widget(self.tree)

    def _on_sort_clicked(self, key, desc):
        """Клик по заголовку → пересортировать уже загруженные данные."""
        self._sort_key = key
        self._sort_desc = desc
        # НЕ зовём self.refresh() — иначе идёт повторный запрос к сервису.
        # Достаточно применить сортировку к уже имеющимся строкам.
        self._apply_sort_to_current()

    def _apply_sort_to_current(self):
        """Отсортировать уже загруженные в tree строки и обновить их."""
        if self.tree is None:
            return
        rows = list(getattr(self.tree, '_rows', []) or [])
        if not rows:
            return
        # _rows уже подготовленные словари
        rows_sorted = self._sort_rows(rows)
        # set_rows поймёт, что структура та же, и обновит на месте
        self.tree.set_rows(rows_sorted)

    def _sort_rows(self, rows):
        """Отсортировать список словарей `rows` по self._sort_key."""
        if not self._sort_key:
            return rows

        def conv(v):
            if v is None or v == '':
                return (1, '')
            try:
                return (0, float(str(v).replace(',', '.')))
            except (ValueError, TypeError):
                return (0, str(v).lower())

        try:
            return sorted(
                rows,
                key=lambda r: conv(r.get(self._sort_key, '')),
                reverse=self._sort_desc,
            )
        except Exception:
            return rows

    def _build_top(self):
        return None

    def _build_buttons(self):
        return None

    def refresh(self):
        pass