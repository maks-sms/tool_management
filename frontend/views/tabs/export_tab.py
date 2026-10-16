# frontend/views/tabs/export_tab.py
"""Универсальная вкладка экспорта (аналог client_desktop)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line

from frontend.theme import C
from frontend.widgets.modern_button import ModernButton


class ExportTab(BoxLayout):
    """Вкладка экспорта."""

    def __init__(self, app, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('spacing', 0)
        kw.setdefault('padding', 0)
        super().__init__(**kw)

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.app = app

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(6))

        content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(12), dp(10), dp(12), dp(12)],
        )
        content.bind(minimum_height=content.setter('height'))

        # ─── Заголовок ───
        content.add_widget(self._label(
            '📤  Экспорт данных',
            bold=True, size=dp(16), color=C['primary'], height=dp(26),
        ))
        content.add_widget(self._label(
            'Выгрузка данных в файл Excel.',
            size=dp(12), color=C['gray'], height=dp(18),
        ))

        # ─── Карточки ───
        self._card(
            content,
            '📦  Экспорт склада',
            'Выгрузка инструмента, который есть на складе (остаток > 0).',
            [('📊  Экспорт в Excel', 'success', self._export_tools_xlsx)],
        )
        self._card(
            content,
            '⚙  Инструмент на станках',
            'Выгрузка всех размещений на станках.',
            [('📊  Экспорт в Excel', 'success', self._export_machines_xlsx)],
        )

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    # ─── Хелперы ───

    def _label(self, text, *, bold=False, size=dp(13),
               color=None, height=None):
        """Label с корректным левым выравниванием и подгонкой высоты."""
        lbl = Label(
            text=text,
            bold=bold,
            font_size=size,
            color=color or C['text'],
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=height or dp(20),
        )
        # Ключевое: text_size = ширина лейбла, иначе halign не работает
        lbl.bind(width=lambda i, w: setattr(
            i, 'text_size', (w, None)))
        return lbl

    # ─── Карточка ───

    def _card(self, parent, title, desc, buttons):
        """Компактная карточка: заголовок + описание + кнопки справа."""
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(12), dp(10), dp(12), dp(10)],
            spacing=dp(4),
        )

        with card.canvas.before:
            Color(*C['panel'])
            card._bg = Rectangle(pos=card.pos, size=card.size)
        with card.canvas.after:
            Color(*C['border'])
            card._border = Line(
                rectangle=(card.x, card.y, card.width, card.height),
                width=1,
            )

        def _sync(inst, *_):
            inst._bg.pos = inst.pos
            inst._bg.size = inst.size
            inst._border.rectangle = (
                inst.x, inst.y, inst.width, inst.height)

        card.bind(pos=_sync, size=_sync)

        # Заголовок
        card.add_widget(self._label(
            title, bold=True, size=dp(14),
            color=C['primary'], height=dp(22),
        ))

        # Описание — высота по содержимому (не фиксируем 36)
        desc_lbl = Label(
            text=desc,
            color=C['gray'],
            font_size=dp(12),
            halign='left',
            valign='top',
            size_hint_y=None,
        )
        desc_lbl.bind(
            width=lambda i, w: setattr(i, 'text_size', (w, None)),
            texture_size=lambda i, ts: setattr(i, 'height', ts[1]),
        )
        card.add_widget(desc_lbl)

        # Кнопки — справа
        row = BoxLayout(
            size_hint_y=None,
            height=dp(36),
            spacing=dp(6),
        )
        row.add_widget(BoxLayout())  # распорка слева
        for text, color, cb in buttons:
            btn = ModernButton(
                text=text,
                color=color,
                size_hint=(None, None),
                size=(dp(180), dp(34)),
            )
            btn.bind(on_release=lambda *_a, f=cb: f())
            row.add_widget(btn)
        card.add_widget(row)

        # Высота карточки = сумма детей + padding + spacing
        def _fit(inst, *_):
            h = inst.padding[1] + inst.padding[3]
            for i, ch in enumerate(inst.children):
                h += ch.height
            h += inst.spacing * (len(inst.children) - 1)
            inst.height = h

        card.bind(minimum_height=_fit)
        parent.add_widget(card)

    # ─── Экспорты ───

    def _export_tools_xlsx(self):
        """Экспорт склада (только остаток > 0) в .xlsx."""
        from datetime import datetime
        from shared.excel.tools_excel import export_tools_to_excel

        default_name = f"sklad_available_{datetime.now():%Y-%m-%d_%H-%M}.xlsx"

        def _do_export(path):
            if not path:
                return
            try:
                count = export_tools_to_excel(path, only_available=True)
            except ImportError:
                self._show_message(
                    "Ошибка",
                    "Библиотека openpyxl не установлена.\n\n"
                    "Установите: pip install openpyxl",
                )
                return
            except Exception as e:
                self._show_message("Ошибка экспорта", str(e))
                return

            if count == 0:
                self._show_message("Экспорт", "Нет данных для экспорта.")
                return

            self._show_message("Экспорт завершён", f"Файл сохранён:\n{path}")

        self._ask_save_path(default_name, _do_export)

    def _export_machines_xlsx(self):
        """Экспорт инструмента на станках в .xlsx."""
        from datetime import datetime
        from shared.excel.machines_excel import export_machines_to_excel

        default_name = f"machines_{datetime.now():%Y-%m-%d_%H-%M}.xlsx"

        def _do_export(path):
            if not path:
                return
            try:
                count = export_machines_to_excel(path)
            except ImportError:
                self._show_message(
                    "Ошибка",
                    "Библиотека openpyxl не установлена.\n\n"
                    "Установите: pip install openpyxl",
                )
                return
            except Exception as e:
                self._show_message("Ошибка экспорта", str(e))
                return

            if count == 0:
                self._show_message("Экспорт", "Нет данных для экспорта.")
                return

            self._show_message("Экспорт завершён", f"Файл сохранён:\n{path}")

        self._ask_save_path(default_name, _do_export)

    # ─── Универсальные диалоги (plyer + fallback на tkinter) ───

    def _ask_save_path(self, default_name, on_result):
        """Спросить путь сохранения. Windows → tkinter, Android → plyer."""
        from kivy.utils import platform

        if platform == 'android':
            try:
                from plyer import filechooser
                filechooser.save_file(
                    on_selection=lambda paths: on_result(
                        paths[0] if paths else None
                    ),
                    filters=[("*.xlsx", "*.csv")],
                )
                return
            except Exception as e:
                self._show_message("Ошибка", f"Файловый диалог: {e}")
                return

        # Desktop (Windows / Linux / macOS)
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile=default_name,
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            )
            root.destroy()
            on_result(path)
        except Exception as e:
            self._show_message("Ошибка", f"Файловый диалог: {e}")

    def _ask_open_path(self, on_result, filters=None):
        """Спросить путь для открытия файла.
        Windows → tkinter, Android → plyer.

        :param on_result: callback(path) — path=None, если отменили
        :param filters:   список фильтров для plyer (Android);
                          на desktop всегда CSV/TXT/All.
        """
        from kivy.utils import platform

        if platform == 'android':
            try:
                from plyer import filechooser
                filechooser.open_file(
                    on_selection=lambda paths: on_result(
                        paths[0] if paths else None
                    ),
                    filters=filters or [],
                )
            except Exception as e:
                self._show_message("Ошибка", f"Файловый диалог: {e}")
            return

        # Desktop (Windows / Linux / macOS)
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
            on_result(path)
        except Exception as e:
            self._show_message("Ошибка", f"Файловый диалог: {e}")

    def _show_message(self, title, message):
        """Показать сообщение: Android → Kivy Popup, Desktop → tkinter."""
        from kivy.utils import platform

        if platform == 'android':
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.label import Label
            from frontend.widgets.modern_button import ModernButton

            box = BoxLayout(orientation='vertical', padding=16, spacing=8)
            box.add_widget(Label(text=str(message), halign='center'))
            btn = ModernButton(text='OK', color='info',
                               size_hint=(None, None), size=(120, 40))
            btn.pos_hint = {'center_x': 0.5}
            box.add_widget(btn)
            popup = Popup(title=title, content=box,
                          size_hint=(None, None), size=(400, 200))
            btn.bind(on_release=lambda *_: popup.dismiss())
            popup.open()
            return

        # Desktop
        try:
            from tkinter import messagebox
            messagebox.showinfo(title, message)
        except Exception:
            print(f'[{title}] {message}')

    def refresh(self):
        pass