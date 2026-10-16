"""Пользовательская сессия (перенос из client_desktop/app/session.py)."""
from shared.config import ROLE_ADMIN


class UserSession:
    def __init__(self, user_tuple):
        # (id, username, role, full_name, permissions)
        self.user_id = user_tuple[0]
        self.username = user_tuple[1]
        self.role = user_tuple[2]
        self.full_name = user_tuple[3] or user_tuple[1]
        self.permissions = user_tuple[4] or {}

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def as_tuple(self):
        return (self.user_id, self.username, self.role,
                self.full_name, self.permissions)

    def can_view(self, tab):
        if self.is_admin:
            return True
        p = self.permissions.get(tab, {})
        return p.get('view', False)

    def can_edit(self, tab):
        if self.is_admin:
            return True
        p = self.permissions.get(tab, {})
        return p.get('edit', False)