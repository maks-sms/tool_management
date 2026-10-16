# server/services/placement_service.py
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import LOCATION_MACHINE_PREFIX, LOCATION_RESERVE
from shared.models.placement import PlacementCreate
from server.repositories.placement_repository import PlacementRepository
from server.repositories.tool_repository import ToolRepository
from server.repositories.history_repository import HistoryRepository
from server.services.tool_service import ToolService
from server.services.machine_service import MachineService
from server.database.db_manager import DatabaseManager
from shared.utils import now_full


class PlacementService:
    """Сервис для работы с размещениями инструментов (станки, резерв)."""

    def __init__(self, db_path: str = None):
        self.repository = PlacementRepository(db_path)
        self.tool_repository = ToolRepository(db_path)
        self.history_repository = HistoryRepository(db_path)
        self.tool_service = ToolService(db_path)
        self.machine_service = MachineService(db_path)

    # ---------- Чтение ----------

    def get_machines_placements(self) -> List[tuple]:
        """Все размещения на станках."""
        return self.repository.get_by_location(f"{LOCATION_MACHINE_PREFIX}%")

    def get_reserve_placements(self) -> List[tuple]:
        """Все размещения в резерве."""
        return self.repository.get_by_location(LOCATION_RESERVE)

    # ---------- Операции (атомарные) ----------

    def move_to_machine(self, tool_id: int, tool_code: str, qty: int,
                        machine: str, worker: str) -> bool:
        """Перемещение инструмента на станок."""
        if qty <= 0:
            return False

        tool = self.tool_service.get_by_id(tool_id)
        if not tool or tool.qty_total < qty:
            return False

        now = now_full()
        location = f"{LOCATION_MACHINE_PREFIX}{machine}"

        with DatabaseManager.transaction() as conn:
            # 1. Списываем со склада
            self.tool_repository.update_quantity_with_conn(conn, tool_id, -qty)

            # 2. Размещение: обновляем или создаём
            existing = self.repository._execute(
                "SELECT id, qty FROM placement "
                "WHERE tool_id = ? AND note = ? AND location = ?",
                (tool_id, machine, location), fetch_one=True,
            )
            if existing:
                self.repository._execute(
                    "UPDATE placement SET qty = ?, date = ? WHERE id = ?",
                    (existing[1] + qty, now, existing[0]), commit=True,
                )
            else:
                self.repository.create_with_conn(
                    conn,
                    PlacementCreate(
                        tool_id=tool_id, location=location, qty=qty,
                        note=machine, date=now,
                    ),
                )

            # 3. История
            self.history_repository.add_with_conn(
                conn, tool_code, "Выдача на станок", qty, machine, worker,
            )

        return True

    def move_to_reserve(self, tool_id: int, tool_code: str, qty: int,
                        task: str, worker: str) -> bool:
        """Перемещение инструмента в резерв."""
        if qty <= 0:
            return False

        tool = self.tool_service.get_by_id(tool_id)
        if not tool or tool.qty_total < qty:
            return False

        now = now_full()
        location = LOCATION_RESERVE

        with DatabaseManager.transaction() as conn:
            self.tool_repository.update_quantity_with_conn(conn, tool_id, -qty)

            existing = self.repository._execute(
                "SELECT id, qty FROM placement "
                "WHERE tool_id = ? AND note = ? AND location = ?",
                (tool_id, task, location), fetch_one=True,
            )
            if existing:
                self.repository._execute(
                    "UPDATE placement SET qty = ?, date = ? WHERE id = ?",
                    (existing[1] + qty, now, existing[0]), commit=True,
                )
            else:
                self.repository.create_with_conn(
                    conn,
                    PlacementCreate(
                        tool_id=tool_id, location=location, qty=qty,
                        note=task, date=now,
                    ),
                )

            self.history_repository.add_with_conn(
                conn, tool_code, "Перемещение в резерв", qty, task, worker,
            )

        return True

    def return_from_placement(self, placement_id: int, tool_id: int,
                              tool_code: str, qty: int, worker: str) -> bool:
        """Возврат инструмента на склад."""
        if qty <= 0:
            return False

        placement = self.repository.get_by_id(placement_id)
        if not placement or placement.qty < qty:
            return False

        with DatabaseManager.transaction() as conn:
            # Уменьшаем или удаляем размещение
            if placement.qty - qty <= 0:
                self.repository._execute(
                    "DELETE FROM placement WHERE id = ?",
                    (placement_id,), commit=True,
                )
            else:
                self.repository._execute(
                    "UPDATE placement SET qty = ? WHERE id = ?",
                    (placement.qty - qty, placement_id), commit=True,
                )

            # Увеличиваем склад
            self.tool_repository.update_quantity_with_conn(conn, tool_id, qty)

            # История
            self.history_repository.add_with_conn(
                conn, tool_code, "Возврат на склад", qty, "Склад", worker,
            )

        return True

    def transfer_to_machine(self, from_placement_id: int, tool_id: int,
                            tool_code: str, qty: int, new_machine: str,
                            worker: str) -> bool:
        """Передача инструмента с одного станка на другой."""
        if qty <= 0:
            return False

        placement = self.repository.get_by_id(from_placement_id)
        if not placement or placement.qty < qty:
            return False

        now = now_full()
        old_note = placement.note or ""
        new_location = f"{LOCATION_MACHINE_PREFIX}{new_machine}"

        with DatabaseManager.transaction() as conn:
            # Уменьшаем старое размещение
            if placement.qty - qty <= 0:
                self.repository._execute(
                    "DELETE FROM placement WHERE id = ?",
                    (from_placement_id,), commit=True,
                )
            else:
                self.repository._execute(
                    "UPDATE placement SET qty = ? WHERE id = ?",
                    (placement.qty - qty, from_placement_id), commit=True,
                )

            # Увеличиваем или создаём новое
            existing = self.repository._execute(
                "SELECT id, qty FROM placement "
                "WHERE tool_id = ? AND note = ? AND location = ?",
                (tool_id, new_machine, new_location), fetch_one=True,
            )
            if existing:
                self.repository._execute(
                    "UPDATE placement SET qty = ?, date = ? WHERE id = ?",
                    (existing[1] + qty, now, existing[0]), commit=True,
                )
            else:
                self.repository._execute(
                    "INSERT INTO placement (tool_id, location, qty, note, date) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (tool_id, new_location, qty, new_machine, now), commit=True,
                )

            # История
            self.history_repository.add_with_conn(
                conn, tool_code, "Передача на станок", qty,
                f"{old_note} → {new_machine}", worker,
            )

        return True

    def writeoff_from_placement(self, placement_id: int, tool_id: int,
                                tool_code: str, qty: int, reason: str,
                                additional_comment: str, worker: str,
                                is_machine: bool = True) -> bool:
        """Списание инструмента со станка или из резерва."""
        if qty <= 0:
            return False

        placement = self.repository.get_by_id(placement_id)
        if not placement or placement.qty < qty:
            return False

        with DatabaseManager.transaction() as conn:
            # Уменьшаем или удаляем размещение
            if placement.qty - qty <= 0:
                self.repository._execute(
                    "DELETE FROM placement WHERE id = ?",
                    (placement_id,), commit=True,
                )
            else:
                self.repository._execute(
                    "UPDATE placement SET qty = ? WHERE id = ?",
                    (placement.qty - qty, placement_id), commit=True,
                )

            # Формируем комментарий
            if is_machine:
                base = f"со станка '{placement.note}'"
            else:
                base = "из резерва"

            full_reason = (
                f"{reason}: {additional_comment} {base}"
                if additional_comment else f"{reason} {base}"
            )

            # История
            self.history_repository.add_with_conn(
                conn, tool_code, "СПИСАНИЕ", qty, full_reason, worker,
            )

        return True