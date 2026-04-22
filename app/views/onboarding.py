from __future__ import annotations

from collections import namedtuple

import flet as ft

from app.state import AppState
from app.components.controls import dot_indicator, primary_button
from app.components.theme import ACCENT, ACCENT_DARK

TutorialPage = namedtuple("TutorialPage", ["icon", "title", "description"])

TUTORIAL_PAGES = [
    TutorialPage(ft.icons.WAVING_HAND, "Welcome to ASEAN Gov Chat", "Ask questions about government services and documents in your language, simply and easily."),
    TutorialPage(ft.icons.QUESTION_ANSWER, "Ask About Government Documents", "Type your question and the app will find answers from official government sources for you."),
    TutorialPage(ft.icons.PUBLIC, "Choose Your Country", "Select your country so the app shows information relevant to your government and region."),
    TutorialPage(ft.icons.UPLOAD_FILE, "Upload or Link a Document", "Share a document or paste a website link to get a summary or ask questions about it."),
    TutorialPage(ft.icons.EXTENSION, "Use It in Your Browser Too", "Install the browser extension to summarise any government web page and chat about it directly in your browser."),
]


def build_onboarding_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /onboarding tutorial view — 5 pages navigated in-view."""

    current_page = [0]
    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    # --- mutable controls ---
    icon_ctrl = ft.Icon(
        TUTORIAL_PAGES[0].icon,
        size=80,
        color=accent,
    )

    title_ctrl = ft.Text(
        TUTORIAL_PAGES[0].title,
        size=state.font_sp() + 4,
        weight=ft.FontWeight.BOLD,
        color=state.text_color(),
        text_align=ft.TextAlign.CENTER,
    )

    desc_ctrl = ft.Text(
        TUTORIAL_PAGES[0].description,
        size=state.font_sp(),
        color=state.text_color(),
        text_align=ft.TextAlign.CENTER,
        width=320,
    )

    dots_row = dot_indicator(len(TUTORIAL_PAGES), 0, state)

    back_btn = ft.OutlinedButton(
        text="Back",
        visible=False,
        style=ft.ButtonStyle(color=accent),
        on_click=None,
    )

    next_btn = ft.OutlinedButton(
        text="Next",
        visible=True,
        style=ft.ButtonStyle(color=accent),
        on_click=None,
    )

    get_started_btn = primary_button(
        label="Get Started",
        on_click=lambda e: page.go("/preferences"),
        width=280,
        state=state,
    )
    get_started_btn.visible = False

    # nav_area is a Column; we rebuild its controls on each page change
    nav_area = ft.Column(
        controls=[
            ft.Row(
                controls=[next_btn],
                alignment=ft.MainAxisAlignment.CENTER,
                width=320,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )

    def _build_nav(idx: int):
        last = idx == len(TUTORIAL_PAGES) - 1
        first = idx == 0
        if first:
            # page 0: Next centered
            nav_area.controls = [
                ft.Row(
                    controls=[next_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    width=320,
                )
            ]
        elif last:
            # last page: Back centered, spacing, then Get Started centered below
            nav_area.controls = [
                ft.Row(
                    controls=[back_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    width=320,
                ),
                ft.Container(height=16),
                ft.Row(
                    controls=[get_started_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    width=320,
                ),
            ]
        else:
            # middle pages: Back and Next side by side
            nav_area.controls = [
                ft.Row(
                    controls=[back_btn, next_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    width=320,
                )
            ]

    def _refresh():
        idx = current_page[0]
        tp = TUTORIAL_PAGES[idx]

        icon_ctrl.name = tp.icon
        title_ctrl.value = tp.title
        desc_ctrl.value = tp.description

        new_dots = dot_indicator(len(TUTORIAL_PAGES), idx, state)
        dots_row.controls = new_dots.controls

        back_btn.visible = idx > 0
        next_btn.visible = idx < len(TUTORIAL_PAGES) - 1
        get_started_btn.visible = idx == len(TUTORIAL_PAGES) - 1

        _build_nav(idx)
        page.update()

    def handle_back(e):
        if current_page[0] > 0:
            current_page[0] -= 1
            _refresh()

    def handle_next(e):
        if current_page[0] < len(TUTORIAL_PAGES) - 1:
            current_page[0] += 1
            _refresh()

    back_btn.on_click = handle_back
    next_btn.on_click = handle_next

    content_column = ft.Column(
        controls=[
            icon_ctrl,
            ft.Container(height=16),
            title_ctrl,
            ft.Container(height=12),
            desc_ctrl,
            ft.Container(height=24),
            dots_row,
            ft.Container(height=32),
            nav_area,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
        tight=True,
    )

    return ft.View(
        route="/onboarding",
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
