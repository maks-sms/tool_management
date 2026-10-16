# server/services/user_service.py
import hashlib  # ← можно удалить, если больше нигде не используется
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.user import User, UserCreate, UserUpdate
from server.repositories.user_repository import UserRepository
from shared.utils.password_utils import (
    hash_password,
    verify_password,
    needs_rehash,
    is_legacy_hash,
)


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, db_path: str = None):
        self.repository = UserRepository(db_path)

    # Чтение

    def get_all(self) -> List[User]:
        """Получение всех пользователей."""
        return self.repository.get_all()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID."""
        return self.repository.get_by_id(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по логину."""
        return self.repository.get_by_username(username)

    # Аутентификация

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Аутентификация пользователя."""
        user = self.repository.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.password):
            return None

        # Прозрачная миграция: если хеш старый — перехешируем
        if needs_rehash(user.password):
            try:
                new_hash = hash_password(password)
                self.repository.update_password(user.id, new_hash)
            except Exception:
                pass

        self.repository.update_last_login(user.id)
        return user

    # CRUD

    def create(self, user_data: UserCreate) -> Optional[User]:
        """Создание нового пользователя."""
        existing = self.repository.get_by_username(user_data.username)
        if existing:
            return None

        if len(user_data.password) < 4:
            raise Exception("Пароль должен быть не менее 4 символов")

        hashed = hash_password(user_data.password)
        return self.repository.create(user_data, hashed)

    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        return self.repository.update(user_id, user_data)

    def delete(self, user_id: int) -> bool:
        return self.repository.delete(user_id)

    # Пароли

    def change_password(self, user_id: int, old_password: str,
                        new_password: str) -> bool:
        """Смена пароля пользователя."""
        user = self.repository.get_by_id(user_id)
        if not user:
            return False
        if not verify_password(old_password, user.password):
            return False
        if len(new_password) < 4:
            raise Exception("Пароль должен быть не менее 4 символов")

        return self.repository.update_password(
            user_id, hash_password(new_password)
        )

    def reset_password(self, user_id: int, new_password: str) -> bool:
        """Сброс пароля (для администратора)."""
        if len(new_password) < 4:
            raise Exception("Пароль должен быть не менее 4 символов")

        return self.repository.update_password(
            user_id, hash_password(new_password)
        )