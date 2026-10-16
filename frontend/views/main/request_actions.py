# frontend/views/main/request_actions.py
"""Действия с заявками (обычными и групповыми) из главного окна.

Ключевое:
    - пока открыт диалог, вкладка помечена _busy=True;
    - при закрытии диалога _on_dismiss снимает _busy и
      ГАРАНТИРОВАННО перечитывает данные через tab.refresh().
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from frontend.widgets.modern_window import ModernWindow
from frontend.widgets.modern_button import ModernButton
from frontend.widgets.modern_tree import ModernTree
from frontend.widgets.styled_fields import (
    StyledTextInput, StyledSpinner, LabeledField,
)


class RequestActions:
    def __init__(self, app):
        self.app = app

    # ─── Утилиты ────────────────────────────────────────────────

    def _tab(self):
        tabs = getattr(self.app.main_screen, 'tab_widgets', {}) or {}
        return tabs.get('requests')

    def _selected(self):
        tab = self._tab()
        if not tab or tab.tree is None:
            return None
        return tab.tree.get_selected()

    def _bind_busy(self, dlg, tab, refresh_after=True):
        """Снять _busy при закрытии диалога и, если нужно, перечитать данные.

        refresh_after=True — вызывать tab.refresh() (для диалогов,
        которые меняют данные и должны сразу показать результат).

        refresh_after=False — только снять _busy (для диалогов-просмотров).
        """
        if tab is None:
            return

        def _on_dismiss(*_):
            tab._busy = False
            tab._dirty = True
            if refresh_after:
                try:
                    tab.refresh()
                    tab._dirty = False
                except Exception as e:
                    print(f'[request_actions.on_dismiss] {e}')

        try:
            dlg.bind(on_dismiss=_on_dismiss)
        except Exception:
            pass

    def _finish_and_refresh(self, tab, dlg):
        """Закрыть диалог. Обновление выполнит _on_dismiss."""
        if tab is not None:
            tab._busy = False
            tab._dirty = True
        try:
            dlg.dismiss()
        except Exception:
            pass

    def _info(self, title, msg):
        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(10))
        body.add_widget(Label(text=msg, halign='center'))
        dlg = ModernWindow(title=title, body=body, size=(400, 160))
        row = BoxLayout(size_hint_y=None, height=dp(40))
        ok = ModernButton(text='OK', color='info', size_hint=(1, 1))
        ok.bind(on_release=lambda *_: dlg.dismiss())
        row.add_widget(ok)
        body.add_widget(row)
        dlg.open()

    def _status_display(self, status):
        mapping = {
            'pending': '🟡 Ожидает',
            'in_progress': '🟠 В работе',
            'completed': '🟢 Выполнена',
            'rejected': '🔴 Отклонена',
        }
        return mapping.get(status, status or '—')

    # ─── Взять в работу ────────────────────────────────────────

    def take_to_work(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        processor = self.app.get_current_worker_name()

        if sel.get('_is_group'):
            gid = sel.get('id')
            try:
                ok = self.app.group_request_service_extended.take_to_work(
                    gid, processor,
                )
                if ok:
                    self.app.refresh_requests_tab()
                else:
                    self._info('Ошибка', 'Не удалось взять в работу')
            except Exception as e:
                self._info('Ошибка', str(e))
            return

        if self.app.purchase_request_service.take_to_work(
                sel.get('id'), processor):
            self.app.refresh_requests_tab()

    # ─── Частичное поступление ─────────────────────────────────

    def receive_partial(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        if sel.get('_is_group'):
            return self._receive_group_dialog(sel)

        self._receive_dialog(sel)

    def _receive_dialog(self, sel):
        tab = self._tab()
        if tab is not None:
            tab._busy = True

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))
        body.add_widget(Label(text=f"Заявка №{sel.get('id')}",
                              bold=True, size_hint_y=None, height=dp(24)))
        body.add_widget(Label(text=f"Инструмент: {sel.get('tool_code', '')}",
                              size_hint_y=None, height=dp(22)))
        inp = TextInput(text=str(sel.get('requested_qty', '1')),
                        multiline=False, input_filter='int',
                        size_hint_y=None, height=dp(34))
        body.add_widget(inp)

        dlg = ModernWindow(title='Поступление по заявке', body=body,
                           size=(400, 240))
        self._bind_busy(dlg, tab, refresh_after=True)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Принять', color='success', size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def confirm(*_):
            try:
                q = int(inp.text or '0')
            except ValueError:
                return
            if q <= 0:
                return
            processor = self.app.get_current_worker_name()
            tool = self.app.tool_service.get_by_code(sel.get('tool_code', ''))
            if tool:
                self.app.tool_service.update_quantity(tool.id, q)
            if self.app.purchase_request_service.receive_partial(
                    sel.get('id'), q, processor, ''):
                self.app.history_service.add_record(
                    sel.get('tool_code', ''), 'ПОСТУПЛЕНИЕ ПО ЗАЯВКЕ',
                    q, f"Заявка №{sel.get('id')}", processor)
                self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=confirm)
        dlg.open()

    def _receive_group_dialog(self, sel):
        """Поступление по позиции групповой заявки."""
        tab = self._tab()
        if tab is not None:
            tab._busy = True

        gid = sel.get('id')
        svc = self.app.group_request_service_extended

        try:
            group = svc.get_by_id(gid)
            items = svc.get_items(gid) or []
        except Exception as e:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', f'Не удалось загрузить: {e}')

        if not group:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', 'Групповая заявка не найдена')

        available = []
        for it in items:
            try:
                requested = it[7] or 0
                received = it[8] or 0
                if received < requested:
                    available.append(it)
            except Exception:
                continue

        if not available:
            if tab is not None:
                tab._busy = False
            return self._info('Инфо', 'Все позиции уже получены')

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))

        body.add_widget(Label(
            text=f"Групповая заявка №{getattr(group, 'request_number', '')}",
            bold=True, size_hint_y=None, height=dp(24)))
        body.add_widget(Label(
            text=f"Позиций к поступлению: {len(available)}",
            size_hint_y=None, height=dp(20)))

        rows_data = []
        scroll = ScrollView(size_hint=(1, 1))

        grid = GridLayout(cols=4, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter('height'))

        for h in ('Код', 'Артикул', 'Осталось', 'Кол-во'):
            grid.add_widget(Label(
                text=h, bold=True, size_hint_y=None, height=dp(22),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))

        for it in available:
            item_id = it[0]
            code = it[2]
            articul = it[3]
            req_qty = it[7] or 0
            recv_qty = it[8] or 0
            remaining = req_qty - recv_qty

            grid.add_widget(Label(
                text=str(code), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))
            grid.add_widget(Label(
                text=str(articul), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))
            grid.add_widget(Label(
                text=str(remaining), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))

            qty_inp = StyledTextInput(
                text=str(remaining), input_filter='int',
                size_hint_y=None, height=dp(30),
            )
            grid.add_widget(qty_inp)
            rows_data.append({
                'item_id': item_id,
                'remaining': remaining,
                'input': qty_inp,
            })

        scroll.add_widget(grid)
        body.add_widget(scroll)

        dlg = ModernWindow(title='Поступление по групповой заявке',
                           body=body, size=(640, 480))
        self._bind_busy(dlg, tab, refresh_after=True)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Принять', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def confirm(*_):
            processor = self.app.get_current_worker_name()
            success = 0
            for rd in rows_data:
                try:
                    q = int(rd['input'].text or '0')
                except ValueError:
                    continue
                if q <= 0 or q > rd['remaining']:
                    continue
                try:
                    result = svc.receive_item(
                        gid, rd['item_id'], q, processor, ''
                    )
                    if isinstance(result, dict) and result.get('success'):
                        success += 1
                    elif result:
                        success += 1
                except Exception as e:
                    print(f'[receive_group_item] {e}')
            if success:
                self._finish_and_refresh(tab, dlg)
            else:
                dlg.dismiss()

        ok.bind(on_release=confirm)
        dlg.open()

    # ─── Выполнить ─────────────────────────────────────────────

    def complete(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        processor = self.app.get_current_worker_name()

        if sel.get('_is_group'):
            gid = sel.get('id')
            try:
                ok = self.app.group_request_service_extended.complete(
                    gid, processor,
                )
                if ok:
                    self.app.refresh_requests_tab()
                else:
                    self._info('Инфо',
                               'Не все позиции поступили полностью')
            except Exception as e:
                self._info('Ошибка', str(e))
            return

        if self.app.purchase_request_service.complete(
                sel.get('id'), processor):
            self.app.refresh_requests_tab()

    # ─── Отклонить ─────────────────────────────────────────────

    def reject(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        processor = self.app.get_current_worker_name()

        if sel.get('_is_group'):
            gid = sel.get('id')
            try:
                ok = self.app.group_request_service_extended.reject(
                    gid, processor,
                )
                if ok:
                    self.app.refresh_requests_tab()
            except Exception as e:
                self._info('Ошибка', str(e))
            return

        if self.app.purchase_request_service.reject(
                sel.get('id'), processor):
            self.app.refresh_requests_tab()

    # ─── РЕДАКТИРОВАНИЕ ────────────────────────────────────────

    def edit(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        if sel.get('_is_group'):
            return self._edit_group(sel)

        return self._edit_single(sel)

    def _edit_single(self, sel):
        tab = self._tab()
        if tab is not None:
            tab._busy = True

        svc = self.app.purchase_request_service
        req = None
        try:
            req = svc.get_by_id(sel.get('id'))
        except Exception as e:
            print(f'[request.edit] {e}')

        if req is None:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', 'Не удалось загрузить заявку')

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))

        body.add_widget(Label(
            text=f"Заявка №{sel.get('id')}",
            bold=True, size_hint_y=None, height=dp(24)))
        body.add_widget(Label(
            text=f"Инструмент: {getattr(req, 'tool_code', '')}",
            size_hint_y=None, height=dp(22)))

        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter('height'))

        qty_inp = StyledTextInput(
            text=str(getattr(req, 'requested_qty', 1)),
            input_filter='int',
        )
        grid.add_widget(LabeledField(label='Количество:', widget=qty_inp))

        reason_inp = StyledTextInput(
            text=str(getattr(req, 'reason', '') or ''),
        )
        grid.add_widget(LabeledField(label='Причина:', widget=reason_inp))

        comment_inp = StyledTextInput(
            text=str(getattr(req, 'comment', '') or ''),
            multiline=True, size_hint_y=None, height=dp(80),
        )
        grid.add_widget(LabeledField(label='Комментарий:',
                                     widget=comment_inp))

        body.add_widget(grid)

        dlg = ModernWindow(title='Редактирование заявки',
                           body=body, size=(520, 400))
        self._bind_busy(dlg, tab, refresh_after=True)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Сохранить', color='success',
                          size_hint=(1, 1))
        row.add_widget(ok)
        body.add_widget(row)

        def save(*_):
            try:
                q = int(qty_inp.text or '0')
            except ValueError:
                return
            if q <= 0:
                return
            try:
                svc.update(
                    sel.get('id'),
                    requested_qty=q,
                    reason=reason_inp.text.strip(),
                    comment=comment_inp.text.strip(),
                )
                self._finish_and_refresh(tab, dlg)
            except Exception as e:
                print(f'[request.update] {e}')
                self._info('Ошибка', str(e))

        ok.bind(on_release=save)
        dlg.open()

    def _edit_group(self, sel):
        tab = self._tab()
        if tab is not None:
            tab._busy = True

        gid = sel.get('id')
        svc = self.app.group_request_service_extended

        try:
            group = svc.get_by_id(gid)
            items = svc.get_items(gid) or []
        except Exception as e:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', f'Не удалось загрузить: {e}')

        if not group:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', 'Групповая заявка не найдена')

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))

        body.add_widget(Label(
            text=f"Групповая заявка №{getattr(group, 'request_number', '')}",
            bold=True, size_hint_y=None, height=dp(24)))
        body.add_widget(Label(
            text=f"Позиций: {len(items)}",
            size_hint_y=None, height=dp(20)))

        grid_top = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid_top.bind(minimum_height=grid_top.setter('height'))

        name_inp = StyledTextInput(
            text=str(getattr(group, 'name', '') or ''),
        )
        grid_top.add_widget(LabeledField(label='Название заявки:',
                                         widget=name_inp))

        reason_inp = StyledTextInput(
            text=str(getattr(group, 'reason', '') or ''),
        )
        grid_top.add_widget(LabeledField(label='Причина закупки:',
                                         widget=reason_inp))

        comment_inp = StyledTextInput(
            text=str(getattr(group, 'comment', '') or ''),
            multiline=True, size_hint_y=None, height=dp(60),
        )
        grid_top.add_widget(LabeledField(label='Комментарий:',
                                         widget=comment_inp))

        body.add_widget(grid_top)

        body.add_widget(Label(
            text='Позиции заявки:',
            bold=True, size_hint_y=None, height=dp(20),
            color=(0.17, 0.24, 0.31, 1)))

        rows_data = []
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=5, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter('height'))

        for h in ('ID', 'Код', 'Артикул', 'Заказано', 'Новое кол-во'):
            grid.add_widget(Label(
                text=h, bold=True, size_hint_y=None, height=dp(22),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))

        for it in items:
            try:
                item_id = it[0]
                code = it[2]
                articul = it[3]
                requested = it[7] or 0
                received = it[8] or 0
            except Exception:
                continue

            grid.add_widget(Label(
                text=str(item_id), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))
            grid.add_widget(Label(
                text=str(code), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))
            grid.add_widget(Label(
                text=str(articul), size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))
            grid.add_widget(Label(
                text=f"{requested} (пост. {received})",
                size_hint_y=None, height=dp(30),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12)))

            qty_inp = StyledTextInput(
                text=str(requested), input_filter='int',
                size_hint_y=None, height=dp(30),
            )
            grid.add_widget(qty_inp)
            rows_data.append({
                'item_id': item_id,
                'received': received,
                'input': qty_inp,
            })

        scroll.add_widget(grid)
        body.add_widget(scroll)

        dlg = ModernWindow(title='Редактирование групповой заявки',
                           body=body, size=(720, 620))
        self._bind_busy(dlg, tab, refresh_after=True)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        ok = ModernButton(text='Сохранить', color='success',
                          size_hint=(1, 1))
        cancel = ModernButton(text='Отмена', color='danger',
                              size_hint=(1, 1))
        row.add_widget(ok)
        row.add_widget(cancel)
        body.add_widget(row)

        def save(*_):
            try:
                if hasattr(svc, 'update_info'):
                    svc.update_info(
                        gid,
                        name_inp.text.strip(),
                        reason_inp.text.strip(),
                        comment_inp.text.strip(),
                    )
                elif hasattr(svc, 'update'):
                    svc.update(
                        gid,
                        name=name_inp.text.strip(),
                        reason=reason_inp.text.strip(),
                        comment=comment_inp.text.strip(),
                    )
                else:
                    print('[edit_group] нет метода update_info/update')
            except Exception as e:
                print(f'[edit_group header] {e}')
                return self._info('Ошибка', str(e))

            for rd in rows_data:
                try:
                    new_qty = int(rd['input'].text or '0')
                except ValueError:
                    continue
                if new_qty <= 0:
                    continue
                if new_qty < rd['received']:
                    continue
                try:
                    if hasattr(svc, 'update_item_qty'):
                        svc.update_item_qty(rd['item_id'], new_qty)
                    elif hasattr(svc, 'item_repository'):
                        svc.item_repository.update_qty(
                            rd['item_id'], new_qty
                        )
                except Exception as e:
                    print(f'[edit_group item {rd["item_id"]}] {e}')

            self._finish_and_refresh(tab, dlg)

        ok.bind(on_release=save)
        cancel.bind(on_release=lambda *_: dlg.dismiss())
        dlg.open()

    # ─── Удалить ───────────────────────────────────────────────

    def delete(self):
        sel = self._selected()
        if not sel:
            return self._info('Внимание', 'Выберите заявку')

        if sel.get('_is_group'):
            gid = sel.get('id')
            try:
                ok = self.app.group_request_service_extended.delete(gid)
                if ok:
                    self.app.refresh_requests_tab()
            except Exception as e:
                self._info('Ошибка', str(e))
            return

        if self.app.purchase_request_service.delete(sel.get('id')):
            self.app.refresh_requests_tab()

    # ─── Двойной клик ─────────────────────────────────────────

    def on_double_click(self, row=None):
        if not row:
            return
        if not row.get('_is_group'):
            return
        self.view_group(row.get('id'))

    # ─── ПРОСМОТР ГРУППОВОЙ ЗАЯВКИ ─────────────────────────────

    def view_group(self, gid):
        """Открыть окно просмотра групповой заявки (только чтение)."""
        tab = self._tab()
        if tab is not None:
            tab._busy = True

        svc = self.app.group_request_service_extended
        try:
            group = svc.get_by_id(gid)
            items = svc.get_items(gid) or []
        except Exception as e:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', f'Не удалось загрузить: {e}')

        if not group:
            if tab is not None:
                tab._busy = False
            return self._info('Ошибка', 'Групповая заявка не найдена')

        body = BoxLayout(orientation='vertical', padding=dp(14),
                         spacing=dp(8))

        header = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        header.bind(minimum_height=header.setter('height'))

        def _line(text, bold=False):
            lbl = Label(
                text=text, bold=bold, size_hint_y=None, height=dp(20),
                color=(0.17, 0.24, 0.31, 1), font_size=dp(12),
                halign='left', valign='middle',
            )
            lbl.bind(size=lambda i, *_: setattr(
                i, 'text_size', (i.width, i.height)))
            return lbl

        header.add_widget(_line(
            f"Групповая заявка №{getattr(group, 'request_number', '')}",
            bold=True))
        header.add_widget(_line(
            f"Название: {getattr(group, 'name', '')}"))
        header.add_widget(_line(
            f"Заявитель: {getattr(group, 'requester_name', '')}"))
        header.add_widget(_line(
            f"Дата: {getattr(group, 'request_date', '')}"))
        header.add_widget(_line(
            f"Статус: {self._status_display(getattr(group, 'status', ''))}"))

        reason = getattr(group, 'reason', '')
        if reason:
            header.add_widget(_line(f"Причина: {reason}"))
        comment = getattr(group, 'comment', '')
        if comment:
            header.add_widget(_line(f"Комментарий: {comment}"))

        body.add_widget(header)

        body.add_widget(Label(
            text='Позиции:',
            bold=True, size_hint_y=None, height=dp(20),
            color=(0.17, 0.24, 0.31, 1)))

        cols = [
            ('id', 'ID', 1),
            ('code', 'Код', 2),
            ('articul', 'Артикул', 3),
            ('type', 'Тип', 2),
            ('req', 'Заказано', 1),
            ('recv', 'Поступило', 1),
        ]
        tree = ModernTree(columns=cols)
        tree.size_hint_y = 1

        rows = []
        total_req = 0
        total_recv = 0
        for it in items:
            try:
                item_id = it[0]
                code = it[2]
                articul = it[3]
                itype = it[4] or ''
                requested = it[7] or 0
                received = it[8] or 0
                total_req += requested
                total_recv += received
                rows.append({
                    'id': item_id,
                    'code': code,
                    'articul': articul,
                    'type': itype,
                    'req': requested,
                    'recv': received,
                })
            except Exception:
                continue

        tree.set_rows(rows)
        body.add_widget(tree)

        remaining = total_req - total_recv
        body.add_widget(Label(
            text=f"Итого: заказано {total_req}, поступило {total_recv}, "
                 f"осталось {remaining}",
            bold=True, size_hint_y=None, height=dp(24),
            color=(0.17, 0.24, 0.31, 1),
        ))

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        row.add_widget(ModernButton(
            text='Закрыть', color='info', size_hint=(1, 1),
            on_release=lambda *_: dlg.dismiss(),
        ))
        body.add_widget(row)

        dlg = ModernWindow(title='Просмотр групповой заявки',
                           body=body, size=(760, 560))
        # Только снять _busy, данные не менялись
        self._bind_busy(dlg, tab, refresh_after=False)
        dlg.open()