# server/repositories/request_repository.py
from typing import List, Optional, Dict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .base_repository import BaseRepository
from shared.models.request import PurchaseRequest, GroupRequest
from shared.models.request import PurchaseRequest, GroupRequest, PurchaseRequestStatus


_STATUS_MAP = {
    "Ожидает": PurchaseRequestStatus.PENDING.value,
    "В работе": PurchaseRequestStatus.IN_PROGRESS.value,
    "Выполнена": PurchaseRequestStatus.COMPLETED.value,
    "Отклонена": PurchaseRequestStatus.REJECTED.value,
}


class PurchaseRequestRepository(BaseRepository[PurchaseRequest]):
    """Репозиторий для работы с заявками на закупку."""

    _SELECT = """SELECT id, tool_code, tool_articul, tool_type, tool_diameter, tool_brand,
                        requested_qty, received_qty, reason, requester_name, 
                        request_date, status, comment
                 FROM purchase_requests"""

    def get_by_id(self, request_id: int) -> Optional[PurchaseRequest]:
        row = self._execute(f"{self._SELECT} WHERE id = ?", (request_id,), fetch_one=True)
        return PurchaseRequest.from_db_row(row) if row else None

    def get_all(self, filters: Dict[str, str] = None) -> List[PurchaseRequest]:
        filters = filters or {}

        query = f"{self._SELECT} WHERE 1=1"
        params = []

        if filters.get('status'):
            status_value = _STATUS_MAP.get(filters['status'])
            if status_value:
                query += " AND status = ?"
                params.append(status_value)

        if filters.get('search_code'):
            query += " AND (LOWER(tool_code) LIKE ? OR LOWER(tool_articul) LIKE ?)"
            s = f"%{filters['search_code'].lower()}%"
            params.extend([s, s])

        if filters.get('requester'):
            query += " AND LOWER(requester_name) LIKE ?"
            params.append(f"%{filters['requester'].lower()}%")

        query += " ORDER BY id DESC"

        rows = self._execute(query, tuple(params), fetch_all=True)
        return [PurchaseRequest.from_db_row(row) for row in rows] if rows else []

    def create(self, request_data: dict) -> Optional[PurchaseRequest]:
        query = """INSERT INTO purchase_requests
                  (tool_id, tool_code, tool_articul, tool_type, tool_diameter, tool_brand,
                   requested_qty, reason, requester_id, requester_name, request_date, status, comment)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        last_id = self._insert_and_get_id(query, (
            request_data.get('tool_id'),
            request_data.get('tool_code'),
            request_data.get('tool_articul'),
            request_data.get('tool_type', ''),
            request_data.get('tool_diameter', ''),
            request_data.get('tool_brand', ''),
            request_data.get('requested_qty'),
            request_data.get('reason'),
            request_data.get('requester_id'),
            request_data.get('requester_name'),
            request_data.get('request_date'),
            request_data.get('status', PurchaseRequestStatus.PENDING.value),
            request_data.get('comment', ''),
        ))
        return self.get_by_id(last_id)

    def update_status(self, request_id: int, status: str, processed_by: str = None,
                      processed_date: str = None, comment: str = None) -> bool:
        updates = ["status = ?"]
        params = [status]

        if processed_by:
            updates.append("processed_by = ?")
            params.append(processed_by)
        if processed_date:
            updates.append("processed_date = ?")
            params.append(processed_date)
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)

        params.append(request_id)
        query = f"UPDATE purchase_requests SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def update_received_qty(self, request_id: int, received_qty: int, comment: str = None) -> bool:
        if comment is not None:
            self._execute(
                "UPDATE purchase_requests SET received_qty = ?, comment = ? WHERE id = ?",
                (received_qty, comment, request_id),
                commit=True,
            )
        else:
            self._execute(
                "UPDATE purchase_requests SET received_qty = ? WHERE id = ?",
                (received_qty, request_id),
                commit=True,
            )
        return True

    def update_received_qty_and_status(self, request_id: int, received_qty: int,
                                        status: str, processed_by: str = None,
                                        processed_date: str = None,
                                        comment: str = None) -> bool:
        """Атомарно обновляет received_qty и статус одной транзакцией."""
        updates = ["received_qty = ?", "status = ?"]
        params = [received_qty, status]

        if processed_by is not None:
            updates.append("processed_by = ?")
            params.append(processed_by)
        if processed_date is not None:
            updates.append("processed_date = ?")
            params.append(processed_date)
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)

        params.append(request_id)
        query = f"UPDATE purchase_requests SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def update_fields(self, request_id: int, **fields) -> bool:
        """Универсальное обновление полей (для сервиса update)."""
        if not fields:
            return True

        updates = [f"{k} = ?" for k in fields.keys()]
        params = list(fields.values())
        params.append(request_id)

        query = f"UPDATE purchase_requests SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def delete(self, request_id: int) -> bool:
        self._execute("DELETE FROM purchase_requests WHERE id = ?", (request_id,), commit=True)
        return True


class GroupRequestRepository(BaseRepository[GroupRequest]):
    """Репозиторий для работы с групповыми заявками."""

    _SELECT = """SELECT id, request_number, name, reason, comment, requester_id,
                        requester_name, request_date, status, processed_by, processed_date
                 FROM group_requests"""

    def get_by_id(self, group_id: int) -> Optional[GroupRequest]:
        row = self._execute(f"{self._SELECT} WHERE id = ?", (group_id,), fetch_one=True)
        return GroupRequest.from_db_row(row) if row else None

    def get_all(self, filters: Dict[str, str] = None) -> List[GroupRequest]:
        filters = filters or {}

        query = f"{self._SELECT} WHERE 1=1"
        params = []

        if filters.get('status'):
            status_value = _STATUS_MAP.get(filters['status'])
            if status_value:
                query += " AND status = ?"
                params.append(status_value)

        if filters.get('search_number'):
            query += " AND (LOWER(request_number) LIKE ? OR LOWER(name) LIKE ?)"
            s = f"%{filters['search_number'].lower()}%"
            params.extend([s, s])

        if filters.get('requester'):
            query += " AND LOWER(requester_name) LIKE ?"
            params.append(f"%{filters['requester'].lower()}%")

        query += " ORDER BY id DESC"

        rows = self._execute(query, tuple(params), fetch_all=True)
        return [GroupRequest.from_db_row(row) for row in rows] if rows else []

    def get_all_with_summary(self, filters: Dict[str, str] = None) -> List[GroupRequest]:
        """Получение всех групповых заявок с агрегатами по позициям (один SQL).

        Возвращает List[GroupRequest] с заполненными полями:
        items_count, total_qty, received_qty.
        """
        filters = filters or {}

        query = """
            SELECT g.id, g.request_number, g.name, g.reason, g.comment,
                   g.requester_id, g.requester_name, g.request_date, g.status,
                   g.processed_by, g.processed_date,
                   COUNT(i.id)                             AS items_count,
                   COALESCE(SUM(i.requested_qty), 0)       AS total_qty,
                   COALESCE(SUM(IFNULL(i.received_qty, 0)), 0) AS received_qty
            FROM group_requests g
            LEFT JOIN group_request_items i ON i.group_request_id = g.id
            WHERE 1=1
        """
        params = []

        if filters.get('status'):
            status_value = _STATUS_MAP.get(filters['status'])
            if status_value:
                query += " AND g.status = ?"
                params.append(status_value)

        if filters.get('search_number'):
            query += " AND (LOWER(g.request_number) LIKE ? OR LOWER(g.name) LIKE ?)"
            s = f"%{filters['search_number'].lower()}%"
            params.extend([s, s])

        if filters.get('requester'):
            query += " AND LOWER(g.requester_name) LIKE ?"
            params.append(f"%{filters['requester'].lower()}%")

        query += " GROUP BY g.id ORDER BY g.id DESC"

        rows = self._execute(query, tuple(params), fetch_all=True)
        return [GroupRequest.from_db_row(row) for row in rows] if rows else []

    def create(self, group_data: dict) -> Optional[int]:
        query = """INSERT INTO group_requests
                  (request_number, name, reason, comment, requester_id, requester_name, request_date, status)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""

        return self._insert_and_get_id(query, (
            group_data.get('request_number'),
            group_data.get('name'),
            group_data.get('reason', ''),
            group_data.get('comment', ''),
            group_data.get('requester_id'),
            group_data.get('requester_name'),
            group_data.get('request_date'),
            group_data.get('status', PurchaseRequestStatus.PENDING.value),
        ))

    def update_status(self, group_id: int, status: str, processed_by: str = None,
                      processed_date: str = None) -> bool:
        updates = ["status = ?"]
        params = [status]

        if processed_by:
            updates.append("processed_by = ?")
            params.append(processed_by)
        if processed_date:
            updates.append("processed_date = ?")
            params.append(processed_date)

        params.append(group_id)
        query = f"UPDATE group_requests SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def update_info(self, group_id: int, name: str = None, reason: str = None,
                    comment: str = None) -> bool:
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if reason is not None:
            updates.append("reason = ?")
            params.append(reason)
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)

        if not updates:
            return True

        params.append(group_id)
        query = f"UPDATE group_requests SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def delete(self, group_id: int) -> bool:
        self._execute(
            "DELETE FROM group_request_items WHERE group_request_id = ?",
            (group_id,), commit=True,
        )
        self._execute("DELETE FROM group_requests WHERE id = ?", (group_id,), commit=True)
        return True


