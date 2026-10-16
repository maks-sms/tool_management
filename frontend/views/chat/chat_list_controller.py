# frontend/views/chat/chat_list_controller.py
"""Список диалогов в левой панели."""
from frontend.views.chat.chat_constants import ChatType


class ChatListController:
    """Отображает список диалогов и обрабатывает выбор."""

    def __init__(self, manager):
        self.manager = manager
        self._filter = ''

    def set_filter(self, text):
        self._filter = (text or '').strip().lower()
        self.update()

    def update(self):
        m = self.manager
        if m.ui is None:
            return

        try:
            groups = m.chat_service.get_user_groups(m.current_user[0]) or []
            users = m.chat_service.get_users_except(m.current_user[0]) or []
        except Exception as e:
            print(f'[chat.list] {e}')
            groups, users = [], []

        q = self._filter
        items = []

        # Общий чат
        if not q or 'общий' in q:
            active = (m.current_chat_type == ChatType.GENERAL.value)
            items.append(('📢  Общий чат',
                          {'type': ChatType.GENERAL.value, 'id': None},
                          active))

        # Группы
        for g in groups:
            gid, name, _t, member_count = g[:4]
            if q and q not in (name or '').lower():
                continue
            active = (m.current_chat_type == ChatType.GROUP.value
                      and m.current_group
                      and m.current_group.get('id') == gid)
            items.append((f"👥  {name} ({member_count})",
                          {'type': ChatType.GROUP.value, 'id': gid,
                           'name': name, 'member_count': member_count},
                          active))

        # Пользователи
        for u in users:
            uid, username, full_name, _utype = u[:4]
            display = full_name or username
            if q and q not in display.lower():
                continue
            try:
                online = m.chat_service.is_user_online(uid)
            except Exception:
                online = False
            icon = '🟢' if online else '⚫'
            active = (m.current_chat_type == ChatType.PRIVATE.value
                      and m.selected_user == uid)
            items.append((f"{icon}  {display}",
                          {'type': ChatType.PRIVATE.value, 'id': uid,
                           'name': display, 'username': username},
                          active))

        m.ui.fill_dialog_list(items)

    def on_select(self, data):
        m = self.manager
        if not data:
            return

        if data['type'] == ChatType.GENERAL.value:
            m.select_general()
        elif data['type'] == ChatType.GROUP.value:
            m.select_group(data['id'], data['name'],
                           data.get('member_count', 0))
        elif data['type'] == ChatType.PRIVATE.value:
            m.select_user(data['id'], data['name'])

        # Обновить активный пункт
        self.update()