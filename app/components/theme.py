from __future__ import annotations

import flet as ft

from app.state import AppState

# Blue → Purple → Pink → Mint gradient
ACCENT        = "#6B5FD9"   # Purple (primary accent)
ACCENT_DARK   = "#7DD3C0"   # Mint (dark mode accent)
ACCENT_BLUE   = "#0066CC"   # Deep blue (secondary)
ACCENT_BLUE_DARK = "#E991CC"  # Pink (dark mode)

# Multi-color gradient
GRAD_START    = "#0066CC"   # Deep blue
GRAD_END      = "#7DD3C0"   # Mint

GRAD_START_DARK  = "#0066CC"  # Deep blue
GRAD_END_DARK    = "#7DD3C0"  # Mint


def accent_gradient(dark: bool = False) -> ft.LinearGradient:
    """Blue → Purple → Pink → Mint gradient for both light and dark modes."""
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
