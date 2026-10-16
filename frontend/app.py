# frontend/app.py
"""
Главный контейнер приложения (Kivy-виджет).
Хранит сессию, сервисы, менеджеры, actions.
Запускается внутри BootstrapApp (frontend/main.py).
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from frontend.theme import C
from frontend.session import UserSession


class _Context:
    """Мини-аналог AppContext: хранит все сервисы."""

    def __init__(self, **services):
        for name, value in services.items():
            setattr(self, name, value)
        self.on_refresh_callback = None


class WarehouseApp(BoxLayout):
    """Главный виджет. Заменяет прежний App-класс.

    API:
        WarehouseApp(user_tuple=(...), bootstrap=app).show()
    """

    def __init__(self, user_tuple, bootstrap=None, **kw):
        kw.setdefault('orientation', 'vertical')
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self.bootstrap = bootstrap
        self.session = UserSession(user_tuple)
        self.main_screen = None

        self._init_services()
        self._init_managers()
        self._build()

    # ─── Сервисы ───
    def _init_services(self):
        from shared.services.tool_service import ToolService
        from shared.services.user_service import UserService
        from shared.services.history_service import HistoryService
        from shared.services.chat_service import ChatService
        from shared.services.request_service import PurchaseRequestService
        from shared.services.group_request_service import GroupRequestServiceExtended
        from shared.services.placement_service import PlacementService
        from shared.services.machine_service import MachineService
        from shared.services.stats_service import StatsService
        from shared.services.view_services import (
            InventoryViewService, MachinesViewService, ReserveViewService,
            HistoryViewService, RequestsViewService,
        )

        self.tool_service = ToolService()
        self.user_service = UserService()
        self.history_service = HistoryService()
        self.chat_service = ChatService()
        self.purchase_request_service = PurchaseRequestService()
        self.group_request_service_extended = GroupRequestServiceExtended()
        self.group_request_service = self.group_request_service_extended
        self.placement_service = PlacementService()
        self.machine_service = MachineService()
        self.stats_service = StatsService()

        self.inventory_view_service = InventoryViewService()
        self.machines_view_service = MachinesViewService()
        self.reserve_view_service = ReserveViewService()
        self.history_view_service = HistoryViewService()
        self.requests_view_service = RequestsViewService()

        self.context = _Context(
            tool_service=self.tool_service,
            user_service=self.user_service,
            history_service=self.history_service,
            chat_service=self.chat_service,
            purchase_request_service=self.purchase_request_service,
            group_request_service=self.group_request_service,
            group_request_service_extended=self.group_request_service_extended,
            placement_service=self.placement_service,
            machine_service=self.machine_service,
            stats_service=self.stats_service,
            inventory_view_service=self.inventory_view_service,
            machines_view_service=self.machines_view_service,
            reserve_view_service=self.reserve_view_service,
            history_view_service=self.history_view_service,
            requests_view_service=self.requests_view_service,
        )
        self.context.session = self.session

    def _init_managers(self):
        from frontend.views.main.request_actions import RequestActions
        from frontend.views.main.inventory_actions import InventoryActions
        from frontend.views.main.admin_actions import AdminActions
        from frontend.views.main.close_handler import CloseHandler
        from frontend.views.main.chat_background import ChatBackground
        from frontend.views.main.filter_actions import FilterActions
        from frontend.views.main.notifications import Notifications

        self.request_actions = RequestActions(self)
        self.inventory_actions = InventoryActions(self)
        self.admin_actions = AdminActions(self)
        self.close_handler = CloseHandler(self)
        self.chat_background = ChatBackground(self)
        self.filter_actions = FilterActions(self)
        self.notifications = Notifications(self)

    # ─── Свойства сессии ───
    @property
    def current_user(self):
        return self.session.as_tuple

    @property
    def current_user_id(self):
        return self.session.user_id

    @property
    def current_username(self):
        return self.session.username

    @property
    def current_user_role(self):
        return self.session.role

    @property
    def current_user_fullname(self):
        return self.session.full_name

    @property
    def is_admin(self):
        return self.session.is_admin

    @property
    def user_permissions(self):
        return self.session.permissions

    def has_view_permission(self, tab):
        return self.session.can_view(tab)

    def has_edit_permission(self, tab):
        return self.session.can_edit(tab)

    def get_current_worker_name(self):
        return self.session.full_name or self.session.username

    def get_machines(self):
        return self.machine_service.get_all()


    # ─── Build ───
    def _build(self):
        from frontend.views.main.main_screen import MainScreen
        self.main_screen = MainScreen(app=self)
        self.add_widget(self.main_screen)
        # НИКАКИХ Clock.schedule_once для Window —
        # размер уже установлен в BootstrapApp._step_main()

    # ─── Обновление данных ───
    def refresh_all(self):
        """Обновить только активную вкладку + помеченные «грязными».

        Не трогает вкладки с _busy=True (например, открыт диалог).
        """
        if not self.main_screen:
            return

        tabs = getattr(self.main_screen, 'tab_widgets', {}) or {}
        active_key = self._get_active_tab_key()

        for name, tab in tabs.items():
            is_dirty = getattr(tab, '_dirty', False)
            is_busy = getattr(tab, '_busy', False)

            if is_busy:
                continue
            if name != active_key and not is_dirty:
                continue

            try:
                tab.refresh()
                tab._dirty = False
            except Exception as e:
                print(f'[refresh_all] вкладка {name}: {e}')

    def _get_active_tab_key(self):
        """Ключ активной вкладки (или None)."""
        if not self.main_screen:
            return None
        try:
            tabs = getattr(self.main_screen, 'tab_widgets', {}) or {}
            current = self.main_screen.tabs.current_tab
            for name, widget in tabs.items():
                if widget.parent is current:
                    return name
        except Exception:
            pass
        return None

    def refresh_requests_tab(self):
        """Совместимость. Обновляет вкладку заявок через refresh_requests_now."""
        self.refresh_requests_now()

    def refresh_requests_now(self):
        """Обновить вкладку заявок НЕМЕДЛЕННО, независимо от _dirty и активности.

        Вызывается после создания/изменения заявки, чтобы список сразу
        содержал свежие данные. Не полагается ни на _dirty, ни на active_key,
        но уважает _busy (чтобы не дёргать вкладку во время открытого диалога).
        """
        if not self.main_screen:
            return
        tabs = getattr(self.main_screen, 'tab_widgets', {}) or {}
        req = tabs.get('requests')
        if not req:
            return
        # Если вкладка занята своим диалогом — отложим до его закрытия
        if getattr(req, '_busy', False):
            req._dirty = True
            return
        try:
            req.refresh()
            req._dirty = False
        except Exception as e:
            print(f'[refresh_requests_now] {e}')

    def manual_refresh(self):
        self.refresh_all()

    def start_auto_refresh(self):
        print('[auto_refresh] старт')

    def stop_auto_refresh(self):
        print('[auto_refresh] стоп')

    def toggle_auto_refresh(self):
        print('[auto_refresh] переключение')

    def set_refresh_interval(self, interval):
        print(f'[auto_refresh] интервал = {interval} сек')

    # ─── Действия с заявками ───
    def take_to_work_via_service(self):
        self.request_actions.take_to_work()

    def receive_partial_request_via_service(self):
        self.request_actions.receive_partial()

    def complete_request_via_service(self):
        self.request_actions.complete()

    def reject_request_via_service(self):
        self.request_actions.reject()

    def edit_request_via_service(self):
        self.request_actions.edit()

    def delete_request_via_service(self):
        self.request_actions.delete()

    def on_request_double_click(self, event=None):
        self.request_actions.on_double_click(event)

    # ─── Групповые заявки ───
    def open_group_request(self, row=None):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout as BX
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from frontend.widgets.modern_button import ModernButton
        from kivy.metrics import dp as _dp

        if not row:
            return
        gid = row.get('id')
        if gid in (None, ''):
            return

        group = None
        items = []
        try:
            svc = getattr(self, 'group_request_service_extended', None)
            if svc is not None:
                group = svc.get_by_id(gid)
                items = svc.get_items(gid) or []
        except Exception as e:
            print(f'[group] не удалось получить данные: {e}')

        bx = BX(orientation='vertical', padding=_dp(14), spacing=_dp(6),
                size_hint_y=None)
        bx.bind(minimum_height=bx.setter('height'))

        bx.add_widget(Label(
            text=f"Групповая заявка №{row.get('tool_code', '')}",
            bold=True, size_hint_y=None, height=_dp(26), color=C['dark']))
        bx.add_widget(Label(
            text=row.get('tool_articul', ''),
            size_hint_y=None, height=_dp(22), color=C['dark']))

        if group is not None:
            info_lines = [
                f"Заявитель: {getattr(group, 'requester_name', '')}",
                f"Дата:      {getattr(group, 'request_date', '')}",
                f"Статус:    {getattr(group, 'status', '')}",
                f"Позиций:   {getattr(group, 'items_count', len(items))}",
                f"Заказано:  {getattr(group, 'total_qty', '')} шт.",
                f"Поступило: {getattr(group, 'received_qty', 0)} шт.",
            ]
            for line in info_lines:
                bx.add_widget(Label(
                    text=line, halign='left', color=C['dark'],
                    size_hint_y=None, height=_dp(20)))

        if items:
            bx.add_widget(Label(text='—', size_hint_y=None, height=_dp(1),
                                color=C['dark']))
            bx.add_widget(Label(text='Позиции:', bold=True,
                                size_hint_y=None, height=_dp(20),
                                color=C['dark']))
            for it in items[:30]:
                try:
                    line = f"• {it[2]}  {it[3]}  {it[8]}/{it[7]}"
                except Exception:
                    line = str(it)
                bx.add_widget(Label(text=line, halign='left',
                                    size_hint_y=None, height=_dp(18),
                                    color=C['dark']))

        row_btn = BX(size_hint_y=None, height=_dp(44), spacing=_dp(8))
        close_btn = ModernButton(text='Закрыть', color='info',
                                 size_hint=(1, 1), height=_dp(38))
        row_btn.add_widget(close_btn)
        bx.add_widget(row_btn)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(bx)

        popup = Popup(title='Групповая заявка',
                      content=scroll,
                      size_hint=(None, None),
                      size=(_dp(560), _dp(560)),
                      background_color=C['panel'],
                      title_color=C['dark'],
                      separator_color=C['border'])
        close_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def open_group_request_by_id(self, group_id):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout as BX
        from kivy.uix.label import Label
        from frontend.widgets.modern_button import ModernButton
        from kivy.metrics import dp as _dp

        bx = BX(orientation='vertical', padding=_dp(14), spacing=_dp(6))
        bx.add_widget(Label(text=f"Групповая заявка №{group_id}",
                            bold=True, size_hint_y=None, height=_dp(26),
                            color=C['dark']))

        try:
            svc = self.group_request_service_extended
            group = svc.get_by_id(group_id)
            items = svc.get_items(group_id) or []
            if group:
                bx.add_widget(Label(text=f"Название: {getattr(group, 'name', '')}",
                                    size_hint_y=None, height=_dp(20),
                                    color=C['dark']))
                bx.add_widget(Label(text=f"Заявитель: {getattr(group, 'requester_name', '')}",
                                    size_hint_y=None, height=_dp(20),
                                    color=C['dark']))
                bx.add_widget(Label(text=f"Статус: {getattr(group, 'status', '')}",
                                    size_hint_y=None, height=_dp(20),
                                    color=C['dark']))
            for it in items[:30]:
                try:
                    code = it[2]; articul = it[3]
                    req_qty = it[7]; recv_qty = it[8]
                    bx.add_widget(Label(
                        text=f"• {code}  {articul}  {recv_qty}/{req_qty}",
                        halign='left', size_hint_y=None, height=_dp(18),
                        color=C['dark']))
                except Exception:
                    pass
        except Exception as e:
            bx.add_widget(Label(text=f"Ошибка: {e}", color=C['danger']))

        btn = ModernButton(text='Закрыть', color='info',
                           size_hint=(None, None), size=(_dp(120), _dp(40)))
        btn.pos_hint = {'center_x': 0.5}
        bx.add_widget(btn)
        popup = Popup(title='Групповая заявка', content=bx,
                      size_hint=(None, None), size=(_dp(520), _dp(520)),
                      background_color=C['panel'],
                      title_color=C['dark'],
                      separator_color=C['border'])
        btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    # ─── Склад ───
    def create_request_from_selected(self):
        self.inventory_actions.create_request_from_selected()

    def create_group_request_from_selected(self):
        self.inventory_actions.create_group_request_from_selected()

    def win_add_qty(self):
        self.inventory_actions.add_quantity()

    def win_move(self, mode):
        self.inventory_actions.move(mode)

    def win_add_machine(self):
        self.inventory_actions.add_machine()

    def action_from_place(self, action, tree):
        self.inventory_actions.manage_placement(action, tree)

    # ─── Фильтры ───
    def clear_filters(self):
        self.filter_actions.clear_inventory_filters()

    def clear_requests_filters(self):
        self.filter_actions.clear_requests_filters()

    # ─── Система ───
    def open_settings(self):
        from frontend.views.dialogs.settings import SettingsDialog
        SettingsDialog(self).open()

    def open_backups_folder(self):
        self.admin_actions.open_backups_folder()

    def restore_from_backup(self):
        self.admin_actions.restore_from_backup()

    def manual_backup(self):
        self.admin_actions.manual_backup()

    def open_user_manager(self):
        self.admin_actions.open_user_manager()

    def open_tool_manager(self):
        self.admin_actions.open_tool_manager()

    def open_machine_manager(self):
        self.admin_actions.open_machine_manager()

    def clear_history(self):
        self.admin_actions.clear_history()

    # ─── Пользователь ───
    def switch_user(self):
        print('[пользователь] смена — перезапустите программу')

    def change_password(self):
        print('[пользователь] смена пароля — в разработке')

    def open_profile(self):
        self.notifications.open_profile()

    # ─── Чат ───
    def open_chat(self):
        from frontend.views.chat.chat_screen import open_chat as _open_chat
        _open_chat(self)

    def clear_chat_history(self):
        print('[чат] очистить историю — в разработке')

    def show_notifications_popup(self):
        self.notifications.show_notifications_popup()

    # ─── Импорт/экспорт ───
    def import_csv(self):
        """Импорт склада из CSV (из меню администрирования)."""
        from frontend.views.main.tabs_builder import TabsBuilder
        builder = TabsBuilder(self)
        # не строим весь panel заново, а просто вызываем логику
        builder.open_import_for('tools')

    def export_to_csv(self):
        """Экспорт всего склада в CSV (из меню администрирования)."""
        from frontend.views.main.tabs_builder import TabsBuilder
        builder = TabsBuilder(self)
        builder.open_export_for('tools')

    # ─── Закрытие ───
    def stop(self):
        """Совместимость с прежним App.stop(). Закрывает всё приложение."""
        try:
            if self.bootstrap is not None:
                self.bootstrap.stop()
            else:
                from kivy.app import App
                app = App.get_running_app()
                if app:
                    app.stop()
        except Exception as e:
            print(f'[stop] {e}')

    def on_close(self):
        self.close_handler.close()