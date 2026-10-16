# server/repositories/chat_repository.py (исправленная версия)
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_repository import BaseRepository
from shared.models.chat import ChatMessage, ChatGroup, ChatGroupMember, ChatActiveUser, ReadMessage


class ChatRepository(BaseRepository):
    """Репозиторий для работы с чатом"""

    # Реализация абстрактных методов BaseRepository

    def get_by_id(self, id: int) -> Optional[dict]:
        """Получение сообщения по ID (реализация абстрактного метода)"""
        return self.get_message_by_id(id)

    def get_all(self, limit: int = 100) -> List[tuple]:
        """Получение всех сообщений (реализация абстрактного метода)"""
        return self.get_messages(limit=limit)

    def delete(self, id: int) -> bool:
        """Удаление сообщения по ID (реализация абстрактного метода)"""
        try:
            query = "DELETE FROM chat_messages WHERE id = ?"
            self._execute(query, (id,), commit=True)
            return True
        except Exception:
            return False

    def edit_message(self, msg_id: int, new_text: str) -> bool:
        """Редактирование сообщения."""
        try:
            self._execute(
                "UPDATE chat_messages SET message = ?, "
                "timestamp = datetime('now', 'localtime') WHERE id = ?",
                (new_text, msg_id), commit=True,
            )
            return True
        except Exception:
            return False

    def send_typing_status(self, user_id: int, chat_type: str,
                           group_id: int = None, recipient_id: int = None):
        """Записать статус «печатает»."""
        try:
            self._execute(
                "INSERT OR REPLACE INTO typing_status "
                "(user_id, chat_type, group_id, recipient_id, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                (user_id, chat_type, group_id, recipient_id), commit=True,
            )
        except Exception:
            pass

    def clear_typing_status(self, user_id: int):
        """Убрать статус «печатает»."""
        try:
            self._execute(
                "DELETE FROM typing_status WHERE user_id = ?",
                (user_id,), commit=True,
            )
        except Exception:
            pass

    # Существующие методы

    def get_messages(self, group_id: int = None, user_id: int = None,
                     recipient_id: int = None, is_private: bool = False,
                     is_group: bool = False, limit: int = 100) -> List[tuple]:
        """Получение сообщений"""
        if is_group and group_id:
            query = """SELECT id, username, full_name, message, timestamp, user_id,
                              reply_to_id, file_path, file_name, file_size
                       FROM chat_messages
                       WHERE group_id = ? AND is_group = 1
                       ORDER BY id ASC
                       LIMIT ?"""
            params = (group_id, limit)
        elif is_private and user_id and recipient_id:
            query = """SELECT id, username, full_name, message, timestamp, user_id,
                              reply_to_id, file_path, file_name, file_size
                       FROM chat_messages
                       WHERE is_private = 1 AND
                             ((user_id = ? AND recipient_id = ?) OR
                              (user_id = ? AND recipient_id = ?))
                       ORDER BY id ASC
                       LIMIT ?"""
            params = (user_id, recipient_id, recipient_id, user_id, limit)
        else:
            query = """SELECT id, username, full_name, message, timestamp, user_id,
                              reply_to_id, file_path, file_name, file_size
                       FROM chat_messages
                       WHERE (is_private = 0 OR is_private IS NULL)
                         AND (group_id IS NULL OR group_id = 0)
                       ORDER BY id ASC
                       LIMIT ?"""
            params = (limit,)

        rows = self._execute(query, params, fetch_all=True)
        return rows if rows else []

    def send_message(self, user_id: int, username: str, full_name: str,
                     message: str, timestamp: str, is_private: int = 0,
                     recipient_id: int = None, group_id: int = None,
                     is_group: int = 0, reply_to_id: int = None,
                     file_path: str = None, file_name: str = None,
                     file_size: int = None) -> int:
        """Отправка сообщения"""
        query = """INSERT INTO chat_messages
                  (user_id, username, full_name, message, timestamp,
                   is_private, recipient_id, group_id, is_group,
                   reply_to_id, file_path, file_name, file_size)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        return self._insert_and_get_id(query, (
            user_id, username, full_name, message or "", timestamp,
            is_private, recipient_id, group_id, is_group,
            reply_to_id, file_path, file_name, file_size,
        ))

    def get_message_by_id(self, message_id: int) -> Optional[tuple]:
        """Получение сообщения по ID"""
        query = """SELECT id, username, full_name, message, timestamp, user_id
                   FROM chat_messages WHERE id = ?"""
        return self._execute(query, (message_id,), fetch_one=True)

    def get_reply_info(self, reply_to_id: int) -> Optional[dict]:
        """Получение информации о сообщении для ответа"""
        query = "SELECT username, full_name, message FROM chat_messages WHERE id = ?"
        row = self._execute(query, (reply_to_id,), fetch_one=True)
        if row:
            username, full_name, message = row
            return {
                'sender': full_name if full_name else username,
                'text': message
            }
        return None

    def update_activity(self, user_id: int) -> None:
        """Обновление активности пользователя"""
        query = """INSERT OR REPLACE INTO chat_active_users (user_id, last_activity)
                   VALUES (?, ?)"""
        self._execute(query, (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), commit=True)

    def is_user_online(self, user_id: int) -> bool:
        """Проверка, находится ли пользователь онлайн"""
        two_minutes_ago = (datetime.now() - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        query = "SELECT id FROM chat_active_users WHERE user_id = ? AND last_activity > ?"
        row = self._execute(query, (user_id, two_minutes_ago), fetch_one=True)
        return row is not None

    def get_user_groups(self, user_id: int) -> List[tuple]:
        """Получение групп пользователя"""
        query = """SELECT g.id, g.name, 'group' as type,
                          (SELECT COUNT(*) FROM chat_group_members WHERE group_id = g.id) as member_count
                   FROM chat_groups g
                   JOIN chat_group_members gm ON g.id = gm.group_id
                   WHERE gm.user_id = ?
                   ORDER BY g.name"""
        rows = self._execute(query, (user_id,), fetch_all=True)
        return rows if rows else []

    def get_users_except(self, user_id: int) -> List[tuple]:
        """Получение всех пользователей кроме указанного"""
        query = """SELECT id, username, full_name, 'user' as type
                   FROM users WHERE id != ? ORDER BY full_name"""
        rows = self._execute(query, (user_id,), fetch_all=True)
        return rows if rows else []

    def create_group(self, name: str, description: str, created_by: int,
                     created_at: str) -> Optional[int]:
        """Создание группы"""
        check_query = "SELECT id FROM chat_groups WHERE name = ?"
        if self._execute(check_query, (name,), fetch_one=True):
            return None

        query = """INSERT INTO chat_groups (name, description, created_by, created_at)
                   VALUES (?, ?, ?, ?)"""
        return self._insert_and_get_id(query, (name, description, created_by, created_at))

    def add_group_member(self, group_id: int, user_id: int, joined_at: str) -> bool:
        """Добавление участника в группу"""
        query = """INSERT INTO chat_group_members (group_id, user_id, joined_at)
                   VALUES (?, ?, ?)"""
        try:
            self._execute(query, (group_id, user_id, joined_at), commit=True)
            return True
        except Exception:
            return False

    def get_group_members(self, group_id: int) -> List[tuple]:
        """Получение участников группы"""
        query = """SELECT u.id, u.username, u.full_name,
                          CASE WHEN gm.user_id = g.created_by THEN 1 ELSE 0 END as is_creator
                   FROM chat_group_members gm
                   JOIN users u ON gm.user_id = u.id
                   JOIN chat_groups g ON gm.group_id = g.id
                   WHERE gm.group_id = ?
                   ORDER BY is_creator DESC, u.full_name"""
        rows = self._execute(query, (group_id,), fetch_all=True)
        return rows if rows else []

    def remove_group_member(self, group_id: int, user_id: int) -> bool:
        """Удаление участника из группы"""
        query = "DELETE FROM chat_group_members WHERE group_id = ? AND user_id = ?"
        self._execute(query, (group_id, user_id), commit=True)
        return True

    def is_group_creator(self, group_id: int, user_id: int) -> bool:
        """Проверка, является ли пользователь создателем группы"""
        query = "SELECT created_by FROM chat_groups WHERE id = ?"
        row = self._execute(query, (group_id,), fetch_one=True)
        return row and row[0] == user_id

    def get_group_by_id(self, group_id: int) -> Optional[tuple]:
        """Получение группы по ID"""
        query = "SELECT id, name, description, created_by, created_at FROM chat_groups WHERE id = ?"
        return self._execute(query, (group_id,), fetch_one=True)

    def get_unread_count(self, user_id: int) -> int:
        """Получить количество непрочитанных сообщений"""
        # Получаем ID последнего прочитанного сообщения
        query = "SELECT MAX(message_id) FROM read_messages WHERE user_id = ?"
        row = self._execute(query, (user_id,), fetch_one=True)
        last_read = row[0] if row and row[0] is not None else None

        if last_read:
            query = "SELECT COUNT(*) FROM chat_messages WHERE id > ? AND user_id != ?"
            row = self._execute(query, (last_read, user_id), fetch_one=True)
        else:
            query = "SELECT COUNT(*) FROM chat_messages WHERE user_id != ?"
            row = self._execute(query, (user_id,), fetch_one=True)

        return row[0] if row else 0

    def mark_messages_as_read(self, user_id: int, message_ids: List[int]) -> None:
        """Отметить сообщения как прочитанные"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for msg_id in message_ids:
            query = """INSERT OR IGNORE INTO read_messages (user_id, message_id, read_at)
                       VALUES (?, ?, ?)"""
            self._execute(query, (user_id, msg_id, now), commit=True)

    def get_chat_message_ids(self, group_id: int = None, user_id: int = None,
                             recipient_id: int = None, is_private: bool = False) -> List[int]:
        """Получение ID сообщений в чате"""
        if group_id:
            query = "SELECT id FROM chat_messages WHERE group_id = ? AND user_id != ?"
            rows = self._execute(query, (group_id, user_id), fetch_all=True)
        elif is_private and recipient_id:
            query = """SELECT id FROM chat_messages
                       WHERE is_private = 1 AND user_id = ? AND recipient_id = ?"""
            rows = self._execute(query, (recipient_id, user_id), fetch_all=True)
        else:
            query = "SELECT id FROM chat_messages WHERE (is_private = 0 OR is_private IS NULL) AND user_id != ?"
            rows = self._execute(query, (user_id,), fetch_all=True)

        return [row[0] for row in rows] if rows else []

    def delete_all_messages(self) -> bool:
        """Удаление всех сообщений (для администратора)"""
        try:
            query = "DELETE FROM chat_messages"
            self._execute(query, commit=True)
            return True
        except Exception:
            return False