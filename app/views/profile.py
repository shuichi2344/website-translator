from __future__ import annotations

import flet as ft

from app.state import AppState, save_state
from app.components.theme import ACCENT, ACCENT_DARK, apply_theme
from app.components.controls import selection_tile
from app.views.preferences import SUPPORTED_LANGUAGES, ASEAN_COUNTRIES

FONT_SIZES = ["Small", "Medium", "Large"]


def build_profile_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /profile view — displays user info and editable preferences."""

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    # --- Section header helper ---
    def section_header(title: str) -> ft.Text:
        return ft.Text(
            title,
            size=state.font_sp() + 2,
            weight=ft.FontWeight.BOLD,
            color=state.text_color(),
        )

    # --- Language dropdown ---
    def handle_language_change(e):
        state.language = e.control.value
        save_state(state)
        page.update()

    language_dropdown = ft.Dropdown(
        value=state.language,
        options=[ft.dropdown.Option(lang) for lang in SUPPORTED_LANGUAGES],
        on_change=handle_language_change,
        color=state.text_color(),
        bgcolor=state.surface_color(),
        border_color=accent,
        border_radius=8,
        text_size=state.font_sp(),
        expand=True,
    )

    # --- Country dropdown ---
    def handle_country_change(e):
        state.country = e.control.value
        save_state(state)
        page.update()

    country_dropdown = ft.Dropdown(
        value=state.country,
        options=[ft.dropdown.Option(c) for c in ASEAN_COUNTRIES],
        on_change=handle_country_change,
        color=state.text_color(),
        bgcolor=state.surface_color(),
        border_color=accent,
        border_radius=8,
        text_size=state.font_sp(),
        expand=True,
    )

    # --- Font size tiles ---
    font_tiles_row = ft.Row(spacing=8, expand=True)

    def _build_font_tiles():
        font_tiles_row.controls = [
            selection_tile(
                label=size,
                selected=(size == state.font_size),
                on_click=_make_font_handler(size),
                state=state,
            )
            for size in FONT_SIZES
        ]

    def _make_font_handler(size: str):
        def handler(e):
            state.font_size = size
            save_state(state)
            page.go("/profile")
        return handler

    _build_font_tiles()

    # --- Dark mode switch ---
    dark_switch = ft.Switch(
        label="Dark Mode",
        value=state.theme_mode == "Dark",
        active_color=accent,
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    def handle_switch_change(e):
        state.theme_mode = "Dark" if dark_switch.value else "Light"
        save_state(state)
        apply_theme(page, state)
        page.go("/profile")

    dark_switch.on_change = handle_switch_change

    # --- Log out button ---
    logout_btn = ft.ElevatedButton(
        text="Log Out",
        on_click=lambda _: page.go("/login"),
        width=280,
        height=52,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.RED_600,
            color=ft.colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(vertical=14, horizontal=24),
        ),
    )

    # --- Scrollable content ---
    content = ft.ListView(
        controls=[
            # User avatar + username
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.icons.PERSON_CIRCLE_OUTLINED,
                            size=64,
                            color=accent,
                        ),
                        ft.Text(
                            state.username,
                            size=state.font_sp() + 4,
                            weight=ft.FontWeight.BOLD,
                            color=state.text_color(),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=24),
            ),

            # Language section
            section_header("Language"),
            ft.Container(height=8),
            language_dropdown,
            ft.Container(height=24),

            # Country section
            section_header("Country"),
            ft.Container(height=8),
            country_dropdown,
            ft.Container(height=24),

            # Text size section
            section_header("Text Size"),
            ft.Container(height=8),
            font_tiles_row,
            ft.Container(height=24),

            # Display mode section
            section_header("Display Mode"),
            ft.Container(height=8),
            dark_switch,
            ft.Container(height=32),

            # Log out
            ft.Container(
                content=logout_btn,
                alignment=ft.alignment.center,
            ),
            ft.Container(height=32),
        ],
        spacing=0,
        padding=ft.padding.symmetric(horizontal=24, vertical=24),
        expand=True,
    )

    return ft.View(
        route="/profile",
        appbar=ft.AppBar(
            title=ft.Text(
                "Profile",
                color=state.text_color(),
                size=state.font_sp() + 2,
                weight=ft.FontWeight.BOLD,
            ),
            bgcolor=state.bg_color(),
            leading=ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                icon_color=state.text_color(),
                on_click=lambda _: page.go("/home"),
            ),
            automatically_imply_leading=False,
        ),
        controls=[
            ft.Container(
                content=content,
                expand=True,
                bgcolor=state.bg_color(),
            )
        ],
        bgcolor=state.bg_color(),
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
