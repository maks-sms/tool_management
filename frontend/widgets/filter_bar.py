# frontend/widgets/filter_bar.py
"""Панель фильтров. Единый стиль со styled_fields."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from dataclasses import dataclass
from typing import Callable, Optional, List

from frontend.theme import C
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import (
    StyledTextInput, StyledSpinner,
    StyledSpinnerOption, StyledDropDown,
)


# Алиасы для совместимости с существующим кодом
BorderedTextInput = StyledTextInput
BorderedSpinner = StyledSpinner
FilterSpinnerOption = StyledSpinnerOption
FilterDropDown = StyledDropDown


def _measure_text_width(text, font_size, font_name=None):
    from kivy.core.text import Label as CoreLabel
    if not text:
        return 0
    try:
        lbl = CoreLabel(text=text, font_size=font_size, font_name=font_name)
        lbl.refresh()
        return lbl.texture.size[0]
    except Exception:
        return 0


def _longest_width(values, default='', font_size=dp(13), font_name=None):
    candidates = [str(default or '')] + [str(v) for v in (values or [])]
    longest = max(candidates, key=len) if candidates else ''
    return _measure_text_width(longest, font_size, font_name)


@dataclass
class FilterField:
    name: str
    label: str
    kind: str = 'entry'
    width: int = 140
    values: Optional[List[str]] = None
    values_provider: Optional[Callable] = None
    default: str = ""
    readonly: bool = False


class FilterBar(BoxLayout):
    """Панель фильтров — белые поля с рамкой, светло-серый фон панели."""

    def __init__(self, fields, on_change=None, debounce_ms=250, **kw):
        kw.setdefault('orientation', 'horizontal')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(66))
        kw.setdefault('spacing', dp(8))
        kw.setdefault('padding', [dp(10), dp(6)])
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['soft'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(*C['border'])
            self._line = Line(points=[], width=1)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.fields = fields
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self._widgets = {}
        self._debounce_event = None

        # Флаг: пока True — программные изменения полей НЕ вызывают on_change
        self._suppress_fire = False

        self._build()

    # ─── Фон и линия ───

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        y = self.pos[1]
        self._line.points = [self.x, y, self.x + self.width, y]

    # ─── Построение ───

    def _build(self):
        for f in self.fields:
            cell_width = f.width
            if f.kind != 'entry':
                vals = list(f.values or [])
                if not vals and f.values_provider:
                    try:
                        vals = list(f.values_provider() or [])
                    except Exception:
                        vals = []
                text_w = _longest_width(
                    vals, default=f.default or '', font_size=dp(13),
                )
                needed = text_w + dp(48)
                cell_width = max(f.width, needed)

            cell = BoxLayout(
                orientation='vertical',
                size_hint_x=None,
                width=cell_width,
                spacing=2,
            )

            cell.add_widget(Label(
                text=f.label,
                size_hint_y=None,
                height=dp(14),
                color=C['secondary'],
                font_size=dp(11),
                bold=True,
                halign='left',
                valign='middle',
            ))

            if f.kind == 'entry':
                w = StyledTextInput(
                    hint_text=f.default or '',
                    size_hint_y=None,
                    height=dp(32),
                )
                w.bind(text=lambda inst, val: self._on_widget_text_changed())
                w.bind(on_text_validate=lambda inst: self._fire_now())
            else:
                vals = list(f.values or [])
                if not vals and f.values_provider:
                    try:
                        vals = list(f.values_provider() or [])
                    except Exception:
                        vals = []

                w = StyledSpinner(
                    text=f.default or '',
                    values=vals,
                    size_hint_y=None,
                    height=dp(32),
                )
                w.bind(text=lambda inst, val: self._on_widget_text_changed(
                    immediate=True))

            cell.add_widget(w)
            self._widgets[f.name] = w
            self.add_widget(cell)

        self.add_widget(BoxLayout())

        self._reset_btn = ModernButton(
            text='✖ Сброс',
            color='danger',
            size_hint=(None, None),
            size=(dp(110), dp(36)),
        )
        self._reset_btn.bind(on_release=lambda *_: self.clear())
        self.add_widget(self._reset_btn)

    # ─── Реакция на изменение полей ───

    def _on_widget_text_changed(self, immediate=False):
        """Любое изменение текста в поле.

        :param immediate: True — вызвать on_change сразу (для combo);
                          False — с debounce (для entry).
        """
        if self._suppress_fire:
            return
        if immediate:
            self._fire_now()
        else:
            self._fire_debounced()

    # ─── Публичный API ───

    def get_values(self):
        out = {}
        for f in self.fields:
            w = self._widgets[f.name]
            out[f.name] = (w.text if hasattr(w, 'text') else '').strip()
        return out

    def set_values(self, values: dict):
        """Программно установить значения. Без вызова on_change."""
        self._suppress_fire = True
        try:
            for name, value in (values or {}).items():
                w = self._widgets.get(name)
                if w is None:
                    continue
                try:
                    w.text = str(value) if value is not None else ''
                except Exception:
                    pass
        finally:
            self._suppress_fire = False

    def clear(self):
        """Сброс всех полей. Один вызов on_change в конце."""
        self._suppress_fire = True
        try:
            for f in self.fields:
                w = self._widgets[f.name]
                try:
                    w.text = f.default or ''
                except Exception:
                    pass
        finally:
            self._suppress_fire = False

        # Один явный вызов — независимо от того, что произошло внутри
        self._fire_now()

    def refresh_options(self):
        """Обновить values у combo-полей, не сбрасывая текущий выбор."""
        for f in self.fields:
            if f.kind != 'combo':
                continue

            w = self._widgets[f.name]

            vals = list(f.values or [])
            if not vals and f.values_provider:
                try:
                    vals = list(f.values_provider() or [])
                except Exception:
                    vals = []

            current = w.text

            self._suppress_fire = True
            try:
                w.values = vals

                # Если текущее значение ещё валидно — оставляем
                if current and current in vals:
                    w.text = current
                elif current and not f.readonly:
                    # не readonly combo — пользователь мог ввести своё
                    pass
                else:
                    # значение пропало из списка — сбрасываем на default
                    w.text = f.default or ''
            finally:
                self._suppress_fire = False

    # ─── Debounce / fire ───

    def _fire_debounced(self):
        if self._suppress_fire:
            return

        if self._debounce_event is not None:
            try:
                self._debounce_event.cancel()
            except Exception:
                pass

        self._debounce_event = Clock.schedule_once(
            lambda dt: self._fire_now(),
            self.debounce_ms / 1000.0,
        )

    def _fire_now(self):
        if self._suppress_fire:
            return

        if self._debounce_event is not None:
            try:
                self._debounce_event.cancel()
            except Exception:
                pass
            self._debounce_event = None

        if self.on_change:
            try:
                self.on_change()
            except Exception as e:
                print(f'[FilterBar.on_change] {e}')