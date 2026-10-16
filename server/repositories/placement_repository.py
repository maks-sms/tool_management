# server/repositories/placement_repository.py
from typing import List, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository
from shared.models.placement import Placement, PlacementCreate


class PlacementRepository(BaseRepository[Placement]):
    """Репозиторий для работы с размещениями инструментов."""

    _SELECT = "SELECT id, tool_id, location, qty, note, date FROM placement"

    def get_by_id(self, placement_id: int) -> Optional[Placement]:
        row = self._execute(f"{self._SELECT} WHERE id = ?", (placement_id,), fetch_one=True)
        return Placement.from_db_row(row) if row else None

    def get_all(self) -> List[Placement]:
        rows = self._execute(self._SELECT, fetch_all=True)
        return [Placement.from_db_row(row) for row in rows] if rows else []

    def get_by_tool_id(self, tool_id: int) -> List[Placement]:
        rows = self._execute(f"{self._SELECT} WHERE tool_id = ?", (tool_id,), fetch_all=True)
        return [Placement.from_db_row(row) for row in rows] if rows else []

    def get_by_location(self, location_pattern: str) -> List[tuple]:
        query = """SELECT p.id, p.note, t.inner_code, t.articul, t.type,
                          t.diameter, t.length, t.brand, p.qty
                   FROM placement p
                   JOIN tools t ON p.tool_id = t.id
                   WHERE p.location LIKE ?
                   ORDER BY p.note, t.inner_code"""
        rows = self._execute(query, (location_pattern,), fetch_all=True)
        return rows if rows else []

    def create(self, placement_data: PlacementCreate) -> Optional[Placement]:
        query = """INSERT INTO placement (tool_id, location, qty, note, date)
                   VALUES (?, ?, ?, ?, ?)"""

        last_id = self._insert_and_get_id(query, (
            placement_data.tool_id,
            placement_data.location,
            placement_data.qty,
            placement_data.note,
            placement_data.date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        return self.get_by_id(last_id)

    def update_quantity(self, placement_id: int, new_qty: int) -> bool:
        """Установить НОВОЕ количество. Если <= 0 — удалить запись."""
        if new_qty <= 0:
            return self.delete(placement_id)
        self._execute(
            "UPDATE placement SET qty = ? WHERE id = ?",
            (new_qty, placement_id),
            commit=True,
        )
        return True

    def delete(self, placement_id: int) -> bool:
        self._execute("DELETE FROM placement WHERE id = ?", (placement_id,), commit=True)
        return True

    def delete_by_tool_id(self, tool_id: int) -> bool:
        self._execute("DELETE FROM placement WHERE tool_id = ?", (tool_id,), commit=True)
        return True

    def create_with_conn(self, conn, placement_data: PlacementCreate) -> int:
        """INSERT размещения в рамках транзакции. Возвращает lastrowid."""
        return self._execute_with_conn(
            conn,
            "INSERT INTO placement (tool_id, location, qty, note, date) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                placement_data.tool_id,
                placement_data.location,
                placement_data.qty,
                placement_data.note,
                placement_data.date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
            return_last_id=True,
        )