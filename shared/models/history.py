# shared/models/history.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class HistoryAction(Enum):
    """Типы действий в истории"""
    RECEIPT = "ПОСТУПЛЕНИЯ"
    TO_MACHINE = "НА СТАНОК"
    TO_RESERVE = "В РЕЗЕРВ"
    RETURN = "ВОЗВРАТ"
    WRITEOFF = "СПИСАНИЕ"
    ADD = "ДОБАВЛЕНИЕ"
    DELETE = "УДАЛЕНИЕ"
    CORRECTION = "КОРРЕКТИРОВКА"
    CODE_CHANGE = "ИЗМЕНЕНИЕ КОДА"

    @classmethod
    def from_string(cls, value: str) -> 'HistoryAction':
        for action in cls:
            if action.value == value:
                return action
        return cls.RECEIPT


@dataclass
class HistoryRecord:
    """Модель записи истории"""
    id: Optional[int] = None
    date: str = ""
    articul: str = ""
    action: str = ""
    qty: int = 0
    target: str = ""
    worker: str = ""
    timestamp: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'HistoryRecord':
        return cls(
            id=row[0],
            date=row[1] if len(row) > 1 else "",
            articul=row[2] if len(row) > 2 else "",
            action=row[3] if len(row) > 3 else "",
            qty=row[4] if len(row) > 4 else 0,
            target=row[5] if len(row) > 5 else "",
            worker=row[6] if len(row) > 6 else "",
            timestamp=row[7] if len(row) > 7 else ""
        )