"""
Splash Screen - Shown during module preloading
"""

import flet as ft
from app.components.theme import ACCENT

def create_splash_screen(page: ft.Page) -> ft.Container:
    """Create a splash screen with loading indicator"""
    
    # Progress bar
    progress_bar = ft.ProgressBar(
        width=300,
        color=ACCENT,
        bgcolor=ft.colors.PURPLE_100,
        value=0,
    )
    
    # Status text
    status_text = ft.Text(
        "Initializing...",
        size=14,
        color=ft.colors.GREY_700,
        text_align=ft.TextAlign.CENTER,
    )
    
    # Progress percentage
    progress_text = ft.Text(
        "0%",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=ACCENT,
    )
    
    # App logo/icon
    logo = ft.Icon(
        ft.icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
        size=80,
        color=ACCENT,
    )
    
    # App title
    title = ft.Text(
        "Bridge",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.GREY_900,
    )
    
    subtitle = ft.Text(
        "ASEAN Government Assistant",
        size=14,
        color=ft.colors.GREY_600,
    )
    
    # Container for all elements
    splash = ft.Container(
        content=ft.Column(
            controls=[
                logo,
                ft.Container(height=20),
                title,
                subtitle,
                ft.Container(height=40),
                progress_bar,
                ft.Container(height=10),
                progress_text,
                ft.Container(height=5),
                status_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=["#F5F3FF", "#EFF6FF"],
        ),
    )
    
    return splash, progress_bar, progress_text, status_text
