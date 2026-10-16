# frontend/assets/fonts/build_font.py
"""
Собирает единый TTF: Roboto + Symbola.

Использование:
    python build_font.py

На выходе:
    AppFont-Regular.ttf   — для обычного текста + эмодзи
    AppFont-Bold.ttf      — жирная версия
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Исходники ---
# Возьмите Roboto отсюда: https://fonts.google.com/specimen/Roboto
# Symbola: https://github.com/umbertrust/Symbola
ROBOTO_REGULAR = os.path.join(HERE, 'Roboto-Regular.ttf')
ROBOTO_BOLD    = os.path.join(HERE, 'Roboto-Bold.ttf')
SYMBOLA        = os.path.join(HERE, 'Symbola.ttf')

OUT_REGULAR = os.path.join(HERE, 'AppFont-Regular.ttf')
OUT_BOLD    = os.path.join(HERE, 'AppFont-Bold.ttf')


def merge(base_font, emoji_font, out_font):
    """Слить два TTF в один: base + недостающие глифы из emoji."""
    try:
        from fontTools.merge import Merger
    except ImportError:
        print("Установите fonttools:  pip install fonttools")
        sys.exit(1)

    if not os.path.exists(base_font):
        print(f'[merge] нет файла: {base_font}')
        return False
    if not os.path.exists(emoji_font):
        print(f'[merge] нет файла: {emoji_font}')
        return False

    print(f'[merge] {os.path.basename(base_font)} + '
          f'{os.path.basename(emoji_font)} → '
          f'{os.path.basename(out_font)}')

    merger = Merger()
    # ВАЖНО: base идёт первым — его метрики становятся основными
    font = merger.merge([base_font, emoji_font])
    font.save(out_font)
    print(f'[merge] готово: {out_font}')
    return True


if __name__ == '__main__':
    ok1 = merge(ROBOTO_REGULAR, SYMBOLA, OUT_REGULAR)
    ok2 = merge(ROBOTO_BOLD,    SYMBOLA, OUT_BOLD)

    if not (ok1 and ok2):
        print('\nСкачайте Roboto с https://fonts.google.com/specimen/Roboto')
        print('и Symbola с https://github.com/umbertust/Symbola,')
        print('положите .ttf в', HERE)
        sys.exit(1)