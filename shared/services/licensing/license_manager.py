# shared/services/licensing/license_manager.py
"""
Управление лицензией: сохранение, загрузка, проверка.
"""
import json
import os
from datetime import datetime, date
from typing import Optional, Dict, Any

from shared.config import get_app_dir
from shared.services.licensing.hw_id import get_hardware_id
from shared.services.licensing.license_key import verify_license_key
from shared.utils.logger import get_logger

logger = get_logger(__name__)

LICENSE_FILE = "license.json"


def _license_path() -> str:
    """Путь к файлу лицензии — рядом с .exe/проектом."""
    return os.path.join(get_app_dir(), LICENSE_FILE)


def load_license() -> Optional[Dict[str, Any]]:
    """Загрузить сохранённую лицензию."""
    path = _license_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Ошибка чтения лицензии: %s", e)
        return None


def save_license(data: Dict[str, Any]) -> None:
    """Сохранить лицензию."""
    path = _license_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Ошибка сохранения лицензии: %s", e)


def activate(license_key: str, company: str,
             expire_date: Optional[date] = None) -> bool:
    """
    Активировать программу с указанным ключом.

    :return: True если активация успешна
    """
    hw_id = get_hardware_id()

    if not verify_license_key(license_key, hw_id, company, expire_date):
        return False

    save_license({
        "license_key": license_key.strip().upper(),
        "company": company,
        "hw_id": hw_id,
        "expire_date": expire_date.isoformat() if expire_date else None,
        "activated_at": datetime.now().isoformat(timespec="seconds"),
    })
    return True


def is_activated() -> bool:
    """
    Проверить, активирована ли программа.

    Логика:
    1. Есть файл license.json?
    2. HW-ID в файле совпадает с текущим HW-ID?
    3. Ключ валиден (HMAC-проверка)?
    4. Срок не истёк?
    """
    data = load_license()
    if not data:
        return False

    # 1. HW-ID совпадает
    current_hw = get_hardware_id()
    if data.get("hw_id") != current_hw:
        logger.warning(
            "HW-ID не совпадает: сохранён=%s, текущий=%s",
            data.get("hw_id"), current_hw,
        )
        return False

    # 2. Ключ валиден
    expire = None
    if data.get("expire_date"):
        try:
            expire = datetime.fromisoformat(data["expire_date"]).date()
        except Exception:
            expire = None

    if not verify_license_key(
        data.get("license_key", ""),
        current_hw,
        data.get("company", ""),
        expire,
    ):
        logger.warning("Ключ лицензии невалиден")
        return False

    # 3. Срок не истёк
    if expire and expire < date.today():
        logger.warning("Лицензия истекла %s", expire)
        return False

    return True


def get_license_info() -> Optional[Dict[str, Any]]:
    """Информация о текущей лицензии."""
    return load_license()