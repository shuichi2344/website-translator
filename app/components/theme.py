from __future__ import annotations

import flet as ft

from app.state import AppState

# Purple-to-blue gradient palette
ACCENT        = "#7C3AED"   # violet-600  (light mode primary)
ACCENT_DARK   = "#A78BFA"   # violet-400  (dark mode primary)
ACCENT_BLUE   = "#2563EB"   # blue-600
ACCENT_BLUE_DARK = "#60A5FA"  # blue-400

# Gradient stops used across the app
GRAD_START    = "#7C3AED"   # purple
GRAD_END      = "#2563EB"   # blue

GRAD_START_DARK  = "#A78BFA"
GRAD_END_DARK    = "#60A5FA"


def accent_gradient(dark: bool = False) -> ft.LinearGradient:
    """Horizontal purple→blue gradient for backgrounds and fills."""
    return ft.LinearGradient(
        begin=ft.alignment.center_left,
        end=ft.alignment.center_right,
        colors=[GRAD_START_DARK if dark else GRAD_START,
                GRAD_END_DARK   if dark else GRAD_END],
    )


def apply_theme(page: ft.Page, state: AppState) -> None:
    """Set page.theme_mode and page.bgcolor based on AppState, then update."""
    if state.theme_mode == "Dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = state.bg_color()
    page.update()
