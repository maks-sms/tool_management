# frontend/views/chat/chat_text_widget.py
"""
Рендер сообщения чата в Kivy:
    - Markdown: **bold**, *italic*, `code`, ~~strike~~, __underline__
    - ссылки #tool:CODE# — СИНИМ, упоминания @Имя — ЗЕЛЁНЫМ
    - выделение текста мышью + Ctrl+C (как в обычном TextInput)
    - клик по ссылке срабатывает, ТОЛЬКО если это был клик, а не выделение
"""
import re
from typing import Optional, Callable, List, Tuple

from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard

from frontend.theme import C


RE_BOLD      = re.compile(r'\*\*(.+?)\*\*')
RE_ITALIC    = re.compile(r'(?<!\*)\*([^*\n]+?)\*(?!\*)')
RE_CODE      = re.compile(r'`([^`\n]+?)`')
RE_STRIKE    = re.compile(r'~~(.+?)~~')
RE_UNDERLINE = re.compile(r'__(.+?)__')

RE_TOOL_LINK = re.compile(r'#tool:([^|#]+)(?:\|([^#]+))?#')
RE_MENTION   = re.compile(r'@\[([^\]]+)\]\(user:(\d+)\)')


def _escape_markup(text: str) -> str:
    return text.replace('&', '&amp;').replace('[', '&bl;').replace(']', '&br;')


class _PassThroughLabel(Label):
    """Label с markup, пропускает касания вниз — в TextInput."""
    def on_touch_down(self, touch):
        return False
    def on_touch_move(self, touch):
        return False
    def on_touch_up(self, touch):
        return False


