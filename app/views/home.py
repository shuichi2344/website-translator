from __future__ import annotations

import flet as ft

from app.state import AppState
from app.components.theme import ACCENT, ACCENT_DARK


def build_home_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /home view — chat list + document/web mode selection."""

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    # --- Chat bubble factory ---
    def chat_bubble(message: str, is_user: bool = True) -> ft.Container:
        if is_user:
            bg = accent
            text_color = ft.colors.WHITE
            align = ft.alignment.center_right
            margin = ft.margin.only(left=60, right=10, bottom=10)
            border_radius = ft.border_radius.only(
                top_left=18, top_right=18, bottom_left=18, bottom_right=4
            )
        else:
            bg = state.surface_color()
            text_color = state.text_color()
            align = ft.alignment.center_left
            margin = ft.margin.only(left=10, right=60, bottom=10)
            border_radius = ft.border_radius.only(
                top_left=18, top_right=18, bottom_left=4, bottom_right=18
            )
        return ft.Container(
            content=ft.Text(message, color=text_color, size=state.font_sp()),
            alignment=align,
            padding=12,
            bgcolor=bg,
            border_radius=border_radius,
            margin=margin,
        )

    # --- Chat list ---
    chat_list = ft.ListView(expand=True, spacing=4, padding=20, auto_scroll=True)
    chat_list.controls.append(
        chat_bubble(
            "Hello! I'm your ASEAN Gov Chat assistant. Select a mode to get started.",
            is_user=False,
        )
    )

    # --- Mode card factory ---
    def create_option_card(
        title: str, desc: str, icon, mode: str
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, color=accent, size=28),
                            ft.Text(
                                title,
                                size=state.font_sp() + 4,
                                weight=ft.FontWeight.BOLD,
                                color=state.text_color(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.Text(desc, size=state.font_sp() - 2, color=state.text_color()),
                ],
                spacing=10,
            ),
            width=260,
            height=160,
            padding=20,
            border=ft.border.all(1, state.text_color()),
            border_radius=12,
            bgcolor=state.surface_color(),
            on_click=lambda _, m=mode: enter_focused_mode(m),
        )

    # --- Main card selection ---
    main_selection = ft.Column(
        [
            ft.Text(
                "How can I help you?",
                size=state.font_sp() + 6,
                weight=ft.FontWeight.BOLD,
                color=state.text_color(),
            ),
            ft.Text(
                "Choose a mode to get started",
                size=state.font_sp(),
                color=state.text_color(),
            ),
            ft.Container(height=16),
            ft.Row(
                [
                    create_option_card(
                        "Document",
                        "Upload a file and ask\nquestions about it.",
                        ft.icons.UPLOAD_FILE_OUTLINED,
                        "document",
                    ),
                    create_option_card(
                        "Web",
                        "Paste a URL and get\na summary or Q&A.",
                        ft.icons.LANGUAGE_OUTLINED,
                        "web",
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=16,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- Focused mode UI elements ---
    task_title = ft.Text(
        "", size=state.font_sp() + 4, weight=ft.FontWeight.BOLD, color=state.text_color()
    )

    file_upload_ui = ft.Container(
        content=ft.ElevatedButton(
            "Select File",
            icon=ft.icons.ATTACH_FILE,
            style=ft.ButtonStyle(
                bgcolor=accent,
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=52,
        ),
        visible=False,
        padding=ft.padding.symmetric(vertical=8),
    )

    web_link_ui = ft.TextField(
        label="Paste URL",
        border_color=accent,
        border_radius=8,
        border_width=3,
        visible=False,
        width=400,
        color=state.text_color(),
        bgcolor=state.surface_color(),
        label_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    user_question = ft.TextField(
        hint_text="Ask about this content...",
        border_radius=8,
        border_color=accent,
        border_width=3,
        bgcolor=state.surface_color(),
        color=state.text_color(),
        hint_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
        width=460,
    )

    summary_box = ft.Container(
        content=ft.Text(
            "Summary ready. You can ask follow-up questions below.",
            italic=True,
            color=state.text_color(),
            size=state.font_sp(),
        ),
        padding=16,
        bgcolor=state.surface_color(),
        border=ft.border.all(1, accent),
        border_radius=8,
        visible=False,
        width=460,
    )

    # --- Focused mode logic ---
    def enter_focused_mode(mode: str):
        main_selection.visible = False
        mic_button.visible = False
        focused_view.visible = True
        if mode == "document":
            task_title.value = "Document Mode"
            file_upload_ui.visible = True
            web_link_ui.visible = False
        else:
            task_title.value = "Web Mode"
            file_upload_ui.visible = False
            web_link_ui.visible = True
        page.update()

    def exit_focused_mode():
        main_selection.visible = True
        mic_button.visible = True
        focused_view.visible = False
        summary_box.visible = False
        page.update()

    def handle_submit(e):
        summary_box.visible = True
        page.update()

    focused_view = ft.Column(
        [
            task_title,
            file_upload_ui,
            web_link_ui,
            user_question,
            ft.Container(
                content=ft.ElevatedButton(
                    "Submit",
                    on_click=handle_submit,
                    style=ft.ButtonStyle(
                        bgcolor=accent,
                        color=ft.colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    width=200,
                    height=52,
                ),
                alignment=ft.alignment.center,
            ),
            summary_box,
            ft.TextButton(
                "← Back",
                on_click=lambda _: exit_focused_mode(),
                style=ft.ButtonStyle(color=state.text_color()),
            ),
        ],
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=16,
    )

    mic_button = ft.FloatingActionButton(
        icon=ft.icons.MIC_ROUNDED,
        bgcolor=accent,
        foreground_color=ft.colors.WHITE,
    )

    # --- AppBar ---
    appbar = ft.AppBar(
        title=ft.Text(
            "ASEAN Gov Chat",
            color=state.text_color(),
            size=state.font_sp() + 2,
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=state.bg_color(),
        center_title=True,
        actions=[
            ft.IconButton(
                icon=ft.icons.PERSON_OUTLINE,
                icon_color=state.text_color(),
                on_click=lambda _: page.go("/profile"),
                tooltip="Profile",
            )
        ],
    )

    # --- Bottom panel ---
    bottom_panel = ft.Container(
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=state.bg_color(),
        content=ft.Column(
            [
                main_selection,
                focused_view,
                ft.Container(height=8),
                ft.Row(
                    [mic_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        alignment=ft.alignment.center,
    )

    return ft.View(
        route="/home",
        controls=[
            appbar,
            ft.Container(content=chat_list, expand=True),
            bottom_panel,
        ],
        padding=0,
        bgcolor=state.bg_color(),
    )
