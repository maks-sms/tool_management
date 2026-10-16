# server/services/view_services.py
"""Сервисы для работы с представлениями (вкладками)"""
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.services.tool_service import ToolService
from server.services.placement_service import PlacementService
from server.services.history_service import HistoryService
from server.services import PurchaseRequestService, GroupRequestService
from shared.models.tool import Tool
from shared.models.history import HistoryRecord
from shared.models.request import PurchaseRequest, GroupRequest


class InventoryViewService:
    """Сервис для получения данных для вкладки склада"""

    def __init__(self, db_path: str = None):
        self.tool_service = ToolService(db_path)

    def get_tools_with_filters(self, search_art: str = "", tool_type: str = "",
                                brand: str = "", diameter: str = "",
                                sort_col: str = "inner_code",
                                sort_desc: bool = False) -> List[Tool]:
        """Получение инструментов с фильтрацией и сортировкой"""
        filters = {}

        if search_art and search_art != "%%" and search_art.strip():
            filters['search'] = search_art.strip()

        if tool_type and tool_type != "%%" and tool_type.strip():
            filters['type'] = tool_type.strip()

        if brand and brand != "%%" and brand.strip():
            filters['brand'] = brand.strip()

        if diameter and diameter != "%%" and diameter.strip():
            filters['diameter'] = diameter.strip()

        tools = self.tool_service.get_all(filters)

        # Сортировка
        reverse = sort_desc
        if sort_col == "inner_code":
            tools.sort(key=lambda x: x.inner_code, reverse=reverse)
        elif sort_col == "articul":
            tools.sort(key=lambda x: x.articul, reverse=reverse)
        elif sort_col == "type":
            tools.sort(key=lambda x: x.type or "", reverse=reverse)
        elif sort_col == "diameter":
            tools.sort(key=lambda x: x.diameter or "", reverse=reverse)
        elif sort_col == "brand":
            tools.sort(key=lambda x: x.brand or "", reverse=reverse)
        elif sort_col == "qty_total":
            tools.sort(key=lambda x: x.qty_total, reverse=reverse)

        return tools

    def get_unique_types(self) -> List[str]:
        """Получение уникальных типов"""
        return self.tool_service.get_unique_types()

    def get_unique_brands(self) -> List[str]:
        """Получение уникальных производителей"""
        return self.tool_service.get_unique_brands()


class MachinesViewService:
    """Сервис для получения данных для вкладки станков"""

    def __init__(self, db_path: str = None):
        self.placement_service = PlacementService(db_path)

    def get_machines_placements(self) -> List[Tuple]:
        """Получение размещений на станках"""
        return self.placement_service.get_machines_placements()


class ReserveViewService:
    """Сервис для получения данных для вкладки резерва"""

    def __init__(self, db_path: str = None):
        self.placement_service = PlacementService(db_path)

    def get_reserve_placements(self) -> List[Tuple]:
        """Получение размещений в резерве"""
        return self.placement_service.get_reserve_placements()


class HistoryViewService:
    """Сервис для получения данных для вкладки истории"""

    def __init__(self, db_path: str = None):
        self.history_service = HistoryService(db_path)

    def get_history_records(self, limit: int = 500) -> List[HistoryRecord]:
        """Получение записей истории"""
        return self.history_service.get_all(limit)


class RequestsViewService:
    """Сервис для получения данных для вкладки заявок"""

    def __init__(self, db_path: str = None):
        self.purchase_service = PurchaseRequestService(db_path)
        self.group_service = GroupRequestService(db_path)

    def get_all_requests(self, filters: Dict[str, str] = None) -> Tuple[List[PurchaseRequest], List[GroupRequest]]:
        """Получение всех заявок (обычных и групповых).

        Групповые заявки возвращаются с уже посчитанными агрегатами
        (items_count, total_qty, received_qty) — одним SQL-запросом.
        """
        filters = filters or {}

        # Получаем обычные заявки
        purchase_filters = {}
        if filters.get('search_code'):
            purchase_filters['search_code'] = filters['search_code']
        if filters.get('requester'):
            purchase_filters['requester'] = filters['requester']
        if filters.get('status') and filters['status'] != "Все":
            purchase_filters['status'] = filters['status']

        purchase_requests = self.purchase_service.get_all(purchase_filters)

        # Получаем групповые заявки — ОДНИМ запросом с агрегатами
        group_filters = {}
        if filters.get('search_number'):
            group_filters['search_number'] = filters['search_number']
        if filters.get('requester'):
            group_filters['requester'] = filters['requester']
        if filters.get('status') and filters['status'] != "Все":
            group_filters['status'] = filters['status']

        group_requests = self.group_service.get_all_with_summary(group_filters)

        return purchase_requests, group_requests