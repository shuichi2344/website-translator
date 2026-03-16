from __future__ import annotations

import flet as ft

from app.state import AppState, load_state
from app.components.controls import primary_button
from app.components.theme import ACCENT


def build_login_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /login view — minimalistic iOS-style login/register screen."""

    is_signup = [False]

    username_field = ft.TextField(
        label="Username",
        border_color=ACCENT,
        border_radius=12,
        border_width=3,
        width=300,
        text_size=state.font_sp(),
        color=state.text_color(),
        bgcolor=state.surface_color(),
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    password_field = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        border_color=ACCENT,
        border_radius=12,
        border_width=3,
        width=300,
        text_size=state.font_sp(),
        color=state.text_color(),
        bgcolor=state.surface_color(),
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    # Mutable controls that change between login/signup modes
    title_text = ft.Text(
        "Log In",
        size=state.font_sp() + 6,
        weight=ft.FontWeight.BOLD,
        color=state.text_color(),
    )

    submit_btn = primary_button(
        label="Log In",
        on_click=None,
        width=300,
        state=state,
    )

    toggle_btn = ft.TextButton(
        text="New here? Create an account",
        on_click=None,
        style=ft.ButtonStyle(color=ACCENT),
    )

    def _refresh():
        if is_signup[0]:
            title_text.value = "Create Account"
            submit_btn.text = "Create Account"
            toggle_btn.text = "Already have an account? Log in"
        else:
            title_text.value = "Log In"
            submit_btn.text = "Log In"
            toggle_btn.text = "New here? Create an account"
        page.update()

    def handle_login(e):
        username = username_field.value or ""
        if not username:
            return
        loaded = load_state(username)
        state.username = loaded.username
        state.language = loaded.language
        state.country = loaded.country
        state.font_size = loaded.font_size
        state.theme_mode = loaded.theme_mode
        state.onboarding_complete = loaded.onboarding_complete

        if state.onboarding_complete:
            page.go("/home")
        else:
            page.go("/onboarding")

    def handle_register(e):
        # Save the new user state so they get onboarding on next login
        state.username = username_field.value or "user"
        state.onboarding_complete = False
        from app.state import save_state
        save_state(state)
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Account created! Please log in.", color=ft.colors.WHITE),
            bgcolor=ACCENT,
        )
        page.snack_bar.open = True
        is_signup[0] = False
        _refresh()

    def handle_submit(e):
        if is_signup[0]:
            handle_register(e)
        else:
            handle_login(e)

    def toggle_mode(e):
        is_signup[0] = not is_signup[0]
        _refresh()

    submit_btn.on_click = handle_submit
    toggle_btn.on_click = toggle_mode

    content_column = ft.Column(
        controls=[
            ft.Icon(ft.icons.CHAT_BUBBLE_OUTLINE_ROUNDED, size=72, color=ACCENT),
            ft.Container(height=8),
            title_text,
            ft.Container(height=24),
            username_field,
            ft.Container(height=12),
            password_field,
            ft.Container(height=24),
            submit_btn,
            ft.Container(height=8),
            toggle_btn,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
        tight=True,
    )

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=content_column,
                alignment=ft.alignment.center,
                expand=True,
                padding=ft.padding.symmetric(horizontal=24, vertical=40),
            )
        ],
        bgcolor=state.bg_color(),
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
