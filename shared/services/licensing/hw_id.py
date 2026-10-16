# shared/services/licensing/hw_id.py
"""
Получение уникального идентификатора устройства.

- Windows: MAC + серийник тома + CPU + hostname.
- Android: ANDROID_ID (стабильный идентификатор ОС).
- Linux/macOS: MAC + hostname + /proc/cpuinfo или sysctl.
- Fallback: hostname.
"""
import hashlib
import os
import platform
import subprocess
import uuid
from typing import Optional


# ─── Определение платформы ───

def _is_android() -> bool:
    return 'ANDROID_ARGUMENT' in os.environ


# ─── Компоненты ───

def _get_mac_address() -> str:
    """MAC-адрес основной сетевой карты (не на Android)."""
    if _is_android():
        return ""
    try:
        mac = uuid.getnode()
        # uuid.getnode() возвращает "случайный" MAC, если карты нет.
        # Если установлен multicast-бит — считаем случайным.
        if (mac >> 40) % 2:
            return ""
        return f"{mac:012X}"
    except Exception:
        return ""


def _get_android_id() -> str:
    """ANDROID_ID — стабильный идентификатор устройства на Android."""
    try:
        from jnius import autoclass # type: ignore
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Settings = autoclass('android.provider.Settings$Secure')
        context = PythonActivity.mActivity
        resolver = context.getContentResolver()
        android_id = Settings.getString(resolver, Settings.ANDROID_ID)
        return android_id or ""
    except Exception:
        return ""


def _get_volume_serial() -> str:
    """Серийный номер системного диска (C:) — только Windows."""
    if _is_android():
        return ""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_LogicalDisk "
                    "-Filter \"DeviceID='C:'\").VolumeSerialNumber"
                ],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            serial = result.stdout.strip()
            if serial:
                return serial

            result = subprocess.run(
                ["wmic", "logicaldisk", "where", "DeviceID='C:'",
                 "get", "VolumeSerialNumber"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            for line in lines:
                if line and line != "VolumeSerialNumber":
                    return line
        else:
            result = subprocess.run(
                ["lsblk", "-no", "SERIAL"],
                capture_output=True, text=True, timeout=5,
            )
            serials = [s.strip() for s in result.stdout.splitlines() if s.strip()]
            return serials[0] if serials else ""
    except Exception:
        return ""
    return ""


def _get_cpu_id() -> str:
    """Идентификатор процессора — только desktop."""
    if _is_android():
        return ""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Processor).ProcessorId"
                ],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            return result.stdout.strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("serial"):
                        return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _get_machine_name() -> str:
    """Имя устройства / хоста."""
    try:
        return platform.node() or ""
    except Exception:
        return ""


# ─── Публичный API ───

def get_raw_hw_parts() -> dict:
    """Все компоненты HW-ID — для отображения и логов."""
    if _is_android():
        return {
            "android_id": _get_android_id(),
            "hostname": _get_machine_name(),
        }
    return {
        "mac": _get_mac_address(),
        "volume": _get_volume_serial(),
        "cpu": _get_cpu_id(),
        "hostname": _get_machine_name(),
    }


def get_hardware_id(strict: bool = False) -> str:
    """
    Уникальный HW-ID.

    Windows: MAC + VolumeSerial → 32 hex-символа с дефисами.
    Android: ANDROID_ID + hostname → тот же формат.
    """
    parts = get_raw_hw_parts()

    if _is_android():
        source = "|".join([
            parts.get("android_id", ""),
            parts.get("hostname", ""),
        ])
    else:
        if strict:
            source = "|".join([
                parts.get("mac", ""),
                parts.get("volume", ""),
                parts.get("cpu", ""),
                parts.get("hostname", ""),
            ])
        else:
            source = "|".join([
                parts.get("mac", ""),
                parts.get("volume", ""),
            ])

    if not source.strip("|"):
        source = f"fallback|{parts.get('hostname', '')}|{os.environ.get('COMPUTERNAME', '')}"

    digest = hashlib.sha256(source.encode("utf-8")).hexdigest().upper()
    return "-".join([
        digest[0:8], digest[8:12], digest[12:16],
        digest[16:20], digest[20:32],
    ])


def get_short_hw_id() -> str:
    """Короткая версия HW-ID для окна активации."""
    return get_hardware_id(strict=False)