# frontend/kv_style.py
"""Глобальная светлая тема для нативных Kivy-виджетов."""
from kivy.lang import Builder


KV = """
#:import C frontend.theme.C
#:import F frontend.theme.FONT_NAME

<Label>:
    color: C['dark']
    font_size: '13sp'
    font_name: F

<Button>:
    font_name: F

<TextInput>:
    background_normal: ''
    background_active: ''
    background_color: C['input_bg']
    foreground_color: C['input_fg']
    cursor_color: C['input_fg']
    hint_text_color: C['input_hint']
    font_size: '13sp'
    font_name: F
    padding: [8, 6, 8, 6]

<Spinner>:
    background_normal: ''
    background_down: ''
    background_color: C['input_bg']
    color: C['input_fg']
    font_size: '13sp'
    font_name: F

<SpinnerOption>:
    background_normal: ''
    background_down: ''
    background_color: C['input_bg'] if self.state == 'normal' else C['soft']
    color: C['input_fg']
    font_size: '13sp'
    font_name: F
    height: '32dp'

<DropDown>:
    background_color: C['panel']
    border: [4, 4, 4, 4]

<CheckBox>:
    color: C['checkbox_fg']

<Popup>:
    background: ''
    background_color: C['popup_bg']
    title_color: C['popup_title']
    separator_color: C['border']

<PopupTitle>:
    color: C['popup_title']
    font_name: F

<ScrollView>:
    bar_color: C['scrollbar_grip']
    bar_inactive_color: C['scrollbar_bg']
    bar_width: '8dp'

<TabbedPanel>:
    background_color: C['soft']
    border: [0, 0, 0, 3]  
    tab_width: '170dp'
    tab_height: '38dp'

<TabbedPanelHeader>:
    background_normal: ''
    background_down: ''
    background_color: C['soft'] if self.state == 'normal' else C['panel']
    color: C['gray'] if self.state == 'normal' else C['primary']
    font_size: '13sp'
    font_name: F
    bold: True
    disabled_color: C['gray']

<TabbedPanelItem>:
    background_normal: ''
    background_down: ''
    background_color: C['soft'] if self.state == 'normal' else C['panel']
    color: C['gray'] if self.state == 'normal' else C['primary']
    font_size: '13sp'
    font_name: F
    bold: True

<Slider>:
    color: C['slider_fg']

<ModalView>:
    background: ''
    background_color: C['popup_bg']
    background_opacity: 1.0
"""


_loaded = False


def apply_theme():
    global _loaded
    if _loaded:
        return
    Builder.load_string(KV)
    _loaded = True