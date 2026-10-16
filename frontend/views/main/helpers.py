# frontend/views/main/helpers.py
def get_initials(full_name: str) -> str:
    if not full_name:
        return "?"
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return full_name[0].upper()


def clean_tab_label(tab_text: str) -> str:
    if not tab_text:
        return ""
    for e in ("📦", "⚙", "⏳", "▤", "📋", "📤"):
        tab_text = tab_text.replace(e, "")
    return tab_text.strip()