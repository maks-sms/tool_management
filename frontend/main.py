# frontend/main.py
"""Точка входа Kivy-клиента. Один App, последовательность экранов."""
import os
import sys
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


import sys, os, traceback

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'crash.log')

def _excepthook(exc_type, exc_value, exc_tb):
    with open(_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write('=' * 70 + '\n')
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        f.flush()
    # Пишем в stderr напрямую, минуя Kivy-редиректор
    try:
        orig_stderr = sys.__stderr__
        if orig_stderr:
            traceback.print_exception(exc_type, exc_value, exc_tb,
                                      file=orig_stderr)
            orig_stderr.flush()
    except Exception:
        pass
    sys.exit(1)

sys.excepthook = _excepthook

# ─── 1. KIVY CONFIG ───
from kivy.config import Config
Config.set('graphics', 'width', '460')
Config.set('graphics', 'height', '420')
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'borderless', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
Window.clearcolor = (0.96, 0.96, 0.97, 1)


# ─── 2. ШРИФТЫ ───
def _setup_fonts():
    """Регистрируем единый шрифт AppFont: Roboto + Symbola (эмодзи).

    AppFont-Regular.ttf и AppFont-Bold.ttf собираются скриптом
    assets/fonts/build_font.py из Roboto и Symbola.
    """
    try:
        from kivy.core.text import LabelBase
    except Exception as e:
        print(f'[fonts] {e}')
        return

    assets = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'assets', 'fonts',
    )

    regular = os.path.join(assets, 'AppFont-Regular.ttf')
    bold = os.path.join(assets, 'AppFont-Bold.ttf')

    if not os.path.exists(regular):
        print(f'[fonts] нет {regular}')
        print('[fonts] Соберите шрифт: python assets/fonts/build_font.py')
        # Fallback: Symbola, чтобы приложение запустилось хоть как-то
        symbola = os.path.join(assets, 'Symbola.ttf')
        if os.path.exists(symbola):
            LabelBase.register(
                name='AppFont',
                fn_regular=symbola,
                fn_bold=symbola,
                fn_italic=symbola,
                fn_bolditalic=symbola,
            )
            print(f'[fonts] fallback: Symbola')
        return

    try:
        LabelBase.register(
            name='AppFont',
            fn_regular=regular,
            fn_bold=bold if os.path.exists(bold) else regular,
            fn_italic=regular,
            fn_bolditalic=bold if os.path.exists(bold) else regular,
        )
        print(f'[fonts] AppFont подключён: {regular}')
    except Exception as e:
        print(f'[fonts] {e}')


_setup_fonts()


# ─── 3. ИМПОРТЫ KIVY ───
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition


# ─── 4. ХЕЛПЕР ЦЕНТРИРОВАНИЯ ───
def center_window(w, h):
    """Центрирование окна — только на desktop. На Android no-op."""
    try:
        from kivy.utils import platform
        if platform == 'android':
            return
    except Exception:
        pass

    try:
        Window.size = (w, h)
        try:
            from kivy.utils import platform
            if platform == 'win':
                import ctypes
                user32 = ctypes.windll.user32
                screen_w = user32.GetSystemMetrics(0)
                screen_h = user32.GetSystemMetrics(1)
                Window.left = (screen_w - w) // 2
                Window.top = (screen_h - h) // 2
            else:
                try:
                    Window.center_on_screen()
                except Exception:
                    pass
        except Exception as e:
            print(f'[center] {e}')
    except Exception as e:
        print(f'[center_window] {e}')


# ─── 5. КОРНЕВОЕ ПРИЛОЖЕНИЕ ───
class BootstrapApp(App):
    """
    Единое Kivy-приложение. Последовательность экранов:
        DBConfig -> License -> Auth -> Main
    Каждый экран — обычный Widget, встроенный в Screen.
    """

    title = "Tool Management"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.sm = None
        self.db_path = None
        self.user_tuple = None
        self.main_screen = None

    def build(self):
        from frontend.kv_style import apply_theme
        apply_theme()

        from frontend.theme import C
        Window.clearcolor = C['bg']

        root = BoxLayout(orientation='vertical')
        self.sm = ScreenManager(transition=NoTransition())
        root.add_widget(self.sm)

        Clock.schedule_once(self._step_start, 0)
        return root

    # ─── Переход между экранами ───
    def go_to(self, widget, size=None):
        for s in list(self.sm.screens):
            self.sm.remove_widget(s)
        screen = Screen(name='current')
        screen.add_widget(widget)
        self.sm.add_widget(screen)
        self.sm.current = 'current'
        if size:
            center_window(*size)

    # ─── Шаги ───
    def _step_start(self, dt):
        from frontend.config import get_db_path
        self.db_path = get_db_path()
        if not self.db_path or not os.path.exists(self.db_path):
            self._step_db_config()
        else:
            self._step_backup()

    def _step_db_config(self):
        from frontend.views.db_config_screen import DBConfigScreen
        screen = DBConfigScreen(on_done=self._on_db_config_done)
        self.go_to(screen, size=(640, 260))

    def _on_db_config_done(self, db_path):
        if not db_path:
            self.stop()
            return
        self.db_path = db_path
        self._step_backup()

    def _step_backup(self):
        try:
            from shared.utils.backup_utils import (
                make_backup, cleanup_old_backups, list_backups,
            )
            from datetime import datetime
            backups = list_backups(self.db_path)
            need_backup = True
            if backups:
                last_mtime = os.path.getmtime(backups[0])
                if datetime.now().timestamp() - last_mtime < 30 * 24 * 3600:
                    need_backup = False
            if need_backup:
                make_backup(self.db_path, tag='monthly')
                cleanup_old_backups(self.db_path, keep=12)
        except Exception as e:
            print(f'[autobackup] {e}')

        try:
            from shared.services.database import update_database_schema
            update_database_schema(self.db_path)
        except Exception as e:
            print(f'[schema] {e}')

        self._step_license()

    def _step_license(self):
        from shared.services.licensing.license_manager import is_activated
        if is_activated():
            self._step_auth()
            return
        from frontend.views.license_screen import LicenseScreen
        screen = LicenseScreen(on_done=self._on_license_done)
        self.go_to(screen, size=(600, 620))

    def _on_license_done(self, ok):
        if not ok:
            self.stop()
            return
        self._step_auth()

    def _step_auth(self):
        from frontend.views.auth_screen import AuthScreen
        screen = AuthScreen(on_done=self._on_auth_done)
        self.go_to(screen, size=(460, 420))

    def _on_auth_done(self, user_tuple):
        if not user_tuple:
            self.stop()
            return
        self.user_tuple = user_tuple

        from shared.services.database import DatabaseManager
        DatabaseManager.set_db_path(self.db_path)
        self._step_main()

    def _step_main(self):
        from frontend.app import WarehouseApp
        self.main_screen = WarehouseApp(
            user_tuple=self.user_tuple,
            bootstrap=self,
        )
        self.go_to(self.main_screen, size=(1100, 720))


def main():
    try:
        BootstrapApp().run()
    except Exception:
        print("=== КРИТИЧЕСКАЯ ОШИБКА ===")
        traceback.print_exc()


if __name__ == '__main__':
    main()