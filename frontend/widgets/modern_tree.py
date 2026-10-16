# frontend/widgets/modern_tree.py
"""Кастомная таблица. Поддерживает сортировку, Ctrl/Shift-выделение.

Инкрементальное обновление:
    - если данные не изменились — ничего не делаем;
    - если изменилось только содержимое — обновляем .text у Label;
    - если изменилось количество строк — пересобираем, но первую партию
      добавляем синхронно (без пустого экрана);
    - выделение сохраняется по «ключу» строки (id/inner_code/...).
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock
from frontend.theme import C


ROW_HEIGHT = dp(28)
HEADER_HEIGHT = dp(32)
BATCH_SIZE = 50
BATCH_DELAY = 0.03

# Поля, по которым пытаемся найти «ключ» строки для восстановления выделения
_KEY_CANDIDATES = ('id', 'inner_code', 'tool_code', 'request_number', 'username')


# ─── Кликабельный заголовок ──────────────────────────────────

class _HeaderCell(ButtonBehavior, Label):
    """Кликабельная ячейка заголовка."""
    pass


class TreeHeader(GridLayout):
    columns = ListProperty()
    on_sort = ObjectProperty(None, allownone=True)

    def __init__(self, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', HEADER_HEIGHT)
        kw.setdefault('spacing', 1)
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['soft'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        self._sort_col = None
        self._sort_desc = False

        self.cols = max(1, len(self.columns))
        self._rebuild()

    def _rebuild(self, *a):
        self.clear_widgets()
        cols = self.columns or []
        if not cols:
            if self.cols != 1:
                self.cols = 1
            return

        new_cols = len(cols)
        if self.cols != new_cols:
            self.cols = new_cols

        total_w = sum(w for (_k, _t, w) in cols) or 1
        for key, title, w in cols:
            text = str(title)
            if self._sort_col == key:
                text += ' ▼' if self._sort_desc else ' ▲'

            lbl = _HeaderCell(
                text=text, bold=True,
                color=C['dark'], font_size=dp(13),
                halign='center', valign='middle',
                size_hint_x=w / total_w,
            )
            lbl.bind(size=lambda inst, *_: setattr(
                inst, 'text_size', (inst.width, inst.height)))
            lbl.bind(on_release=lambda inst, k=key: self._on_click(k))
            self.add_widget(lbl)

    def _on_click(self, key):
        if self._sort_col == key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = key
            self._sort_desc = False
        self._rebuild()
        if self.on_sort:
            try:
                self.on_sort(self._sort_col, self._sort_desc)
            except Exception as e:
                print(f'[header.on_sort] {e}')

    def set_sort(self, key, desc):
        self._sort_col = key
        self._sort_desc = bool(desc)
        self._rebuild()


# ─── Строка таблицы ──────────────────────────────────────────

class TreeRow(GridLayout):
    values = ListProperty()
    columns = ListProperty()
    is_selected = False
    row_index = 0

    def __init__(self, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', ROW_HEIGHT)
        kw.setdefault('spacing', 1)
        super().__init__(**kw)
        self.cols = max(1, len(self.columns))
        self._labels = []
        self._select_pending = False
        self._rebuild()
        self.bind(pos=self._draw_bg, size=self._draw_bg)

    def _draw_bg(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.is_selected:
                Color(*C['info'])
            elif self.row_index % 2:
                Color(*C['row_alt'])
            else:
                Color(*C['panel'])
            Rectangle(pos=self.pos, size=self.size)

    def set_selected(self, flag: bool):
        if self.is_selected == flag:
            return
        self.is_selected = flag
        self._draw_bg()
        new_color = (1, 1, 1, 1) if flag else C['dark']
        for lbl in self._labels:
            try:
                lbl.color = new_color
            except Exception:
                pass

    def _rebuild(self, *a):
        self.clear_widgets()
        self._labels = []

        cols = self.columns or []
        if not cols:
            if self.cols != 1:
                self.cols = 1
            return

        new_cols = len(cols)
        if self.cols != new_cols:
            self.cols = new_cols

        total_w = sum(w for (_k, _t, w) in cols) or 1
        for i, (_key, _title, w) in enumerate(cols):
            val = self.values[i] if i < len(self.values) else ''
            color = (1, 1, 1, 1) if self.is_selected else C['dark']
            lbl = Label(
                text=str(val), color=color, font_size=dp(12),
                halign='center', valign='middle',
                size_hint_x=w / total_w,
                shorten=True, shorten_from='right',
            )
            lbl.bind(size=lambda inst, *_: setattr(
                inst, 'text_size', (inst.width, inst.height)))
            self.add_widget(lbl)
            self._labels.append(lbl)

    # ─── Инкрементальное обновление ───

    def update_values(self, values):
        """Обновить текст существующих Label без пересоздания виджетов.

        Если структура изменилась (число колонок) — делаем полную пересборку.
        """
        values = list(values)

        if len(values) != len(self._labels):
            self.values = values
            self._rebuild()
            return

        self.values = values
        new_color = (1, 1, 1, 1) if self.is_selected else C['dark']
        for lbl, val in zip(self._labels, values):
            text = str(val) if val is not None else ''
            if lbl.text != text:
                lbl.text = text
            if lbl.color != new_color:
                lbl.color = new_color

    def update_row_index(self, idx):
        """Обновить индекс для чередования фона — без перерисовки, если не изменился."""
        if self.row_index != idx:
            self.row_index = idx
            self._draw_bg()

    # ─── Клики ───

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if not self.collide_point(*touch.pos):
            return False
        if self._select_pending:
            return True
        self._select_pending = True

        parent_tree = None
        p = self.parent
        while p is not None and not isinstance(p, ModernTree):
            p = p.parent
        parent_tree = p

        double = touch.is_double_tap
        button = touch.button

        try:
            from kivy.core.window import Window
            modifiers = getattr(Window, '_modifiers', []) or []
        except Exception:
            modifiers = []

        ctrl = 'ctrl' in modifiers
        shift = 'shift' in modifiers

        def _do_select(dt):
            self._select_pending = False
            if parent_tree is None:
                return
            if button == 'right':
                parent_tree._on_right_click(self)
                return
            parent_tree._select_row(self, ctrl=ctrl, shift=shift)
            if (double and not ctrl and not shift
                    and parent_tree.on_double_click):
                try:
                    parent_tree.on_double_click(
                        parent_tree.get_selected())
                except Exception as e:
                    print(f'[tree.on_double_click] {e}')

        Clock.schedule_once(_do_select, 0)
        return True


# ─── Сама таблица ────────────────────────────────────────────

class ModernTree(BoxLayout):
    columns = ListProperty()
    on_select = ObjectProperty(None, allownone=True)
    on_double_click = ObjectProperty(None, allownone=True)
    on_right_click = ObjectProperty(None, allownone=True)
    on_sort = ObjectProperty(None, allownone=True)
    selected_index = NumericProperty(-1)
    selected_indices = ListProperty([])

    def __init__(self, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('spacing', 0)
        kw.setdefault('size_hint', (1, 1))
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['panel'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        self._rows = []
        self._row_widgets = []
        self._batch_events = []
        self._last_clicked = -1

        self.header = TreeHeader(columns=list(self.columns))
        self.header.on_sort = self._on_header_sort
        self.add_widget(self.header)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.body = GridLayout(cols=1, size_hint_y=None, spacing=1)

        with self.body.canvas.before:
            Color(*C['panel'])
            self.body._bg = Rectangle(pos=self.body.pos, size=self.body.size)
        self.body.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                       size=lambda i, *_: setattr(i._bg, 'size', i.size))

        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        self.add_widget(self.scroll)

    # ─── Сортировка ───

    def _on_header_sort(self, key, desc):
        if self.on_sort:
            try:
                self.on_sort(key, desc)
            except Exception as e:
                print(f'[tree.on_sort] {e}')

    def set_sort_indicator(self, key, desc):
        self.header.set_sort(key, desc)

    # ─── Данные (инкрементальное обновление) ───

    def set_rows(self, rows):
        """Обновить данные таблицы.

        Стратегии:
          1. Данные идентичны → ничего не делаем.
          2. Одинаковое число строк → обновляем .text у Label.
          3. Разное число строк → полная пересборка, первая партия — сразу.
        Выделение восстанавливается по «ключу» строки.
        """
        # Отменяем старые батчи
        for ev in self._batch_events:
            try:
                ev.cancel()
            except Exception:
                pass
        self._batch_events.clear()

        new_rows = list(rows or [])

        # 1. Быстрый выход: данные не изменились
        if self._rows_equal(new_rows):
            return

        # 2. Сохраняем выделение по ключам
        prev_selected_keys = self._selected_keys()
        prev_last_clicked_key = self._row_key(self._last_clicked)

        same_length = (len(new_rows) == len(self._rows))
        self._rows = new_rows

        # 3. Обновляем
        if same_length and len(self._row_widgets) == len(new_rows):
            self._update_in_place(new_rows)
        else:
            self._rebuild_all(new_rows)

        # 4. Восстанавливаем выделение
        self._restore_selection(prev_selected_keys, prev_last_clicked_key)

    # ─── Вспомогательные ───

    def _row_key(self, idx):
        """Стабильный ключ строки по индексу — для восстановления выделения."""
        if idx is None or idx < 0 or idx >= len(self._rows):
            return None
        row = self._rows[idx]
        if isinstance(row, dict):
            for k in _KEY_CANDIDATES:
                v = row.get(k)
                if v not in (None, ''):
                    return (k, v)
            return ('__dict__', tuple(sorted(
                (k, v) for k, v in row.items()
                if not k.startswith('_')
            )))
        if isinstance(row, (list, tuple)):
            return ('__row__', tuple(row))
        return None

    def _selected_keys(self):
        return {self._row_key(i) for i in self.selected_indices}

    def _rows_equal(self, new_rows):
        """Сравниваем только видимые колонки — этого достаточно для UI."""
        if len(new_rows) != len(self._rows):
            return False
        visible_keys = [k for (k, _t, _w) in self.columns]
        for old, new in zip(self._rows, new_rows):
            if old is new:
                continue
            if isinstance(old, dict) and isinstance(new, dict):
                for k in visible_keys:
                    if old.get(k, '') != new.get(k, ''):
                        return False
                # Дополнительно — служебные флаги (например, _is_group)
                if old.get('_is_group') != new.get('_is_group'):
                    return False
            else:
                if old != new:
                    return False
        return True

    def _update_in_place(self, new_rows):
        """Обновить существующие виджеты без пересоздания."""
        for i, (widget, data) in enumerate(zip(self._row_widgets, new_rows)):
            if isinstance(data, dict):
                values = [data.get(k, '') for (k, _t, _w) in self.columns]
            else:
                values = list(data)
            try:
                widget.update_values(values)
                widget.update_row_index(i)
            except Exception as e:
                print(f'[tree.update_in_place] {e}')

    def _rebuild_all(self, new_rows):
        """Полная пересборка: удаляем виджеты и создаём заново.

        Первую партию строк добавляем синхронно — чтобы не было пустого экрана.
        Остальные — асинхронно, чтобы не морозить UI.
        """
        self.body.clear_widgets()
        self._row_widgets = []
        self.selected_index = -1
        self.selected_indices = []
        self._last_clicked = -1

        n = len(new_rows)
        if n == 0:
            return

        first_batch = new_rows[:BATCH_SIZE]
        self._add_batch(first_batch)

        if n > BATCH_SIZE:
            rest = new_rows[BATCH_SIZE:]
            batches = [rest[i:i + BATCH_SIZE]
                       for i in range(0, len(rest), BATCH_SIZE)]
            for idx, batch in enumerate(batches):
                delay = (idx + 1) * BATCH_DELAY
                ev = Clock.schedule_once(
                    lambda dt, b=batch: self._add_batch(b), delay)
                self._batch_events.append(ev)

    def _restore_selection(self, selected_keys, last_clicked_key):
        """Восстановить выделение по сохранённым ключам."""
        new_indices = []
        for i in range(len(self._rows)):
            if self._row_key(i) in selected_keys:
                new_indices.append(i)

        if new_indices:
            for i, rw in enumerate(self._row_widgets):
                rw.set_selected(i in new_indices)
            self.selected_indices = new_indices
            self.selected_index = new_indices[0]
        else:
            for rw in self._row_widgets:
                rw.set_selected(False)
            self.selected_indices = []
            self.selected_index = -1

        if last_clicked_key is not None:
            for i in range(len(self._rows)):
                if self._row_key(i) == last_clicked_key:
                    self._last_clicked = i
                    break
            else:
                self._last_clicked = -1
        else:
            self._last_clicked = -1

    def _add_batch(self, batch):
        for r in batch:
            if isinstance(r, dict):
                values = [r.get(k, '') for (k, _t, _w) in self.columns]
            else:
                values = list(r)
            row = TreeRow(values=values, columns=list(self.columns))
            row.row_index = len(self._row_widgets)
            self.body.add_widget(row)
            self._row_widgets.append(row)

    # ─── Выделение ───

    def get_selected(self):
        if 0 <= self.selected_index < len(self._rows):
            raw = self._rows[self.selected_index]
            if isinstance(raw, dict):
                return raw
            return {k: (raw[i] if i < len(raw) else '')
                    for i, (k, _t, _w) in enumerate(self.columns)}
        return None

    def get_selected_all(self):
        out = []
        for idx in self.selected_indices:
            if 0 <= idx < len(self._rows):
                raw = self._rows[idx]
                if isinstance(raw, dict):
                    out.append(raw)
                else:
                    out.append({k: (raw[i] if i < len(raw) else '')
                                for i, (k, _t, _w) in enumerate(self.columns)})
        return out

    def get_selected_values(self):
        sel = self.get_selected()
        if not sel:
            return []
        return [sel.get(k, '') for (k, _t, _w) in self.columns]

    def get_selected_values_all(self):
        return [[s.get(k, '') for (k, _t, _w) in self.columns]
                for s in self.get_selected_all()]

    def select_index(self, idx, ctrl=False, shift=False):
        if idx < 0 or idx >= len(self._rows):
            return
        if idx >= len(self._row_widgets):
            Clock.schedule_once(
                lambda dt: self.select_index(idx, ctrl, shift), 0.1)
            return

        if shift and self._last_clicked >= 0:
            a, b = sorted((self._last_clicked, idx))
            new_set = set(range(a, b + 1))
        elif ctrl:
            new_set = set(self.selected_indices)
            if idx in new_set:
                new_set.discard(idx)
            else:
                new_set.add(idx)
        else:
            new_set = {idx}

        self._last_clicked = idx

        for i, rw in enumerate(self._row_widgets):
            rw.set_selected(i in new_set)

        self.selected_indices = sorted(new_set)
        self.selected_index = self.selected_indices[0] if self.selected_indices else -1

        if self.on_select:
            callback = self.on_select
            data = self.get_selected()
            Clock.schedule_once(
                lambda dt: callback(data) if callback else None, 0,
            )

    def _select_row(self, row_widget, ctrl=False, shift=False):
        try:
            idx = self._row_widgets.index(row_widget)
        except ValueError:
            return
        self.select_index(idx, ctrl=ctrl, shift=shift)

    def _on_right_click(self, row_widget):
        try:
            idx = self._row_widgets.index(row_widget)
        except ValueError:
            return

        if idx not in self.selected_indices:
            for i, rw in enumerate(self._row_widgets):
                rw.set_selected(i == idx)
            self.selected_indices = [idx]
            self.selected_index = idx
            self._last_clicked = idx

        if self.on_right_click:
            try:
                self.on_right_click(self)
            except Exception as e:
                print(f'[tree.on_right_click] {e}')

    def clear(self):
        self._rows = []
        self.body.clear_widgets()
        self._row_widgets = []
        self.selected_index = -1
        self.selected_indices = []
        self._last_clicked = -1