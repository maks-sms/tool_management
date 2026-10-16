# server/repositories/tool_repository.py
from typing import List, Optional, Dict
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository
from shared.models.tool import Tool, ToolCreate, ToolUpdate


class ToolRepository(BaseRepository[Tool]):
    """Репозиторий для работы с инструментами."""

    def get_by_id(self, tool_id: int) -> Optional[Tool]:
        query = """SELECT id, inner_code, articul, type, diameter, length,
                          brand, analog, qty_total, min_qty, location,
                          created_at, updated_at
                   FROM tools WHERE id = ?"""
        row = self._execute(query, (tool_id,), fetch_one=True)
        return Tool.from_db_row(row) if row else None

    def get_by_code(self, inner_code: str) -> Optional[Tool]:
        query = """SELECT id, inner_code, articul, type, diameter, length,
                          brand, analog, qty_total, min_qty, location,
                          created_at, updated_at
                   FROM tools WHERE inner_code = ?"""
        row = self._execute(query, (inner_code,), fetch_one=True)
        return Tool.from_db_row(row) if row else None

    def get_all(self, filters: Dict[str, str] = None) -> List[Tool]:
        filters = filters or {}

        query = """SELECT id, inner_code, articul, type, diameter, length,
                          brand, analog, qty_total, min_qty, location,
                          created_at, updated_at
                   FROM tools WHERE 1=1"""
        params = []

        if filters.get('search'):
            search = f"%{filters['search']}%"
            query += " AND (inner_code LIKE ? OR articul LIKE ?)"
            params.extend([search, search])

        if filters.get('type'):
            query += " AND type = ?"
            params.append(filters['type'])

        if filters.get('brand'):
            query += " AND brand = ?"
            params.append(filters['brand'])

        if filters.get('diameter'):
            query += " AND diameter LIKE ?"
            params.append(f"%{filters['diameter']}%")

        query += " ORDER BY inner_code"

        rows = self._execute(query, tuple(params), fetch_all=True)
        return [Tool.from_db_row(row) for row in rows] if rows else []

    def create(self, tool_data: ToolCreate) -> Optional[Tool]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """INSERT INTO tools
                  (inner_code, articul, type, diameter, length, brand, analog,
                   qty_total, min_qty, created_at, updated_at)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        last_id = self._insert_and_get_id(query, (
            tool_data.inner_code, tool_data.articul, tool_data.type,
            tool_data.diameter, tool_data.length, tool_data.brand,
            tool_data.analog, tool_data.qty_total, tool_data.min_qty,
            now, now,
        ))
        return self.get_by_id(last_id)

    def update(self, tool_id: int, tool_data: ToolUpdate) -> Optional[Tool]:
        existing = self.get_by_id(tool_id)
        if not existing:
            return None

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates = []
        params = []

        for attr, column in [
            ('inner_code', 'inner_code'), ('articul', 'articul'),
            ('type', 'type'), ('diameter', 'diameter'),
            ('length', 'length'), ('brand', 'brand'),
            ('analog', 'analog'), ('qty_total', 'qty_total'),
            ('min_qty', 'min_qty'), ('location', 'location'),
        ]:
            value = getattr(tool_data, attr, None)
            if value is not None:
                updates.append(f"{column} = ?")
                params.append(value)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(now)
        params.append(tool_id)

        query = f"UPDATE tools SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)

        return self.get_by_id(tool_id)

    def update_quantity(self, tool_id: int, delta: int) -> Optional[Tool]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "UPDATE tools SET qty_total = qty_total + ?, updated_at = ? WHERE id = ?"
        self._execute(query, (delta, now, tool_id), commit=True)
        return self.get_by_id(tool_id)

    def delete(self, tool_id: int) -> bool:
        """Удаление только если нет активных размещений (безопасно)."""
        row = self._execute(
            "SELECT COUNT(*) FROM placement WHERE tool_id = ?",
            (tool_id,), fetch_one=True,
        )
        if row and row[0] > 0:
            raise ValueError(
                f"Нельзя удалить инструмент: есть {row[0]} активных размещений"
            )
        self._execute("DELETE FROM tools WHERE id = ?", (tool_id,), commit=True)
        return True
    
    def get_next_inner_code(self) -> str:
        query = "SELECT inner_code FROM tools WHERE inner_code LIKE 'INS%' ORDER BY inner_code DESC"
        rows = self._execute(query, fetch_all=True)

        if not rows:
            return "INS001"

        max_num = 0
        for row in rows:
            code_str = row[0]
            if code_str.startswith('INS'):
                try:
                    num = int(code_str[3:])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue

        return f"INS{max_num + 1:03d}"

    def get_unique_types(self) -> List[str]:
        query = "SELECT DISTINCT type FROM tools WHERE type IS NOT NULL AND type != '' ORDER BY type"
        rows = self._execute(query, fetch_all=True)
        return [row[0] for row in rows] if rows else []

    def get_unique_brands(self) -> List[str]:
        query = "SELECT DISTINCT brand FROM tools WHERE brand IS NOT NULL AND brand != '' ORDER BY brand"
        rows = self._execute(query, fetch_all=True)
        return [row[0] for row in rows] if rows else []

    def update_quantity_with_conn(self, conn, tool_id: int, delta: int) -> None:
        """Изменение количества инструмента в рамках транзакции."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execute_with_conn(
            conn,
            "UPDATE tools SET qty_total = qty_total + ?, updated_at = ? WHERE id = ?",
            (delta, now, tool_id),
        )