# server/repositories/machine_repository.py
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository


class MachineRepository(BaseRepository):
    """Репозиторий для работы со станками"""

    def get_by_id(self, machine_id: int) -> Optional[dict]:
        """Получение станка по ID"""
        query = "SELECT id, name FROM machines WHERE id = ?"
        result = self._execute(query, (machine_id,), fetch_one=True)
        if result:
            return {'id': result[0], 'name': result[1]}
        return None

    def get_all(self) -> List[str]:
        """Получение списка всех станков"""
        query = "SELECT name FROM machines ORDER BY name ASC"
        rows = self._execute(query, fetch_all=True)
        return [row[0] for row in rows] if rows else []

    def delete(self, machine_id: int) -> bool:
        """Удаление станка по ID"""
        query = "DELETE FROM machines WHERE id = ?"
        self._execute(query, (machine_id,), commit=True)
        return True

    def add(self, name: str) -> bool:
        """Добавление нового станка"""
        try:
            query = "INSERT INTO machines (name) VALUES (?)"
            self._execute(query, (name,), commit=True)
            return True
        except Exception:
            return False

    def exists(self, name: str) -> bool:
        """Проверка существования станка"""
        query = "SELECT id FROM machines WHERE name = ?"
        result = self._execute(query, (name,), fetch_one=True)
        return result is not None

    def get_by_name(self, name: str) -> Optional[dict]:
        """Получение станка по имени"""
        query = "SELECT id, name FROM machines WHERE name = ?"
        result = self._execute(query, (name,), fetch_one=True)
        if result:
            return {'id': result[0], 'name': result[1]}
        return None

    def delete_by_name(self, name: str) -> bool:
        self._execute("DELETE FROM machines WHERE name = ?", (name,), commit=True)
        return True

    # Расширенные операции

    def get_all_with_counts(self) -> list:
        """
        Список станков с количеством инструментов на каждом.
        Возвращает список кортежей: (machine_id, name, placements_count, total_qty)
        """
        query = """
            SELECT m.id,
                   m.name,
                   COUNT(p.id)                   AS placements_count,
                   COALESCE(SUM(p.qty), 0)       AS total_qty
            FROM machines m
            LEFT JOIN placement p
                   ON p.note = m.name
                  AND p.location LIKE ?
            GROUP BY m.id, m.name
            ORDER BY m.name
        """
        # Импортируем префикс из shared.config
        from shared.config import LOCATION_MACHINE_PREFIX
        rows = self._execute(
            query, (f"{LOCATION_MACHINE_PREFIX}%",), fetch_all=True
        )
        return rows if rows else []

    def get_with_count(self, machine_id: int) -> Optional[tuple]:
        """
        Один станок с количеством инструментов.
        Возвращает (machine_id, name, placements_count, total_qty) или None.
        """
        query = """
            SELECT m.id,
                   m.name,
                   COUNT(p.id)                   AS placements_count,
                   COALESCE(SUM(p.qty), 0)       AS total_qty
            FROM machines m
            LEFT JOIN placement p
                   ON p.note = m.name
                  AND p.location LIKE ?
            WHERE m.id = ?
            GROUP BY m.id, m.name
        """
        from shared.config import LOCATION_MACHINE_PREFIX
        return self._execute(
            query, (f"{LOCATION_MACHINE_PREFIX}%", machine_id), fetch_one=True
        )

    def rename(self, machine_id: int, new_name: str) -> bool:
        """
        Переименовать станок.
        Обновляет machines.name, placement.note и placement.location
        для всех связанных записей.
        """
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        from shared.config import LOCATION_MACHINE_PREFIX

        # Получаем текущее имя
        row = self._execute(
            "SELECT name FROM machines WHERE id = ?",
            (machine_id,), fetch_one=True,
        )
        if not row:
            return False
        old_name = row[0]

        # 1) Обновляем machines
        self._execute(
            "UPDATE machines SET name = ? WHERE id = ?",
            (new_name, machine_id), commit=True,
        )

        # 2) Обновляем placement.note и placement.location
        self._execute(
            "UPDATE placement SET note = ? WHERE note = ? AND location LIKE ?",
            (new_name, old_name, f"{LOCATION_MACHINE_PREFIX}%"),
            commit=True,
        )
        self._execute(
            "UPDATE placement SET location = ? WHERE location = ?",
            (f"{LOCATION_MACHINE_PREFIX}{new_name}",
             f"{LOCATION_MACHINE_PREFIX}{old_name}"),
            commit=True,
        )
        return True

    def get_placement_count(self, machine_id: int) -> int:
        """Сколько записей размещений привязано к станку."""
        from shared.config import LOCATION_MACHINE_PREFIX
        row = self._execute(
            "SELECT name FROM machines WHERE id = ?",
            (machine_id,), fetch_one=True,
        )
        if not row:
            return 0
        name = row[0]
        r = self._execute(
            "SELECT COUNT(*) FROM placement "
            "WHERE note = ? AND location LIKE ?",
            (name, f"{LOCATION_MACHINE_PREFIX}%"),
            fetch_one=True,
        )
        return r[0] if r else 0