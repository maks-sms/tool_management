# server/services/request_service.py
from typing import List, Optional, Dict
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.request import PurchaseRequest, PurchaseRequestStatus
from server.repositories.request_repository import PurchaseRequestRepository
from server.services.tool_service import ToolService
from server.services.history_service import HistoryService
from shared.utils import now_long


class PurchaseRequestService:
    """Сервис для работы с заявками на закупку (обычные заявки)."""

    def __init__(self, db_path: str = None):
        self.repository = PurchaseRequestRepository(db_path)
        self.tool_service = ToolService(db_path)
        self.history_service = HistoryService(db_path)

    def get_all(self, filters: Dict[str, str] = None) -> List[PurchaseRequest]:
        """Получение всех заявок с фильтрацией."""
        return self.repository.get_all(filters)

    def get_by_id(self, request_id: int) -> Optional[PurchaseRequest]:
        """Получение заявки по ID."""
        return self.repository.get_by_id(request_id)

    def create(self, tool_id: int, tool_code: str, tool_articul: str,
               requested_qty: int, reason: str, requester_id: int,
               requester_name: str, tool_type: str = "", tool_diameter: str = "",
               tool_brand: str = "", comment: str = "") -> Optional[PurchaseRequest]:
        """Создание новой заявки."""
        request_data = {
            'tool_id': tool_id,
            'tool_code': tool_code,
            'tool_articul': tool_articul,
            'tool_type': tool_type,
            'tool_diameter': tool_diameter,
            'tool_brand': tool_brand,
            'requested_qty': requested_qty,
            'reason': reason,
            'requester_id': requester_id,
            'requester_name': requester_name,
            'request_date': now_long(),
            'status': PurchaseRequestStatus.PENDING.value,
            'comment': comment
        }
        return self.repository.create(request_data)

    def take_to_work(self, request_id: int, processor: str) -> bool:
        """Взять заявку в работу."""
        return self.repository.update_status(
            request_id, PurchaseRequestStatus.IN_PROGRESS.value, processor, now_long()
        )

    def receive_partial(self, request_id: int, receive_qty: int,
                        processor: str, comment: str = None) -> bool:
        """Частичное поступление по заявке (атомарно)."""
        request = self.get_by_id(request_id)
        if not request:
            return False

        if receive_qty <= 0:
            return False

        new_received = request.received_qty + receive_qty
        is_complete = new_received >= request.requested_qty

        return self.repository.update_received_qty_and_status(
            request_id,
            received_qty=new_received,
            status=PurchaseRequestStatus.COMPLETED.value if is_complete else request.status,
            processed_by=processor if is_complete else None,
            processed_date=now_long() if is_complete else None,
            comment=comment,
        )

    def complete(self, request_id: int, processor: str) -> bool:
        """Выполнение заявки (только для полностью поступивших)."""
        request = self.get_by_id(request_id)
        if not request or request.received_qty < request.requested_qty:
            return False

        return self.repository.update_status(
            request_id, PurchaseRequestStatus.COMPLETED.value, processor, now_long()
        )

    def reject(self, request_id: int, processor: str) -> bool:
        """Отклонение заявки."""
        return self.repository.update_status(
            request_id, PurchaseRequestStatus.REJECTED.value, processor, now_long()
        )

    def update(self, request_id: int, requested_qty: int = None,
               reason: str = None, comment: str = None) -> bool:
        """Редактирование заявки."""
        request = self.get_by_id(request_id)
        if not request:
            return False

        if request.status not in [
            PurchaseRequestStatus.PENDING.value,
            PurchaseRequestStatus.IN_PROGRESS.value,
        ]:
            return False

        fields = {}
        if requested_qty is not None:
            fields['requested_qty'] = requested_qty
        if reason is not None:
            fields['reason'] = reason
        if comment is not None:
            fields['comment'] = comment

        if not fields:
            return True

        return self.repository.update_fields(request_id, **fields)

    def delete(self, request_id: int) -> bool:
        """Удаление заявки."""
        return self.repository.delete(request_id)