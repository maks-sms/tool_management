# frontend/views/main/menu_builder.py
"""Строитель верхнего меню. Своё overlay-меню поверх окна (не Popup)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line

from frontend.theme import C


class _MenuOverlay(FloatLayout):
    """Прозрачный слой на всё окно. По клику вне меню — закрывается."""

    def __init__(self, items, anchor_pos, on_close, **kw):
        super().__init__(**kw)
        self._on_close = on_close

        # Фон overlay — полностью прозрачный (клики всё равно ловит)
        with self.canvas.before:
            Color(0, 0, 0, 0)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        real_items = [it for it in items if it[0] is not None]
        menu_w = dp(220)                                        # было dp(260)
        menu_h = min(dp(420), dp(6) + dp(28) * len(real_items) + dp(6))  # было dp(560)/dp(32)/dp(8)

        ax, ay = anchor_pos
        win_w, win_h = Window.size

        menu_x = ax
        menu_y = ay - dp(30) - menu_h
        if menu_x + menu_w > win_w:
            menu_x = win_w - menu_w - dp(4)
        if menu_x < 0:
            menu_x = dp(4)
        if menu_y < 0:
            menu_y = ay + dp(4)

        # Белая панель меню + тень-граница
        menu_frame = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(menu_w, menu_h),
            pos=(menu_x, menu_y),
            padding=[dp(2), dp(4)],
            spacing=dp(1),
        )
        with menu_frame.canvas.before:
            Color(*C['panel'])                     # БЕЛЫЙ фон
            menu_frame._bg_rect = Rectangle(
                pos=menu_frame.pos, size=menu_frame.size
            )
        with menu_frame.canvas.after:
            Color(*C['border'])                    # тонкая рамка
            menu_frame._border = Line(
                rectangle=(menu_frame.x, menu_frame.y,
                           menu_frame.width, menu_frame.height),
                width=1,
            )
        menu_frame.bind(
            pos=lambda inst, *_: (
                setattr(inst._bg_rect, 'pos', inst.pos),
                setattr(inst._border, 'rectangle',
                        (inst.x, inst.y, inst.width, inst.height)),
            ),
            size=lambda inst, *_: (
                setattr(inst._bg_rect, 'size', inst.size),
                setattr(inst._border, 'rectangle',
                        (inst.x, inst.y, inst.width, inst.height)),
            ),
        )

        inner = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(1))
        inner.bind(minimum_height=inner.setter('height'))

        for label, cb in items:
            if label is None:
                # Разделитель
                sep = BoxLayout(size_hint_y=None, height=dp(1))
                with sep.canvas.before:
                    Color(*C['border'])
                    sep._bg = Rectangle(pos=sep.pos, size=sep.size)
                sep.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                         size=lambda i, *_: setattr(i._bg, 'size', i.size))
                inner.add_widget(sep)
                continue

            b = Button(
                text=label, size_hint_y=None, height=dp(28),   # было dp(32)
                halign='left', valign='middle',
                background_normal='',
                background_down='',
                background_color=C['panel'],           # БЕЛЫЙ
                color=C['dark'],                       # тёмный текст
                font_size=dp(12),                              # было dp(13)
            )
            b.bind(
                width=lambda inst, *_: setattr(
                    inst, 'text_size', (inst.width - dp(20), None)
                )
            )

            def make_handler(c):
                def h(*_):
                    self.close()
                    try:
                        c()
                    except Exception as e:
                        print(f'[menu] {e}')
                return h

            b.bind(on_release=make_handler(cb))
            inner.add_widget(b)

        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(inner)
        menu_frame.add_widget(scroll)

        self.add_widget(menu_frame)

    def _update_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_touch_down(self, touch):
        children = [w for w in self.children if isinstance(w, BoxLayout)]
        if children:
            menu = children[0]
            if not menu.collide_point(*touch.pos):
                self.close()
                return True
        return super().on_touch_down(touch)

    def close(self):
        try:
            if self.parent:
                self.parent.remove_widget(self)
        except Exception:
            pass
        if self._on_close:
            self._on_close()


class MenuBuilder(BoxLayout):
    """Строка меню. Клик по кнопке → overlay-меню поверх окна."""

    def __init__(self, app, **kw):
        kw.setdefault('orientation', 'horizontal')
        kw.setdefault('size_hint', (None, 1))          # ← размер задаётся извне
        kw.setdefault('height', dp(30))                # было 34
        kw.setdefault('spacing', dp(1))                # было 2
        kw.setdefault('padding', [dp(6), dp(1)])       # было [dp(8), dp(2)]
        super().__init__(**kw)
        self.app = app
        self._overlay = None

        # БЕЛЫЙ фон + ПОЛНАЯ рамка вокруг меню
        with self.canvas.before:
            Color(*C['panel'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(*C['border'])                        # было C['header_border']
            self._border = Line(                       # было self._line = Line(points=[])
                rectangle=(self.x, self.y, self.width, self.height),
                width=1,
            )
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._build()

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = (
            self.x, self.y, self.width, self.height
        )

    def _menu_button(self, title, items):
        btn = Button(
            text=title,
            size_hint=(None, None),
            size=(dp(130), dp(24)),                # было (dp(160), dp(28))
            background_normal='',
            background_down='',
            background_color=C['panel'],           # БЕЛЫЙ
            color=C['primary'],                    # тёмный текст
            bold=True,
            font_size=dp(12),                      # было dp(13)
        )
        # подсветка при наведении — серым
        btn.bind(
            state=lambda inst, val: setattr(
                inst, 'background_color',
                C['soft'] if val == 'down' else C['panel']
            )
        )
        btn.bind(on_release=lambda *_a, b=btn: self._open_overlay(b, items))
        return btn

    def _open_overlay(self, anchor_btn, items):
        if self._overlay is not None:
            self._overlay.close()
            self._overlay = None

        try:
            ax, ay = anchor_btn.to_window(
                anchor_btn.x, anchor_btn.y, initial=False
            )
            ay_top = ay + anchor_btn.height
        except Exception:
            ax = anchor_btn.x
            ay_top = anchor_btn.y + anchor_btn.height

        overlay = _MenuOverlay(
            items=items,
            anchor_pos=(ax, ay_top),
            on_close=lambda: setattr(self, '_overlay', None),
            size_hint=(1, 1),
            pos=(0, 0),
        )
        self._overlay = overlay
        Window.add_widget(overlay)

    def _build(self):
        app = self.app

        system_items = [
            ('Настройки', app.open_settings),
            ('📁 Открыть папку бэкапов', app.open_backups_folder),
        ]
        if app.is_admin:
            system_items += [
                ('💾 Создать резервную копию', app.manual_backup),
                ('⏪ Восстановить из бэкапа', app.restore_from_backup),
            ]
        system_items += [
            (None, None),
            ('Сменить пользователя', app.switch_user),
            ('Выход', app.on_close),
        ]

        if app.is_admin:
            admin_title = 'Администрирование'
            admin_items = [
                ('Управление пользователями', app.open_user_manager),
                ('Управление инструментами', app.open_tool_manager),
                ('⚙️ Управление станками', app.open_machine_manager),
                (None, None),
                ('Импорт CSV', app.import_csv),
                ('Экспорт CSV', app.export_to_csv),
                (None, None),
                ('🗑️ Очистить журнал', app.clear_history),
                (None, None),
                ('Сменить пароль', app.change_password),
            ]
        else:
            admin_title = 'Пользователь'
            admin_items = [('Сменить пароль', app.change_password)]

        refresh_items = [
            ('🔄 Обновить сейчас', app.manual_refresh),
            (None, None),
            ('⚡ Интервал 30 сек', lambda: app.set_refresh_interval(30)),
            ('⏱ Интервал 60 сек', lambda: app.set_refresh_interval(60)),
            ('⚡ Интервал 120 сек', lambda: app.set_refresh_interval(120)),
        ]

        chat_items = [('Открыть чат', app.open_chat)]
        if app.is_admin:
            chat_items += [
                (None, None),
                ('Очистить историю чата', app.clear_chat_history),
            ]

        self.add_widget(self._menu_button('Система', system_items))
        self.add_widget(self._menu_button(admin_title, admin_items))
        self.add_widget(self._menu_button('Обновление', refresh_items))
        self.add_widget(self._menu_button('💬 Чат', chat_items))
        self.add_widget(BoxLayout())

    def rebuild(self):
        self.clear_widgets()
        self._build()