class MessageText(RelativeLayout):
    """
    Слой 1 (снизу): TextInput readonly — выделение, Ctrl+C.
    Слой 2 (сверху): Label с markup — цветной текст.
    """

    # Порог, при котором клик считается «кликом», а не выделением
    CLICK_MAX_DT = 0.35        # сек
    CLICK_MAX_DIST = dp(4)     # пикселей

    def __init__(
        self,
        raw_text: str,
        fg_rgba,
        bg_rgba,
        on_tool_click: Optional[Callable[[str], None]] = None,
        on_mention_click: Optional[Callable[[int], None]] = None,
        font_size: float = dp(13),
        **kw,
    ):
        super().__init__(
            size_hint=(1, None),
            height=dp(20),
            **kw,
        )

        clean_text, markup_text, click_map = _render_texts(raw_text)

        self._raw_text = raw_text
        self._clean_text = clean_text
        self._markup_text = markup_text
        self._click_map = click_map
        self._on_tool_click = on_tool_click
        self._on_mention_click = on_mention_click
        self._font_size = font_size

        # Запоминаем стартовую позицию нажатия, чтобы в on_touch_up
        # понять — был это клик или выделение
        self._press_start_pos = None
        self._press_start_time = 0.0

        # ─── TextInput (снизу) ───
        self.input = TextInput(
            text=clean_text,
            readonly=True,
            multiline=True,
            background_normal='',
            background_active='',
            background_disabled_normal='',
            background_color=(0, 0, 0, 0),
            foreground_color=(0, 0, 0, 0),
            disabled_foreground_color=(0, 0, 0, 0),
            cursor_color=(0, 0, 0, 0),
            selection_color=(0.3, 0.5, 0.9, 0.4),
            font_size=font_size,
            padding=[0, dp(2), 0, dp(2)],
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            write_tab=False,
            use_bubble=False,
            use_handles=True,
            cursor_blink=False,
            allow_copy=True,
        )
        self.add_widget(self.input)

        # ─── Label (сверху) ───
        self.label = _PassThroughLabel(
            text=markup_text,
            markup=True,
            color=fg_rgba,
            font_size=font_size,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            halign='left',
            valign='top',
            padding=[0, dp(2), 0, dp(2)],
        )
        self.add_widget(self.label)

        # ─── Ловим touch на уровне MessageText ───
        self.bind(on_touch_down=self._on_touch_down_custom)
        self.bind(on_touch_up=self._on_touch_up_custom)

        self.bind(width=self._refresh_height)
        self.label.bind(texture_size=self._refresh_height)
        self.input.bind(width=self._sync_text_sizes)
        self.label.bind(width=self._sync_text_sizes)

        Clock.schedule_once(lambda dt: self._sync_text_sizes(), 0)
        Clock.schedule_once(lambda dt: self._refresh_height(), 0)

    # ─── Размеры ───

    def _sync_text_sizes(self, *_):
        try:
            w = self.width
            if w <= 0:
                return
            self.input.text_size = (w, None)
            self.label.text_size = (w, None)
        except Exception:
            pass

    def _refresh_height(self, *_):
        try:
            self._sync_text_sizes()
            h = max(self.label.texture_size[1],
                    self.input.minimum_height, dp(18))
            self.height = h + dp(4)
        except Exception:
            pass

    # ─── Клики ───

    def _on_touch_down_custom(self, _widget, touch):
        """Запоминаем только координаты и время. Ничего не дёргаем."""
        if not self.collide_point(*touch.pos):
            return False
        if touch.button != 'left':
            return False
        if not self._click_map:
            return False

        self._press_start_pos = (touch.x, touch.y)
        self._press_start_time = touch.time_start
        return False   # не блокируем — пусть TextInput начнёт выделение

    def _on_touch_up_custom(self, _widget, touch):
        """Если это был короткий клик без движения — открываем ссылку."""
        if touch.button != 'left':
            return False
        if self._press_start_pos is None:
            return False

        start_pos = self._press_start_pos
        start_time = self._press_start_time
        self._press_start_pos = None

        # 1. Длительность
        dt = (touch.time_end - start_time) if touch.time_end else 0
        if dt > self.CLICK_MAX_DT:
            return False

        # 2. Расстояние от старта
        dx = abs(touch.x - start_pos[0])
        dy = abs(touch.y - start_pos[1])
        if dx > self.CLICK_MAX_DIST or dy > self.CLICK_MAX_DIST:
            return False

        # 3. Если есть выделение — значит, пользователь что-то выделил
        try:
            if self.input.selection_text:
                return False
        except Exception:
            pass

        # 4. Проверяем, попал ли клик в ссылку
        target = self._hit_test(touch.x, touch.y)
        if target is None:
            return False

        kind, value = target
        if kind == 'tool' and self._on_tool_click:
            self._on_tool_click(value)
            return True
        elif kind == 'mention' and self._on_mention_click:
            self._on_mention_click(int(value))
            return True

        return False

    def _hit_test(self, x, y) -> Optional[Tuple[str, str]]:
        """x, y — координаты в системе MessageText."""
        try:
            col, row = self.input.get_cursor_from_xy(x, y)
        except Exception:
            return None

        clean_lines = self._clean_text.split('\n')
        if row < 0 or row >= len(clean_lines):
            return None

        offset = sum(len(l) + 1 for l in clean_lines[:row])
        pos = offset + col

        for (start, end, kind, value) in self._click_map:
            if start <= pos <= end:
                return (kind, value)
        return None


# ─── Рендер: чистый текст + markup ───

def _render_texts(raw_text: str) -> Tuple[str, str, List[Tuple[int, int, str, str]]]:
    if not raw_text:
        return '', '', []

    fragments = _parse_fragments(raw_text)

    clean_parts: List[str] = []
    markup_parts: List[str] = []
    click_map: List[Tuple[int, int, str, str]] = []
    pos = 0

    for kind, payload, marks in fragments:
        if kind == 'text':
            text = payload
            clean_parts.append(text)
            markup_parts.append(_apply_marks(text, marks))
            pos += len(text)

        elif kind == 'tool':
            code, articul = payload
            label = f"🔧 {code}"
            if articul:
                label += f" — {articul}"
            start = pos
            clean_parts.append(label)
            markup_parts.append(
                f"[color=1976D2][u]{_escape_markup(label)}[/u][/color]"
            )
            pos += len(label)
            click_map.append((start, pos, 'tool', code))

        elif kind == 'mention':
            name, uid = payload
            label = f"@{name}"
            start = pos
            clean_parts.append(label)
            markup_parts.append(
                f"[color=2E7D32][b]{_escape_markup(label)}[/b][/color]"
            )
            pos += len(label)
            click_map.append((start, pos, 'mention', str(uid)))

    return ''.join(clean_parts), ''.join(markup_parts), click_map


