# frontend/views/main/filter_actions.py
"""Сброс фильтров (Kivy)."""


class FilterActions:
    def __init__(self, app):
        self.app = app

    def clear_inventory_filters(self):
        tabs = getattr(self.app.main_screen, 'tab_widgets', {})
        inv = tabs.get('inventory')
        if inv and inv.filter_bar:
            inv.filter_bar.clear()
        self.app.refresh_all()

    def clear_requests_filters(self):
        tabs = getattr(self.app.main_screen, 'tab_widgets', {})
        req = tabs.get('requests')
        if req and req.filter_bar:
            req.filter_bar.clear()
        self.app.refresh_requests_tab()