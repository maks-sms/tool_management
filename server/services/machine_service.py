# server/services/machine_service.py
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.repositories.machine_repository import MachineRepository


class MachineService:
    """Сервис для работы со станками"""

    def __init__(self, db_path: str = None):
        self.repository = MachineRepository(db_path)

    def get_all(self) -> List[str]:
        """Получение списка всех станков"""
        return self.repository.get_all()

    def add(self, name: str) -> bool:
        """Добавление нового станка"""
        if not name or self.repository.exists(name):
            return False
        return self.repository.add(name)

    def delete(self, name: str) -> bool:
        """Удаление станка"""
        return self.repository.delete_by_name(name)

    def delete_by_id(self, machine_id: int) -> bool:
            """Удалить станок по ID."""
            return self.repository.delete(machine_id)

    def exists(self, name: str) -> bool:
        """Проверка существования станка"""
        return self.repository.exists(name)

    def get_all_with_counts(self) -> list:
        """Все станки с числом размещений и суммарным количеством."""
        return self.repository.get_all_with_counts()

    def get_with_count(self, machine_id: int):
        """Один станок с числом размещений."""
        return self.repository.get_with_count(machine_id)

    def rename(self, machine_id: int, new_name: str) -> bool:
        """Переименовать станок (обновляет все связанные записи)."""
        if not new_name or not new_name.strip():
            return False
        # Проверяем, что новое имя не занято другим станком
        existing = self.repository.get_by_name(new_name.strip())
        if existing and existing['id'] != machine_id:
            return False
        return self.repository.rename(machine_id, new_name.strip())

    def get_placement_count(self, machine_id: int) -> int:
        """Сколько инструмента привязано к станку."""
        return self.repository.get_placement_count(machine_id)