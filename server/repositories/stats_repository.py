# server/repositories/stats_repository.py
from typing import Dict, Any
from .base_repository import BaseRepository
from shared.config import LOCATION_RESERVE, LOCATION_MACHINE_PREFIX


class StatsRepository(BaseRepository):
    """Репозиторий для агрегированной статистики.
    
    Не является CRUD-репозиторием, поэтому абстрактные методы
    BaseRepository переопределены как NotImplementedError.
    """

    def get_by_id(self, id):
        raise NotImplementedError("StatsRepository не работает с сущностями по id")

    def get_all(self):
        raise NotImplementedError("StatsRepository не возвращает список сущностей")

    def delete(self, id):
        raise NotImplementedError("StatsRepository не удаляет сущности")

    def get_inventory_stats(self) -> Dict[str, Any]:
        total_qty = (self._execute(
            "SELECT COALESCE(SUM(qty_total), 0) FROM tools", fetch_one=True
        ) or (0,))[0]
        total_items = (self._execute(
            "SELECT COUNT(*) FROM tools", fetch_one=True
        ) or (0,))[0]
        zero_stock = (self._execute(
            "SELECT COUNT(*) FROM tools WHERE qty_total = 0", fetch_one=True
        ) or (0,))[0]
        low_stock = (self._execute(
            "SELECT COUNT(*) FROM tools "
            "WHERE qty_total <= min_qty AND min_qty > 0",
            fetch_one=True,
        ) or (0,))[0]
        return {
            'total_qty': total_qty,
            'total_items': total_items,
            'zero_stock': zero_stock,
            'low_stock': low_stock,
        }

    def get_machines_stats(self) -> Dict[str, Any]:
        total_machines = (self._execute(
            "SELECT COUNT(*) FROM machines", fetch_one=True
        ) or (0,))[0]
        tools_on_machines = (self._execute(
            "SELECT COALESCE(SUM(qty), 0) FROM placement WHERE location LIKE ?",
            (f"{LOCATION_MACHINE_PREFIX}%",), fetch_one=True,
        ) or (0,))[0]
        return {
            'total_machines': total_machines,
            'tools_on_machines': tools_on_machines,
        }

    def get_reserve_stats(self) -> Dict[str, Any]:
        tools_in_reserve = (self._execute(
            "SELECT COALESCE(SUM(qty), 0) FROM placement WHERE location = ?",
            (LOCATION_RESERVE,), fetch_one=True,
        ) or (0,))[0]
        tasks_count = (self._execute(
            "SELECT COUNT(DISTINCT note) FROM placement WHERE location = ?",
            (LOCATION_RESERVE,), fetch_one=True,
        ) or (0,))[0]
        return {
            'tools_in_reserve': tools_in_reserve,
            'tasks_count': tasks_count,
        }

    def get_requests_stats(self) -> Dict[str, Any]:
        active_requests = (self._execute(
            "SELECT COUNT(*) FROM purchase_requests "
            "WHERE status IN ('pending', 'in_progress')",
            fetch_one=True,
        ) or (0,))[0]
        try:
            active_group_requests = (self._execute(
                "SELECT COUNT(*) FROM group_requests "
                "WHERE status IN ('pending', 'in_progress')",
                fetch_one=True,
            ) or (0,))[0]
        except Exception:
            active_group_requests = 0
        return {
            'active_requests': active_requests,
            'active_group_requests': active_group_requests,
        }