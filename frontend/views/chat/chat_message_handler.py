# frontend/views/chat/chat_message_handler.py
"""Обработчик сообщений: пузыри, файлы, ответы, отправка."""
import os
from datetime import datetime
from typing import Optional, Dict, List

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from frontend.theme import C
from frontend.views.chat.chat_constants import BUBBLE_COLORS, FILE_ICONS, ChatType


class ChatBubble(BoxLayout):
    """
    Пузырь одного сообщения.
    Ширина пузыря — фиксированная доля от ширины области сообщений.
    """

    WIDTH_RATIO = 0.65
    MIN_WIDTH = dp(160)
    MAX_WIDTH = dp(720)

    def __init__(self, msg_id, text, display_name, timestamp, is_mine,
                 on_context_menu=None, reply_info=None, file_info=None,
                 manager=None, **kw):
        super().__init__(
            orientation='vertical',
            size_hint=(None, None),
            width=dp(300),
            height=dp(40),
            **kw
        )
        self.manager = manager
        self.msg_id = msg_id
        self._text = text or ''
        self._display_name = display_name
        self._is_mine = is_mine
        self._on_context_menu = on_context_menu
        self._file_info = file_info or {}

        colors = BUBBLE_COLORS['my'] if is_mine else BUBBLE_COLORS['other']
        self._colors = colors

        with self.canvas.before:
            Color(*colors['bubble'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.content = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            spacing=dp(2),
            padding=[dp(10), dp(6)],
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        self.add_widget(self.content)

        self._text_labels = []

        self._build_name()
        self._build_quote(reply_info)
        self._build_file(file_info)
        self._build_text()
        self._build_time(timestamp)

        self.bind(width=self._on_width_changed)
        Clock.schedule_once(self._initial_size, 0)
        Clock.schedule_once(self._initial_size, 0.05)

    # ─── Инициализация размеров ───

    def _initial_size(self, *_):
        self._update_width_from_parent()
        self._update_all_text_sizes()
        Clock.schedule_once(self._sync_height, 0)

    def _update_width_from_parent(self):
        parent = self.parent
        while parent is not None and parent.width < dp(100):
            parent = parent.parent
        if parent is None:
            return

        available = parent.width
        max_w = min(self.MAX_WIDTH, available * self.WIDTH_RATIO)

        text = self._text or self._display_name or ''
        longest_line = max((len(line) for line in text.split('\n')), default=1)
        estimated = longest_line * dp(8) + dp(24)

        target = max(self.MIN_WIDTH, min(max_w, estimated))
        self.width = target

    def _on_width_changed(self, *_):
        self._update_all_text_sizes()
        self._sync_height()

    def _update_all_text_sizes(self):
        inner_w = self.width - dp(20)
        if inner_w <= 0:
            return
        for lbl in self._text_labels:
            try:
                lbl.text_size = (inner_w, None)
            except Exception:
                pass

    def _sync_height(self, *_):
        try:
            self.height = self.content.height
        except Exception:
            pass

    # ─── Компоненты ───

    def _build_name(self):
        if self._is_mine:
            return
        lbl = Label(
            text=self._display_name or '', bold=True,
            color=self._colors['name'], font_size=dp(11),
            size_hint_y=None, height=dp(16),
            halign='left', valign='middle',
        )
        lbl.bind(size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        self.content.add_widget(lbl)

    def _build_quote(self, reply_info):
        if not reply_info:
            return

        q = BoxLayout(orientation='vertical', size_hint=(1, None),
                      spacing=1, padding=[dp(6), dp(4)])
        q.bind(minimum_height=q.setter('height'))

        with q.canvas.before:
            Color(*self._colors['quote_bg'])
            q._bg = Rectangle(pos=q.pos, size=q.size)
        q.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
               size=lambda i, *_: setattr(i._bg, 'size', i.size))

        sender = Label(
            text=f"↩️ {reply_info.get('sender', '')}",
            bold=True, color=self._colors['quote_text'],
            font_size=dp(10), halign='left', valign='middle',
            size_hint_y=None, height=dp(14),
        )
        sender.bind(size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        q.add_widget(sender)

        body = Label(
            text=(reply_info.get('text', '') or '')[:100],
            color=self._colors['text'],
            font_size=dp(11), halign='left', valign='top',
            size_hint=(1, None),
        )
        body.bind(texture_size=lambda i, v: setattr(i, 'height', max(dp(14), v[1])))
        q.add_widget(body)

        self.content.add_widget(q)
        self._text_labels.append(body)

    def _build_file(self, file_info):
        if not file_info:
            return

        f = BoxLayout(size_hint_y=None, height=dp(26),
                      spacing=dp(4), padding=[dp(4), dp(2)])
        with f.canvas.before:
            Color(*self._colors['file_bg'])
            f._bg = Rectangle(pos=f.pos, size=f.size)
        f.bind(pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
               size=lambda i, *_: setattr(i._bg, 'size', i.size))

        name = file_info.get('name', 'файл')
        ext = os.path.splitext(name)[1].lower()
        icon = FILE_ICONS.get(ext, '📄')
        size_str = self._format_size(file_info.get('size', 0))

        lbl = Label(
            text=f"{icon}  {name} ({size_str})",
            color=self._colors['file_text'],
            font_size=dp(11), halign='left', valign='middle',
        )
        lbl.bind(size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        f.add_widget(lbl)
        self.content.add_widget(f)

    def _build_text(self):
        if not self._text:
            return

        from frontend.views.chat.chat_text_widget import create_message_widget

        widget = create_message_widget(
            text=self._text,
            bg_rgba=self._colors['bubble'],
            fg_rgba=self._colors['text'],
            name_color_rgba=self._colors['quote_text'],
            font_size=dp(13),
            on_tool_click=self._on_tool_click,
            on_mention_click=self._on_mention_click,
        )
        self.content.add_widget(widget)
        # НЕ добавляем в self._text_labels — MessageText сам управляет text_size

    def _on_tool_click(self, code: str):
        try:
            tool = self.manager.app.tool_service.get_by_code(code)
        except Exception:
            tool = None

        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout as BL
        from kivy.uix.label import Label as Lbl
        from frontend.widgets.modern_button import ModernButton

        box = BL(orientation='vertical', padding=dp(14), spacing=dp(6))
        if not tool:
            box.add_widget(Lbl(text=f"Инструмент {code} не найден",
                               color=C['danger']))
        else:
            box.add_widget(Lbl(text=f"{tool.inner_code} — {tool.articul}",
                               bold=True, size_hint_y=None, height=dp(24),
                               color=C['primary']))
            box.add_widget(Lbl(text=f"Тип: {tool.type or '—'}",
                               size_hint_y=None, height=dp(20)))
            box.add_widget(Lbl(text=f"Остаток: {tool.qty_total} шт.",
                               size_hint_y=None, height=dp(20)))
            box.add_widget(Lbl(text=f"Бренд: {tool.brand or '—'}",
                               size_hint_y=None, height=dp(20)))

        close = ModernButton(text='Закрыть', color='info',
                             size_hint=(None, None), size=(dp(120), dp(36)))
        close.pos_hint = {'center_x': 0.5}
        box.add_widget(close)

        popup = Popup(title='Инструмент', content=box,
                      size_hint=(None, None), size=(dp(360), dp(260)),
                      background_color=C['panel'])
        close.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def _on_mention_click(self, user_id: int):
        try:
            user = self.manager.user_service.get_by_id(user_id)
        except Exception:
            user = None
        if not user:
            return
        display = user.full_name or user.username
        self.manager.select_user(user_id, display)
        try:
            self.manager.list_controller.update()
        except Exception:
            pass

    def _build_time(self, timestamp):
        lbl = Label(
            text=timestamp or '', color=self._colors['time'],
            font_size=dp(10), size_hint_y=None, height=dp(14),
            halign='right' if self._is_mine else 'left',
            valign='middle',
        )
        lbl.bind(size=lambda i, *_: setattr(i, 'text_size', (i.width, i.height)))
        self.content.add_widget(lbl)

    # ─── Отрисовка фона ───

    def _update_bg(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.button == 'right' and self._on_context_menu:
                self._on_context_menu(self, touch)
                return True
        return super().on_touch_down(touch)

    @staticmethod
    def _format_size(n):
        try:
            n = int(n)
        except Exception:
            return '0 Б'
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != 'Б' else f"{n} {unit}"
            n /= 1024
        return f"{n:.1f} ТБ"


class ChatMessageHandler:
    """Аналог ChatMessageHandler из desktop."""

    def __init__(self, manager):
        self.manager = manager

        self.reply_to_msg_id = None
        self.reply_to_text = None
        self.reply_to_sender = None

        self._typing_event = None

    # ─── Создание пузыря ───

    def create_bubble(self, msg) -> BoxLayout:
        msg_id = msg[0]
        username = msg[1]
        full_name = msg[2]
        text = msg[3] or ''
        timestamp = msg[4]
        user_id = msg[5]
        reply_to_id = msg[6] if len(msg) > 6 else None
        file_path = msg[7] if len(msg) > 7 else None
        file_name = msg[8] if len(msg) > 8 else None
        file_size = msg[9] if len(msg) > 9 else None

        is_mine = (user_id == self.manager.current_user[0])
        display_name = full_name or username

        reply_info = None
        if reply_to_id:
            try:
                reply_info = self.manager.chat_service.get_reply_info(reply_to_id)
            except Exception:
                reply_info = None

        file_info = None
        if file_name:
            file_info = {'name': file_name, 'size': file_size,
                         'path': file_path}

        bubble = ChatBubble(
            msg_id=msg_id, text=text, display_name=display_name,
            timestamp=timestamp, is_mine=is_mine,
            on_context_menu=self._on_context_menu,
            reply_info=reply_info, file_info=file_info,
            manager=self.manager,
        )

        row = BoxLayout(orientation='horizontal', size_hint_y=None,
                        spacing=dp(4))
        row.bind(minimum_height=row.setter('height'))
        if is_mine:
            row.add_widget(BoxLayout())
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(BoxLayout())

        def _sync(*_):
            row.height = bubble.height
        bubble.bind(height=_sync)
        Clock.schedule_once(_sync, 0)
        return row

    # ─── Отправка ───

    def send_message(self):
        if self.manager.ui is None:
            return
        ui = self.manager.ui
        text = ui.input.text.strip()

        if not text and not self.manager.pending_file:
            return

        try:
            file_path = file_name = file_size = None
            if self.manager.pending_file:
                file_path = self.manager.pending_file['path']
                file_name = self.manager.pending_file['name']
                file_size = self.manager.pending_file['size']
                self.manager.pending_file = None

            self.manager.chat_service.send_message(
                user_id=self.manager.current_user[0],
                username=self.manager.current_user[1],
                full_name=self.manager.current_user[3] or self.manager.current_user[1],
                message=text,
                chat_type=self.manager.current_chat_type,
                recipient_id=self.manager.selected_user,
                group_id=self.manager.current_group['id']
                if self.manager.current_group else None,
                reply_to_id=self.reply_to_msg_id,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
            )

            ui.input.text = ''
            self.cancel_reply()
            self.manager.load_messages()
        except Exception as e:
            print(f'[chat.send] {e}')

    # ─── Ответ ───

    def start_reply(self, bubble):
        self.reply_to_msg_id = bubble.msg_id
        self.reply_to_text = (bubble._text or '')[:100]
        self.reply_to_sender = bubble._display_name
        self.manager.ui.set_reply_preview(
            self.reply_to_sender, self.reply_to_text
        )

    def cancel_reply(self):
        self.reply_to_msg_id = None
        self.reply_to_text = None
        self.reply_to_sender = None
        if self.manager.ui:
            self.manager.ui.clear_reply_preview()

    # ─── Контекстное меню ───

    def _on_context_menu(self, bubble, touch):
        from kivy.uix.dropdown import DropDown
        dd = DropDown()

        def add(label, cb):
            b = Button(text=label, size_hint_y=None, height=dp(32),
                       background_normal='',
                       background_color=C['panel'], color=C['dark'])
            b.bind(on_release=lambda *_: (dd.dismiss(), cb()))
            dd.add_widget(b)

        add('↩️ Ответить', lambda: self.start_reply(bubble))
        if bubble._is_mine:
            add('✏️ Редактировать', lambda: self.edit_message(bubble))
            add('🗑️ Удалить', lambda: self.delete_message(bubble.msg_id))
        if bubble._text:
            add('📋 Копировать', lambda: self._copy_text(bubble._text))

        file_info = getattr(bubble, '_file_info', None)
        if file_info and file_info.get('path'):
            add('📥 Скачать файл',
                lambda p=file_info['path']: self.download_file(p))

        dd.open(bubble)

    def _copy_text(self, text):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(text)
        except Exception:
            pass

    def edit_message(self, bubble):
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        from frontend.widgets.modern_button import ModernButton

        box = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        box.add_widget(Label(text='Редактирование сообщения:',
                             size_hint_y=None, height=dp(22)))
        inp = TextInput(text=bubble._text, multiline=True,
                        size_hint_y=None, height=dp(100))
        box.add_widget(inp)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        ok = ModernButton(text='Сохранить', color='success',
                          size_hint=(1, 1), height=dp(38))
        cancel = ModernButton(text='Отмена', color='danger',
                              size_hint=(1, 1), height=dp(38))
        row.add_widget(ok)
        row.add_widget(cancel)
        box.add_widget(row)

        popup = Popup(title='', content=box,
                      size_hint=(None, None),
                      size=(dp(420), dp(240)),
                      background_color=C['panel'],
                      separator_color=C['border'])

        def do_save(*_):
            new_text = inp.text.strip()
            if new_text and new_text != bubble._text:
                try:
                    self.manager.chat_service.edit_message(bubble.msg_id, new_text)
                    self.manager.load_messages()
                except Exception as e:
                    print(f'[chat.edit] {e}')
            popup.dismiss()

        ok.bind(on_release=do_save)
        cancel.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def delete_message(self, msg_id):
        try:
            if self.manager.chat_service.delete_message(msg_id):
                self.manager.load_messages()
        except Exception as e:
            print(f'[chat.delete] {e}')

    # ─── Файлы ───

    def pick_file(self):
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            path = filedialog.askopenfilename(title='Выберите файл')
            root.destroy()
        except Exception as e:
            print(f'[chat.attach] {e}')
            return None
        if not path:
            return None

        try:
            import shutil
            target_dir = self.manager.chat_files_dir
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            base = os.path.basename(path)
            safe = ''.join(c for c in
                           f'{self.manager.current_user[1]}_{ts}_{base}'
                           if c.isalnum() or c in '._-')
            dest = os.path.join(target_dir, safe)
            shutil.copy2(path, dest)

            info = {
                'path': dest,
                'name': base,
                'size': os.path.getsize(path),
            }
            self.manager.pending_file = info

            if self.manager.ui:
                self.manager.ui.input.text = (
                    f"[📎 {base}] " + self.manager.ui.input.text
                )
            return info
        except Exception as e:
            print(f'[chat.attach.save] {e}')
            return None

    def download_file(self, file_path: str):
        """Сохранить файл через tkinter-диалог."""
        try:
            import shutil
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            save_path = filedialog.asksaveasfilename(
                initialfile=os.path.basename(file_path),
                title='Сохранить файл как',
            )
            root.destroy()
            if save_path:
                shutil.copy2(file_path, save_path)
        except Exception as e:
            print(f'[chat.download] {e}')

    # ─── Печатание ───

    def send_typing_status(self):
        if self._typing_event:
            try:
                self._typing_event.cancel()
            except Exception:
                pass

        try:
            self.manager.chat_service.send_typing_status(
                self.manager.current_user[0],
                self.manager.current_chat_type,
                self.manager.current_group['id']
                if self.manager.current_group else None,
                self.manager.selected_user,
            )
        except Exception:
            pass

        self._typing_event = Clock.schedule_once(
            lambda dt: self.clear_typing_status(), 3
        )

    def clear_typing_status(self):
        try:
            self.manager.chat_service.clear_typing_status(
                self.manager.current_user[0]
            )
        except Exception:
            pass

    def cancel_typing(self):
        if self._typing_event:
            try:
                self._typing_event.cancel()
            except Exception:
                pass
            self._typing_event = None
        self.clear_typing_status()