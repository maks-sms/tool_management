# frontend/views/chat/chat_ui_builder.py
"""Построитель UI чата. Аналог ChatUIBuilder из desktop."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.metrics import dp
from kivy.clock import Clock

from frontend.theme import C
from frontend.views.chat.chat_constants import ChatType


class ChatUIBuilder:
    """Строит UI чата. Хранит ссылки на ключевые виджеты."""

    def __init__(self, manager):
        self.manager = manager
        self.root = None

        # Левая панель
        self.search_dialogs = None
        self.chats_box = None
        self.chats_scroll = None
        self._chat_items = []

        # Правая панель
        self.chat_title_lbl = None
        self.chat_status_lbl = None
        self.avatar_lbl = None
        self.messages_scroll = None
        self.messages_box = None
        self.search_chat = None
        self.search_counter_lbl = None
        self.reply_bar = None
        self.reply_label = None
        self.input = None
        self.scroll_bottom_btn = None
        self.autocomplete_box = None

    # ═══════════════════════════════════════════════════════════
    #                     BUILD
    # ═══════════════════════════════════════════════════════════

    def build(self) -> BoxLayout:
        root = BoxLayout(orientation='vertical', padding=0, spacing=0)
        with root.canvas.before:
            Color(*C['panel'])
            root._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        root.add_widget(self._build_top_bar())

        body = BoxLayout(orientation='horizontal',
                         spacing=dp(4), padding=[dp(4), dp(4)])
        body.add_widget(self._build_left_panel())
        body.add_widget(self._build_right_panel())
        root.add_widget(body)

        self.root = root
        return root

    # ─── Верхняя шапка с крестиком ───

    def _build_top_bar(self) -> BoxLayout:
        bar = BoxLayout(size_hint_y=None, height=dp(42),
                        spacing=dp(6), padding=[dp(12), dp(6)])
        with bar.canvas.before:
            Color(*C['primary'])
            bar._bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                 size=lambda i, *_: setattr(i._bg, 'size', i.size))

        bar.add_widget(Label(
            text='💬  Чат', bold=True, color=C['white'],
            font_size=dp(15), halign='left', valign='middle',
        ))
        bar.add_widget(BoxLayout())

        close_btn = Button(
            text='✖', size_hint=(None, None), size=(dp(32), dp(32)),
            background_normal='', background_down='',
            background_color=(0, 0, 0, 0),
            color=C['white'], font_size=dp(16), bold=True,
        )
        close_btn.bind(on_release=lambda *_: self.manager.close_chat())
        bar.add_widget(close_btn)

        return bar

    # ─── Левая панель ───

    def _build_left_panel(self) -> BoxLayout:
        left = BoxLayout(orientation='vertical', size_hint_x=None,
                         width=dp(280), spacing=dp(4), padding=[dp(2), dp(2)])
        with left.canvas.before:
            Color(*C['panel'])
            left._bg = Rectangle(pos=left.pos, size=left.size)
        left.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        header = BoxLayout(size_hint_y=None, height=dp(44),
                           spacing=dp(6), padding=[dp(8), dp(6)])
        with header.canvas.before:
            Color(*C['primary'])
            header._bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                    size=lambda i, *_: setattr(i._bg, 'size', i.size))

        header.add_widget(Label(
            text='Диалоги', bold=True, color=C['white'],
            font_size=dp(15), halign='left', valign='middle',
        ))

        plus_btn = Button(
            text='+', size_hint=(None, None), size=(dp(32), dp(32)),
            background_normal='', background_down='',
            background_color=C['success'],
            color=C['white'], font_size=dp(20), bold=True,
        )
        plus_btn.bind(on_release=lambda *_: self.manager.create_group_dialog())
        header.add_widget(plus_btn)
        left.add_widget(header)

        self.search_dialogs = TextInput(
            hint_text='🔍 Поиск', multiline=False,
            size_hint_y=None, height=dp(30), font_size=dp(13),
            padding=[dp(8), dp(6)],
            background_normal='', background_active='',
            background_color=C['input_bg'],
            foreground_color=C['input_fg'],
            cursor_color=C['input_fg'],
            hint_text_color=C['input_hint'],
        )
        self.search_dialogs.bind(
            text=lambda i, v: self.manager.list_controller.set_filter(v)
        )
        left.add_widget(self.search_dialogs)

        self.chats_box = GridLayout(cols=1, size_hint_y=None, spacing=dp(1))
        self.chats_box.bind(minimum_height=self.chats_box.setter('height'))
        self.chats_scroll = ScrollView(do_scroll_x=False)
        self.chats_scroll.add_widget(self.chats_box)
        left.add_widget(self.chats_scroll)

        return left

    # ─── Правая панель ───

    def _build_right_panel(self) -> BoxLayout:
        right = BoxLayout(orientation='vertical', spacing=0)
        with right.canvas.before:
            Color(*C['panel'])
            right._bg = Rectangle(pos=right.pos, size=right.size)
        right.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                   size=lambda i, *_: setattr(i._bg, 'size', i.size))

        right.add_widget(self._build_chat_header())
        right.add_widget(self._build_chat_search())
        right.add_widget(self._build_messages_area())
        right.add_widget(self._build_reply_bar())
        right.add_widget(self._build_input_bar())

        return right

    def _build_chat_header(self) -> BoxLayout:
        header = BoxLayout(size_hint_y=None, height=dp(54),
                           spacing=dp(8), padding=[dp(10), dp(8)])
        with header.canvas.before:
            Color(*C['primary'])
            header._bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                    size=lambda i, *_: setattr(i._bg, 'size', i.size))

        self.avatar_lbl = Label(
            text='💬', size_hint=(None, None), size=(dp(36), dp(36)),
            font_size=dp(18), color=C['white'],
            halign='center', valign='middle',
        )
        with self.avatar_lbl.canvas.before:
            Color(*C['info'])
            self.avatar_lbl._bg = Rectangle(pos=self.avatar_lbl.pos,
                                            size=self.avatar_lbl.size)
        self.avatar_lbl.bind(
            pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
            size=lambda i, *_: setattr(i._bg, 'size', i.size),
        )
        header.add_widget(self.avatar_lbl)

        info = BoxLayout(orientation='vertical', spacing=0)
        self.chat_title_lbl = Label(
            text='Общий чат', bold=True, color=C['white'],
            font_size=dp(14), halign='left', valign='middle',
        )
        self.chat_title_lbl.bind(
            size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height))
        )
        info.add_widget(self.chat_title_lbl)

        self.chat_status_lbl = Label(
            text='все пользователи', color=C['light'],
            font_size=dp(11), halign='left', valign='middle',
        )
        self.chat_status_lbl.bind(
            size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height))
        )
        info.add_widget(self.chat_status_lbl)
        header.add_widget(info)

        attach_btn = Button(
            text='📎', size_hint=(None, None), size=(dp(34), dp(34)),
            background_normal='', background_down='',
            background_color=C['secondary'],
            color=C['white'], font_size=dp(15),
        )
        attach_btn.bind(on_release=lambda *_: self.manager.attach_file())
        header.add_widget(attach_btn)

        menu_btn = Button(
            text='⋮', size_hint=(None, None), size=(dp(34), dp(34)),
            background_normal='', background_down='',
            background_color=C['secondary'],
            color=C['white'], font_size=dp(18), bold=True,
        )
        menu_btn.bind(on_release=lambda *_: self._show_chat_menu(menu_btn))
        header.add_widget(menu_btn)

        return header

    def _build_chat_search(self) -> BoxLayout:
        bar = BoxLayout(size_hint_y=None, height=dp(36),
                        spacing=dp(6), padding=[dp(10), dp(4)])

        self.search_chat = TextInput(
            hint_text='🔍 Поиск в чате...', multiline=False,
            size_hint=(1, 1), font_size=dp(13),
            padding=[dp(8), dp(6)],
            background_normal='', background_active='',
            background_color=C['input_bg'],
            foreground_color=C['input_fg'],
            cursor_color=C['input_fg'],
            hint_text_color=C['input_hint'],
        )
        self.search_chat.bind(
            text=lambda i, v: self.manager.search_controller.search(v)
        )
        bar.add_widget(self.search_chat)

        self.search_counter_lbl = Label(
            text='0/0', size_hint=(None, None), size=(dp(50), dp(24)),
            color=C['secondary'], font_size=dp(11),
            halign='center', valign='middle',
        )
        self.search_counter_lbl.bind(
            size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height))
        )
        bar.add_widget(self.search_counter_lbl)

        up_btn = Button(
            text='↑', size_hint=(None, None), size=(dp(28), dp(28)),
            background_normal='', background_down='',
            background_color=C['info'],
            color=C['white'], font_size=dp(13), bold=True,
        )
        up_btn.bind(on_release=lambda *_: self.manager.search_controller.prev())
        bar.add_widget(up_btn)

        down_btn = Button(
            text='↓', size_hint=(None, None), size=(dp(28), dp(28)),
            background_normal='', background_down='',
            background_color=C['info'],
            color=C['white'], font_size=dp(13), bold=True,
        )
        down_btn.bind(on_release=lambda *_: self.manager.search_controller.next())
        bar.add_widget(down_btn)

        return bar

    def _build_messages_area(self) -> FloatLayout:
        self.messages_box = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(6),
            padding=[dp(8), dp(8)],
        )
        self.messages_box.bind(minimum_height=self.messages_box.setter('height'))

        self.messages_scroll = ScrollView(do_scroll_x=False)
        self.messages_scroll.add_widget(self.messages_box)

        wrap = FloatLayout()
        wrap.add_widget(self.messages_scroll)
        self.messages_scroll.size_hint = (1, 1)
        self.messages_scroll.pos_hint = {'x': 0, 'y': 0}

        self.scroll_bottom_btn = Button(
            text='↓', size_hint=(None, None), size=(dp(40), dp(40)),
            background_normal='', background_down='',
            background_color=C['info'],
            color=C['white'], font_size=dp(18), bold=True,
            opacity=0,
            disabled=True,
        )
        self.scroll_bottom_btn.bind(
            on_release=lambda *_: self.scroll_to_bottom()
        )

        def _place_btn(*_):
            try:
                self.scroll_bottom_btn.right = self.messages_scroll.right - dp(12)
                self.scroll_bottom_btn.y = self.messages_scroll.y + dp(12)
            except Exception:
                pass
        self.messages_scroll.bind(pos=_place_btn, size=_place_btn)
        wrap.add_widget(self.scroll_bottom_btn)

        self.messages_scroll.bind(scroll_y=self._on_scroll)
        return wrap

    def _build_reply_bar(self) -> BoxLayout:
        self.reply_bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=0,
            spacing=dp(6), padding=[dp(8), dp(4)],
            opacity=0,
            disabled=True,
        )
        with self.reply_bar.canvas.before:
            Color(*C['soft'])
            self.reply_bar._bg = Rectangle(pos=self.reply_bar.pos,
                                           size=self.reply_bar.size)
        self.reply_bar.bind(
            pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
            size=lambda i, *_: setattr(i._bg, 'size', i.size),
        )

        self.reply_bar.add_widget(Label(
            text='↩️', size_hint_x=None, width=dp(24), font_size=dp(14),
        ))

        self.reply_label = Label(
            text='', color=C['secondary'],
            font_size=dp(12), halign='left', valign='middle',
        )
        self.reply_label.bind(
            size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height))
        )
        self.reply_bar.add_widget(self.reply_label)

        cancel = Button(
            text='✖', size_hint=(None, None), size=(dp(28), dp(28)),
            background_normal='', background_down='',
            background_color=C['soft'],
            color=C['danger'], font_size=dp(14), bold=True,
        )
        cancel.bind(on_release=lambda *_: self.manager.cancel_reply())
        self.reply_bar.add_widget(cancel)

        return self.reply_bar

    def _build_input_bar(self) -> BoxLayout:
        """
        Панель ввода + панель автодополнения.
        Внешний wrapper — size_hint_y=None, height фиксирован под input.
        Автодополнение добавляется ПЕРЕД bar — при появлении высота
        wrapper'а растёт, чтобы не обрезать список.
        """
        wrapper = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            spacing=0,
        )

        # Панель автодополнения — сверху (изначально height=0)
        self.autocomplete_box = AutocompletePanel(manager=self.manager)
        wrapper.add_widget(self.autocomplete_box)

        bar = BoxLayout(
            size_hint_y=None, height=dp(50),
            spacing=dp(6), padding=[dp(10), dp(6)],
        )

        self.input = TextInput(
            multiline=False, size_hint=(1, 1), font_size=dp(13),
            hint_text='Enter — отправка. Shift+Enter — перенос строки.',
            padding=[dp(8), dp(6)],
            background_normal='', background_active='',
            background_color=C['input_bg'],
            foreground_color=C['input_fg'],
            cursor_color=C['input_fg'],
            hint_text_color=C['input_hint'],
        )
        self.input.bind(on_text_validate=lambda *_: self.manager.send_message())
        self.input.bind(text=self.manager.input_controller.on_text_change)
        bar.add_widget(self.input)

        send_btn = Button(
            text='➤', size_hint=(None, None), size=(dp(50), dp(38)),
            background_normal='', background_down='',
            background_color=C['success'],
            color=C['white'], font_size=dp(18), bold=True,
        )
        send_btn.bind(on_release=lambda *_: self.manager.send_message())
        bar.add_widget(send_btn)

        wrapper.add_widget(bar)

        # Синхронизация высоты wrapper'а с высотой автодополнения
        def _sync_wrapper_height(*_):
            extra = self.autocomplete_box.height if self.autocomplete_box else 0
            wrapper.height = dp(50) + extra
        self.autocomplete_box.bind(height=_sync_wrapper_height)

        return wrapper

    # ═══════════════════════════════════════════════════════════
    #                 Публичные методы (для контроллеров)
    # ═══════════════════════════════════════════════════════════

    def set_chat_header(self, title: str, status: str, avatar: str):
        self.chat_title_lbl.text = title
        self.chat_status_lbl.text = status
        self.avatar_lbl.text = avatar

    def clear_messages(self):
        self.messages_box.clear_widgets()

    def add_message(self, bubble):
        self.messages_box.add_widget(bubble)

    def scroll_to_bottom(self):
        Clock.schedule_once(
            lambda dt: setattr(self.messages_scroll, 'scroll_y', 0), 0.05
        )

    def set_reply_preview(self, sender: str, text: str):
        self.reply_label.text = f"{sender}: {text}"
        self.reply_bar.height = dp(34)
        self.reply_bar.opacity = 1
        self.reply_bar.disabled = False

    def clear_reply_preview(self):
        self.reply_bar.height = 0
        self.reply_bar.opacity = 0
        self.reply_bar.disabled = True
        self.reply_label.text = ''

    def set_search_counter(self, current: int, total: int):
        self.search_counter_lbl.text = f"{current}/{total}" if total else "0/0"

    def fill_dialog_list(self, items):
        self.chats_box.clear_widgets()
        for text, data, active in items:
            btn = self._make_dialog_button(text, data, active)
            self.chats_box.add_widget(btn)

    def _make_dialog_button(self, label, data, active):
        bg = (0.85, 0.92, 1.0, 1) if active else C['panel']
        btn = Button(
            text=label, size_hint_y=None, height=dp(30),
            halign='left', valign='middle',
            background_normal='', background_down='',
            background_color=bg,
            color=C['primary'], font_size=dp(13),
        )
        btn.bind(width=lambda i, *_: setattr(
            i, 'text_size', (i.width - dp(12), None)))
        btn.bind(on_release=lambda *_: self.manager.list_controller.on_select(data))
        return btn

    # ─── Меню чата (⋮) ───

    def _show_chat_menu(self, anchor):
        from kivy.uix.dropdown import DropDown
        dd = DropDown()
        m = self.manager

        items = []
        if m.current_chat_type == ChatType.GROUP.value and m.current_group:
            items += [
                ('ℹ️ Информация о группе', m.group_manager.show_group_info),
                ('🚪 Покинуть группу', m.group_manager.leave_current_group),
            ]
        items += [
            ('🔄 Обновить', m.load_messages),
        ]

        for label, cb in items:
            b = Button(text=label, size_hint_y=None, height=dp(34),
                       background_normal='',
                       background_color=C['panel'],
                       color=C['dark'])
            b.bind(on_release=lambda _b, c=cb: (dd.dismiss(), c()))
            dd.add_widget(b)
        dd.open(anchor)

    # ─── Плавающая ↓ ───

    def _on_scroll(self, *_):
        try:
            if self.messages_scroll.scroll_y > 0.05:
                self.scroll_bottom_btn.opacity = 1
                self.scroll_bottom_btn.disabled = False
            else:
                self.scroll_bottom_btn.opacity = 0
                self.scroll_bottom_btn.disabled = True
        except Exception:
            pass


# ─── Панель автодополнения ───

class AutocompleteItem(ButtonBehavior, BoxLayout):
    def __init__(self, item, on_select, **kw):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None, height=dp(24),
            padding=[dp(8), dp(2)],
            **kw,
        )
        self.item = item
        self._on_select = on_select

        with self.canvas.before:
            Color(*C['panel'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

        lbl = Label(
            text=item[1],
            color=C['dark'],
            font_size=dp(12),
            halign='left', valign='middle',
            size_hint=(1, 1),
        )
        lbl.bind(size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        self.add_widget(lbl)

    def on_release(self):
        if self._on_select:
            self._on_select(self.item)


class AutocompletePanel(BoxLayout):
    """Панель подсказок: скрыта при height=0, показывается при наличии items."""

    def __init__(self, manager, **kw):
        super().__init__(
            orientation='vertical',
            size_hint_y=None,
            height=0,
            spacing=1,
            padding=[dp(4), 0],
            **kw,
        )
        self.manager = manager
        self._items = []
        self._selected = 0

        with self.canvas.before:
            Color(*C['soft'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
                  size=lambda i, *_: setattr(i._bg, 'size', i.size))

    def set_items(self, items):
        self._items = items
        self._selected = 0
        self._rebuild()
        if items:
            self.height = dp(24) * len(items) + dp(4)
        else:
            self.height = 0

    def hide(self):
        self._items = []
        self.clear_widgets()
        self.height = 0

    def _rebuild(self):
        self.clear_widgets()
        for it in self._items:
            row = AutocompleteItem(it, self._pick)
            self.add_widget(row)
        self._refresh_selection()

    def _refresh_selection(self):
        children = self.children[::-1]  # сверху вниз
        for i, ch in enumerate(children):
            try:
                ch.canvas.before.clear()
                with ch.canvas.before:
                    if i == self._selected:
                        Color(0.85, 0.92, 1.0, 1)
                    else:
                        Color(*C['panel'])
                    ch._bg = Rectangle(pos=ch.pos, size=ch.size)
                ch.bind(
                    pos=lambda inst, *_, w=ch: setattr(w._bg, 'pos', w.pos),
                    size=lambda inst, *_, w=ch: setattr(w._bg, 'size', w.size),
                )
            except Exception:
                pass

    def _pick(self, item):
        self.manager.input_controller._ac_apply(item)
        self.hide()