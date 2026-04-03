from __future__ import annotations

import sys
import os
import flet as ft

from app.state import AppState, load_state
from app.components.controls import primary_button
from app.components.theme import ACCENT

# Add parent directory to path for database imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Database imports
try:
    from engine.database.auth_handler import AuthHandler
    auth_handler = AuthHandler()
    DB_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Database not available: {e}")
    auth_handler = None
    DB_AVAILABLE = False


def build_login_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /login view — minimalistic iOS-style login/register screen."""

    is_signup = [False]

    username_field = ft.TextField(
        label="Email",
        border_color=ACCENT,
        border_radius=12,
        border_width=3,
        width=300,
        text_size=state.font_sp(),
        color=state.text_color(),
        bgcolor=state.surface_color(),
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )
    
    name_field = ft.TextField(
        label="Full Name",
        border_color=ACCENT,
        border_radius=12,
        border_width=3,
        width=300,
        text_size=state.font_sp(),
        color=state.text_color(),
        bgcolor=state.surface_color(),
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
        visible=False,  # Only show in signup mode
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
            name_field.visible = True
        else:
            title_text.value = "Log In"
            submit_btn.text = "Log In"
            toggle_btn.text = "New here? Create an account"
            name_field.visible = False
        page.update()

    def handle_login(e):
        email = username_field.value or ""
        password = password_field.value or ""
        
        if not email or not password:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Please enter email and password", color=ft.colors.WHITE),
                bgcolor=ft.colors.RED_400,
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Try MySQL authentication first
        if DB_AVAILABLE and auth_handler:
            try:
                result = auth_handler.login_user(email, password)
                if result['success']:
                    # Store user data in state
                    user_data = result['user_data']
                    state.username = user_data['name']
                    state.user_id = user_data['user_id']
                    state.email = user_data['email']
                    state.language = user_data.get('language') or 'English'
                    state.country = user_data.get('country') or ''
                    
                    # Check if this is first login (last_login was NULL before this login)
                    # If country or language is not set, it's first time
                    is_first_login = not user_data.get('country') or not user_data.get('language')
                    
                    if is_first_login:
                        # First time login - go to onboarding
                        state.onboarding_complete = False
                        from app.state import save_state
                        save_state(state)
                        
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"Welcome, {state.username}! Let's set up your preferences.", color=ft.colors.WHITE),
                            bgcolor=ACCENT,
                        )
                        page.snack_bar.open = True
                        page.update()
                        page.go("/onboarding")
                    else:
                        # Returning user - go directly to home
                        state.onboarding_complete = True
                        from app.state import save_state
                        save_state(state)
                        
                        page.snack_bar = ft.SnackBar(
                            content=ft.Text(f"Welcome back, {state.username}!", color=ft.colors.WHITE),
                            bgcolor=ACCENT,
                        )
                        page.snack_bar.open = True
                        page.update()
                        page.go("/home")
                    return
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(result['message'], color=ft.colors.WHITE),
                        bgcolor=ft.colors.RED_400,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
            except Exception as ex:
                print(f"Database login error: {ex}")
        
        # Fallback to file-based authentication
        loaded = load_state(email)
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
        email = username_field.value or ""
        password = password_field.value or ""
        name = name_field.value or ""
        
        if not email or not password or not name:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Please fill all fields", color=ft.colors.WHITE),
                bgcolor=ft.colors.RED_400,
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Try MySQL registration first
        if DB_AVAILABLE and auth_handler:
            try:
                result = auth_handler.register_user(
                    name=name,
                    email=email,
                    password=password,
                    country=None,  # Don't set country yet - will be set in onboarding
                    language=None  # Don't set language yet - will be set in onboarding
                )
                
                if result['success']:
                    # Store user data for onboarding
                    state.username = name
                    state.email = email
                    state.user_id = result['user_data']['user_id']
                    state.onboarding_complete = False
                    
                    from app.state import save_state
                    save_state(state)
                    
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("Account created! Let's set up your preferences.", color=ft.colors.WHITE),
                        bgcolor=ACCENT,
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # Go directly to onboarding for new users
                    page.go("/onboarding")
                    return
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(result['message'], color=ft.colors.WHITE),
                        bgcolor=ft.colors.RED_400,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
            except Exception as ex:
                print(f"Database registration error: {ex}")
        
        # Fallback to file-based registration
        state.username = name
        state.email = email
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
            name_field,  # Name field (only visible in signup)
            ft.Container(height=12),  # Space between name and email
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
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=["#F5F3FF", "#EFF6FF"] if state.theme_mode == "Light" else ["#1A0F2E", "#0D1B3E"],
                ),
            )
        ],
        bgcolor=state.bg_color(),
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