def _apply_marks(text: str, marks: Tuple[str, ...]) -> str:
    safe = _escape_markup(text)
    if 'md_code' in marks:
        safe = f"[color=1E1E1E][bg=EFEFEF]{safe}[/bg][/color]"
    if 'md_strike' in marks:
        safe = f"[s]{safe}[/s]"
    if 'md_underline' in marks:
        safe = f"[u]{safe}[/u]"
    if 'md_italic' in marks:
        safe = f"[i]{safe}[/i]"
    if 'md_bold' in marks:
        safe = f"[b]{safe}[/b]"
    return safe


# ─── Парсер markdown + ссылок ───

def _parse_fragments(text: str) -> List[Tuple[str, object, Tuple[str, ...]]]:
    if not text:
        return []

    markers: List[Tuple[int, int, str, object]] = []
    for m in RE_TOOL_LINK.finditer(text):
        markers.append((m.start(), m.end(), 'tool', (m.group(1), m.group(2))))
    for m in RE_MENTION.finditer(text):
        markers.append((m.start(), m.end(), 'mention', (m.group(1), int(m.group(2)))))

    markers.sort(key=lambda x: x[0])

    filtered = []
    last_end = -1
    for mk in markers:
        if mk[0] >= last_end:
            filtered.append(mk)
            last_end = mk[1]

    result: List[Tuple[str, object, Tuple[str, ...]]] = []
    pos = 0
    for start, end, kind, payload in filtered:
        if start > pos:
            _append_text_fragments(text[pos:start], result)
        result.append((kind, payload, ()))
        pos = end
    if pos < len(text):
        _append_text_fragments(text[pos:], result)
    return result


def _append_text_fragments(text: str, out: list) -> None:
    pos = 0
    for m in RE_CODE.finditer(text):
        if m.start() > pos:
            _split_bold(text[pos:m.start()], out, marks=())
        out.append(('text', m.group(1), ('md_code',)))
        pos = m.end()
    if pos < len(text):
        _split_bold(text[pos:], out, marks=())


def _split_bold(text: str, out: list, marks: Tuple[str, ...]) -> None:
    pos = 0
    for m in RE_BOLD.finditer(text):
        if m.start() > pos:
            _split_italic(text[pos:m.start()], out, marks)
        out.append(('text', m.group(1), marks + ('md_bold',)))
        pos = m.end()
    if pos < len(text):
        _split_italic(text[pos:], out, marks)


def _split_italic(text: str, out: list, marks: Tuple[str, ...]) -> None:
    pos = 0
    for m in RE_ITALIC.finditer(text):
        if m.start() > pos:
            _split_strike(text[pos:m.start()], out, marks)
        out.append(('text', m.group(1), marks + ('md_italic',)))
        pos = m.end()
    if pos < len(text):
        _split_strike(text[pos:], out, marks)


def _split_strike(text: str, out: list, marks: Tuple[str, ...]) -> None:
    pos = 0
    for m in RE_STRIKE.finditer(text):
        if m.start() > pos:
            _split_underline(text[pos:m.start()], out, marks)
        out.append(('text', m.group(1), marks + ('md_strike',)))
        pos = m.end()
    if pos < len(text):
        _split_underline(text[pos:], out, marks)


def _split_underline(text: str, out: list, marks: Tuple[str, ...]) -> None:
    pos = 0
    for m in RE_UNDERLINE.finditer(text):
        if m.start() > pos:
            out.append(('text', text[pos:m.start()], marks))
        out.append(('text', m.group(1), marks + ('md_underline',)))
        pos = m.end()
    if pos < len(text):
        out.append(('text', text[pos:], marks))


# ─── Публичная фабрика ───

def create_message_widget(
    text: str,
    bg_rgba,
    fg_rgba,
    name_color_rgba,
    font_size: float = dp(13),
    on_tool_click: Optional[Callable[[str], None]] = None,
    on_mention_click: Optional[Callable[[int], None]] = None,
) -> MessageText:
    return MessageText(
        raw_text=text,
        fg_rgba=fg_rgba,
        bg_rgba=bg_rgba,
        font_size=font_size,
        on_tool_click=on_tool_click,
        on_mention_click=on_mention_click,
    )