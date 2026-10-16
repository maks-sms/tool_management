# frontend/views/tabs/requests_tab.py
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp

from frontend.widgets.filter_bar import FilterBar, FilterField
from frontend.widgets.modern_button import ModernButton
from frontend.views.tabs.base_tab import BaseTab


STATUS_DISPLAY = {
    'pending':     '🟡 Ожидает',
    'in_progress': '🟠 В работе',
    'completed':   '🟢 Выполнена',
    'rejected':    '🔴 Отклонена',
}


class RequestsTab(BaseTab):
    def __init__(self, app, **kw):
        self.filter_bar = None
        self._buttons_row = None
        super().__init__(
            app=app,
            columns=[
                ('id', 'ID', 1),
                ('tool_code', 'Код', 2),
                ('tool_articul', 'Артикул', 3),
                ('tool_type', 'Тип', 2),
                ('tool_diameter', 'Диаметр', 1),
                ('tool_brand', 'Пр-ль', 2),
                ('requested_qty', 'Кол-во', 1),
                ('received_qty', 'Поступило', 1),
                ('reason', 'Причина', 3),
                ('requester_name', 'Заявитель', 2),
                ('request_date', 'Дата', 2),
                ('status', 'Статус', 2),
                ('comment', 'Комментарий', 4),
            ],
            **kw,
        )

    def _build_top(self):
        self.filter_bar = FilterBar(
            fields=[
                FilterField('status', 'Статус:', 'combo',
                            values=['Все', 'Ожидает', 'В работе',
                                    'Выполнена', 'Отклонена'],
                            default='Все', readonly=True, width=dp(120)),
                FilterField('search_code', 'Код/Артикул:', 'entry',
                            width=dp(140)),
                FilterField('requester', 'Заявитель:', 'entry',
                            width=dp(140)),
                FilterField('search_number', 'Номер заявки:', 'entry',
                            width=dp(140)),
            ],
            on_change=self.refresh,
        )
        return self.filter_bar

    def _build_buttons(self):
        wrapper = BoxLayout(size_hint_y=None, height=dp(50),
                            padding=[dp(6), dp(4)], spacing=dp(4))
        self._buttons_row = wrapper
        return wrapper

    def refresh(self):
        svc = getattr(self.app, 'requests_view_service', None)
        if svc is None:
            return

        try:
            purchase_requests, group_requests = svc.get_all_requests()
        except Exception as e:
            print(f'[requests] ошибка: {e}')
            self.tree.set_rows([])
            return

        f = self.filter_bar.get_values() if self.filter_bar else {}
        search_code = (f.get('search_code') or '').lower()
        requester = (f.get('requester') or '').lower()
        number = (f.get('search_number') or '').lower()

        status_filter = (f.get('status') or 'Все').strip()
        status_map = {
            'Ожидает': 'pending', 'В работе': 'in_progress',
            'Выполнена': 'completed', 'Отклонена': 'rejected',
        }
        want_status = status_map.get(status_filter)

        prepared = []

        for g in group_requests or []:
            gs = getattr(g, 'status', '')
            if want_status and gs != want_status:
                continue
            gnum = (getattr(g, 'request_number', '') or '').lower()
            gname = (getattr(g, 'name', '') or '').lower()
            greq = (getattr(g, 'requester_name', '') or '').lower()
            if number and number not in gnum:
                continue
            if search_code and search_code not in gnum and search_code not in gname:
                continue
            if requester and requester not in greq:
                continue

            prepared.append({
                'id':             getattr(g, 'id', ''),
                'tool_code':      getattr(g, 'request_number', ''),
                'tool_articul':   f"📁 {getattr(g, 'name', '')}",
                'tool_type':      'Групповая',
                'tool_diameter':  '',
                'tool_brand':     '',
                'requested_qty':  getattr(g, 'total_qty', ''),
                'received_qty':   getattr(g, 'received_qty', ''),
                'reason':         (getattr(g, 'reason', '') or 'Групповая заявка'),
                'requester_name': getattr(g, 'requester_name', ''),
                'request_date':   getattr(g, 'request_date', ''),
                'status':         STATUS_DISPLAY.get(gs, gs),
                'comment':        f"📦 №{getattr(g, 'request_number', '')} | {getattr(g, 'name', '')}",
                '_is_group':      True,
            })

        for r in purchase_requests or []:
            rs = getattr(r, 'status', '')
            if want_status and rs != want_status:
                continue
            rcode = (getattr(r, 'tool_code', '') or '').lower()
            rart = (getattr(r, 'tool_articul', '') or '').lower()
            rreq = (getattr(r, 'requester_name', '') or '').lower()
            if search_code and search_code not in rcode and search_code not in rart:
                continue
            if requester and requester not in rreq:
                continue
            if number and number not in str(getattr(r, 'id', '')).lower():
                continue

            prepared.append({
                'id':             getattr(r, 'id', ''),
                'tool_code':      getattr(r, 'tool_code', ''),
                'tool_articul':   getattr(r, 'tool_articul', ''),
                'tool_type':      getattr(r, 'tool_type', '') or '',
                'tool_diameter':  getattr(r, 'tool_diameter', '') or '',
                'tool_brand':     getattr(r, 'tool_brand', '') or '',
                'requested_qty':  getattr(r, 'requested_qty', ''),
                'received_qty':   getattr(r, 'received_qty', 0),
                'reason':         getattr(r, 'reason', '') or '',
                'requester_name': getattr(r, 'requester_name', ''),
                'request_date':   getattr(r, 'request_date', ''),
                'status':         STATUS_DISPLAY.get(rs, rs),
                'comment':        getattr(r, 'comment', '') or '',
                '_is_group':      False,
            })
        prepared = self._sort_rows(prepared)
        self.tree.set_rows(prepared)
        self.tree.on_select = self._on_row_selected
        self.tree.on_double_click = self._on_row_dbl_click
        self._rebuild_buttons()

    def _on_row_selected(self, row):
        self._rebuild_buttons()

    def _on_row_dbl_click(self, row):
        if not row:
            return
        if row.get('_is_group'):
            self.app.on_request_double_click(row)

    def _rebuild_buttons(self):
        if self._buttons_row is None:
            return
        self._buttons_row.clear_widgets()

        buttons = self._get_buttons_for_selection()
        if not buttons:
            self._buttons_row.add_widget(Label(
                text='Выберите заявку для действий',
                color=(0.58, 0.65, 0.65, 1), font_size=dp(12),
            ))
            return

        for text, cb, color in buttons:
            btn = ModernButton(text=text, color=color, size_hint=(1, 1))
            btn.bind(on_release=lambda *_a, f=cb: f())
            self._buttons_row.add_widget(btn)

    def _get_buttons_for_selection(self):
        sel_all = self.tree.get_selected_all()
        if not sel_all:
            return []

        # Мультивыделение
        if len(sel_all) > 1:
            items = []
            if self.app.is_admin:
                items.append((f'🗑️ Удалить ({len(sel_all)})',
                              self.app.delete_request_via_service,
                              'danger'))
            items.append(('🔄 Обновить', self.refresh, 'info'))
            return items

        sel = sel_all[0]
        is_group = bool(sel.get('_is_group'))
        status_display = str(sel.get('status', ''))

        if "🟡" in status_display:
            status = "pending"
        elif "🟠" in status_display:
            status = "in_progress"
        elif "🟢" in status_display:
            status = "completed"
        elif "🔴" in status_display:
            status = "rejected"
        else:
            status = "unknown"

        buttons = []
        is_admin = self.app.is_admin
        can_edit = self.app.has_edit_permission('requests')
        requester_name = str(sel.get('requester_name', ''))
        can_edit_own = is_admin or (
            requester_name == self.app.current_user_fullname)

        if status == 'pending':
            if can_edit:
                buttons.append(("🟠 Взять в работу",
                                self.app.take_to_work_via_service,
                                'warning'))
                buttons.append(("❌ Отклонить",
                                self.app.reject_request_via_service,
                                'danger'))
            if can_edit_own:
                buttons.append(("✏️ Редактировать",
                                self.app.edit_request_via_service,
                                'warning'))
            if is_admin:
                buttons.append(("🗑️ Удалить",
                                self.app.delete_request_via_service,
                                'danger'))
        elif status == 'in_progress':
            if can_edit:
                if is_group:
                    buttons.append(("📦 Открыть заявку",
                                    self.app.open_group_request,
                                    'info'))
                else:
                    buttons.append(("📦 Поступление",
                                    self.app.receive_partial_request_via_service,
                                    'info'))
                buttons.append(("✅ Выполнить",
                                self.app.complete_request_via_service,
                                'success'))
                buttons.append(("❌ Отклонить",
                                self.app.reject_request_via_service,
                                'danger'))
            if can_edit_own:
                buttons.append(("✏️ Редактировать",
                                self.app.edit_request_via_service,
                                'warning'))
            if is_admin:
                buttons.append(("🗑️ Удалить",
                                self.app.delete_request_via_service,
                                'danger'))
        elif status in ('completed', 'rejected'):
            if is_group:
                buttons.append(("👁️ Открыть заявку",
                                self.app.open_group_request,
                                'info'))
            if is_admin:
                buttons.append(("🗑️ Удалить",
                                self.app.delete_request_via_service,
                                'danger'))
        else:
            if is_admin:
                buttons.append(("🗑️ Удалить",
                                self.app.delete_request_via_service,
                                'danger'))

        buttons.append(("🔄 Обновить", self.refresh, 'info'))
        return buttons

    # ─── Контекстное меню ───

    def _build_context_menu(self, tree_widget):
        sel_all = tree_widget.get_selected_all()
        if not sel_all:
            return [('🔄 Обновить', self.refresh)]

        n = len(sel_all)
        if n > 1:
            items = []
            if self.app.is_admin:
                items.append((f'🗑️ Удалить ({n})',
                              self.app.delete_request_via_service))
            items.append((None, None))
            items.append(('🔄 Обновить', self.refresh))
            return items

        sel = sel_all[0]
        is_group = bool(sel.get('_is_group'))
        status_display = str(sel.get('status', ''))

        items = []
        if '🟡' in status_display:
            items.append(('🟠 Взять в работу',
                          self.app.take_to_work_via_service))
            items.append(('❌ Отклонить',
                          self.app.reject_request_via_service))
            items.append(('✏️ Редактировать',
                          self.app.edit_request_via_service))
            if self.app.is_admin:
                items.append(('🗑️ Удалить',
                              self.app.delete_request_via_service))
        elif '🟠' in status_display:
            if is_group:
                items.append(('📦 Открыть заявку',
                              self.app.open_group_request))
            else:
                items.append(('📦 Поступление',
                              self.app.receive_partial_request_via_service))
            items.append(('✅ Выполнить',
                          self.app.complete_request_via_service))
            items.append(('❌ Отклонить',
                          self.app.reject_request_via_service))
            items.append(('✏️ Редактировать',
                          self.app.edit_request_via_service))
            if self.app.is_admin:
                items.append(('🗑️ Удалить',
                              self.app.delete_request_via_service))
        elif '🟢' in status_display or '🔴' in status_display:
            if is_group:
                items.append(('👁️ Открыть заявку',
                              self.app.open_group_request))
            if self.app.is_admin:
                items.append(('🗑️ Удалить',
                              self.app.delete_request_via_service))
        else:
            if self.app.is_admin:
                items.append(('🗑️ Удалить',
                              self.app.delete_request_via_service))

        items.append((None, None))
        items.append(('🔄 Обновить', self.refresh))
        return items