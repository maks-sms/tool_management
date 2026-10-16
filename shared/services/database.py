# shared/services/database.py
"""
Обёртка над server.database.db_manager.
Это единственное место в клиенте, где разрешено импортировать server.*.
"""
from server.database.db_manager import (
    DatabaseManager,
    update_database_schema,
    create_default_db,
    init_db,
)
from shared.config import save_db_path, get_db_path

__all__ = [
    "DatabaseManager",
    "update_database_schema",
    "create_default_db",
    "init_db",
    "save_db_path",
    "get_db_path",
]