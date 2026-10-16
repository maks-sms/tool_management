# server/repositories/base_repository.py
from typing import List, Optional, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.config import get_current_db_path
from server.database.db_manager import DatabaseManager

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Базовый репозиторий.

    Все операции идут через DatabaseManager (WAL, retry, единые таймауты).
    Прямое `sqlite3.connect` здесь больше не используется.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_current_db_path()

    def _execute(
        self,
        query: str,
        params: tuple = None,
        *,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False,
        return_last_id: bool = False,
        as_dict: bool = False,
    ) -> Any:
        """Обёртка над DatabaseManager.execute_query()."""
        return DatabaseManager.execute_query(
            query,
            params,
            fetch_one=fetch_one,
            fetch_all=fetch_all,
            commit=commit,
            return_last_id=return_last_id,
            as_dict=as_dict,
        )

    def _insert_and_get_id(self, query: str, params: tuple) -> int:
        """INSERT + возврат lastrowid."""
        return self._execute(
            query, params, commit=True, return_last_id=True
        )

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        pass

    def _execute_with_conn(
        self,
        conn,
        query: str,
        params: tuple = None,
        *,
        fetch_one: bool = False,
        fetch_all: bool = False,
        return_last_id: bool = False,
    ):
        """
        Выполнить запрос в рамках уже открытой транзакции.

        В отличие от `_execute` — НЕ открывает своё соединение,
        работает с переданным `conn` и НЕ делает commit.
        Commit делает вызывающий код через DatabaseManager.transaction().
        """
        cur = conn.cursor()
        cur.execute(query, params or ())
        if fetch_one:
            return cur.fetchone()
        if fetch_all:
            return cur.fetchall()
        if return_last_id:
            return cur.lastrowid
        return cur.rowcount