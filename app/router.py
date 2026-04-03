from __future__ import annotations

import flet as ft

from app.state import AppState


def make_route_handler(state: AppState):
    """Return a route_change handler bound to the given AppState."""

    def route_change(e: ft.RouteChangeEvent) -> None:
        page: ft.Page = e.page
        route = page.route

        # Show loading indicator for heavy routes
        if route == "/home":
            # Clear views and show loading screen
            page.views.clear()
            loading_view = ft.View(
                route="/loading",
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.ProgressRing(color=ft.colors.PURPLE),
                                ft.Container(height=20),
                                ft.Text("Loading...", size=16, color=ft.colors.PURPLE),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                ],
                bgcolor=state.bg_color(),
            )
            page.views.append(loading_view)
            page.update()

        # Clear views for actual route
        page.views.clear()

        if route == "/login":
            from app.views.login import build_login_view
            view = build_login_view(page, state)
        elif route == "/onboarding":
            from app.views.onboarding import build_onboarding_view
            view = build_onboarding_view(page, state)
        elif route == "/preferences":
            from app.views.preferences import build_preferences_view
            view = build_preferences_view(page, state)
        elif route == "/home":
            from app.views.home import build_home_view
            view = build_home_view(page, state)
        elif route == "/profile":
            from app.views.profile import build_profile_view
            view = build_profile_view(page, state)
        else:
            page.go("/login")
            return

        page.views.append(view)
        page.update()

    return route_change
