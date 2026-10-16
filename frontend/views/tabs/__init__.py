# frontend/views/tabs/__init__.py
from .base_tab import BaseTab
from .inventory_tab import InventoryTab
from .machines_tab import MachinesTab
from .reserve_tab import ReserveTab
from .history_tab import HistoryTab
from .requests_tab import RequestsTab
from .export_tab import ExportTab

__all__ = [
    'BaseTab',
    'InventoryTab',
    'MachinesTab',
    'ReserveTab',
    'HistoryTab',
    'RequestsTab',
    'ExportTab',
]