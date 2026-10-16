# shared/models/tool.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Tool:
    """Модель инструмента"""
    id: Optional[int] = None
    inner_code: str = ""
    articul: str = ""
    type: str = ""
    diameter: str = ""
    length: str = ""
    brand: str = ""
    analog: str = ""
    qty_total: int = 0
    min_qty: int = 0
    location: str = "Склад"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Tool':
        """Создание модели из строки БД"""
        return cls(
            id=row[0],
            inner_code=row[1] if len(row) > 1 else "",
            articul=row[2] if len(row) > 2 else "",
            type=row[3] if len(row) > 3 else "",
            diameter=row[4] if len(row) > 4 else "",
            length=row[5] if len(row) > 5 else "",
            brand=row[6] if len(row) > 6 else "",
            analog=row[7] if len(row) > 7 else "",
            qty_total=row[8] if len(row) > 8 else 0,
            min_qty=row[9] if len(row) > 9 else 0,
            location=row[10] if len(row) > 10 else "Склад",
            created_at=row[11] if len(row) > 11 else None,
            updated_at=row[12] if len(row) > 12 else None
        )

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'inner_code': self.inner_code,
            'articul': self.articul,
            'type': self.type,
            'diameter': self.diameter,
            'length': self.length,
            'brand': self.brand,
            'analog': self.analog,
            'qty_total': self.qty_total,
            'min_qty': self.min_qty,
            'location': self.location,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ToolCreate:
    """Данные для создания инструмента"""
    inner_code: str
    articul: str
    type: str = ""
    diameter: str = ""
    length: str = ""
    brand: str = ""
    analog: str = ""
    qty_total: int = 0
    min_qty: int = 0


@dataclass
class ToolUpdate:
    """Данные для обновления инструмента"""
    inner_code: Optional[str] = None
    articul: Optional[str] = None
    type: Optional[str] = None
    diameter: Optional[str] = None
    length: Optional[str] = None
    brand: Optional[str] = None
    analog: Optional[str] = None
    qty_total: Optional[int] = None
    min_qty: Optional[int] = None
    location: Optional[str] = None