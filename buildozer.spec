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

#Ключевое для Android
requirements = hostpython3==3.11.9, python3==3.11.9, kivy==2.2.1, plyer, openpyxl
p4a.branch = develop
android.python_version = 3.11

orientation = landscape
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
