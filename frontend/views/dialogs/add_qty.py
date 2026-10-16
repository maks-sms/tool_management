from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import StyledTextInput, LabeledField


class AddQuantityDialog(ModernDialog):
    def __init__(self, app, tool_id, tool_code, current_qty, **kw):
        self.app = app
        self.tool_id = tool_id
        self.tool_code = tool_code
        self.current_qty = current_qty

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        self.qty = StyledTextInput(
            text='1',
            input_filter='int',
            hint_text='Введите количество',
        )
        grid.add_widget(LabeledField(
            label=f'Инструмент: {tool_code}  |  Остаток: {current_qty}',
            widget=self.qty,
        ))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='OK', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._confirm(),
        ))
        bx.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (440, 200))
        super().__init__(title='Поступление инструмента', body=bx, **kw)

    def _confirm(self):
        try:
            qty = int(self.qty.text or '0')
        except ValueError:
            return
        if qty <= 0:
            return
        worker = self.app.get_current_worker_name()
        updated = self.app.tool_service.update_quantity(self.tool_id, qty)
        if updated:
            self.app.history_service.add_receipt(self.tool_code, qty, worker)
            self.app.refresh_all()
            self.dismiss()