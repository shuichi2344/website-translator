import flet as ft

from app.state import AppState
from app.router import make_route_handler
from app.components.theme import apply_theme


def main(page: ft.Page) -> None:
    page.title = "ASEAN Gov Chat"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    state = AppState()
    apply_theme(page, state)

    page.on_route_change = make_route_handler(state)
    page.on_resize = lambda _: page.update()
    page.go("/login")


ft.app(target=main)
