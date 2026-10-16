# shared/models/placement.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Placement:
    """Модель размещения инструмента"""
    id: Optional[int] = None
    tool_id: int = 0
    location: str = ""
    qty: int = 0
    note: str = ""
    date: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Placement':
        return cls(
            id=row[0],
            tool_id=row[1],
            location=row[2],
            qty=row[3],
            note=row[4] if len(row) > 4 else "",
            date=row[5] if len(row) > 5 else ""
        )


@dataclass
class PlacementCreate:
    """Данные для создания размещения"""
    tool_id: int
    location: str
    qty: int
    note: str = ""
    date: str = ""