# server/services/tool_service.py
from datetime import datetime
from typing import List, Optional, Dict, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.tool import Tool, ToolCreate, ToolUpdate
from server.repositories.tool_repository import ToolRepository


class ToolService:
    """Сервис для работы с инструментами"""

    def __init__(self, db_path: str = None):
        self.repository = ToolRepository(db_path)

    def get_all(self, filters: Dict[str, str] = None) -> List[Tool]:
        """Получение всех инструментов с фильтрацией"""
        return self.repository.get_all(filters)

    def get_by_id(self, tool_id: int) -> Optional[Tool]:
        """Получение инструмента по ID"""
        return self.repository.get_by_id(tool_id)

    def get_by_code(self, inner_code: str) -> Optional[Tool]:
        """Получение инструмента по коду"""
        return self.repository.get_by_code(inner_code)

    def create(self, tool_data: ToolCreate) -> Optional[Tool]:
        """Создание нового инструмента"""
        # Проверяем, существует ли инструмент с таким кодом
        existing = self.repository.get_by_code(tool_data.inner_code)
        if existing:
            raise Exception(f"Инструмент с кодом {tool_data.inner_code} уже существует")

        return self.repository.create(tool_data)

    def update(self, tool_id: int, tool_data: ToolUpdate) -> Optional[Tool]:
        """Обновление инструмента"""
        existing = self.repository.get_by_id(tool_id)
        if not existing:
            return None

        # Если меняется код, проверяем уникальность
        if tool_data.inner_code and tool_data.inner_code != existing.inner_code:
            code_exists = self.repository.get_by_code(tool_data.inner_code)
            if code_exists:
                raise Exception(f"Инструмент с кодом {tool_data.inner_code} уже существует")

        return self.repository.update(tool_id, tool_data)

    def update_quantity(self, tool_id: int, delta: int) -> Optional[Tool]:
        """Обновление количества инструмента"""
        return self.repository.update_quantity(tool_id, delta)

    def delete(self, tool_id: int) -> bool:
        """Удаление инструмента"""
        return self.repository.delete(tool_id)

    def get_next_inner_code(self) -> str:
        """Генерация следующего внутреннего кода"""
        return self.repository.get_next_inner_code()

    def get_unique_types(self) -> List[str]:
        """Получение уникальных типов инструментов"""
        return self.repository.get_unique_types()

    def get_unique_brands(self) -> List[str]:
        """Получение уникальных производителей"""
        return self.repository.get_unique_brands()