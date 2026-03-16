from __future__ import annotations

import flet as ft

from app.state import AppState, PreferencesSaveError, save_state
from app.components.controls import primary_button
from app.components.theme import ACCENT, ACCENT_DARK

SUPPORTED_LANGUAGES = [
    "English", "Bahasa Melayu", "Bahasa Indonesia", "Thai", "Vietnamese",
    "Filipino/Tagalog", "Burmese", "Khmer", "Lao", "Chinese (Simplified)", "Tamil"
]

ASEAN_COUNTRIES = [
    "Malaysia", "Indonesia", "Thailand", "Vietnam", "Philippines",
    "Myanmar", "Cambodia", "Laos", "Singapore", "Brunei", "Timor-Leste"
]

FONT_SIZES = ["Small", "Medium", "Large"]


def build_preferences_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /preferences view — country, language, font size."""

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    sel_country = [state.country or None]
    sel_language = [state.language or None]
    sel_font = [state.font_size or "Medium"]

    error_text = ft.Text("", color=ft.colors.RED_600, visible=False)

    def section_header(title: str) -> ft.Text:
        return ft.Text(
            title,
            size=state.font_sp() + 2,
            weight=ft.FontWeight.BOLD,
            color=state.text_color(),
        )

    def _all_selected() -> bool:
        return bool(sel_country[0] and sel_language[0] and sel_font[0])

    confirm_btn = primary_button(label="Confirm", on_click=None, width=280, state=state)
    confirm_btn.disabled = not _all_selected()

    # --- Country dropdown ---
    def on_country_change(e):
        sel_country[0] = e.control.value
        confirm_btn.disabled = not _all_selected()
        error_text.visible = False
        page.update()

    country_dropdown = ft.Dropdown(
        value=sel_country[0],
        hint_text="Select a country...",
        options=[ft.dropdown.Option(c) for c in ASEAN_COUNTRIES],
        on_change=on_country_change,
        color=state.text_color(),
        bgcolor=state.surface_color(),
        border_color=accent,
        border_radius=8,
        text_size=state.font_sp(),
    )

    # --- Language dropdown ---
    def on_language_change(e):
        sel_language[0] = e.control.value
        confirm_btn.disabled = not _all_selected()
        error_text.visible = False
        page.update()

    language_dropdown = ft.Dropdown(
        value=sel_language[0],
        hint_text="Select a language...",
        options=[ft.dropdown.Option(lang) for lang in SUPPORTED_LANGUAGES],
        on_change=on_language_change,
        color=state.text_color(),
        bgcolor=state.surface_color(),
        border_color=accent,
        border_radius=8,
        text_size=state.font_sp(),
    )

    # --- Font size buttons ---
    font_preview = ft.Text(
        "This is how your text will look.",
        size={"Small": 14, "Medium": 16, "Large": 20}.get(sel_font[0], 16),
        color=state.text_color(),
    )

    font_row = ft.Row(spacing=8)

    def _build_font_tiles():
        def _handler(size):
            def h(e):
                sel_font[0] = size
                font_preview.size = {"Small": 14, "Medium": 16, "Large": 20}[size]
                _build_font_tiles()
                confirm_btn.disabled = not _all_selected()
                error_text.visible = False
                page.update()
            return h
        font_row.controls = [
            ft.Container(
                content=ft.Text(size, size=state.font_sp(), color=state.text_color()),
                on_click=_handler(size),
                bgcolor=ft.colors.with_opacity(0.08, accent) if size == sel_font[0] else ft.colors.TRANSPARENT,
                border=ft.border.all(3, accent if size == sel_font[0] else ft.colors.GREY_400),
                border_radius=8,
                padding=ft.padding.symmetric(vertical=14, horizontal=20),
                height=52,
                alignment=ft.alignment.center,
            )
            for size in FONT_SIZES
        ]

    _build_font_tiles()

    # --- Confirm ---
    def handle_confirm(e):
        error_text.visible = False
        state.country = sel_country[0]
        state.language = sel_language[0]
        state.font_size = sel_font[0]
        state.onboarding_complete = True
        try:
            save_state(state)
        except PreferencesSaveError as exc:
            error_text.value = f"Could not save preferences: {exc}"
            error_text.visible = True
            page.update()
            return
        page.go("/home")

    confirm_btn.on_click = handle_confirm

    content = ft.Column(
        controls=[
            section_header("Select Your Country"),
            ft.Container(height=8),
            country_dropdown,
            ft.Container(height=28),

            section_header("Select Your Language"),
            ft.Container(height=8),
            language_dropdown,
            ft.Container(height=28),

            section_header("Choose Text Size"),
            ft.Container(height=8),
            font_row,
            ft.Container(height=12),
            font_preview,
            ft.Container(height=28),

            error_text,
            ft.Container(height=8),
            ft.Container(content=confirm_btn, alignment=ft.alignment.center),
            ft.Container(height=40),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.View(
        route="/preferences",
        controls=[
            ft.Container(
                content=content,
                expand=True,
                bgcolor=state.bg_color(),
                padding=ft.padding.symmetric(horizontal=24, vertical=32),
            )
        ],
        bgcolor=state.bg_color(),
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
