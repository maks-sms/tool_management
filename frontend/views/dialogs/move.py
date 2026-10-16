from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import (
    StyledTextInput, StyledSpinner, LabeledField,
)


class MoveToMachineDialog(ModernDialog):
    def __init__(self, app, tool_id, tool_code, current_qty, **kw):
        self.app = app
        self.tool_id = tool_id
        self.tool_code = tool_code
        self.current_qty = current_qty

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        self.qty = StyledTextInput(text='1', input_filter='int')
        grid.add_widget(LabeledField(
            label=f'Инструмент: {tool_code}  |  Доступно: {current_qty}',
            widget=self.qty,
        ))

        machines = self.app.machine_service.get_all() or []
        self.target = StyledSpinner(
            text=machines[0] if machines else '',
            values=list(machines),
        )
        grid.add_widget(LabeledField(label='Станок:', widget=self.target))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='Переместить', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._confirm(),
        ))
        bx.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (440, 240))
        super().__init__(title='Перемещение на станок', body=bx, **kw)

    def _confirm(self):
        try:
            qty = int(self.qty.text or '0')
        except ValueError:
            return
        if qty <= 0 or qty > self.current_qty:
            return
        machine = self.target.text
        if not machine:
            return
        worker = self.app.get_current_worker_name()
        if self.app.placement_service.move_to_machine(
                self.tool_id, self.tool_code, qty, machine, worker):
            self.app.refresh_all()
            self.dismiss()


class MoveToReserveDialog(ModernDialog):
    def __init__(self, app, tool_id, tool_code, current_qty, **kw):
        self.app = app
        self.tool_id = tool_id
        self.tool_code = tool_code
        self.current_qty = current_qty

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        self.qty = StyledTextInput(text='1', input_filter='int')
        grid.add_widget(LabeledField(
            label=f'Инструмент: {tool_code}  |  Доступно: {current_qty}',
            widget=self.qty,
        ))

        self.task = StyledTextInput(hint_text='Например: заказ №42')
        grid.add_widget(LabeledField(label='Задача (назначение):',
                                     widget=self.task))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='Переместить', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._confirm(),
        ))
        bx.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (440, 240))
        super().__init__(title='Перемещение в резерв', body=bx, **kw)

    def _confirm(self):
        try:
            qty = int(self.qty.text or '0')
        except ValueError:
            return
        if qty <= 0 or qty > self.current_qty:
            return
        task = self.task.text.strip()
        if not task:
            return
        worker = self.app.get_current_worker_name()
        if self.app.placement_service.move_to_reserve(
                self.tool_id, self.tool_code, qty, task, worker):
            self.app.refresh_all()
            self.dismiss()