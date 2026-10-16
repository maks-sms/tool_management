# frontend/views/chat/chat_input_controller.py
"""Управление полем ввода: отправка, Ctrl-комбинации, автодополнение."""
import re
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.clock import Clock

from frontend.theme import C


RE_TRIGGER_MENTION = re.compile(r'@(\S*)$')
RE_TRIGGER_TOOL    = re.compile(r'#(\S*)$')

TEXT_HISTORY_LIMIT = 50
MAX_AUTOCOMPLETE_ITEMS = 8


class ChatInputController:
    """Обёртка вокруг TextInput поля ввода."""

    def __init__(self, manager):
        self.manager = manager
        self._typing_event = None

        # История для Ctrl+Z / Ctrl+Y
        self._history = ['']
        self._history_idx = 0

        # Привязка глобального перехвата клавиш (один раз)
        Window.bind(on_key_down=self.on_key_down)

    # ─── Свойства ───
    @property
    def ui(self):
        return self.manager.ui

    # ─── Текст изменён ───
    def on_text_change(self, instance, value):
        """Печатает — послать статус и обновить автодополнение."""
        if value:
            try:
                self.manager.message_handler.send_typing_status()
            except Exception:
                pass
        self._push_history(value)
        self._update_autocomplete(value)

    # ─── Enter ───
    def submit(self):
        self.manager.send_message()

    # ─── Ctrl-комбинации (глобальный перехват) ───
    def on_key_down(self, window, key, scancode=None, codepoint=None, modifier=None):
        """
        Kivy вызывает: on_key_down(window, key, scancode, codepoint, modifiers)
        key — числовой код (ord('c') == 99 и т.д.)
        modifiers — список строк ['ctrl', 'shift', ...]
        """
        if not self.ui or not self.ui.input:
            return False
        if not self.ui.input.focus:
            return False

        mods = set(modifier or [])
        inp = self.ui.input

        # Ctrl+C / V / X / A / Z / Y
        if 'ctrl' in mods:
            if key == 99:   # c
                self._copy()
                return True
            if key == 118:  # v
                self._paste()
                return True
            if key == 120:  # x
                self._cut()
                return True
            if key == 97:   # a
                inp.select_all()
                return True
            if key == 122:  # z
                if 'shift' in mods:
                    self._redo()
                else:
                    self._undo()
                return True
            if key == 121:  # y
                self._redo()
                return True

        # Escape — закрыть автодополнение
        if key == 27:
            self._hide_autocomplete()
            return False

        # Up / Down / Enter — навигация по автодополнению
        if self._ac_visible():
            if key == 273:  # up
                self._ac_move(-1)
                return True
            if key == 274:  # down
                self._ac_move(1)
                return True
            if key in (13, 271):  # enter / numpad enter
                self._ac_apply_current()
                return True

        return False

    # ─── История ───
    def _push_history(self, text: str):
        if self._history_idx < len(self._history) - 1:
            self._history = self._history[:self._history_idx + 1]
        if not self._history or self._history[-1] != text:
            self._history.append(text)
            self._history_idx = len(self._history) - 1
        if len(self._history) > TEXT_HISTORY_LIMIT:
            self._history.pop(0)
            self._history_idx -= 1

    def _undo(self):
        if self._history_idx > 0:
            self._history_idx -= 1
            self.ui.input.text = self._history[self._history_idx]

    def _redo(self):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.ui.input.text = self._history[self._history_idx]

    # ─── Буфер обмена ───
    def _copy(self):
        inp = self.ui.input
        try:
            sel = inp.selection_text
            if sel:
                Clipboard.copy(sel)
        except Exception as e:
            print(f'[chat.copy] {e}')

    def _paste(self):
        inp = self.ui.input
        try:
            txt = Clipboard.paste()
            if txt:
                if inp.selection_text:
                    inp.delete_selection()
                inp.insert_text(txt)
        except Exception as e:
            print(f'[chat.paste] {e}')

    def _cut(self):
        inp = self.ui.input
        try:
            sel = inp.selection_text
            if sel:
                Clipboard.copy(sel)
                inp.delete_selection()
        except Exception as e:
            print(f'[chat.cut] {e}')

    # ═══════════════════════════════════════════════════════
    #                    АВТОДОПОЛНЕНИЕ
    # ═══════════════════════════════════════════════════════

    def _ac_visible(self) -> bool:
        box = getattr(self.ui, 'autocomplete_box', None)
        return box is not None and box.height > 0

    def _ac_move(self, delta: int):
        box = getattr(self.ui, 'autocomplete_box', None)
        if not box:
            return
        items = getattr(box, '_items', [])
        if not items:
            return
        idx = getattr(box, '_selected', 0) + delta
        idx = max(0, min(len(items) - 1, idx))
        box._selected = idx
        box._refresh_selection()

    def _ac_apply_current(self):
        box = getattr(self.ui, 'autocomplete_box', None)
        if not box:
            return
        items = getattr(box, '_items', [])
        idx = getattr(box, '_selected', 0)
        if 0 <= idx < len(items):
            self._ac_apply(items[idx])
            self._hide_autocomplete()

    def _ac_apply(self, item):
        """item = (kind, display, replacement)."""
        inp = self.ui.input
        kind, _display, replacement = item

        text = inp.text or ''
        cursor = inp.cursor_index()

        before = text[:cursor]
        if kind == 'mention':
            m = RE_TRIGGER_MENTION.search(before)
        else:
            m = RE_TRIGGER_TOOL.search(before)
        if not m:
            return

        start = m.start()
        new_text = text[:start] + replacement + ' ' + text[cursor:]
        inp.text = new_text
        try:
            inp.cursor = (None, start + len(replacement) + 1)
        except Exception:
            pass

    # ─── Обновление панели ───
    def _update_autocomplete(self, value: str):
        try:
            cursor = self.ui.input.cursor_index()
            before = (value or '')[:cursor]

            m_mention = RE_TRIGGER_MENTION.search(before)
            m_tool = RE_TRIGGER_TOOL.search(before)

            kind = None
            query = ''
            if m_mention:
                kind = 'mention'
                query = m_mention.group(1)
            elif m_tool:
                kind = 'tool'
                query = m_tool.group(1)

            if not kind:
                self._hide_autocomplete()
                return

            items = self._fetch_candidates(kind, query)
            if not items:
                self._hide_autocomplete()
                return

            self._show_autocomplete(items)
        except Exception as e:
            print(f'[chat.ac] {e}')

    def _fetch_candidates(self, kind, query):
        svc = self.manager.chat_service
        out = []
        try:
            if kind == 'mention':
                users = svc.get_mention_candidates(
                    query, self.manager.current_user[0]
                ) or []
                for uid, name, _username in users[:MAX_AUTOCOMPLETE_ITEMS]:
                    out.append((
                        'mention',
                        f"👤 {name}",
                        svc.make_mention(name, uid),
                    ))
            else:  # tool
                tools = svc.get_tool_candidates(query) or []
                for code, articul in tools[:MAX_AUTOCOMPLETE_ITEMS]:
                    out.append((
                        'tool',
                        f"🔧 {code} — {articul}",
                        svc.make_tool_link(code, articul),
                    ))
        except Exception as e:
            print(f'[chat.ac.fetch] {e}')
        return out

    def _show_autocomplete(self, items):
        box = getattr(self.ui, 'autocomplete_box', None)
        if box is None:
            return
        box.set_items(items)

    def _hide_autocomplete(self):
        box = getattr(self.ui, 'autocomplete_box', None)
        if box is not None:
            box.hide()