# server/services/stats_service.py
from typing import Dict, Any
from server.repositories.stats_repository import StatsRepository


class StatsService:
    """Сервис для получения статистики."""

    def __init__(self, db_path: str = None):
        self.repository = StatsRepository(db_path)

    def get_inventory_stats(self) -> Dict[str, Any]:
        return self.repository.get_inventory_stats()

    def get_machines_stats(self) -> Dict[str, Any]:
        return self.repository.get_machines_stats()

    def get_reserve_stats(self) -> Dict[str, Any]:
        return self.repository.get_reserve_stats()

    def get_requests_stats(self) -> Dict[str, Any]:
        return self.repository.get_requests_stats()