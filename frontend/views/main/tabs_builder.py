# frontend/views/main/tabs_builder.py
"""Строитель вкладок главного окна (Kivy TabbedPanel)."""
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

from frontend.views.tabs.inventory_tab import InventoryTab
from frontend.views.tabs.machines_tab import MachinesTab
from frontend.views.tabs.reserve_tab import ReserveTab
from frontend.views.tabs.history_tab import HistoryTab
from frontend.views.tabs.requests_tab import RequestsTab
from frontend.views.tabs.export_tab import ExportTab


class TabsBuilder:
    """Строит TabbedPanel и наполняет его вкладками."""

    def __init__(self, app, **kw):
        self.app = app
        self.tab_widgets = {}

    def build(self) -> TabbedPanel:
        panel = TabbedPanel(
            do_default_tab=False,
            tab_pos='top_mid',
        )
        self.panel = panel

        def add(key, title, widget):
            self.tab_widgets[key] = widget
            item = TabbedPanelItem(text=title)
            item.add_widget(widget)
            panel.add_widget(item)

        app = self.app
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

        return panel

    # ─── Импорт/экспорт ───
    #
    # Всё делегируется в ExportTab, где уже реализованы
    # кросс-платформенные диалоги (_ask_save_path, _show_message).

    def _get_export_tab(self):
        from frontend.views.tabs.export_tab import ExportTab
        # ищем уже созданный экземпляр в main_screen
        try:
            return self.app.main_screen.tab_widgets.get('export')
        except Exception:
            return None

    def open_import_for(self, kind: str) -> None:
        if kind == 'tools':
            self._import_tools_csv()

    def open_export_for(self, kind: str) -> None:
        if kind == 'tools':
            self._export_tools_csv()
        elif kind == 'tools_xlsx':
            self._export_tools_xlsx()
        elif kind == 'machines_xlsx':
            self._export_machines_xlsx()

    # ─── Импорт склада из CSV ───

    def _import_tools_csv(self):
        """Импорт склада из CSV через диалог ExportTab."""
        tab = self._get_export_tab()
        if tab is None:
            print('[tabs_builder] вкладка export недоступна')
            return

        from shared.excel.csv_io import import_tools_from_csv

        def _do_import(path):
            if not path:
                return
            try:
                result = import_tools_from_csv(path)
            except Exception as e:
                tab._show_message("Ошибка импорта", str(e))
                return

            if result['imported'] == 0 and result['updated'] == 0:
                tab._show_message(
                    "Импорт",
                    "Ничего не импортировано.\n\n"
                    f"Ошибок: {result['errors']}\n"
                    f"Пропущено пустых: {result['skipped_empty']}",
                )
                return

            tab._show_message(
                "Импорт завершён",
                f"Добавлено: {result['imported']}\n"
                f"Обновлено: {result['updated']}\n"
                f"Ошибок: {result['errors']}",
            )
            try:
                self.app.refresh_all()
            except Exception:
                pass

        # У ExportTab нет _ask_open_path — используем tkinter/plyer внутри
        # Сделаем локальный аналог через tkinter:
        from kivy.utils import platform
        if platform == 'android':
            try:
                from plyer import filechooser
                filechooser.open_file(
                    on_selection=lambda paths: _do_import(
                        paths[0] if paths else None
                    ),
                    filters=[("*.csv", "*.txt")],
                )
            except Exception as e:
                tab._show_message("Ошибка", f"Файловый диалог: {e}")
            return

        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()
            _do_import(path)
        except Exception as e:
            tab._show_message("Ошибка", f"Файловый диалог: {e}")

    # ─── Экспорт CSV ───

    def _export_tools_csv(self):
        from datetime import datetime
        from shared.excel.csv_io import export_tools_to_csv
        tab = self._get_export_tab()
        if tab is None:
            return

        default_name = f"sklad_all_{datetime.now():%Y-%m-%d_%H-%M}.csv"

        def _do_export(path):
            if not path:
                return
            try:
                count = export_tools_to_csv(path, only_available=False)
            except Exception as e:
                tab._show_message("Ошибка экспорта", str(e))
                return
            if count == 0:
                tab._show_message("Экспорт", "Нет данных для экспорта.")
                return
            tab._show_message("Экспорт завершён",
                              f"Строк: {count}\nФайл: {path}")

        tab._ask_save_path(default_name, _do_export)

    # ─── Экспорт XLSX склада ───

    def _export_tools_xlsx(self):
        from datetime import datetime
        from shared.excel.tools_excel import export_tools_to_excel
        tab = self._get_export_tab()
        if tab is None:
            return

        default_name = f"sklad_available_{datetime.now():%Y-%m-%d_%H-%M}.xlsx"

        def _do_export(path):
            if not path:
                return
            try:
                count = export_tools_to_excel(path, only_available=True)
            except Exception as e:
                tab._show_message("Ошибка экспорта", str(e))
                return
            if count == 0:
                tab._show_message("Экспорт", "Нет данных для экспорта.")
                return
            tab._show_message("Экспорт завершён", f"Файл сохранён:\n{path}")

        tab._ask_save_path(default_name, _do_export)

    # ─── Экспорт XLSX станков ───

    def _export_machines_xlsx(self):
        from datetime import datetime
        from shared.excel.machines_excel import export_machines_to_excel
        tab = self._get_export_tab()
        if tab is None:
            return

        default_name = f"machines_{datetime.now():%Y-%m-%d_%H-%M}.xlsx"

        def _do_export(path):
            if not path:
                return
            try:
                count = export_machines_to_excel(path)
            except Exception as e:
                tab._show_message("Ошибка экспорта", str(e))
                return
            if count == 0:
                tab._show_message("Экспорт", "Нет данных для экспорта.")
                return
            tab._show_message("Экспорт завершён", f"Файл сохранён:\n{path}")

        tab._ask_save_path(default_name, _do_export)