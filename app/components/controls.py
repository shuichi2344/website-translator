from __future__ import annotations

import flet as ft

from app.state import AppState
from app.components.theme import ACCENT, ACCENT_DARK, accent_gradient


def primary_button(
    label: str,
    on_click,
    width: int = 280,
    state: AppState = None,
) -> ft.ElevatedButton:
    """Accessible primary button — min 52px height, min 200px width, gradient bg."""
    dark = state and state.theme_mode == "Dark"
    bgcolor = ACCENT_DARK if dark else ACCENT
    return ft.ElevatedButton(
        text=label,
        on_click=on_click,
        width=max(width, 200),
        style=ft.ButtonStyle(
            bgcolor=bgcolor,
            color=ft.colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(vertical=14, horizontal=24),
            side=ft.BorderSide(width=0, color=ft.colors.TRANSPARENT),
        ),
        height=56,
    )


def selection_tile(
    label: str,
    selected: bool,
    on_click,
    state: AppState,
) -> ft.Container:
    """Tappable selection tile — min 48×48px touch target, highlighted when selected."""
    accent = ACCENT_DARK if (state and state.theme_mode == "Dark") else ACCENT
    if selected:
        border_color = accent
        bg = ft.colors.with_opacity(0.12, accent)
    else:
        border_color = (
            ft.colors.GREY_400 if (state and state.theme_mode == "Light") else ft.colors.GREY_700
        )
        bg = ft.colors.TRANSPARENT

    return ft.Container(
        content=ft.Text(
            label,
            color=state.text_color() if state else ft.colors.BLACK,
            size=state.font_sp() if state else 16,
        ),
        on_click=on_click,
        bgcolor=bg,
        border=ft.border.all(3, border_color),
        border_radius=8,
        padding=ft.padding.symmetric(vertical=12, horizontal=16),
        height=48,
        expand=True,
        alignment=ft.alignment.center_left,
    )


def dot_indicator(total: int, current: int, state: AppState) -> ft.Row:
    """Row of `total` dots; filled (ACCENT) at index `current`, grey elsewhere."""
    accent = ACCENT_DARK if (state and state.theme_mode == "Dark") else ACCENT
    dots = []
    for i in range(total):
        filled = i == current
        dots.append(
            ft.Container(
                width=10,
                height=10,
                border_radius=5,
                bgcolor=accent if filled else ft.colors.GREY_400,
                margin=ft.margin.symmetric(horizontal=4),
            )
        )
    return ft.Row(controls=dots, alignment=ft.MainAxisAlignment.CENTER)
