# shared/models/user.py
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

class UserRole(Enum):
    """Роли пользователей"""
    ADMIN = "admin"
    USER = "user"

    @classmethod
    def from_string(cls, value: str) -> 'UserRole':
        for role in cls:
            if role.value == value:
                return role
        return cls.USER


@dataclass
class User:
    """Модель пользователя"""
    id: Optional[int] = None
    username: str = ""
    password: str = ""
    role: str = "user"
    full_name: str = ""
    created_at: str = ""
    permissions: Dict[str, Any] = field(default_factory=dict)
    last_login: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'User':
        import json
        permissions = {}
        if len(row) > 6 and row[6]:
            try:
                permissions = json.loads(row[6])
            except:
                pass
        return cls(
            id=row[0],
            username=row[1] if len(row) > 1 else "",
            password=row[2] if len(row) > 2 else "",
            role=row[3] if len(row) > 3 else "user",
            full_name=row[4] if len(row) > 4 else "",
            created_at=row[5] if len(row) > 5 else "",
            permissions=permissions,
            last_login=row[7] if len(row) > 7 else ""
        )

    def is_admin(self) -> bool:
        return self.role == "admin"

    def has_permission(self, tab: str, action: str = 'view') -> bool:
        """Проверка права доступа"""
        if self.is_admin():
            return True
        tab_perms = self.permissions.get(tab, {})
        return tab_perms.get(action, False)


@dataclass
class UserCreate:
    """Данные для создания пользователя"""
    username: str
    password: str
    full_name: str = ""
    role: str = "user"
    permissions: Dict[str, Any] = field(default_factory=lambda: {
        "inventory": {"view": True, "edit": True},
        "machines": {"view": True, "edit": True},
        "reserve": {"view": True, "edit": True},
        "history": {"view": True, "edit": True},
        "tools": {"view": True, "edit": True},
        "requests": {"view": True, "edit": True},
        "export": {"view": True, "edit": False}
    })


@dataclass
class UserUpdate:
    """Данные для обновления пользователя"""
    full_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    password: Optional[str] = None