# server/services/history_service.py
from typing import List, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.history import HistoryRecord, HistoryAction
from server.repositories.history_repository import HistoryRepository


class HistoryService:
    """Сервис для работы с историей операций"""

    def __init__(self, db_path: str = None):
        self.repository = HistoryRepository(db_path)

    def get_all(self, limit: int = 500) -> List[HistoryRecord]:
        """Получение всех записей истории"""
        return self.repository.get_all(limit)

    def get_by_id(self, history_id: int) -> Optional[HistoryRecord]:
        """Получение записи по ID"""
        return self.repository.get_by_id(history_id)

    def add_record(self, articul: str, action: str, qty: int, target: str, worker: str) -> None:
        """Добавление записи в историю"""
        self.repository.add(articul, action, qty, target, worker)

    def add_receipt(self, articul: str, qty: int, worker: str) -> None:
        """Добавление записи о поступлении"""
        self.add_record(articul, HistoryAction.RECEIPT.value, qty, "Склад", worker)

    def add_to_machine(self, articul: str, qty: int, machine: str, worker: str) -> None:
        """Добавление записи о выдаче на станок"""
        self.add_record(articul, HistoryAction.TO_MACHINE.value, qty, machine, worker)

    def add_to_reserve(self, articul: str, qty: int, task: str, worker: str) -> None:
        """Добавление записи о перемещении в резерв"""
        self.add_record(articul, HistoryAction.TO_RESERVE.value, qty, task, worker)

    def add_return(self, articul: str, qty: int, worker: str) -> None:
        """Добавление записи о возврате на склад"""
        self.add_record(articul, HistoryAction.RETURN.value, qty, "Склад", worker)

    def add_writeoff(self, articul: str, qty: int, reason: str, worker: str) -> None:
        """Добавление записи о списании"""
        self.add_record(articul, HistoryAction.WRITEOFF.value, qty, reason, worker)

    def add_tool_creation(self, articul: str, qty: int, worker: str) -> None:
        """Добавление записи о создании инструмента"""
        self.add_record(articul, HistoryAction.ADD.value, qty, "Склад", worker)

    def add_tool_deletion(self, articul: str, qty: int, worker: str) -> None:
        """Добавление записи об удалении инструмента"""
        self.add_record(articul, HistoryAction.DELETE.value, qty, "Удален из системы", worker)


    #  Очистка

    def clear_all(self) -> int:
        """Удалить всю историю. Возвращает количество удалённых записей."""
        return self.repository.clear_all()

    def clear_before_date(self, date_str: str) -> int:
        """Удалить записи старше date_str. Возвращает количество удалённых записей."""
        return self.repository.clear_before_date(date_str)

    def clear_period(self, date_from: str, date_to: str) -> int:
        """Удалить записи в диапазоне. Возвращает количество удалённых записей."""
        return self.repository.clear_period(date_from, date_to)