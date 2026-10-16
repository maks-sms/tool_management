# shared/models/chat.py
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ChatMessage:
    """Модель сообщения чата"""
    id: Optional[int] = None
    user_id: int = 0
    username: str = ""
    full_name: str = ""
    message: str = ""
    timestamp: str = ""
    is_private: int = 0
    recipient_id: Optional[int] = None
    group_id: Optional[int] = None
    is_group: int = 0
    reply_to_id: Optional[int] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChatMessage':
        return cls(
            id=row[0],
            user_id=row[1] if len(row) > 1 else 0,
            username=row[2] if len(row) > 2 else "",
            full_name=row[3] if len(row) > 3 else "",
            message=row[4] if len(row) > 4 else "",
            timestamp=row[5] if len(row) > 5 else "",
            is_private=row[6] if len(row) > 6 else 0,
            recipient_id=row[7] if len(row) > 7 else None,
            group_id=row[8] if len(row) > 8 else None,
            is_group=row[9] if len(row) > 9 else 0,
            reply_to_id=row[10] if len(row) > 10 else None,
            file_path=row[11] if len(row) > 11 else None,
            file_name=row[12] if len(row) > 12 else None,
            file_size=row[13] if len(row) > 13 else None
        )


@dataclass
class ChatGroup:
    """Модель группы чата"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_by: int = 0
    created_at: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChatGroup':
        return cls(
            id=row[0],
            name=row[1] if len(row) > 1 else "",
            description=row[2] if len(row) > 2 else "",
            created_by=row[3] if len(row) > 3 else 0,
            created_at=row[4] if len(row) > 4 else ""
        )


@dataclass
class ChatGroupMember:
    """Модель участника группы чата"""
    id: Optional[int] = None
    group_id: int = 0
    user_id: int = 0
    joined_at: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChatGroupMember':
        return cls(
            id=row[0],
            group_id=row[1] if len(row) > 1 else 0,
            user_id=row[2] if len(row) > 2 else 0,
            joined_at=row[3] if len(row) > 3 else ""
        )


@dataclass
class ChatActiveUser:
    """Модель активного пользователя чата"""
    id: Optional[int] = None
    user_id: int = 0
    last_activity: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChatActiveUser':
        return cls(
            id=row[0],
            user_id=row[1] if len(row) > 1 else 0,
            last_activity=row[2] if len(row) > 2 else ""
        )


@dataclass
class ReadMessage:
    """Модель прочитанного сообщения"""
    id: Optional[int] = None
    user_id: int = 0
    message_id: int = 0
    read_at: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ReadMessage':
        return cls(
            id=row[0],
            user_id=row[1] if len(row) > 1 else 0,
            message_id=row[2] if len(row) > 2 else 0,
            read_at=row[3] if len(row) > 3 else ""
        )