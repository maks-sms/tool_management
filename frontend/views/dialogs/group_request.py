# frontend/views/dialogs/group_request.py
"""Создание групповой заявки из нескольких инструментов."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from frontend.widgets.modern_dialog import ModernDialog
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.styled_fields import StyledTextInput, LabeledField


class CreateGroupRequestDialog(ModernDialog):
    """Создание групповой заявки из нескольких инструментов."""

    def __init__(self, app, selected_tools, **kw):
        self.app = app
        self.selected_tools = selected_tools
        self._rows = []   # [(tool_dict, qty_input)]

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))

        # Заголовок
        self.title_lbl = Label(
            text=f'Групповая заявка — {len(selected_tools)} позиций',
            bold=True, size_hint_y=None, height=dp(26),
            color=(0.17, 0.24, 0.31, 1),
        )
        body.add_widget(self.title_lbl)

        # ─── Скролл с позициями ───
        self.scroll = ScrollView(size_hint=(1, 1))

        self.grid = GridLayout(cols=5, size_hint_y=None, spacing=dp(6))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        body.add_widget(self.scroll)

        # Заголовки таблицы
        for h in ('Код', 'Артикул', 'Остаток', 'Кол-во', ''):
            self.grid.add_widget(Label(
                text=h, bold=True, size_hint_y=None, height=dp(22),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='center', valign='middle',
            ))

        # Заполняем позиции
        for t in selected_tools:
            self._add_row(t)

        # ─── Кнопка «Добавить инструмент» ───
        add_row = BoxLayout(size_hint_y=None, height=dp(36),
                            spacing=dp(6))
        add_row.add_widget(ModernButton(
            text='➕ Добавить инструмент', color='success',
            size_hint=(None, None), size=(dp(200), dp(34)),
            on_release=lambda *_: self._add_tool(),
        ))
        add_row.add_widget(BoxLayout())
        body.add_widget(add_row)

        # ─── Общая причина ───
        self.reason = StyledTextInput(
            text='Пополнение склада',
            size_hint_y=None, height=dp(32),
        )
        body.add_widget(LabeledField(
            label='Общая причина закупки:',
            widget=self.reason,
            size_hint_y=None,
        ))

        # ─── Общий комментарий ───
        self.comment = StyledTextInput(
            text='', multiline=True,
            size_hint_y=None, height=dp(60),
        )
        body.add_widget(LabeledField(
            label='Общий комментарий:',
            widget=self.comment,
            size_hint_y=None,
        ))

        # ─── Кнопки ───
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='✅ Создать', color='success', size_hint=(1, 1),
            on_release=lambda *_: self._save(),
        ))
        row.add_widget(ModernButton(
            text='❌ Отмена', color='danger', size_hint=(1, 1),
            on_release=lambda *_: self.dismiss(),
        ))
        body.add_widget(row)

        kw.pop('size_hint', None)
        kw.setdefault('size', (820, 600))
        super().__init__(title='Создание групповой заявки', body=body, **kw)

    # ─── Работа с позициями ────────────────────────────────────

    def _add_row(self, tool):
        code = tool.get('inner_code', '')
        articul = tool.get('articul', '')
        current_qty = tool.get('current_qty', 0)

        # рекомендуемое количество
        qty = 1
        if current_qty == 0:
            qty = 5
        elif current_qty < 3:
            qty = 3

        self.grid.add_widget(Label(
            text=code, size_hint_y=None, height=dp(30),
            color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
            halign='center', valign='middle',
        ))
        self.grid.add_widget(Label(
            text=articul, size_hint_y=None, height=dp(30),
            color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
            halign='center', valign='middle',
        ))
        self.grid.add_widget(Label(
            text=str(current_qty), size_hint_y=None, height=dp(30),
            color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
            halign='center', valign='middle',
        ))

        qty_inp = StyledTextInput(
            text=str(qty), input_filter='int',
            size_hint_y=None, height=dp(30),
        )
        self.grid.add_widget(qty_inp)

        del_btn = ModernButton(
            text='🗑', color='danger',
            size_hint_y=None, height=dp(30),
            size=(dp(36), dp(30)),
        )
        self.grid.add_widget(del_btn)

        rec = {'tool': tool, 'input': qty_inp}
        self._rows.append(rec)
        del_btn.bind(on_release=lambda *_: self._remove_row(rec))

    def _remove_row(self, rec):
        if rec not in self._rows:
            return
        self._rows.remove(rec)
        # Перерисовываем таблицу
        self._rebuild_grid()

    def _rebuild_grid(self):
        self.grid.clear_widgets()
        # Заголовки
        for h in ('Код', 'Артикул', 'Остаток', 'Кол-во', ''):
            self.grid.add_widget(Label(
                text=h, bold=True, size_hint_y=None, height=dp(22),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='center', valign='middle',
            ))
        # Строки
        rows = self._rows[:]
        self._rows = []
        for rec in rows:
            tool = rec['tool']
            current_qty = tool.get('current_qty', 0)

            self.grid.add_widget(Label(
                text=tool.get('inner_code', ''),
                size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='center', valign='middle',
            ))
            self.grid.add_widget(Label(
                text=tool.get('articul', ''),
                size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='center', valign='middle',
            ))
            self.grid.add_widget(Label(
                text=str(current_qty), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='center', valign='middle',
            ))

            qty_inp = StyledTextInput(
                text=rec['input'].text or '1',
                input_filter='int',
                size_hint_y=None, height=dp(30),
            )
            self.grid.add_widget(qty_inp)

            del_btn = ModernButton(
                text='🗑', color='danger',
                size_hint_y=None, height=dp(30),
                size=(dp(36), dp(30)),
            )
            self.grid.add_widget(del_btn)

            new_rec = {'tool': tool, 'input': qty_inp}
            self._rows.append(new_rec)
            del_btn.bind(on_release=lambda *_, r=new_rec: self._remove_row(r))

        self.title_lbl.text = f'Групповая заявка — {len(self._rows)} позиций'

    def _add_tool(self):
        """Открыть диалог выбора инструмента."""
        current_codes = [r['tool']['inner_code'] for r in self._rows]

        def on_select(tool_info, qty):
            # Если уже есть — не добавляем
            if tool_info['inner_code'] in current_codes:
                return
            tool_info['_recommended_qty'] = qty
            self._rows.append({
                'tool': {
                    'tool_id': tool_info['tool_id'],
                    'inner_code': tool_info['inner_code'],
                    'articul': tool_info['articul'],
                    'type': tool_info['type'],
                    'diameter': tool_info['diameter'],
                    'brand': tool_info['brand'],
                    'current_qty': tool_info['current_qty'],
                },
                'input': None,   # заполним в _rebuild_grid
            })
            self._rebuild_grid()

        from frontend.views.dialogs.tool_selector import ToolSelectorDialog
        ToolSelectorDialog(
            self.app,
            on_select=on_select,
            current_tools=current_codes,
            title='Выбор инструмента для групповой заявки',
        ).open()

    # ─── Сохранение ────────────────────────────────────────────

    def _save(self):
        items = []
        for rec in self._rows:
            t = rec['tool']
            inp = rec['input']
            if inp is None:
                continue
            try:
                q = int(inp.text or '0')
            except ValueError:
                continue
            if q <= 0:
                continue
            items.append({
                'tool_id': t['tool_id'],
                'inner_code': t['inner_code'],
                'articul': t['articul'],
                'type': t.get('type', ''),
                'diameter': t.get('diameter', ''),
                'brand': t.get('brand', ''),
                'requested_qty': q,
            })

        if not items:
            return

        try:
            self.app.group_request_service.create(
                name='Групповая заявка',
                requester_id=self.app.current_user_id,
                requester_name=self.app.get_current_worker_name(),
                items=items,
                reason=self.reason.text.strip() or 'Пополнение склада',
                comment=self.comment.text.strip(),
            )
        except Exception as e:
            print(f'[CreateGroupRequestDialog._save] ошибка создания: {e}')
            return

        # 1. Явно обновляем вкладку заявок
        try:
            self.app.refresh_requests_now()
        except Exception as e:
            print(f'[CreateGroupRequestDialog._save] refresh_requests_now: {e}')

        # 2. Обновляем активную вкладку (Склад)
        try:
            self.app.refresh_all()
        except Exception as e:
            print(f'[CreateGroupRequestDialog._save] refresh_all: {e}')

        self.dismiss()