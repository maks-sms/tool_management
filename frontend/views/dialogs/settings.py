from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from frontend.config import get_db_path, save_db_path
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.styled_fields import StyledTextInput, LabeledField


class SettingsDialog(ModernDialog):
    def __init__(self, app, **kw):
        self.app = app

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        self.path_inp = StyledTextInput(text=get_db_path() or '')
        grid.add_widget(LabeledField(label='Путь к базе данных:',
                                     widget=self.path_inp))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='Сохранить', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._save(),
        ))
        bx.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (560, 180))
        super().__init__(title='Настройки', body=bx, **kw)

    def _save(self):
        p = self.path_inp.text.strip()
        if not p:
            return
        from shared.services.database import init_db
        if init_db(p):
            save_db_path(p)
            self.dismiss()