from __future__ import annotations

import flet as ft

from app.state import AppState

ACCENT = "#000000"       # black accent (light mode)
ACCENT_DARK = "#FFFFFF"  # white accent (dark mode)


def apply_theme(page: ft.Page, state: AppState) -> None:
    """Set page.theme_mode and page.bgcolor based on AppState, then update."""
    if state.theme_mode == "Dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = state.bg_color()
    page.update()
