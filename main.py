# main.py
"""
Точка входа для Android-сборки.

Buildozer ищет main.py в корне проекта. Он запускает Kivy-приложение
из frontend/main.py.
"""
import os
import sys

# Корень проекта в sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Запуск настоящего приложения из frontend/main.py
from frontend.main import main

if __name__ == '__main__':
    main()
