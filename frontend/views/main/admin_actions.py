# frontend/views/main/admin_actions.py
"""Административные действия (Kivy-обёртки)."""
import os
import platform
import subprocess

from shared.config import get_db_path
from shared.utils.backup_utils import (
    get_backups_dir, make_backup, cleanup_old_backups,
)


class AdminActions:
    def __init__(self, app):
        self.app = app

    # ─── Бэкапы ───
    def open_backups_folder(self):
        db_path = get_db_path()
        if not db_path:
            print('[backups] нет пути к БД')
            return
        backups_dir = get_backups_dir(db_path)
        if not os.path.isdir(backups_dir):
            print(f'[backups] нет папки: {backups_dir}')
            return
        try:
            system = platform.system()
            if system == 'Windows':
                os.startfile(backups_dir)
            elif system == 'Darwin':
                subprocess.Popen(['open', backups_dir])
            else:
                subprocess.Popen(['xdg-open', backups_dir])
        except Exception as e:
            print(f'[backups] не удалось открыть: {e}')

    def restore_from_backup(self):
        print('[backups] Восстановление — в разработке')

    def manual_backup(self):
        db_path = get_db_path()
        if not db_path:
            print('[backup] нет пути к БД')
            return
        path = make_backup(db_path, tag='manual')
        if path:
            cleanup_old_backups(db_path, keep=10)
            print(f'[backup] создан: {path}')
        else:
            print('[backup] не удалось создать')

    # ─── Менеджеры ───
    def open_user_manager(self):
        from frontend.views.dialogs.user_manager import UserManagerDialog
        UserManagerDialog(self.app).open()

    def open_tool_manager(self):
        from frontend.views.dialogs.tool_manager import ToolManagerDialog
        ToolManagerDialog(self.app).open()

    def open_machine_manager(self):
        from frontend.views.dialogs.machine_manager import MachineManagerDialog
        MachineManagerDialog(self.app).open()

    # ─── История ───
    def clear_history(self):
        print('[история] очистка — в разработке')