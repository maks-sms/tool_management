# frontend/views/main_screen.py
"""Главный экран: Menu + Header + Tabs. app передаётся явно."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from frontend.theme import C
from frontend.views.main.header_bar import HeaderBar
from frontend.views.main.menu_builder import MenuBuilder
from frontend.views.main.helpers import clean_tab_label

from frontend.views.tabs.inventory_tab import InventoryTab
from frontend.views.tabs.machines_tab import MachinesTab
from frontend.views.tabs.reserve_tab import ReserveTab
from frontend.views.tabs.history_tab import HistoryTab
from frontend.views.tabs.requests_tab import RequestsTab
from frontend.views.tabs.export_tab import ExportTab


class MainScreen(BoxLayout):
    def __init__(self, app, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', 0)
        kw.setdefault('spacing', 0)
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['bg'])
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.app = app
        self.tab_widgets = {}
        self._build()

    def _sync_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _build(self):
        # Menu
        menu_wrap = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(34),
            padding=[dp(10), dp(2), dp(10), dp(2)],
            spacing=0,
        )
        self.menu_bar = MenuBuilder(app=self.app)
        self.menu_bar.size_hint = (None, 1)
        self.menu_bar.width = dp(700)
        menu_wrap.add_widget(self.menu_bar)
        menu_wrap.add_widget(BoxLayout())
        self.menu_wrap = menu_wrap
        self.add_widget(menu_wrap)

        # Header
        self.header = HeaderBar(app=self.app)
        self.header.size_hint_y = None
        self.header.height = dp(48)
        self.add_widget(self.header)

        # Tabs
        self.tabs = TabbedPanel(
            do_default_tab=False,
            tab_pos='top_mid',
            background_color=C['bg'],
            border=[0, 0, 0, 0],
        )
        self._add_tabs()
        self.tabs.bind(current_tab=self._on_tab_changed)
        self.add_widget(self.tabs)

        if self.tabs.tab_list:
            self.tabs.switch_to(self.tabs.tab_list[0])

        Clock.schedule_interval(self._tick_unread, 30)
        Clock.schedule_once(self._initial_load, 0.5)

    def _initial_load(self, dt):
        """Первичная загрузка — только активная вкладка."""
        print('[main] начальная загрузка данных...')
        try:
            # Помечаем ВСЕ вкладки «грязными», кроме активной
            current = self.tabs.current_tab
            for key, widget in self.tab_widgets.items():
                widget._dirty = (widget.parent is not current)

            # Обновляем только активную
            self.app.refresh_all()
        except Exception as e:
            print(f'[main] ошибка загрузки: {e}')

    def _add_tabs(self):
        app = self.app
        self.tab_widgets = {}

        def add(key, title, widget):
            self.tab_widgets[key] = widget
            item = TabbedPanelItem(text=title)
            item.background_normal = ''
            item.background_down = ''
            item.background_color = C['panel'] 
            item.color = C['dark']  
            item.add_widget(widget)
            self.tabs.add_widget(item)

        if app.has_view_permission('inventory'):
            add('inventory', ' 📦 СКЛАД ', InventoryTab(app=app))
        if app.has_view_permission('machines'):
            add('machines', ' ⚙ НА СТАНКАХ ', MachinesTab(app=app))
        if app.has_view_permission('reserve'):
            add('reserve', ' ⏳ В РЕЗЕРВЕ ', ReserveTab(app=app))
        if app.has_view_permission('history'):
            add('history', ' ▤ ЖУРНАЛ ', HistoryTab(app=app))
        if app.has_view_permission('requests'):
            add('requests', ' 📋 ЗАЯВКИ ', RequestsTab(app=app))
        if app.has_view_permission('export'):
            add('export', ' 📤 ЭКСПОРТ ', ExportTab(app=app))

        print(f'[main] вкладок: {len(self.tab_widgets)}')

    def _on_tab_changed(self, *_):
        """Обновить крошки + обновить/пометить вкладки."""
        try:
            current = self.tabs.current_tab
            if not current:
                return
            self.header.set_breadcrumb(clean_tab_label(current.text))

            # Определяем активную вкладку
            for key, widget in self.tab_widgets.items():
                if widget.parent is current:
                    widget._dirty = False
                    widget.refresh()
                else:
                    widget._dirty = True
        except Exception as e:
            print(f'[_on_tab_changed] {e}')

    def _tick_unread(self, *_):
        try:
            count = 0
            svc = getattr(self.app, 'chat_service', None)
            if svc and hasattr(svc, 'get_unread_count'):
                count = svc.get_unread_count(self.app.current_user_id)
            self.header.set_chat_badge(count)
        except Exception:
            pass