[app]
title = Tool Management
package.name = toolmanagement
package.domain = org.solodovnikov

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,db,csv

source.include_patterns = \
    frontend/*, \
    frontend/assets/*, \
    frontend/assets/fonts/*, \
    frontend/views/*, \
    frontend/views/**/*, \
    shared/*, \
    shared/**/*, \
    server/*, \
    server/**/*

version = 2.0

# ─── Ключевое: явно указываем версию Python и Kivy ───
# Мы используем Python 3.11, так как он стабильно поддерживается p4a.
# Kivy 2.1.0 не тянет за собой проблемный libthorvg.
requirements = python3==3.10.11, hostpython3==3.10.11, kivy==2.1.0, plyer, openpyxl

# ─── Ключевое: используем существующий стабильный тег p4a ───
# Тег v2023.09.16 — последняя стабильная версия на Python 3.10/3.11 без libthorvg.
p4a.branch = v2023.09.16

orientation = landscape
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True
android.accept_sdk_license = True
