# server/repositories/user_repository.py
import json
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository
from shared.models.user import User, UserCreate, UserUpdate


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    _SELECT = """SELECT id, username, password, role, full_name,
                        created_at, permissions, last_login
                 FROM users"""

    def get_by_id(self, user_id: int) -> Optional[User]:
        row = self._execute(f"{self._SELECT} WHERE id = ?", (user_id,), fetch_one=True)
        return User.from_db_row(row) if row else None

    def get_by_username(self, username: str) -> Optional[User]:
        row = self._execute(f"{self._SELECT} WHERE username = ?", (username,), fetch_one=True)
        return User.from_db_row(row) if row else None

    def get_all(self) -> List[User]:
        rows = self._execute(f"{self._SELECT} ORDER BY id", fetch_all=True)
        return [User.from_db_row(row) for row in rows] if rows else []

    def create(self, user_data: UserCreate, hashed_password: str) -> Optional[User]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """INSERT INTO users
                  (username, password, role, full_name, created_at, permissions, last_login)
                  VALUES (?, ?, ?, ?, ?, ?, ?)"""

        last_id = self._insert_and_get_id(query, (
            user_data.username, hashed_password, user_data.role,
            user_data.full_name, now,
            json.dumps(user_data.permissions, ensure_ascii=False), now,
        ))
        return self.get_by_id(last_id)

    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        existing = self.get_by_id(user_id)
        if not existing:
            return None

        updates = []
        params = []

        if user_data.full_name is not None:
            updates.append("full_name = ?")
            params.append(user_data.full_name)

        if user_data.role is not None:
            updates.append("role = ?")
            params.append(user_data.role)

        if user_data.permissions is not None:
            updates.append("permissions = ?")
            params.append(json.dumps(user_data.permissions, ensure_ascii=False))

        if not updates:
            return existing

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return self.get_by_id(user_id)

    def update_password(self, user_id: int, hashed_password: str) -> bool:
        self._execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hashed_password, user_id),
            commit=True,
        )
        return True

    def update_last_login(self, user_id: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now, user_id),
            commit=True,
        )
        return True

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user or user.username == "admin":
            return False

        self._execute("DELETE FROM users WHERE id = ?", (user_id,), commit=True)
        return True