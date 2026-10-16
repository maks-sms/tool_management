# server/repositories/history_repository.py
from typing import List, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository
from shared.models.history import HistoryRecord
from shared.utils import now_short, now_full

class HistoryRepository(BaseRepository[HistoryRecord]):
    """Репозиторий для работы с историей"""

    def get_by_id(self, history_id: int) -> Optional[HistoryRecord]:
        """Получение записи истории по ID"""
        query = "SELECT id, date, articul, action, qty, target, worker, timestamp FROM history WHERE id = ?"
        row = self._execute(query, (history_id,), fetch_one=True)
        return HistoryRecord.from_db_row(row) if row else None

    def get_all(self, limit: int = 500) -> List[HistoryRecord]:
        """Получение всех записей истории (с ограничением)"""
        query = "SELECT id, date, articul, action, qty, target, worker, timestamp FROM history ORDER BY id DESC LIMIT ?"
        rows = self._execute(query, (limit,), fetch_all=True)
        return [HistoryRecord.from_db_row(row) for row in rows] if rows else []

    def add(self, articul: str, action: str, qty: int, target: str, worker: str) -> None:
        query = """INSERT INTO history (date, articul, action, qty, target, worker, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
        self._execute(query, (
            now_short(),
            articul,
            action,
            qty,
            target,
            worker,
            now_full(),
        ), commit=True)

    def delete(self, history_id: int) -> bool:
        """Удаление записи истории"""
        query = "DELETE FROM history WHERE id = ?"
        self._execute(query, (history_id,), commit=True)
        return True

    def add_with_conn(self, conn, articul: str, action: str, qty: int,
                      target: str, worker: str) -> None:
        """INSERT записи истории в рамках транзакции."""
        self._execute_with_conn(
            conn,
            "INSERT INTO history (date, articul, action, qty, target, worker, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now_short(), articul, action, qty, target, worker, now_full()),
        )

    # Очистка истории

    def clear_all(self) -> int:
        """
        Удалить все записи истории.
        :return: количество удалённых записей
        """
        row = self._execute("SELECT COUNT(*) FROM history", fetch_one=True)
        count = row[0] if row else 0
        self._execute("DELETE FROM history", commit=True)
        return count

    def clear_before_date(self, date_str: str) -> int:
        """
        Удалить все записи истории старше указанной даты (по полю timestamp).
        :param date_str: дата в формате '%Y-%m-%d %H:%M:%S'
        :return: количество удалённых записей
        """
        row = self._execute(
            "SELECT COUNT(*) FROM history WHERE timestamp < ?",
            (date_str,), fetch_one=True,
        )
        count = row[0] if row else 0
        self._execute(
            "DELETE FROM history WHERE timestamp < ?",
            (date_str,), commit=True,
        )
        return count

    def clear_period(self, date_from: str, date_to: str) -> int:
        """
        Удалить записи истории в диапазоне дат (по полю timestamp).
        :return: количество удалённых записей
        """
        row = self._execute(
            "SELECT COUNT(*) FROM history WHERE timestamp >= ? AND timestamp <= ?",
            (date_from, date_to), fetch_one=True,
        )
        count = row[0] if row else 0
        self._execute(
            "DELETE FROM history WHERE timestamp >= ? AND timestamp <= ?",
            (date_from, date_to), commit=True,
        )
        return count