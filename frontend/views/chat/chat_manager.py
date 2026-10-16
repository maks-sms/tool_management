# frontend/views/chat/chat_manager.py
"""Главный менеджер чата — аналог client_desktop ChatManager."""
import os
from typing import Optional, Dict, List, Set

from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.metrics import dp

from frontend.theme import C
from frontend.views.chat.chat_constants import ChatType
from frontend.views.chat.chat_ui_builder import ChatUIBuilder
from frontend.views.chat.chat_message_handler import ChatMessageHandler
from frontend.views.chat.chat_list_controller import ChatListController
from frontend.views.chat.chat_search_controller import ChatSearchController
from frontend.views.chat.chat_input_controller import ChatInputController
from frontend.views.chat.chat_group_manager import ChatGroupManager


class ChatManager:
    """Полный аналог ChatManager из desktop, но на Kivy."""

    def __init__(self, app):
        self.app = app
        self.chat_service = app.chat_service
        self.user_service = app.user_service
        self.current_user = app.current_user

        # Состояние
        self.chat_popup: Optional[ModalView] = None
        self.ui: Optional[ChatUIBuilder] = None
        self.current_chat_type = ChatType.GENERAL.value
        self.current_group: Optional[Dict] = None
        self.selected_user: Optional[int] = None
        self.pending_file: Optional[Dict] = None

        # Реестры сообщений
        self.message_bubbles: List = []
        self.message_widgets: Dict[int, object] = {}
        # Какой чат был открыт при последней загрузке — если он сменился,
        # нужно полное перестроение
        self._last_loaded_key = None

        # Таймеры
        self._refresh_event = None
        self._activity_event = None

        # Под-контроллеры
        self.message_handler = ChatMessageHandler(self)
        self.list_controller = ChatListController(self)
        self.search_controller = ChatSearchController(self)
        self.input_controller = ChatInputController(self)
        self.group_manager = ChatGroupManager(self)

        self.chat_files_dir = self.chat_service.get_chat_files_dir()

    # ─── Открытие / закрытие ───

    def open_chat(self):
        if self.chat_popup is not None:
            try:
                self.chat_popup.dismiss()
            except Exception:
                pass
            self.chat_popup = None

        self.ui = ChatUIBuilder(self)
        content = self.ui.build()

        self.chat_popup = ModalView(
            size_hint=(None, None),
            size=(dp(1000), dp(650)),
            auto_dismiss=False,
            background='',
            background_color=C['panel'],
            overlay_color=(0, 0, 0, 0.35),
        )
        self.chat_popup.add_widget(content)
        self.chat_popup.open()

        def _center(dt):
            try:
                win_w, win_h = Window.size
                self.chat_popup.center_x = win_w / 2
                self.chat_popup.center_y = win_h / 2
            except Exception:
                pass
        Clock.schedule_once(_center, 0)

        Clock.schedule_once(lambda dt: self.list_controller.update(), 0.1)
        Clock.schedule_once(lambda dt: self.load_messages(), 0.2)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.35)

        self._start_auto_refresh()
        self._start_activity()

    def close_chat(self):
        self._stop_auto_refresh()
        self._stop_activity()
        self.message_handler.cancel_typing()
        self.message_handler.cancel_reply()
        if self.chat_popup is not None:
            try:
                self.chat_popup.dismiss()
            except Exception:
                pass
            self.chat_popup = None
        self.ui = None
        self.message_bubbles = []
        self.message_widgets = {}
        self._last_loaded_key = None

    # ─── Ключ текущего чата ───

    def _current_chat_key(self):
        return (
            self.current_chat_type,
            self.current_group['id'] if self.current_group else None,
            self.selected_user,
        )

    # ─── Загрузка данных (инкрементальная) ───

    def load_messages(self, scroll_to_bottom: bool = True):
        """
        Инкрементальная загрузка:
        - если сменился чат — полная перезагрузка;
        - иначе — добавляем только новые и удаляем пропавшие.
        Скролл и выделение сохраняются.
        """
        if not self.ui:
            return

        chat_key = self._current_chat_key()
        full_reload = (chat_key != self._last_loaded_key)

        try:
            messages = self.chat_service.get_messages(
                chat_type=self.current_chat_type,
                group_id=self.current_group['id'] if self.current_group else None,
                user_id=self.current_user[0],
                recipient_id=self.selected_user,
                limit=100,
            ) or []
        except Exception as e:
            print(f'[chat.load] {e}')
            return

        if full_reload:
            self._rebuild_all_messages(messages, scroll_to_bottom)
            self._last_loaded_key = chat_key
            return

        # ─── Инкрементальное обновление ───

        # Сохраняем текущий скролл
        prev_scroll = None
        try:
            prev_scroll = self.ui.messages_scroll.scroll_y
        except Exception:
            pass

        # Кто сейчас в реестре
        existing_ids: Set[int] = set(self.message_widgets.keys())
        incoming_ids: Set[int] = {m[0] for m in messages}

        # 1. Удаляем пропавшие (удалённые на сервере)
        removed_ids = existing_ids - incoming_ids
        if removed_ids:
            for mid in removed_ids:
                row = self.message_widgets.pop(mid, None)
                if row is not None:
                    try:
                        self.ui.messages_box.remove_widget(row)
                    except Exception:
                        pass
            # пересобрать список message_bubbles
            self.message_bubbles = [
                self.message_widgets[mid]
                for mid in self.message_widgets
                if mid in self.message_widgets
            ]

        # 2. Добавляем новые (по порядку)
        new_count = 0
        for msg in messages:
            mid = msg[0]
            if mid in self.message_widgets:
                continue
            try:
                row = self.message_handler.create_bubble(msg)
                self.ui.add_message(row)
                self.message_widgets[mid] = row
                self.message_bubbles.append(row)
                new_count += 1
            except Exception as e:
                print(f'[chat.bubble] {e}')

        # 3. Восстанавливаем скролл
        #    - если были внизу — оставляем внизу (это и есть scroll_y=0)
        #    - если скроллили вверх — возвращаем приблизительно туда же
        if new_count > 0:
            try:
                if prev_scroll is not None and prev_scroll > 0.05:
                    # Был не внизу — возвращаем позицию, чуть сдвинув
                    # чтобы компенсировать новые сообщения внизу
                    self.ui.messages_scroll.scroll_y = prev_scroll
                elif scroll_to_bottom or prev_scroll is not None and prev_scroll <= 0.05:
                    self._scroll_to_bottom()
            except Exception:
                pass

        # Отметить прочитанным
        self.mark_current_chat_as_read()

    def _rebuild_all_messages(self, messages, scroll_to_bottom: bool):
        """Полное перестроение — только при смене чата."""
        self.ui.clear_messages()
        self.message_bubbles = []
        self.message_widgets = {}

        for msg in messages:
            try:
                row = self.message_handler.create_bubble(msg)
                self.ui.add_message(row)
                self.message_widgets[msg[0]] = row
                self.message_bubbles.append(row)
            except Exception as e:
                print(f'[chat.bubble] {e}')

        if scroll_to_bottom:
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)

        self.mark_current_chat_as_read()

    def _scroll_to_bottom(self):
        if self.ui:
            self.ui.scroll_to_bottom()

    def mark_current_chat_as_read(self):
        try:
            ids = self.chat_service.get_chat_message_ids(
                chat_type=self.current_chat_type,
                group_id=self.current_group['id'] if self.current_group else None,
                user_id=self.current_user[0],
                recipient_id=self.selected_user,
            )
            if ids and hasattr(self.app, 'chat_manager_extended'):
                self.app.chat_manager_extended.mark_as_read(ids)
                self.app.chat_manager_extended.update_menu_badge()
        except Exception as e:
            print(f'[chat.read] {e}')

    # ─── Отправка ───

    def send_message(self):
        self.message_handler.send_message()

    # ─── Автообновление ───

    def _start_auto_refresh(self):
        self._refresh_event = Clock.schedule_interval(
            self._auto_refresh_tick,
            self.chat_service_refresh_interval(),
        )

    def _stop_auto_refresh(self):
        if self._refresh_event:
            try:
                self._refresh_event.cancel()
            except Exception:
                pass
            self._refresh_event = None

    def chat_service_refresh_interval(self):
        from frontend.views.chat.chat_constants import REFRESH_INTERVALS
        return REFRESH_INTERVALS['chats_list']

    def _auto_refresh_tick(self, dt):
        if self.ui is None:
            self._stop_auto_refresh()
            return
        self.list_controller.update()
        self.load_messages(scroll_to_bottom=False)

    def _start_activity(self):
        self._activity_event = Clock.schedule_interval(
            self._activity_tick, 60,
        )

    def _stop_activity(self):
        if self._activity_event:
            try:
                self._activity_event.cancel()
            except Exception:
                pass
            self._activity_event = None

    def _activity_tick(self, dt):
        try:
            self.chat_service.update_activity(self.current_user[0])
        except Exception:
            pass

    # ─── Переключение чата ───

    def select_general(self):
        self.current_chat_type = ChatType.GENERAL.value
        self.current_group = None
        self.selected_user = None
        # сбросить ключ, чтобы загрузился полный rebuild
        self._last_loaded_key = None
        self.ui.set_chat_header('Общий чат', 'все пользователи', '💬')
        self.load_messages()

    def select_group(self, group_id, name, member_count=0):
        self.current_chat_type = ChatType.GROUP.value
        self.current_group = {'id': group_id, 'name': name,
                              'member_count': member_count}
        self.selected_user = None
        self._last_loaded_key = None
        self.ui.set_chat_header(name, f"{member_count} участников", '👥')
        self.load_messages()

    def select_user(self, user_id, name):
        self.current_chat_type = ChatType.PRIVATE.value
        self.current_group = None
        self.selected_user = user_id
        self._last_loaded_key = None
        try:
            online = self.chat_service.is_user_online(user_id)
        except Exception:
            online = False
        self.ui.set_chat_header(name, 'онлайн' if online else 'офлайн', '👤')
        self.load_messages()

    # ─── Делегирование ───

    def attach_file(self):
        self.pending_file = self.message_handler.pick_file()

    def cancel_reply(self):
        self.message_handler.cancel_reply()

    def create_group_dialog(self):
        self.group_manager.create_group_dialog()

    def show_group_info(self):
        self.group_manager.show_group_info()

    def leave_current_group(self):
        self.group_manager.leave_current_group()