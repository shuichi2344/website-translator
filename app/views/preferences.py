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

def build_preferences_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /preferences view — country and language."""

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    sel_country = [state.country or None]
    sel_language = [state.language or None]

    error_text = ft.Text("", color=ft.colors.RED_600, visible=False)

    def section_header(title: str) -> ft.Text:
        return ft.Text(
            title,
            size=state.font_sp() + 2,
            weight=ft.FontWeight.BOLD,
            color=state.text_color(),
        )

    def _all_selected() -> bool:
        return bool(sel_country[0] and sel_language[0])

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

    # --- Confirm ---
    def handle_confirm(e):
        error_text.visible = False
        state.country = sel_country[0]
        state.language = sel_language[0]
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
