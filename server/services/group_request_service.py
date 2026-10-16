# server/services/group_request_service.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.request import GroupRequest, GroupRequestItem, PurchaseRequestStatus
from server.repositories.request_repository import GroupRequestRepository, GroupRequestItemRepository
from server.services.tool_service import ToolService
from server.services.history_service import HistoryService
from shared.utils import now_long

class GroupRequestServiceExtended:
    """
    Расширенный сервис для работы с групповыми заявками.
    Содержит бизнес-логику, которая раньше была в main_window.py.
    """

    def __init__(self, db_path: str = None):
        self.repository = GroupRequestRepository(db_path)
        self.item_repository = GroupRequestItemRepository(db_path)
        self.tool_service = ToolService(db_path)
        self.history_service = HistoryService(db_path)

    def get_by_id(self, group_id: int) -> Optional[GroupRequest]:
        """Получение групповой заявки по ID"""
        return self.repository.get_by_id(group_id)

    def get_items(self, group_id: int) -> List[Tuple]:
        """Получение всех позиций групповой заявки"""
        return self.item_repository.get_by_group_id(group_id)

    def get_pending_items(self, group_id: int) -> List[Tuple]:
        """Получение невыполненных позиций"""
        return self.item_repository.get_pending_items(group_id)

    def get_summary(self, group_id: int) -> Tuple:
        """Получение сводки по групповой заявке"""
        return self.item_repository.get_summary(group_id)

    def get_all(self, filters: Dict[str, str] = None) -> List[GroupRequest]:
        """Получение всех групповых заявок (без агрегатов)."""
        return self.repository.get_all(filters)

    def get_all_with_summary(self, filters: Dict[str, str] = None) -> List[GroupRequest]:
        """Получение всех групповых заявок с агрегатами по позициям."""
        return self.repository.get_all_with_summary(filters)

    def create(self, name: str, requester_id: int, requester_name: str,
               items: List[Dict], reason: str = "", comment: str = "") -> Optional[int]:
        """Создание групповой заявки.

        :param items: список dict с ключами inner_code, articul, type,
                      diameter, brand, requested_qty
        :return: id созданной заявки или None
        """
        request_number = self._generate_request_number()
        request_date = now_long()

        group_data = {
            'request_number': request_number,
            'name': name,
            'reason': reason,
            'comment': comment,
            'requester_id': requester_id,
            'requester_name': requester_name,
            'request_date': request_date,
            'status': PurchaseRequestStatus.PENDING.value,
        }

        group_id = self.repository.create(group_data)
        if not group_id:
            return None

        for item in items:
            tool = self.tool_service.get_by_code(item['inner_code'])
            if not tool:
                continue

            item_data = {
                'group_request_id': group_id,
                'tool_id': tool.id,
                'tool_code': item['inner_code'],
                'tool_articul': item['articul'],
                'tool_type': item.get('type', ''),
                'tool_diameter': item.get('diameter', ''),
                'tool_brand': item.get('brand', ''),
                'requested_qty': item.get('requested_qty', 1),
                'status': PurchaseRequestStatus.PENDING.value,
            }
            self.item_repository.create(item_data)

        return group_id

    def _generate_request_number(self) -> str:
        """Генерация уникального номера групповой заявки вида GR-YYYYMMDD-NNN."""
        today = datetime.now().strftime("%Y%m%d")

        # Последний номер среди сегодняшних заявок
        row = self.repository._execute(
            "SELECT request_number FROM group_requests "
            "WHERE request_number LIKE ? "
            "ORDER BY request_number DESC LIMIT 1",
            (f"GR-{today}%",),
            fetch_one=True,
        )

        if not row or not row[0]:
            return f"GR-{today}-001"

        try:
            num = int(row[0].split('-')[2])
            return f"GR-{today}-{num + 1:03d}"
        except (IndexError, ValueError):
            return f"GR-{today}-001"

    def take_to_work(self, group_id: int, processor: str) -> bool:
        """Взять групповую заявку в работу"""
        # Обновляем статус групповой заявки
        result = self.repository.update_status(
            group_id, PurchaseRequestStatus.IN_PROGRESS.value, processor, now_long()
        )

        items = self.get_items(group_id)
        for item in items:
            if item[9] == PurchaseRequestStatus.PENDING.value:  # status
                self.item_repository.update_received_qty(
                    item[0], item[8], status=PurchaseRequestStatus.IN_PROGRESS.value
                )

        return result

    def receive_item(self, group_id: int, item_id: int, receive_qty: int,
                     processor: str, comment: str = None) -> Dict:
        """Поступление по позиции групповой заявки"""
        # Получаем позицию
        item = self.item_repository.get_by_id(item_id)
        if not item:
            return {'success': False, 'message': 'Позиция не найдена'}

        item_id, tool_id, tool_code, tool_articul, tool_type, tool_diameter, \
            tool_brand, requested_qty, received_qty, status, item_comment = item

        if status not in (PurchaseRequestStatus.PENDING.value, PurchaseRequestStatus.IN_PROGRESS.value):
            return {
                'success': False,
                'message': f'Нельзя поступить по позиции в статусе "{status}"'
            }

        remaining_qty = requested_qty - received_qty
        if remaining_qty <= 0:
            return {'success': False, 'message': 'Позиция уже полностью выполнена'}

        if receive_qty > remaining_qty:
            return {'success': False, 'message': f'Нельзя поступить больше {remaining_qty} шт.'}

        new_received = received_qty + receive_qty
        new_status = PurchaseRequestStatus.COMPLETED.value if new_received >= requested_qty else PurchaseRequestStatus.IN_PROGRESS.value

        # Обновляем количество инструмента на складе
        self.tool_service.update_quantity(tool_id, receive_qty)

        # Обновляем позицию
        self.item_repository.update_received_qty(item_id, new_received, new_status, comment)

        # Проверяем, все ли позиции выполнены
        pending_items = self.item_repository.get_pending_items(group_id)

        group_completed = False
        if not pending_items:
            # Все позиции выполнены - закрываем групповую заявку
            self.repository.update_status(
                group_id, PurchaseRequestStatus.COMPLETED.value, processor, now_long()
            )
            group_completed = True

        # Запись в историю
        group = self.get_by_id(group_id)
        group_name = group.name if group else "Групповая заявка"

        self.history_service.add_record(
            tool_code,
            "ПОСТУПЛЕНИЕ ПО ГРУППОВОЙ ЗАЯВКЕ",
            receive_qty,
            f"Групповая заявка: {group_name} | Позиция: {tool_code}",
            processor
        )

        return {
            'success': True,
            'message': f'Позиция {"полностью выполнена" if new_status == PurchaseRequestStatus.COMPLETED.value else "частично выполнена"}',
            'group_completed': group_completed
        }

    def complete(self, group_id: int, processor: str) -> bool:
        """Выполнение групповой заявки"""
        # Проверяем, все ли позиции выполнены
        pending_items = self.item_repository.get_pending_items(group_id)

        if pending_items:
            return False

        return self.repository.update_status(
            group_id, PurchaseRequestStatus.COMPLETED.value, processor, now_long()
        )

    def reject(self, group_id: int, processor: str) -> bool:
        """Отклонение групповой заявки"""
        result = self.repository.update_status(
            group_id, PurchaseRequestStatus.REJECTED.value, processor, now_long()
        )

        items = self.get_items(group_id)
        for item in items:
            self.item_repository.update_received_qty(
                item[0], item[8], status=PurchaseRequestStatus.REJECTED.value
            )

        return result

    def delete(self, group_id: int) -> bool:
        """Удаление групповой заявки"""
        return self.repository.delete(group_id)

    def update_info(self, group_id: int, name: str = None, reason: str = None,
                    comment: str = None) -> bool:
        """Обновление информации о групповой заявке"""
        return self.repository.update_info(group_id, name, reason, comment)

    def update_item_qty(self, item_id: int, requested_qty: int) -> bool:
        """Обновление количества в позиции"""
        return self.item_repository.update_requested_qty(item_id, requested_qty)

    def add_item(self, group_id: int, tool_info: Dict, requested_qty: int) -> bool:
        """Добавление позиции в групповую заявку"""
        tool = self.tool_service.get_by_code(tool_info['inner_code'])
        if not tool:
            return False

        item_data = {
            'group_request_id': group_id,
            'tool_id': tool.id,
            'tool_code': tool_info['inner_code'],
            'tool_articul': tool_info['articul'],
            'tool_type': tool_info.get('type', ''),
            'tool_diameter': tool_info.get('diameter', ''),
            'tool_brand': tool_info.get('brand', ''),
            'requested_qty': requested_qty,
            'status': PurchaseRequestStatus.PENDING.value
        }
        return self.item_repository.create(item_data) is not None

    def remove_item(self, item_id: int) -> bool:
        """Удаление позиции из групповой заявки"""
        return self.item_repository.delete(item_id)

    def get_item_by_id(self, item_id: int) -> Optional[Tuple]:
        """Получение позиции по ID"""
        return self.item_repository.get_by_id(item_id)