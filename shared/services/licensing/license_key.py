# shared/services/licensing/license_key.py
"""
Генерация и проверка лицензионных ключей.

Схема:
1. У вас есть СЕКРЕТНЫЙ КЛЮЧ (SECRET) — известен только вам.
2. Вы генерируете ключ для клиента:
   license_key = HMAC(SECRET, hw_id + company_name + expire_date)
3. Клиент вводит ключ → программа проверяет:
   HMAC(SECRET, hw_id + company_name + expire_date) == введённый ключ

ВАЖНО: SECRET_KEY должен быть вкомпилирован в .exe,
но НЕ храниться в открытом виде в исходниках, которые вы даёте.
"""
import hmac
import hashlib
import base64
from datetime import datetime, date
from typing import Optional


_SECRET_KEY = b"zyI58ix7GR5WgVcrds2xCwH-Jd7KcFg1HnRuqyUAX4AJdTzmzYP9q-zf8hk1CvTGeahOxjLZVlXID6q8ctosgg"


def _normalize_hw_id(hw_id: str) -> str:
    """Привести HW-ID к единому виду (без дефисов, в верхнем регистре)."""
    return hw_id.replace("-", "").upper().strip()


def _normalize_company(company: str) -> str:
    """Нормализовать имя компании."""
    return company.strip()[:64]


def generate_license_key(
    hw_id: str,
    company: str,
    expire_date: Optional[date] = None,
) -> str:
    """
    Сгенерировать лицензионный ключ.

    ВЫЗЫВАЕТСЯ ТОЛЬКО ВАМИ (у вас есть SECRET_KEY).

    :param hw_id:      HW-ID клиента (например, "A3F8C21B-D49E-...")
    :param company:    название компании-лицензиата
    :param expire_date: дата окончания (None — бессрочная)
    :return: строка ключа вида "TM2-XXXXX-XXXXX-XXXXX-XXXXX"
    """
    hw = _normalize_hw_id(hw_id)
    cmp = _normalize_company(company)
    exp = expire_date.strftime("%Y%m%d") if expire_date else "99999999"

    payload = f"{hw}|{cmp}|{exp}".encode("utf-8")
    sig = hmac.new(_SECRET_KEY, payload, hashlib.sha256).digest()

    # Берём первые 15 байт, кодируем в base32 (без похожих символов)
    b32 = base64.b32encode(sig[:15]).decode("ascii").rstrip("=")

    # Форматируем: TM2-XXXXX-XXXXX-XXXXX-XXXXX (25 символов base32)
    b32 = b32[:25]
    grouped = "-".join([b32[i:i+5] for i in range(0, 25, 5)])

    return f"TM2-{grouped}"


def verify_license_key(
    license_key: str,
    hw_id: str,
    company: str,
    expire_date: Optional[date] = None,
) -> bool:
    """
    Проверить лицензионный ключ.

    ВЫЗЫВАЕТСЯ В ПРОГРАММЕ у клиента.

    :return: True — ключ валиден
    """
    try:
        expected = generate_license_key(hw_id, company, expire_date)
        return hmac.compare_digest(
            license_key.strip().upper(),
            expected.strip().upper(),
        )
    except Exception:
        return False