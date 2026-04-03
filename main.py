import flet as ft
import threading
import time

from app.state import AppState
from app.router import make_route_handler
from app.components.theme import apply_theme
from app.splash import create_splash_screen
from app.preloader import preload_modules


def main(page: ft.Page) -> None:
    page.title = "Bridge - ASEAN Gov Assistant"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Create splash screen
    splash, progress_bar, progress_text, status_text = create_splash_screen(page)
    page.add(splash)
    page.update()
    
    # Flag to track if loading is complete
    loading_complete = [False]
    
    # Preload modules in background
    def load_modules():
        def update_ui(progress: int, status: str):
            """Update splash screen UI"""
            try:
                progress_bar.value = progress / 100
                progress_text.value = f"{progress}%"
                status_text.value = status
                page.update()
            except Exception as e:
                print(f"UI update error: {e}")
        
        try:
            # Load all heavy modules
            preload_modules(progress_callback=update_ui)
            
            # Small delay to show "Ready!" message
            time.sleep(0.5)
            
            # Mark loading as complete
            loading_complete[0] = True
            
        except Exception as e:
            # Show error on splash screen
            try:
                status_text.value = f"Error: {e}"
                status_text.color = ft.colors.RED
                page.update()
            except:
                pass
            print(f"Startup error: {e}")
    
    # Start loading in background thread
    loading_thread = threading.Thread(target=load_modules, daemon=True)
    loading_thread.start()
    
    # Wait for loading to complete, then initialize app
    def check_loading_complete():
        if loading_complete[0]:
            # Remove splash screen
            page.clean()
            
            # Initialize state and router
            state = AppState()
            apply_theme(page, state)
            page.on_route_change = make_route_handler(state)
            page.on_resize = lambda _: page.update()
            
            # Navigate to login
            page.go("/login")
        else:
            # Check again in 100ms
            time.sleep(0.1)
            check_loading_complete()
    
    # Start checking in a separate thread
    threading.Thread(target=check_loading_complete, daemon=True).start()


ft.app(target=main)
