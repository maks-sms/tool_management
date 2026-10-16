# frontend/widgets/context_menu.py
"""Выпадающее контекстное меню по правому клику (поверх всего окна)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from kivy.metrics import dp


class ContextMenu(FloatLayout):
    """Меню поверх окна. Клик вне меню — закрыть."""

    def __init__(self, items, anchor_pos, **kw):
        """
        :param items:      список (label, callback) или (None, None) —
                           разделитель
        :param anchor_pos: (x, y) — координаты клика в координатах окна
        """
        # Всегда размещаем оверлей на весь экран
        kw['size_hint'] = (1, 1)
        kw['pos'] = (0, 0)
        super().__init__(**kw)

        self._closed = False

        # Прозрачный фон — ловит клики вне меню
        with self.canvas.before:
            Color(0, 0, 0, 0)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Размеры меню
        real_items = [it for it in items if it[0] is not None]
        menu_w = dp(240)
        menu_h = dp(8) + dp(30) * len(real_items) + dp(8)

        win_w, win_h = Window.size
        ax, ay = anchor_pos

        # Позиция меню: справа-снизу от курсора, с ограничением по окну
        menu_x = ax
        menu_y = ay - menu_h
        if menu_x + menu_w > win_w:
            menu_x = win_w - menu_w - dp(4)
        if menu_x < 0:
            menu_x = dp(4)
        if menu_y < 0:
            menu_y = ay + dp(4)

        # Рамка меню — белый фон + тонкая серая граница
        frame = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(menu_w, menu_h),
            pos=(menu_x, menu_y),
            padding=[dp(2), dp(4)],
            spacing=dp(1),
        )
        with frame.canvas.before:
            Color(0.99, 0.99, 1, 1)
            frame._bg = Rectangle(pos=frame.pos, size=frame.size)
        with frame.canvas.after:
            Color(0.82, 0.84, 0.87, 1)
            frame._border = Line(
                rectangle=(frame.x, frame.y, frame.width, frame.height),
                width=1,
            )
        frame.bind(
            pos=lambda i, *_: (
                setattr(i._bg, 'pos', i.pos),
                setattr(i._border, 'rectangle',
                        (i.x, i.y, i.width, i.height)),
            ),
            size=lambda i, *_: (
                setattr(i._bg, 'size', i.size),
                setattr(i._border, 'rectangle',
                        (i.x, i.y, i.width, i.height)),
            ),
        )

        # Пункты меню
        for label, cb in items:
            if label is None:
                sep = BoxLayout(size_hint_y=None, height=dp(1))
                with sep.canvas.before:
                    Color(0.82, 0.84, 0.87, 1)
                    sep._bg = Rectangle(pos=sep.pos, size=sep.size)
                sep.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                         size=lambda i, *_: setattr(i._bg, 'size', i.size))
                frame.add_widget(sep)
                continue

            b = Button(
                text=label,
                size_hint_y=None,
                height=dp(30),
                halign='left',
                valign='middle',
                background_normal='',
                background_down='',
                background_color=(1, 1, 1, 1),
                color=(0.17, 0.24, 0.31, 1),
                font_size=dp(12),
            )
            b.bind(width=lambda inst, *_: setattr(
                inst, 'text_size', (inst.width - dp(20), None)))

            def make_handler(c):
                def h(*_):
                    self.close()
                    try:
                        c()
                    except Exception as e:
                        print(f'[context_menu] {e}')
                return h

            b.bind(on_release=make_handler(cb))
            frame.add_widget(b)

        self.add_widget(frame)

    def _update_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_touch_down(self, touch):
        # Клик вне меню — закрываем
        children = [w for w in self.children if isinstance(w, BoxLayout)]
        if children:
            menu = children[0]
            if not menu.collide_point(*touch.pos):
                self.close()
                return True
        return super().on_touch_down(touch)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if self.parent:
                self.parent.remove_widget(self)
        except Exception:
            pass


def show_context_menu(items, pos):
    """Показать контекстное меню в заданной точке (x, y)."""
    menu = ContextMenu(items=items, anchor_pos=pos)
    Window.add_widget(menu)
    return menu