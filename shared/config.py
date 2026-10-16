# shared/config.py
"""
Общий конфиг для клиента и сервера.
Здесь живёт то, что нужно обоим:
  - путь к БД (get_db_path / save_db_path)
  - префиксы локаций
  - роли
  - лимиты
  - базовые цвета (используются и в вебе)
Никаких импортов из client_desktop.* или server.* тут быть не должно!
"""
import os
import json
import sys


# Пути

def get_app_dir() -> str:
    """Папка приложения.

    - Android: приватная папка приложения (доступна для записи).
    - Windows .exe: рядом с .exe.
    - Windows/Linux из исходников: корень проекта.
    """
    # Android
    if 'ANDROID_ARGUMENT' in os.environ:
        # 1. Kivy знает правильную папку — это самый надёжный способ
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app is not None:
                path = app.user_data_dir
                os.makedirs(path, exist_ok=True)
                print(f'[get_app_dir] user_data_dir = {path!r}')
                return path
        except Exception as e:
            print(f'[get_app_dir] user_data_dir failed: {e}')

        # 2. ANDROID_PRIVATE
        private = os.environ.get('ANDROID_PRIVATE', '')
        if private:
            try:
                os.makedirs(private, exist_ok=True)
                print(f'[get_app_dir] ANDROID_PRIVATE = {private!r}')
                return private
            except Exception as e:
                print(f'[get_app_dir] ANDROID_PRIVATE failed: {e}')

        # 3. jnius — как последний шанс
        try:
            from jnius import autoclass # type: ignore
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            ctx = PythonActivity.mActivity
            path = ctx.getFilesDir().getAbsolutePath()
            os.makedirs(path, exist_ok=True)
            print(f'[get_app_dir] jnius = {path!r}')
            return path
        except Exception as e:
            print(f'[get_app_dir] jnius failed: {e}')

    # Windows .exe
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    # Из исходников — корень проекта
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_backups_dir() -> str:
    """Папка для резервных копий (рядом с текущей БД)."""
    db_path = get_db_path()
    if not db_path:
        return ""
    base = os.path.dirname(os.path.abspath(db_path))
    return os.path.join(base, "backups")


CONFIG_FILE = os.path.join(get_app_dir(), "warehouse_config.json")
DEFAULT_DB_NAME = "factory_sklad_v10.db"
VERSION = "2.0"
COMPANY = "ООО 'Солодовников'"
APP_NAME = f"ToolManagement {VERSION}"


# Домен

LOCATION_WAREHOUSE = "Склад"
LOCATION_RESERVE = "Резерв"
LOCATION_MACHINE_PREFIX = "Станок "

HISTORY_LIMIT = 500
CHAT_MESSAGE_LIMIT = 100
CHAT_USER_STATUS_MINUTES = 2
CHAT_UNREAD_BADGE_MAX = 99

ROLE_ADMIN = "admin"
ROLE_USER = "user"

REFRESH_INTERVAL_DEFAULT = 60_000
REFRESH_INTERVAL_OPTIONS = [30_000, 60_000, 120_000]


# JSON-конфиг (общий файл!)

def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_db_path() -> str:
    """Путь к БД из общего конфига."""
    return _load_config().get('db_path', '')


def save_db_path(db_path: str) -> None:
    config = _load_config()
    config['db_path'] = db_path
    _save_config(config)


def get_saved_username() -> str:
    return _load_config().get('saved_username', '')


def save_username(username: str) -> None:
    config = _load_config()
    config['saved_username'] = username
    _save_config(config)


def get_column_widths_config() -> dict:
    return _load_config().get('column_widths', {})


def save_column_widths(tree_name: str, widths: dict) -> None:
    config = _load_config()
    config.setdefault('column_widths', {})[tree_name] = widths
    _save_config(config)


def get_column_alignment_config() -> dict:
    return _load_config().get('column_alignment', {})


def save_column_alignment(tree_name: str, alignments: dict) -> None:
    config = _load_config()
    config.setdefault('column_alignment', {})[tree_name] = alignments
    _save_config(config)


# Опционально: хранение пароля
def get_remember_password() -> bool:
    return _load_config().get('remember_password', False)


def save_remember_password(remember: bool) -> None:
    config = _load_config()
    config['remember_password'] = remember
    _save_config(config)


def get_saved_password() -> str:
    return _load_config().get('saved_password', '')


def save_password(password: str) -> None:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("cryptography не установлена, пароль не сохранён")
        return
    key_file = os.path.join(get_app_dir(), "secret.key")
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
    cipher = Fernet(key)
    config = _load_config()
    config['saved_password'] = cipher.encrypt(password.encode()).decode()
    _save_config(config)


def get_decrypted_password() -> str:
    encrypted = get_saved_password()
    if not encrypted:
        return ""
    try:
        from cryptography.fernet import Fernet
        key_file = os.path.join(get_app_dir(), "secret.key")
        if not os.path.exists(key_file):
            return ""
        with open(key_file, 'rb') as f:
            key = f.read()
        return Fernet(key).decrypt(encrypted.encode()).decode()
    except Exception:
        return ""
