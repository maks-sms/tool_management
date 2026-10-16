# server/database/db_manager.py
import sqlite3
import os
import time
import logging
import json
from datetime import datetime
from typing import Any, List, Optional
from contextlib import contextmanager
from typing import Iterator

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Общие настройки
from shared.config import DEFAULT_DB_NAME, get_app_dir, get_db_path, save_db_path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Единая точка работы с SQLite-БД.

    - WAL-режим для параллельного доступа
    - Автоматический retry при блокировке
    - Явный rollback при ошибке
    - Возврат `lastrowid` при INSERT
    """

    _current_db_path: Optional[str] = None

    # Публичный API

    @classmethod
    def set_db_path(cls, db_path: str) -> None:
        """Установить текущий путь к БД (кэшируется)."""
        cls._current_db_path = db_path

    @classmethod
    def get_db_path(cls) -> str:
        """Получить текущий путь к БД."""
        if cls._current_db_path:
            return cls._current_db_path
        path = get_db_path()
        cls._current_db_path = path
        return path

    @classmethod
    def execute_query(
        cls,
        query: str,
        params: Optional[tuple] = None,
        *,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False,
        return_last_id: bool = False,
        as_dict: bool = False,
        retries: int = 3,
    ) -> Any:
        """
        Выполнить SQL-запрос.

        :param query: SQL-строка
        :param params: параметры (tuple/list)
        :param fetch_one: вернуть одну строку
        :param fetch_all: вернуть все строки
        :param commit: сделать commit (для INSERT/UPDATE/DELETE)
        :param return_last_id: вернуть lastrowid (для INSERT)
        :param as_dict: возвращать dict вместо tuple
        :param retries: количество попыток при блокировке
        """
        db_path = cls.get_db_path()
        if not db_path or not os.path.exists(db_path):
            raise RuntimeError(f"База данных недоступна: {db_path}")

        last_error: Optional[Exception] = None

        for attempt in range(retries):
            conn = None
            try:
                conn = sqlite3.connect(db_path, timeout=20)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")

                if as_dict:
                    conn.row_factory = sqlite3.Row

                cur = conn.cursor()

                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                result = None

                if fetch_one:
                    row = cur.fetchone()
                    result = dict(row) if (as_dict and row) else row
                elif fetch_all:
                    rows = cur.fetchall()
                    result = [dict(r) for r in rows] if as_dict else rows
                elif return_last_id:
                    result = cur.lastrowid
                else:
                    result = cur.rowcount

                if commit:
                    conn.commit()

                return result

            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e).lower() and attempt < retries - 1:
                    logger.warning(
                        "БД заблокирована, попытка %d/%d", attempt + 1, retries
                    )
                    if conn:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    time.sleep(0.5 * (attempt + 1))
                    continue
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                logger.error("Ошибка SQL (%s): %s | params=%s", query[:80], e, params)
                raise

            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                logger.error("Ошибка SQL (%s): %s | params=%s", query[:80], e, params)
                raise

            finally:
                if conn:
                    conn.close()

        if last_error:
            raise last_error

    @classmethod
    def execute_many(
        cls,
        query: str,
        params_list: List[tuple],
        commit: bool = True,
    ) -> int:
        """Пакетное выполнение запроса."""
        if not params_list:
            return 0

        db_path = cls.get_db_path()
        if not db_path or not os.path.exists(db_path):
            raise RuntimeError(f"База данных недоступна: {db_path}")

        conn = sqlite3.connect(db_path, timeout=20)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            cur = conn.cursor()
            cur.executemany(query, params_list)
            if commit:
                conn.commit()
            return cur.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def transaction(cls) -> Iterator[sqlite3.Connection]:
        """
        Контекстный менеджер для транзакций.

        Использование:
            with DatabaseManager.transaction() as conn:
                cur = conn.cursor()
                cur.execute(...)
                cur.execute(...)
                # commit произойдёт автоматически при выходе

        При исключении — rollback.
        """
        db_path = cls.get_db_path()
        if not db_path or not os.path.exists(db_path):
            raise RuntimeError(f"База данных недоступна: {db_path}")

        conn = sqlite3.connect(db_path, timeout=20)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ

def _create_indexes(cur) -> None:
    """
    Создать индексы для часто используемых колонок.

    IF NOT EXISTS — можно вызывать сколько угодно раз,
    повторные вызовы ничего не делают.
    """
    indexes = [
        # Склад
        "CREATE INDEX IF NOT EXISTS idx_tools_inner_code ON tools(inner_code)",
        "CREATE INDEX IF NOT EXISTS idx_tools_articul ON tools(articul)",
        "CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type)",
        "CREATE INDEX IF NOT EXISTS idx_tools_brand ON tools(brand)",

        # Размещения (станки, резерв)
        "CREATE INDEX IF NOT EXISTS idx_placement_tool_id ON placement(tool_id)",
        "CREATE INDEX IF NOT EXISTS idx_placement_location ON placement(location)",
        "CREATE INDEX IF NOT EXISTS idx_placement_note ON placement(note)",

        # История
        "CREATE INDEX IF NOT EXISTS idx_history_date ON history(date)",
        "CREATE INDEX IF NOT EXISTS idx_history_articul ON history(articul)",
        "CREATE INDEX IF NOT EXISTS idx_history_worker ON history(worker)",

        # Заявки на закупку
        "CREATE INDEX IF NOT EXISTS idx_purchase_requests_status ON purchase_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_requests_requester ON purchase_requests(requester_name)",

        # Групповые заявки
        "CREATE INDEX IF NOT EXISTS idx_group_requests_status ON group_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_group_requests_number ON group_requests(request_number)",
        "CREATE INDEX IF NOT EXISTS idx_group_request_items_group ON group_request_items(group_request_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_request_items_tool ON group_request_items(tool_id)",

        # Чат
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_group_id ON chat_messages(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_recipient ON chat_messages(recipient_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_read_messages_user ON read_messages(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_read_messages_msg ON read_messages(message_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_active_users_user ON chat_active_users(user_id)",

        # Пользователи
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    ]
    for sql in indexes:
        try:
            cur.execute(sql)
        except sqlite3.OperationalError as e:
            # Индекс может не создаться, если колонка отсутствует
            # (например, старая версия БД). Это не критично.
            print(f"[indexes] Пропуск: {e}")

def init_db(db_path):
    """Инициализация единой базы данных"""
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        # tools
        cur.execute('''CREATE TABLE IF NOT EXISTS tools
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       inner_code TEXT UNIQUE NOT NULL,
                       articul TEXT NOT NULL,
                       type TEXT,
                       diameter TEXT,
                       length TEXT,
                       brand TEXT,
                       analog TEXT,
                       qty_total INTEGER DEFAULT 0,
                       min_qty INTEGER DEFAULT 0,
                       location TEXT DEFAULT 'Склад',
                       created_at TEXT,
                       updated_at TEXT)''')

        for col_sql in [
            "ALTER TABLE tools ADD COLUMN min_qty INTEGER DEFAULT 0",
            "ALTER TABLE tools ADD COLUMN location TEXT DEFAULT 'Склад'",
            "ALTER TABLE tools ADD COLUMN created_at TEXT",
            "ALTER TABLE tools ADD COLUMN updated_at TEXT",
        ]:
            try:
                cur.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        # placement
        cur.execute('''CREATE TABLE IF NOT EXISTS placement
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       tool_id INTEGER,
                       location TEXT,
                       qty INTEGER,
                       note TEXT,
                       date TEXT,
                       FOREIGN KEY (tool_id) REFERENCES tools(id))''')
        try:
            cur.execute("ALTER TABLE placement ADD COLUMN date TEXT")
        except sqlite3.OperationalError:
            pass

        # history
        cur.execute('''CREATE TABLE IF NOT EXISTS history
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       date TEXT,
                       articul TEXT,
                       action TEXT,
                       qty INTEGER,
                       target TEXT,
                       worker TEXT,
                       timestamp TEXT)''')
        try:
            cur.execute("ALTER TABLE history ADD COLUMN timestamp TEXT")
        except sqlite3.OperationalError:
            pass

        # machines
        cur.execute('''CREATE TABLE IF NOT EXISTS machines
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')

        # users
        cur.execute('''CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       username TEXT UNIQUE,
                       password TEXT,
                       role TEXT,
                       full_name TEXT,
                       created_at TEXT,
                       permissions TEXT,
                       last_login TEXT)''')
        try:
            cur.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        except sqlite3.OperationalError:
            pass

        # chat
        cur.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       username TEXT,
                       full_name TEXT,
                       message TEXT,
                       timestamp TEXT,
                       is_private INTEGER DEFAULT 0,
                       recipient_id INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS chat_active_users
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER UNIQUE,
                       last_activity TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS chat_groups
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT UNIQUE NOT NULL,
                       description TEXT,
                       created_by INTEGER,
                       created_at TEXT,
                       FOREIGN KEY (created_by) REFERENCES users(id))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS chat_group_members
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       group_id INTEGER,
                       user_id INTEGER,
                       joined_at TEXT,
                       FOREIGN KEY (group_id) REFERENCES chat_groups(id),
                       FOREIGN KEY (user_id) REFERENCES users(id),
                       UNIQUE(group_id, user_id))''')

        try:
            cur.execute("PRAGMA table_info(chat_messages)")
            columns = [col[1] for col in cur.fetchall()]
            for col_name, col_type in [
                ('group_id', 'INTEGER'),
                ('is_group', 'INTEGER DEFAULT 0'),
                ('reply_to_id', 'INTEGER'),
                ('file_path', 'TEXT'),
                ('file_name', 'TEXT'),
                ('file_size', 'INTEGER'),
            ]:
                if col_name not in columns:
                    cur.execute(f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                logger.error(" при добавлении колонок: {e}")

        # purchase_requests
        cur.execute('''CREATE TABLE IF NOT EXISTS purchase_requests
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       tool_id INTEGER,
                       tool_code TEXT,
                       tool_articul TEXT,
                       tool_type TEXT,
                       tool_diameter TEXT,
                       tool_brand TEXT,
                       requested_qty INTEGER,
                       received_qty INTEGER DEFAULT 0,
                       reason TEXT,
                       requester_id INTEGER,
                       requester_name TEXT,
                       request_date TEXT,
                       status TEXT DEFAULT 'pending',
                       processed_by TEXT,
                       processed_date TEXT,
                       comment TEXT,
                       FOREIGN KEY (tool_id) REFERENCES tools(id))''')

        # notifications
        cur.execute('''CREATE TABLE IF NOT EXISTS notifications
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER,
                       title TEXT,
                       message TEXT,
                       type TEXT,
                       created_at TEXT,
                       is_read INTEGER DEFAULT 0)''')

        # Дефолтные права
        default_perms = json.dumps({
            "inventory": {"view": True, "edit": True},
            "machines": {"view": True, "edit": True},
            "reserve": {"view": True, "edit": True},
            "history": {"view": True, "edit": True},
            "tools": {"view": True, "edit": True},
            "requests": {"view": True, "edit": True},
            "export": {"view": True, "edit": False}
        })

        # Дефолтные станки
        default_machines = [
            "1М63 (ДИП 300)", "1М65 (ДИП 500)", "1К625Д", "CU1332",
            "DL 465/1500 B", "С5116", "CKA6150i", "СК5126", "NL638TM",
            "VL-1600 ATC", "СК62100", "ГС545", "2А554", "BOSM-DS2525",
            "BOSM-DS600", "BOSM-DPH1212", "TPHD2016F", "ВМ 127",
            "VM1370S", "PM2030", "KXT1515"
        ]
        for machine in default_machines:
            try:
                cur.execute("INSERT INTO machines (name) VALUES (?)", (machine,))
            except sqlite3.IntegrityError:
                pass

        # Администратор
        cur.execute("SELECT id FROM users WHERE role = 'admin'")
        if not cur.fetchone():
            from shared.utils.password_utils import hash_password
            hashed = hash_password("admin123")
            cur.execute("""INSERT INTO users
                          (username, password, role, full_name, created_at, permissions, last_login)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       ("admin", hashed, "admin", "Администратор",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        default_perms,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Индексы
        _create_indexes(cur)

        conn.commit()
        conn.close()

        # Устанавливаем путь в DatabaseManager
        DatabaseManager.set_db_path(db_path)
        return True
    except Exception as e:
        logger.error(" инициализации БД: {str(e)}")
        return False


def update_database_schema(db_path):
    """Обновление структуры существующей базы данных"""
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        updated = False

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]

        # --- tools ---
        if 'tools' in tables:
            cur.execute("PRAGMA table_info(tools)")
            columns = [col[1] for col in cur.fetchall()]
            for col_name, col_def in [
                ('min_qty', 'INTEGER DEFAULT 0'),
                ('location', "TEXT DEFAULT 'Склад'"),
                ('created_at', 'TEXT'),
                ('updated_at', 'TEXT'),
            ]:
                if col_name not in columns:
                    cur.execute(f"ALTER TABLE tools ADD COLUMN {col_name} {col_def}")
                    updated = True
                    if col_name in ('created_at', 'updated_at'):
                        cur.execute(
                            f"UPDATE tools SET {col_name} = ? WHERE {col_name} IS NULL",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
                        )

        # --- chat_messages ---
        if 'chat_messages' in tables:
            cur.execute("PRAGMA table_info(chat_messages)")
            columns = [col[1] for col in cur.fetchall()]
            for col_name, col_def in [
                ('group_id', 'INTEGER'),
                ('is_group', 'INTEGER DEFAULT 0'),
                ('reply_to_id', 'INTEGER'),
                ('file_path', 'TEXT'),
                ('file_name', 'TEXT'),
                ('file_size', 'INTEGER'),
            ]:
                if col_name not in columns:
                    cur.execute(f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_def}")
                    updated = True

        # --- Создаём недостающие таблицы ---
        if 'chat_groups' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS chat_groups
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           name TEXT UNIQUE NOT NULL,
                           description TEXT,
                           created_by INTEGER,
                           created_at TEXT)''')
            updated = True

        if 'chat_group_members' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS chat_group_members
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           group_id INTEGER,
                           user_id INTEGER,
                           joined_at TEXT,
                           UNIQUE(group_id, user_id))''')
            updated = True

        if 'notifications' not in tables:
            cur.execute("""CREATE TABLE IF NOT EXISTS notifications
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           title TEXT,
                           message TEXT,
                           type TEXT,
                           created_at TEXT,
                           is_read INTEGER DEFAULT 0)""")
            updated = True

        if 'group_requests' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS group_requests
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           request_number TEXT UNIQUE NOT NULL,
                           name TEXT NOT NULL,
                           reason TEXT,
                           comment TEXT,
                           requester_id INTEGER,
                           requester_name TEXT,
                           request_date TEXT,
                           status TEXT DEFAULT 'pending',
                           processed_by TEXT,
                           processed_date TEXT,
                           FOREIGN KEY (requester_id) REFERENCES users(id))''')
            updated = True

        if 'group_request_items' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS group_request_items
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           group_request_id INTEGER,
                           tool_id INTEGER,
                           tool_code TEXT,
                           tool_articul TEXT,
                           tool_type TEXT,
                           tool_diameter TEXT,
                           tool_brand TEXT,
                           requested_qty INTEGER,
                           received_qty INTEGER DEFAULT 0,
                           status TEXT DEFAULT 'pending',
                           comment TEXT,
                           FOREIGN KEY (group_request_id) REFERENCES group_requests(id),
                           FOREIGN KEY (tool_id) REFERENCES tools(id))''')
            updated = True

        if 'purchase_requests' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS purchase_requests
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           tool_id INTEGER,
                           tool_code TEXT,
                           tool_articul TEXT,
                           tool_type TEXT,
                           tool_diameter TEXT,
                           tool_brand TEXT,
                           requested_qty INTEGER,
                           received_qty INTEGER DEFAULT 0,
                           reason TEXT,
                           requester_id INTEGER,
                           requester_name TEXT,
                           request_date TEXT,
                           status TEXT DEFAULT 'pending',
                           processed_by TEXT,
                           processed_date TEXT,
                           comment TEXT)''')
            updated = True
        else:
            cur.execute("PRAGMA table_info(purchase_requests)")
            columns = [col[1] for col in cur.fetchall()]
            if 'received_qty' not in columns:
                cur.execute("ALTER TABLE purchase_requests ADD COLUMN received_qty INTEGER DEFAULT 0")
                updated = True

        # --- placement ---
        if 'placement' in tables:
            cur.execute("PRAGMA table_info(placement)")
            columns = [col[1] for col in cur.fetchall()]
            if 'date' not in columns:
                cur.execute("ALTER TABLE placement ADD COLUMN date TEXT")
                updated = True

        # --- history ---
        if 'history' in tables:
            cur.execute("PRAGMA table_info(history)")
            columns = [col[1] for col in cur.fetchall()]
            if 'timestamp' not in columns:
                cur.execute("ALTER TABLE history ADD COLUMN timestamp TEXT")
                updated = True

        # --- read_messages ---
        if 'read_messages' not in tables:
            cur.execute('''CREATE TABLE IF NOT EXISTS read_messages
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           message_id INTEGER,
                           read_at TEXT,
                           UNIQUE(user_id, message_id))''')
            updated = True

        # --- typing_status ---
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='typing_status'")
        if not cur.fetchone():
            cur.execute('''CREATE TABLE IF NOT EXISTS typing_status
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           chat_type TEXT,
                           group_id INTEGER,
                           recipient_id INTEGER,
                           updated_at TEXT,
                           UNIQUE(user_id, chat_type, group_id, recipient_id))''')
            updated = True

        if 'users' in tables:
            _migrate_user_permissions(cur)

        # --- Индексы ---
        _create_indexes(cur)

        conn.commit()
        conn.close()

        # Устанавливаем путь в DatabaseManager
        DatabaseManager.set_db_path(db_path)

        if updated:
            print("База данных успешно обновлена!")
        else:
            print("Структура базы данных актуальна")

        return True
    except Exception as e:
        logger.error(" обновления базы данных: {e}")
        return False


def create_default_db():
    """Создать базу данных по умолчанию (рядом с приложением)."""
    app_dir = get_app_dir()
    default_path = os.path.join(app_dir, DEFAULT_DB_NAME)

    if init_db(default_path):
        save_db_path(default_path)
        return default_path
    return None

def _migrate_user_permissions(cur):
    """Добавляет недостающие ключи прав в JSON пользователей."""
    NEW_PERMISSIONS = {
        "export": {"view": True, "edit": False},
    }

    cur.execute("SELECT id, permissions FROM users")
    rows = cur.fetchall()

    updated_count = 0
    for user_id, perms_json in rows:
        try:
            perms = json.loads(perms_json) if perms_json else {}
        except (json.JSONDecodeError, TypeError):
            perms = {}

        changed = False
        for key, default in NEW_PERMISSIONS.items():
            if key not in perms:
                perms[key] = dict(default)
                changed = True

        if changed:
            cur.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (json.dumps(perms, ensure_ascii=False), user_id)
            )
            updated_count += 1

    if updated_count:
        print(f"[migration] Обновлены права у {updated_count} пользователей")