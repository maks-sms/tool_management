# frontend/views/chat/chat_constants.py
"""Константы чата: типы, цвета, иконки, лимиты."""
from enum import Enum


class ChatType(str, Enum):
    GENERAL = "general"
    PRIVATE = "private"
    GROUP = "group"


class MessageAlignment(str, Enum):
    LEFT = "left"
    RIGHT = "right"


# Цвета пузырьков (RGBA, как понимает Kivy)
# Взяты из client_desktop/views/chat/chat_constants.py, переведены в RGBA.
BUBBLE_COLORS = {
    'my': {
        'bubble':  (0.910, 0.961, 0.914, 1),   # #E8F5E9
        'text':    (0.118, 0.118, 0.118, 1),   # #1E1E1E
        'name':    (0.180, 0.490, 0.196, 1),   # #2E7D32
        'time':    (0.459, 0.459, 0.459, 1),   # #757575
        'quote_bg':(0.878, 0.949, 0.878, 1),   # #E0F2E0
        'quote_border': (0.506, 0.780, 0.522, 1),  # #81C784
        'quote_text': (0.180, 0.490, 0.196, 1),
        'file_bg': (0.878, 0.949, 0.878, 1),
        'file_text': (0.180, 0.490, 0.196, 1),
    },
    'other': {
        'bubble':  (0.961, 0.961, 0.961, 1),   # #F5F5F5
        'text':    (0.118, 0.118, 0.118, 1),
        'name':    (0.098, 0.463, 0.824, 1),   # #1976D2
        'time':    (0.459, 0.459, 0.459, 1),
        'quote_bg':(0.910, 0.910, 0.910, 1),   # #E8E8E8
        'quote_border': (0.392, 0.710, 0.965, 1),  # #64B5F6
        'quote_text': (0.098, 0.463, 0.824, 1),
        'file_bg': (0.910, 0.910, 0.910, 1),
        'file_text': (0.098, 0.463, 0.824, 1),
    },
}


FILE_ICONS = {
    '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️',
    '.zip': '📦', '.rar': '📦', '.7z': '📦',
    '.pdf': '📑',
    '.xls': '📊', '.xlsx': '📊',
    '.doc': '📝', '.docx': '📝',
}


REFRESH_INTERVALS = {
    'messages':   5,
    'chats_list': 5,
    'activity':   60,
    'badge':      30,
}


MESSAGE_LIMIT = 100
MESSAGE_PREVIEW_LENGTH = 100