# frontend/views/license_screen.py
"""Окно активации. Виджет, без своего App."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from frontend.config import APP_NAME
from frontend.theme import C
from frontend.widgets.modern_entry import ModernEntry
from frontend.widgets.modern_button import ModernButton


class LicenseScreen(BoxLayout):
    def __init__(self, on_done=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('padding', [dp(24), dp(16)])
        kw.setdefault('spacing', dp(6))
        super().__init__(**kw)

        self._on_done = on_done

        with self.canvas.before:
            Color(*C['bg'])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build()

    def _label(self, text, bold=False, color=None, height=18, size=12):
        lbl = Label(
            text=text, bold=bold, color=color or C['secondary'],
            font_size=dp(size), size_hint_y=None, height=dp(height),
            halign='left', valign='middle',
        )
        lbl.bind(size=lambda inst, *_: setattr(
            inst, 'text_size', (inst.width, inst.height)))
        return lbl

    def _build(self):
        from shared.services.licensing.hw_id import get_hardware_id
        from shared.services.licensing.license_manager import (
            get_license_info,
        )

        self.add_widget(Label(
            text='🔐  Активация программы',
            bold=True, font_size=dp(18), color=C['primary'],
            size_hint_y=None, height=dp(32),
        ))
        self.add_widget(Label(
            text=APP_NAME, font_size=dp(12), color=C['gray'],
            size_hint_y=None, height=dp(18),
        ))

        try:
            info = get_license_info()
        except Exception:
            info = None
        if info:
            self.add_widget(self._label(
                f"Текущая лицензия: {info.get('company', '—')}",
                bold=True, color=C['primary'], height=20, size=12,
            ))

        self.add_widget(BoxLayout(size_hint_y=None, height=dp(6)))

        try:
            hw = get_hardware_id() or ''
        except Exception as e:
            print(f'[license] hw_id error: {e}')
            hw = ''

        self.add_widget(self._label(
            'Ваш HW-ID:', bold=True, color=C['secondary'],
            height=18, size=12,
        ))

        hw_wrap = BoxLayout(
            orientation='horizontal', size_hint_y=None,
            height=dp(34), padding=[dp(8), dp(6)],
        )
        with hw_wrap.canvas.before:
            Color(*C['soft'])
            hw_wrap._bg = Rectangle(pos=hw_wrap.pos, size=hw_wrap.size)
        hw_wrap.bind(
            pos=lambda i, *_: setattr(i._bg, 'pos', i.pos),
            size=lambda i, *_: setattr(i._bg, 'size', i.size),
        )
        self.hw_label = Label(
            text=hw if hw else '— не удалось получить HW-ID —',
            color=C['input_fg'] if hw else C['danger'],
            font_size=dp(13), halign='center', valign='middle',
        )
        self.hw_label.bind(
            size=lambda inst, *_: setattr(
                inst, 'text_size', (inst.width, inst.height)))
        hw_wrap.add_widget(self.hw_label)
        self.add_widget(hw_wrap)

        copy_row = BoxLayout(
            size_hint_y=None, height=dp(32), spacing=dp(6),
        )
        copy_row.add_widget(ModernButton(
            text='📋  Копировать HW-ID', color='info',
            size_hint=(None, None), size=(dp(200), dp(30)),
            on_release=lambda *_: self._copy_hw(hw),
        ))
        copy_row.add_widget(BoxLayout())
        self.add_widget(copy_row)

        self.add_widget(BoxLayout(size_hint_y=None, height=dp(6)))

        self.company = ModernEntry(
            label_text='Название организации:',
            placeholder='ООО «Пример»',
        )
        self.add_widget(self.company)

        self.key = ModernEntry(
            label_text='Ключ активации:',
            placeholder='TM2-XXXXX-XXXXX-XXXXX-XXXXX',
        )
        self.add_widget(self.key)

        self.expire = ModernEntry(
            label_text='Срок действия (ГГГГ-ММ-ДД):',
            placeholder='2027-12-31',
        )
        self.add_widget(self.expire)

        self.error_lbl = Label(
            text='', color=C['danger'],
            size_hint_y=None, height=dp(18), font_size=dp(11),
        )
        self.add_widget(self.error_lbl)

        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        row.add_widget(ModernButton(
            text='✅  Активировать', color='success',
            on_release=lambda *_: self._activate(),
        ))
        row.add_widget(ModernButton(
            text='❌  Закрыть', color='danger',
            on_release=lambda *_: self._close(),
        ))
        self.add_widget(row)

    def _copy_hw(self, hw):
        try:
            if hw:
                Clipboard.copy(hw)
                self.error_lbl.text = 'HW-ID скопирован в буфер обмена'
                self.error_lbl.color = C['success']
            else:
                self.error_lbl.text = 'HW-ID отсутствует'
                self.error_lbl.color = C['danger']
        except Exception as e:
            self.error_lbl.text = f'Ошибка: {e}'
            self.error_lbl.color = C['danger']

    def _activate(self):
        from shared.services.licensing.license_manager import activate
        from datetime import datetime

        company = self.company.get().strip()
        key = self.key.get().strip()
        exp_str = self.expire.get().strip()

        if not company:
            self.error_lbl.text = 'Укажите название организации'
            self.error_lbl.color = C['danger']
            return
        if not key:
            self.error_lbl.text = 'Введите ключ активации'
            self.error_lbl.color = C['danger']
            return

        expire = None
        if exp_str:
            try:
                expire = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except ValueError:
                self.error_lbl.text = 'Дата в формате ГГГГ-ММ-ДД'
                self.error_lbl.color = C['danger']
                return

        if activate(key, company, expire):
            if self._on_done:
                self._on_done(True)
        else:
            self.error_lbl.text = '❌ Неверный ключ активации'
            self.error_lbl.color = C['danger']

    def _close(self):
        if self._on_done:
            self._on_done(False)