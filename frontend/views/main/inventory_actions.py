# frontend/views/main/inventory_actions.py
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_window import ModernWindow


class InventoryActions:
    def __init__(self, app):
        self.app = app

    def _inv_tab(self):
        tabs = getattr(self.app.main_screen, 'tab_widgets', {}) or {}
        return tabs.get('inventory')

    # ─── Вспомогательный хелпер ───

    def _finish_and_refresh(self, tab, dlg):
        """Снять _busy, пометить dirty, вызвать refresh_all, закрыть диалог.

        Порядок важен: сначала _busy=False, потом refresh_all —
        иначе refresh_all пропустит занятую вкладку.
        """
        if tab is not None:
            tab._busy = False
            tab._dirty = True
        try:
            self.app.refresh_all()
        except Exception as e:
            print(f'[inventory_actions.refresh] {e}')
        try:
            dlg.dismiss()
        except Exception:
            pass

    def _bind_busy(self, dlg, tab):
        """Автосброс _busy при закрытии диалога (крестик, Esc и т. п.)."""
        if tab is None:
            return

        def _on_dismiss(*_):
            tab._busy = False
            tab._dirty = True
        try:
            dlg.bind(on_dismiss=_on_dismiss)
        except Exception:
            pass

    # ─── Поступления ───

    def add_quantity(self):
        tab = self._inv_tab()
        if not tab or tab.tree is None:
            self._info('Внимание', 'Вкладка склада недоступна')
            return

        selected = tab.tree.get_selected_all()
        if not selected:
            self._info('Внимание', 'Выберите инструмент')
            return

        if len(selected) > 1:
            return self._bulk_add_quantity(selected)

        code = selected[0].get('inner_code', '')
        tool = self.app.tool_service.get_by_code(code)
        if not tool:
            self._info('Ошибка', 'Инструмент не найден')
            return
        self._add_qty_dialog(tool)

    def _add_qty_dialog(self, tool):
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        body.add_widget(Label(text=f"Инструмент: {tool.inner_code}",
                              bold=True, size_hint_y=None, height=dp(26)))
        body.add_widget(Label(text=f"Текущий остаток: {tool.qty_total} шт.",
                              size_hint_y=None, height=dp(22)))
        body.add_widget(Label(text="Количество для поступления:",
                              size_hint_y=None, height=dp(22)))
        inp = TextInput(text='1', multiline=False, input_filter='int',
                        size_hint_y=None, height=dp(34))
        body.add_widget(inp)

        dlg = ModernWindow(title='Поступление инструмента', body=body,
                           size=(400, 260))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='OK', color='success', size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def confirm(*_):
            try:
                qty = int(inp.text or '0')
            except ValueError:
                return
            if qty <= 0:
                return
            worker = self.app.get_current_worker_name()
            updated = self.app.tool_service.update_quantity(tool.id, qty)
            if updated:
                self.app.history_service.add_receipt(
                    tool.inner_code, qty, worker)
                self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=confirm)
        dlg.open()

    def _bulk_add_quantity(self, selected_rows):
        """Массовое поступление на несколько выбранных инструментов."""
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(6))
        body.add_widget(Label(
            text=f'Массовое поступление ({len(selected_rows)} шт.)',
            bold=True, size_hint_y=None, height=dp(26)))

        rows_data = []
        for r in selected_rows:
            code = r.get('inner_code', '')
            tool = self.app.tool_service.get_by_code(code)
            if not tool:
                continue
            rows_data.append({'tool': tool, 'qty': 1})

            line = BoxLayout(size_hint_y=None, height=dp(34),
                             spacing=dp(6))
            line.add_widget(Label(
                text=f'{code}  |  ост.: {tool.qty_total}',
                size_hint_x=0.6, color=(0.17, 0.24, 0.31, 1)))
            qty_inp = TextInput(
                text='1', multiline=False, input_filter='int',
                size_hint=(0.4, None), height=dp(30))
            line.add_widget(qty_inp)
            body.add_widget(line)
            rows_data[-1]['input'] = qty_inp

        dlg = ModernWindow(title='Массовое поступление', body=body,
                           size=(500, 400))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Применить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def apply_all(*_):
            worker = self.app.get_current_worker_name()
            count = 0
            for rd in rows_data:
                try:
                    q = int(rd['input'].text or '0')
                except ValueError:
                    continue
                if q <= 0:
                    continue
                if self.app.tool_service.update_quantity(rd['tool'].id, q):
                    self.app.history_service.add_receipt(
                        rd['tool'].inner_code, q, worker)
                    count += 1
            if count:
                self._finish_and_refresh(tab, dlg)
            else:
                dlg.dismiss()

        ok.bind(on_release=apply_all)
        dlg.open()

    # ─── Перемещение ───

    def move(self, mode):
        tab = self._inv_tab()
        if not tab or tab.tree is None:
            self._info('Внимание', 'Вкладка склада недоступна')
            return

        selected = tab.tree.get_selected_all()
        if not selected:
            self._info('Внимание', 'Выберите инструмент')
            return

        if len(selected) > 1:
            return self._bulk_move(selected, mode)

        code = selected[0].get('inner_code', '')
        tool = self.app.tool_service.get_by_code(code)
        if not tool:
            self._info('Ошибка', 'Инструмент не найден')
            return
        if mode == 'СТАНОК':
            self._move_to_machine_dialog(tool)
        else:
            self._move_to_reserve_dialog(tool)

    def _bulk_move(self, selected_rows, mode):
        """Массовое перемещение на станок / в резерв."""
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        rows_data = []
        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(6))
        body.add_widget(Label(
            text=f'Массовое перемещение ({mode}) — {len(selected_rows)} шт.',
            bold=True, size_hint_y=None, height=dp(26)))

        for r in selected_rows:
            code = r.get('inner_code', '')
            tool = self.app.tool_service.get_by_code(code)
            if not tool:
                continue
            line = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
            line.add_widget(Label(
                text=f'{code}  |  ост.: {tool.qty_total}',
                size_hint_x=0.6, color=(0.17, 0.24, 0.31, 1)))
            qty_inp = TextInput(text='1', multiline=False,
                                input_filter='int',
                                size_hint=(0.4, None), height=dp(30))
            line.add_widget(qty_inp)
            body.add_widget(line)
            rows_data.append({'tool': tool, 'input': qty_inp})

        target_widget = None
        if mode == 'СТАНОК':
            body.add_widget(Label(text='Станок:', size_hint_y=None,
                                  height=dp(22)))
            machines = self.app.machine_service.get_all() or []
            target_widget = Spinner(
                text=machines[0] if machines else '',
                values=list(machines), size_hint_y=None, height=dp(34))
            body.add_widget(target_widget)
        else:
            body.add_widget(Label(text='Задача (назначение):',
                                  size_hint_y=None, height=dp(22)))
            target_widget = TextInput(multiline=False,
                                      size_hint_y=None, height=dp(34))
            body.add_widget(target_widget)

        dlg = ModernWindow(title=f'Массовое перемещение — {mode}',
                           body=body, size=(500, 460))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Применить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def apply_all(*_):
            target = (target_widget.text if hasattr(target_widget, 'text')
                      else '')
            if not target:
                return
            worker = self.app.get_current_worker_name()
            count = 0
            for rd in rows_data:
                try:
                    q = int(rd['input'].text or '0')
                except ValueError:
                    continue
                if q <= 0 or q > rd['tool'].qty_total:
                    continue
                if mode == 'СТАНОК':
                    ok_ = self.app.placement_service.move_to_machine(
                        rd['tool'].id, rd['tool'].inner_code,
                        q, target, worker)
                else:
                    ok_ = self.app.placement_service.move_to_reserve(
                        rd['tool'].id, rd['tool'].inner_code,
                        q, target, worker)
                if ok_:
                    count += 1
            if count:
                self._finish_and_refresh(tab, dlg)
            else:
                dlg.dismiss()

        ok.bind(on_release=apply_all)
        dlg.open()

    def _move_to_machine_dialog(self, tool):
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        body.add_widget(Label(text=f"Инструмент: {tool.inner_code}",
                              bold=True, size_hint_y=None, height=dp(26)))
        body.add_widget(Label(text=f"Доступно: {tool.qty_total} шт.",
                              size_hint_y=None, height=dp(22)))
        body.add_widget(Label(text="Количество:", size_hint_y=None,
                              height=dp(22)))
        inp = TextInput(text='1', multiline=False, input_filter='int',
                        size_hint_y=None, height=dp(34))
        body.add_widget(inp)
        body.add_widget(Label(text="Станок:", size_hint_y=None,
                              height=dp(22)))
        machines = self.app.machine_service.get_all() or []
        sp = Spinner(text=machines[0] if machines else '',
                     values=machines, size_hint_y=None, height=dp(34))
        body.add_widget(sp)

        dlg = ModernWindow(title='Перемещение на станок', body=body,
                           size=(420, 340))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Переместить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def confirm(*_):
            try:
                qty = int(inp.text or '0')
            except ValueError:
                return
            if qty <= 0 or qty > tool.qty_total:
                return
            machine = sp.text
            if not machine:
                return
            worker = self.app.get_current_worker_name()
            if self.app.placement_service.move_to_machine(
                    tool.id, tool.inner_code, qty, machine, worker):
                self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=confirm)
        dlg.open()

    def _move_to_reserve_dialog(self, tool):
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        body.add_widget(Label(text=f"Инструмент: {tool.inner_code}",
                              bold=True, size_hint_y=None, height=dp(26)))
        body.add_widget(Label(text=f"Доступно: {tool.qty_total} шт.",
                              size_hint_y=None, height=dp(22)))
        body.add_widget(Label(text="Количество:", size_hint_y=None,
                              height=dp(22)))
        inp = TextInput(text='1', multiline=False, input_filter='int',
                        size_hint_y=None, height=dp(34))
        body.add_widget(inp)
        body.add_widget(Label(text="Задача:", size_hint_y=None,
                              height=dp(22)))
        task = TextInput(multiline=False, size_hint_y=None, height=dp(34))
        body.add_widget(task)

        dlg = ModernWindow(title='Перемещение в резерв', body=body,
                           size=(420, 340))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Переместить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def confirm(*_):
            try:
                qty = int(inp.text or '0')
            except ValueError:
                return
            if qty <= 0 or qty > tool.qty_total:
                return
            if not task.text.strip():
                return
            worker = self.app.get_current_worker_name()
            if self.app.placement_service.move_to_reserve(
                    tool.id, tool.inner_code, qty,
                    task.text.strip(), worker):
                self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=confirm)
        dlg.open()

    # ─── Станки ───

    def add_machine(self):
        tab = self._inv_tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
        body.add_widget(Label(text='Название нового станка:',
                              size_hint_y=None, height=dp(24)))
        inp = TextInput(multiline=False, size_hint_y=None, height=dp(34))
        body.add_widget(inp)

        dlg = ModernWindow(title='Добавление станка', body=body,
                           size=(380, 200))
        self._bind_busy(dlg, tab)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Добавить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def save(*_):
            name = inp.text.strip()
            if not name:
                return
            if self.app.machine_service.add(name):
                self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=save)
        dlg.open()

    # ─── Заявки ───

    def create_request_from_selected(self):
        tab = self._inv_tab()
        if not tab or tab.tree is None:
            self._info('Внимание', 'Вкладка склада недоступна')
            return
        selected = tab.tree.get_selected_all()
        if not selected:
            self._info('Внимание', 'Выберите инструмент')
            return

        # 2+ → групповая
        if len(selected) >= 2:
            return self.create_group_request_from_selected()

        row = selected[0]
        code = row.get('inner_code', '')
        tool = self.app.tool_service.get_by_code(code)
        if not tool:
            self._info('Ошибка', 'Инструмент не найден')
            return
        from frontend.views.dialogs.request import CreateRequestDialog
        CreateRequestDialog(
            self.app, tool.inner_code, tool.articul,
            tool.type or '', tool.diameter or '', tool.brand or '',
            tool.qty_total,
        ).open()

    def create_group_request_from_selected(self):
        """Создание групповой заявки из 2+ выделенных инструментов."""
        tab = self._inv_tab()
        if not tab or tab.tree is None:
            self._info('Внимание', 'Вкладка склада недоступна')
            return

        selected = tab.tree.get_selected_all()
        if len(selected) < 2:
            self._info('Внимание', 'Выберите 2 и более инструмента')
            return

        selected_tools = []
        for row in selected:
            code = row.get('inner_code', '')
            tool = self.app.tool_service.get_by_code(code)
            if not tool:
                continue
            selected_tools.append({
                'tool_id': tool.id,
                'inner_code': tool.inner_code,
                'articul': tool.articul or '',
                'type': tool.type or '',
                'diameter': tool.diameter or '',
                'brand': tool.brand or '',
                'current_qty': tool.qty_total or 0,
            })

        if not selected_tools:
            self._info('Ошибка', 'Не удалось получить данные инструментов')
            return

        from frontend.views.dialogs.group_request import (
            CreateGroupRequestDialog,
        )
        CreateGroupRequestDialog(self.app, selected_tools).open()

    def manage_placement(self, action, tree_widget):
        self._info('Управление', 'Управление размещением — в разработке')

    def _info(self, title, message):
        body = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        body.add_widget(Label(text=message, halign='center'))
        dlg = ModernWindow(title=title, body=body, size=(400, 160))
        row = BoxLayout(size_hint_y=None, height=dp(40))
        ok = ModernButton(text='OK', color='info', size_hint=(1, 1))
        ok.bind(on_release=lambda *_: dlg.dismiss())
        row.add_widget(ok)
        body.add_widget(row)
        dlg.open()