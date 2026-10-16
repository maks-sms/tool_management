# frontend/views/dialogs/request.py
"""Создание обычной заявки на закупку."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import (
    StyledTextInput, StyledSpinner, LabeledField,
)


class CreateRequestDialog(ModernDialog):
    def __init__(self, app, tool_code, tool_articul, tool_type,
                 tool_diameter, tool_brand, current_qty, **kw):
        self.app = app
        self.tool_code = tool_code
        self.tool_articul = tool_articul
        self.tool_type = tool_type
        self.tool_diameter = tool_diameter
        self.tool_brand = tool_brand
        self.current_qty = current_qty

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        info = f'Код: {tool_code} | Арт: {tool_articul}'
        if tool_type:
            info += f' | Тип: {tool_type}'
        if tool_brand:
            info += f' | Пр-ль: {tool_brand}'

        self.qty = StyledTextInput(text='1', input_filter='int')
        grid.add_widget(LabeledField(
            label=f'{info}  |  Остаток: {current_qty}',
            widget=self.qty,
        ))

        self.reason = StyledSpinner(
            text='Пополнение склада',
            values=['Пополнение склада', 'Для выполнения заказа',
                    'Замена изношенного', 'Расширение номенклатуры',
                    'Срочная потребность', 'Другое'],
        )
        grid.add_widget(LabeledField(label='Причина закупки *:',
                                     widget=self.reason))

        comment_text = ''
        if current_qty == 0:
            comment_text = f'Инструмент отсутствует (остаток: {current_qty} шт.)'
        elif current_qty < 5:
            comment_text = f'Критически малый остаток: {current_qty} шт.'

        self.comment = StyledTextInput(
            text=comment_text,
            multiline=True,
            height=80,
        )
        grid.add_widget(LabeledField(label='Комментарий:',
                                     widget=self.comment))

        bx = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        bx.add_widget(grid)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='📝 Создать', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._save(),
        ))
        bx.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (560, 400))
        super().__init__(title='Создание заявки на закупку', body=bx, **kw)

    def _save(self):
        try:
            qty = int(self.qty.text or '0')
        except ValueError:
            return
        if qty <= 0:
            return
        tool = self.app.tool_service.get_by_code(self.tool_code)
        if not tool:
            return
        try:
            self.app.purchase_request_service.create(
                tool_id=tool.id, tool_code=self.tool_code,
                tool_articul=self.tool_articul, requested_qty=qty,
                reason=self.reason.text,
                requester_id=self.app.current_user_id,
                requester_name=self.app.get_current_worker_name(),
                tool_type=self.tool_type or '',
                tool_diameter=self.tool_diameter or '',
                tool_brand=self.tool_brand or '',
                comment=self.comment.text or '',
            )
        except Exception as e:
            print(f'[CreateRequestDialog._save] ошибка создания: {e}')
            return

        # 1. Явно обновляем вкладку заявок — не ждём переключения вкладок.
        try:
            self.app.refresh_requests_now()
        except Exception as e:
            print(f'[CreateRequestDialog._save] refresh_requests_now: {e}')

        # 2. Обновляем и активную вкладку (Склад) — на случай, если
        #    поменялись счётчики или что-то ещё.
        try:
            self.app.refresh_all()
        except Exception as e:
            print(f'[CreateRequestDialog._save] refresh_all: {e}')

        self.dismiss()