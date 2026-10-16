# frontend/views/db_config_screen.py
"""Выбор пути к БД. Виджет без своего App.

Умеет:
  - показать текущий путь к БД,
  - создать новую БД в папке приложения,
  - выбрать существующий файл БД через системный диалог,
  - показать ошибку, если ничего не получилось.
"""
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.utils import platform

from frontend.config import APP_NAME, get_db_path, save_db_path
from frontend.theme import C
from frontend.widgets.modern_button import ModernButton


class DBConfigScreen(BoxLayout):
    def __init__(self, on_done=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', dp(24))
        kw.setdefault('spacing', dp(10))
        super().__init__(**kw)

        self._on_done = on_done

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build()

    def _build(self):
        self.add_widget(Label(
            text=APP_NAME, bold=True, font_size=dp(20),
            color=C['primary'], size_hint_y=None, height=dp(34),
        ))
        self.add_widget(Label(
            text='Путь к базе данных склада:',
            color=C['secondary'], bold=True,
            size_hint_y=None, height=dp(20),
        ))

        # Строка: поле ввода + кнопка «Обзор…»
        row_input = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(36),
            spacing=dp(6),
        )

        self.path_inp = TextInput(
            text=get_db_path() or '', multiline=False,
            size_hint=(1, 1), font_size=dp(13),
            background_normal='', background_active='',
            background_color=C['input_bg'],
            foreground_color=C['input_fg'],
            cursor_color=C['input_fg'],
            padding=[dp(8), dp(6)],
        )
        row_input.add_widget(self.path_inp)

        browse_btn = ModernButton(
            text='📂 Обзор',
            color='info',
            size_hint=(None, 1),
            width=dp(110),
        )
        browse_btn.bind(on_release=lambda *_: self._browse())
        row_input.add_widget(browse_btn)

        self.add_widget(row_input)

        # Вторая строка: подсказки
        row_hint = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(30),
            spacing=dp(6),
        )
        row_hint.add_widget(ModernButton(
            text='📍 Путь по умолчанию',
            color='info',
            size_hint=(1, 1),
            on_release=lambda *_: self._fill_default_path(),
        ))
        self.add_widget(row_hint)

        # Кнопки действий
        row_buttons = BoxLayout(
            size_hint_y=None, height=dp(42),
            spacing=dp(8),
        )
        row_buttons.add_widget(ModernButton(
            text='Создать новую',
            color='warning',
            on_release=lambda *_: self._create_new(),
        ))
        row_buttons.add_widget(ModernButton(
            text='Продолжить',
            color='success',
            on_release=lambda *_: self._save(),
        ))
        row_buttons.add_widget(ModernButton(
            text='Выход',
            color='danger',
            on_release=lambda *_: self._finish(None),
        ))
        self.add_widget(row_buttons)

        # Подсказка
        self.info_lbl = Label(
            text='',
            color=C['gray'],
            font_size=dp(11),
            size_hint_y=None,
            height=dp(20),
        )
        self.add_widget(self.info_lbl)

    # ─── Заполнить путь по умолчанию ───

    def _fill_default_path(self):
        """Заполнить поле путём по умолчанию (папка приложения)."""
        try:
            from shared.config import get_app_dir, DEFAULT_DB_NAME
            app_dir = get_app_dir()
            default_path = os.path.join(app_dir, DEFAULT_DB_NAME)
            self.path_inp.text = default_path
            self.info_lbl.text = f'Путь по умолчанию: {default_path}'
        except Exception as e:
            self._show_error(f'Ошибка: {e}')

    # ─── Выбор файла БД ───

    def _browse(self):
        """Выбрать существующий файл БД."""
        if platform == 'android':
            try:
                from plyer import filechooser
                print('[db_config] открываю filechooser...')
                filechooser.open_file(
                    on_selection=self._on_android_file_selected,
                    filters=[("*.db", "SQLite DB"), ("*.*", "All files")],
                )
                self.info_lbl.text = 'Выберите файл БД...'
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._show_error(
                    f'Не удалось открыть диалог:\n{e}\n\n'
                    'Нажмите «Путь по умолчанию» или «Создать новую».'
                )
            return

        # Desktop
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title='Выберите файл базы данных',
                filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")],
            )
            root.destroy()
            if path:
                self.path_inp.text = path
                self.info_lbl.text = f'Выбран: {os.path.basename(path)}'
        except Exception as e:
            self._show_error(f'Ошибка выбора файла:\n{e}')

    def _on_android_file_selected(self, paths):
        """Callback от plyer на Android."""
        print(f'[db_config] on_android_file_selected: {paths!r}')
        if not paths:
            self.info_lbl.text = 'Файл не выбран'
            return
        path = paths[0]
        print(f'[db_config] выбран путь: {path!r}')
        self.path_inp.text = path
        self.info_lbl.text = f'Выбран: {os.path.basename(path)}'

    # ─── Создать новую БД ───

    def _create_new(self):
        from shared.services.database import create_default_db
        try:
            new_path = create_default_db()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f'Ошибка создания БД:\n{e}')
            return

        if not new_path:
            self._show_error(
                'Не удалось создать базу данных.\n\n'
                'Проверьте права доступа к папке приложения.\n'
                'Либо выберите существующий файл БД кнопкой «Обзор».'
            )
            return

        self.path_inp.text = new_path
        self.info_lbl.text = 'База создана. Нажмите «Продолжить».'

    # ─── Продолжить ───

    def _save(self):
        from shared.services.database import init_db, create_default_db

        p = self.path_inp.text.strip()

        if not p:
            # Поле пустое → создаём БД по умолчанию
            try:
                new_path = create_default_db()
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._show_error(f'Ошибка создания БД:\n{e}')
                return

            if not new_path:
                self._show_error(
                    'Не удалось создать базу данных по умолчанию.\n\n'
                    'Нажмите «Путь по умолчанию», затем «Создать новую», '
                    'или выберите существующий файл кнопкой «Обзор».'
                )
                return

            self._finish(new_path)
            return

        # Поле заполнено → пробуем использовать указанный путь
        try:
            save_db_path(p)
            if init_db(p):
                self._finish(p)
                return
        except Exception as e:
            print(f'[db_config] ошибка init_db({p}): {e}')

        # Не получилось — пробуем создать новую
        try:
            new_path = create_default_db()
            if new_path:
                self._finish(new_path)
                return
        except Exception as e:
            print(f'[db_config] ошибка create_default_db: {e}')

        self._show_error(
            f'Не удалось использовать путь:\n{p}\n\n'
            'Файл не существует или недоступен.\n'
            'Нажмите «Путь по умолчанию» или «Создать новую».'
        )

    # ─── Сообщения ───

    def _show_error(self, message: str):
        box = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        box.add_widget(Label(text=message, halign='center'))
        btn = ModernButton(
            text='OK', color='info',
            size_hint=(None, None), size=(dp(120), dp(40)),
        )
        btn.pos_hint = {'center_x': 0.5}
        box.add_widget(btn)
        popup = Popup(
            title='Ошибка', content=box,
            size_hint=(None, None), size=(dp(420), dp(280)),
        )
        btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def _finish(self, path):
        if self._on_done:
            self._on_done(path)