class GroupRequestItemRepository(BaseRepository):
    """Репозиторий для работы с позициями групповых заявок."""

    _SELECT = """SELECT id, tool_id, tool_code, tool_articul, tool_type, tool_diameter,
                        tool_brand, requested_qty, IFNULL(received_qty, 0) as received_qty,
                        status, comment
                 FROM group_request_items"""

    def get_by_id(self, item_id: int) -> Optional[tuple]:
        return self._execute(f"{self._SELECT} WHERE id = ?", (item_id,), fetch_one=True)

    def get_all(self, limit: int = None) -> List[tuple]:
        query = self._SELECT
        if limit:
            query += f" LIMIT {limit}"
        rows = self._execute(query, fetch_all=True)
        return rows if rows else []

    def get_by_group_id(self, group_id: int) -> List[tuple]:
        rows = self._execute(
            f"{self._SELECT} WHERE group_request_id = ?", (group_id,), fetch_all=True
        )
        return rows if rows else []

    def get_pending_items(self, group_id: int) -> List[tuple]:
        query = """SELECT id, tool_id, tool_code, tool_articul, tool_type, tool_diameter,
                          tool_brand, requested_qty, IFNULL(received_qty, 0) as received_qty, status
                   FROM group_request_items
                   WHERE group_request_id = ? AND IFNULL(received_qty, 0) < requested_qty
                   ORDER BY tool_code"""
        rows = self._execute(query, (group_id,), fetch_all=True)
        return rows if rows else []

    def create(self, item_data: dict) -> Optional[int]:
        query = """INSERT INTO group_request_items
                  (group_request_id, tool_id, tool_code, tool_articul, tool_type,
                   tool_diameter, tool_brand, requested_qty, status, comment)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        return self._insert_and_get_id(query, (
            item_data.get('group_request_id'),
            item_data.get('tool_id'),
            item_data.get('tool_code'),
            item_data.get('tool_articul'),
            item_data.get('tool_type', ''),
            item_data.get('tool_diameter', ''),
            item_data.get('tool_brand', ''),
            item_data.get('requested_qty'),
            item_data.get('status', PurchaseRequestStatus.PENDING.value),
            item_data.get('comment', ''),
        ))

    def update_received_qty(self, item_id: int, received_qty: int,
                            status: str = None, comment: str = None) -> bool:
        updates = ["received_qty = ?"]
        params = [received_qty]

        if status:
            updates.append("status = ?")
            params.append(status)
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)

        params.append(item_id)
        query = f"UPDATE group_request_items SET {', '.join(updates)} WHERE id = ?"
        self._execute(query, tuple(params), commit=True)
        return True

    def update_requested_qty(self, item_id: int, requested_qty: int) -> bool:
        self._execute(
            "UPDATE group_request_items SET requested_qty = ? WHERE id = ?",
            (requested_qty, item_id),
            commit=True,
        )
        return True

    def update_status_by_group(self, group_id: int, status: str) -> bool:
        self._execute(
            "UPDATE group_request_items SET status = ? "
            "WHERE group_request_id = ? AND status = 'pending'",
            (status, group_id),
            commit=True,
        )
        return True

    def delete(self, item_id: int) -> bool:
        self._execute("DELETE FROM group_request_items WHERE id = ?", (item_id,), commit=True)
        return True

    def delete_by_group_id(self, group_id: int) -> bool:
        self._execute(
            "DELETE FROM group_request_items WHERE group_request_id = ?",
            (group_id,), commit=True,
        )
        return True

    def get_summary(self, group_id: int) -> tuple:
        query = """SELECT COUNT(*),
                        COALESCE(SUM(requested_qty), 0),
                        COALESCE(SUM(IFNULL(received_qty, 0)), 0)
                FROM group_request_items WHERE group_request_id = ?"""
        row = self._execute(query, (group_id,), fetch_one=True)
        return row if row else (0, 0, 0)