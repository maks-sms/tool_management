# shared/models/request.py
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

class PurchaseRequestStatus(Enum):
    """Статусы заявок на закупку"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"

    @classmethod
    def from_string(cls, value: str) -> 'PurchaseRequestStatus':
        for status in cls:
            if status.value == value:
                return status
        return cls.PENDING

    def display_name(self) -> str:
        names = {
            "pending": "🟡 Ожидает",
            "in_progress": "🟠 В работе",
            "completed": "🟢 Выполнена",
            "rejected": "🔴 Отклонена"
        }
        return names.get(self.value, self.value)


@dataclass
class PurchaseRequest:
    """Модель заявки на закупку"""
    id: Optional[int] = None
    tool_id: int = 0
    tool_code: str = ""
    tool_articul: str = ""
    tool_type: str = ""
    tool_diameter: str = ""
    tool_brand: str = ""
    requested_qty: int = 0
    received_qty: int = 0
    reason: str = ""
    requester_id: int = 0
    requester_name: str = ""
    request_date: str = ""
    status: str = "pending"
    processed_by: str = ""
    processed_date: str = ""
    comment: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'PurchaseRequest':
        return cls(
            id=row[0],
            tool_code=row[1] if len(row) > 1 else "",
            tool_articul=row[2] if len(row) > 2 else "",
            tool_type=row[3] if len(row) > 3 else "",
            tool_diameter=row[4] if len(row) > 4 else "",
            tool_brand=row[5] if len(row) > 5 else "",
            requested_qty=row[6] if len(row) > 6 else 0,
            received_qty=row[7] if len(row) > 7 else 0,
            reason=row[8] if len(row) > 8 else "",
            requester_name=row[9] if len(row) > 9 else "",
            request_date=row[10] if len(row) > 10 else "",
            status=row[11] if len(row) > 11 else "pending",
            comment=row[12] if len(row) > 12 else ""
        )

    def remaining_qty(self) -> int:
        return self.requested_qty - self.received_qty

    def is_completed(self) -> bool:
        return self.remaining_qty() <= 0


@dataclass
class GroupRequest:
    """Модель групповой заявки"""
    id: Optional[int] = None
    request_number: str = ""
    name: str = ""
    reason: str = ""
    comment: str = ""
    requester_id: int = 0
    requester_name: str = ""
    request_date: str = ""
    status: str = "pending"
    processed_by: str = ""
    processed_date: str = ""
    # Агрегаты по позициям (заполняются через JOIN, могут быть None):
    items_count: int = 0
    total_qty: int = 0
    received_qty: int = 0

    @classmethod
    def from_db_row(cls, row: tuple) -> 'GroupRequest':
        return cls(
            id=row[0],
            request_number=row[1] if len(row) > 1 else "",
            name=row[2] if len(row) > 2 else "",
            reason=row[3] if len(row) > 3 else "",
            comment=row[4] if len(row) > 4 else "",
            requester_id=row[5] if len(row) > 5 else 0,
            requester_name=row[6] if len(row) > 6 else "",
            request_date=row[7] if len(row) > 7 else "",
            status=row[8] if len(row) > 8 else "pending",
            processed_by=row[9] if len(row) > 9 else "",
            processed_date=row[10] if len(row) > 10 else "",
            items_count=row[11] if len(row) > 11 else 0,
            total_qty=row[12] if len(row) > 12 else 0,
            received_qty=row[13] if len(row) > 13 else 0,
        )


@dataclass
class GroupRequestItem:
    """Модель позиции групповой заявки"""
    id: Optional[int] = None
    group_request_id: int = 0
    tool_id: int = 0
    tool_code: str = ""
    tool_articul: str = ""
    tool_type: str = ""
    tool_diameter: str = ""
    tool_brand: str = ""
    requested_qty: int = 0
    received_qty: int = 0
    status: str = "pending"
    comment: str = ""