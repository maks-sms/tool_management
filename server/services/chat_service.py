# server/services/chat_service.py (исправленная версия)
import os
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.config import get_current_db_path
from server.repositories.chat_repository import ChatRepository
from shared.utils.logger import get_logger
logger = get_logger(__name__)
# Регулярки для триггеров автодополнения
RE_TRIGGER_MENTION = re.compile(r'@(\S*)$')
RE_TRIGGER_TOOL    = re.compile(r'#(\S*)$')

# Регулярки для парсинга разметки в тексте сообщения
RE_TOOL_LINK = re.compile(r'#tool:([^|#]+)(?:\|([^#]+))?#')
RE_MENTION   = re.compile(r'@\[([^\]]+)\]\(user:(\d+)\)')

class ChatService:
    """Сервис для работы с чатом"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_current_db_path()
        self.repository = ChatRepository(self.db_path)

    # === Сообщения ===

    def get_messages(self, chat_type: str = "general", group_id: int = None,
                     user_id: int = None, recipient_id: int = None,
                     limit: int = 100) -> List[tuple]:
        """Получение сообщений чата"""
        if chat_type == "group" and group_id:
            return self.repository.get_messages(group_id=group_id, is_group=True, limit=limit)
        elif chat_type == "private" and user_id and recipient_id:
            return self.repository.get_messages(user_id=user_id, recipient_id=recipient_id,
                                               is_private=True, limit=limit)
        else:
            return self.repository.get_messages(limit=limit)

    def send_message(self, user_id: int, username: str, full_name: str,
                     message: str, chat_type: str = "general",
                     recipient_id: int = None, group_id: int = None,
                     reply_to_id: int = None, file_path: str = None,
                     file_name: str = None, file_size: int = None) -> int:
        """Отправка сообщения."""
        now = datetime.now().strftime("%H:%M")

        is_private = int(chat_type == "private" and recipient_id is not None)
        is_group = int(chat_type == "group" and group_id is not None)

        return self.repository.send_message(
            user_id, username, full_name, message or "", now,
            is_private=is_private,
            recipient_id=recipient_id if is_private else None,
            group_id=group_id if is_group else None,
            is_group=is_group,
            reply_to_id=reply_to_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
        )

    def get_message_by_id(self, message_id: int) -> Optional[tuple]:
        """Получение сообщения по ID"""
        return self.repository.get_message_by_id(message_id)

    def get_reply_info(self, reply_to_id: int) -> Optional[dict]:
        """Получить информацию о сообщении, на которое отвечают"""
        return self.repository.get_reply_info(reply_to_id)

    # === Активность пользователей ===

    def update_activity(self, user_id: int) -> None:
        """Обновление активности пользователя"""
        self.repository.update_activity(user_id)

    def is_user_online(self, user_id: int) -> bool:
        """Проверка, находится ли пользователь онлайн"""
        return self.repository.is_user_online(user_id)

    # === Прочитанные сообщения ===

    def mark_as_read(self, user_id: int, message_ids: List[int]) -> None:
        """Отметить сообщения как прочитанные"""
        if message_ids:
            self.repository.mark_messages_as_read(user_id, message_ids)

    def get_unread_count(self, user_id: int) -> int:
        """Получить количество непрочитанных сообщений"""
        return self.repository.get_unread_count(user_id)

    def get_chat_message_ids(self, chat_type: str = "general", group_id: int = None,
                             user_id: int = None, recipient_id: int = None) -> List[int]:
        """Получение ID сообщений в чате"""
        if chat_type == "group" and group_id:
            return self.repository.get_chat_message_ids(group_id=group_id, user_id=user_id)
        elif chat_type == "private" and recipient_id:
            return self.repository.get_chat_message_ids(user_id=user_id, recipient_id=recipient_id, is_private=True)
        else:
            return self.repository.get_chat_message_ids(user_id=user_id)

    # === Группы ===

    def get_user_groups(self, user_id: int) -> List[tuple]:
        """Получение групп пользователя"""
        return self.repository.get_user_groups(user_id)

    def get_users_except(self, user_id: int) -> List[tuple]:
        """Получение всех пользователей кроме указанного"""
        return self.repository.get_users_except(user_id)

    def create_group(self, name: str, description: str, created_by: int,
                     members: List[int] = None) -> Optional[int]:
        """Создание группы"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        group_id = self.repository.create_group(name, description, created_by, now)

        if not group_id:
            return None

        # Добавляем создателя
        self.repository.add_group_member(group_id, created_by, now)

        # Добавляем остальных участников
        if members:
            for member_id in members:
                self.repository.add_group_member(group_id, member_id, now)

        return group_id

    def get_group_members(self, group_id: int) -> List[tuple]:
        """Получение участников группы"""
        return self.repository.get_group_members(group_id)

    def add_group_members(self, group_id: int, user_ids: List[int]) -> int:
        """Добавление участников в группу"""
        added = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for user_id in user_ids:
            if self.repository.add_group_member(group_id, user_id, now):
                added += 1

        return added

    def remove_group_member(self, group_id: int, user_id: int) -> bool:
        """Удаление участника из группы"""
        return self.repository.remove_group_member(group_id, user_id)

    def is_group_creator(self, group_id: int, user_id: int) -> bool:
        """Проверка, является ли пользователь создателем группы"""
        return self.repository.is_group_creator(group_id, user_id)

    def get_group_by_id(self, group_id: int) -> Optional[tuple]:
        """Получение группы по ID"""
        return self.repository.get_group_by_id(group_id)

    # === Файлы чата ===

    def get_chat_files_dir(self) -> str:
        """Получить актуальную папку для файлов чата"""
        if self.db_path:
            db_dir = os.path.dirname(self.db_path)
            files_dir = os.path.join(db_dir, "chat_files")
        else:
            files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_files")

        if not os.path.exists(files_dir):
            try:
                os.makedirs(files_dir)
            except:
                pass
        return files_dir

    def save_chat_file(self, source_path: str, username: str, filename: str) -> Optional[str]:
        """Сохранение файла чата"""
        chat_files_dir = self.get_chat_files_dir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{username}_{timestamp}_{filename}"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._-')

        dest_path = os.path.join(chat_files_dir, safe_filename)

        try:
            shutil.copy2(source_path, dest_path)
            return dest_path
        except Exception as e:
            logger.error(" сохранения файла: {e}")
            return None

    def clear_chat_history(self) -> bool:
        """Очистка всей истории чата"""
        return self.repository.delete_all_messages()

    def edit_message(self, msg_id: int, new_text: str) -> bool:
        return self.repository.edit_message(msg_id, new_text)

    def delete_message(self, msg_id: int) -> bool:
        return self.repository.delete(msg_id)

    def send_typing_status(self, user_id: int, chat_type: str,
                            group_id: int = None, recipient_id: int = None):
        self.repository.send_typing_status(user_id, chat_type,
                                            group_id, recipient_id)

    def clear_typing_status(self, user_id: int):
        self.repository.clear_typing_status(user_id)

    @staticmethod
    def make_tool_link(inner_code: str, articul: str = "") -> str:
        """Сформировать ссылку на инструмент для вставки в текст."""
        if articul:
            return f"#tool:{inner_code}|{articul}#"
        return f"#tool:{inner_code}#"

    @staticmethod
    def make_mention(full_name: str, user_id: int) -> str:
        """Сформировать упоминание пользователя."""
        safe = full_name.replace("]", "").replace("[", "")
        return f"@[{safe}](user:{user_id})"

    @staticmethod
    def extract_tool_codes(text: str) -> list:
        return [m.group(1) for m in RE_TOOL_LINK.finditer(text or "")]

    @staticmethod
    def extract_mention_ids(text: str) -> list:
        return [int(m.group(2)) for m in RE_MENTION.finditer(text or "")]

    def get_mention_candidates(self, query: str, exclude_user_id: int) -> list:
        """
        Пользователи для автодополнения @.
        Возвращает [(user_id, full_name, username), ...]
        """
        users = self.repository.get_users_except(exclude_user_id)
        q = (query or "").lower()
        result = []
        for uid, username, full_name, _ in users:
            display = full_name or username
            if not q or q in display.lower() or q in username.lower():
                result.append((uid, display, username))
        return result

    def get_tool_candidates(self, query: str, limit: int = 10) -> list:
        """
        Инструменты для автодополнения #.
        Возвращает [(inner_code, articul), ...]
        """
        # Через репозиторий инструментов (импортируем локально, чтобы не плодить циклы)
        from server.repositories.tool_repository import ToolRepository
        repo = ToolRepository(self.db_path)
        filters = {}
        if query:
            filters['search'] = query
        tools = repo.get_all(filters)[:limit]
        return [(t.inner_code, t.articul) for t in tools]