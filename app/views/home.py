from __future__ import annotations

import os

import flet as ft

from app.state import AppState
from app.components.theme import ACCENT, ACCENT_DARK
from engine.speech.speech_to_text import create_session
from engine.speech.main import process_voice_result

def is_valid_url(s: str) -> bool:
    """Return True iff *s* starts with 'http://' or 'https://'."""
    return s.startswith("http://") or s.startswith("https://")


def is_valid_extension(ext: str) -> bool:
    """Return True iff *ext* (case-insensitive) is an accepted document/image format."""
    return ext.lower() in {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def build_home_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /home view — Progressive Disclosure dashboard."""

    if state.session is None:
        state.session, state.stream = create_session()

    session = state.session
    stream = state.stream

    # --- Ephemeral dashboard state (mutable via closures) ---
    active_mode: list = [None]    # None | "document" | "web"
    selected_file: list = [None]  # file path/name after picker
    url_valid: list = [False]     # True when URL passes validation
    is_recording: list = [False]  # True while STT is active

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT

    # ------------------------------------------------------------------ #
    #  Action card factory                                                 #
    # ------------------------------------------------------------------ #
    def action_card(
        title: str,
        icon,
        mode: str,
        on_click_fn,
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, color=accent, size=32),
                    ft.Text(
                        title,
                        size=state.font_sp(),
                        weight=ft.FontWeight.BOLD,
                        color=state.text_color(),
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
            ),
            expand=True,
            height=140,
            padding=20,
            border_radius=20,
            border=ft.border.all(2, accent),
            bgcolor=state.surface_color(),
            shadow=ft.BoxShadow(
                blur_radius=12,
                color=ft.colors.with_opacity(0.08, "#000000"),
            ),
            on_click=on_click_fn,
        )

    # ------------------------------------------------------------------ #
    #  Greeting                                                            #
    # ------------------------------------------------------------------ #
    greeting = ft.Text(
        "How can I help you today?",
        size=state.font_sp() + 8,
        weight=ft.FontWeight.BOLD,
        color=state.text_color(),
    )

    # ------------------------------------------------------------------ #
    #  Card instances (created before set_mode is defined; on_click uses  #
    #  a lambda that calls set_mode which is defined later — that's fine  #
    #  because the lambda is only *called* after the function exists)     #
    # ------------------------------------------------------------------ #
    doc_card = action_card(
        "Analyze Document / Image",
        ft.icons.UPLOAD_FILE_OUTLINED,
        "document",
        lambda _: set_mode("document"),
    )
    web_card = action_card(
        "Extract from Web Link",
        ft.icons.LANGUAGE_OUTLINED,
        "web",
        lambda _: set_mode("web"),
    )

    # ------------------------------------------------------------------ #
    #  Document Panel (Task 3.1)                                          #
    # ------------------------------------------------------------------ #

    # File-name display + clear button
    file_name_text = ft.Text(
        "",
        size=state.font_sp(),
        color=state.text_color(),
        visible=False,
    )

    def on_clear_file(_):
        selected_file[0] = None
        file_name_text.value = ""
        file_name_text.visible = False
        clear_file_btn.visible = False
        file_error_text.visible = False
        page.update()

    clear_file_btn = ft.IconButton(
        icon=ft.icons.CLOSE,
        icon_color=accent,
        tooltip="Remove file",
        visible=False,
        on_click=on_clear_file,
    )

    file_error_text = ft.Text(
        "Unsupported format. Accepted: .pdf, .docx, .png, .jpg, .jpeg",
        size=state.font_sp() - 2,
        color=ft.colors.RED_400,
        visible=False,
    )

    # FilePicker (wired into page.overlay at the end of this function)
    file_picker = ft.FilePicker(on_result=None)  # handler set below

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            ext = os.path.splitext(f.name)[1]
            if is_valid_extension(ext):
                selected_file[0] = f.name
                file_name_text.value = f.name
                file_name_text.visible = True
                clear_file_btn.visible = True
                file_error_text.visible = False
            else:
                selected_file[0] = None
                file_name_text.visible = False
                clear_file_btn.visible = False
                file_error_text.visible = True
        page.update()

    file_picker.on_result = on_file_picked

    # Dashed drop-zone container
    drop_zone = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.icons.UPLOAD_FILE_OUTLINED, color=accent, size=40),
                ft.Text(
                    "Drop a file here, or tap to browse",
                    size=state.font_sp(),
                    color=state.text_color(),
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        border=ft.border.all(2, accent),
        border_radius=12,
        bgcolor=state.surface_color(),
        padding=24,
        height=120,
        expand=True,  # fill full width of parent row
        on_click=lambda _: file_picker.pick_files(
            allowed_extensions=["pdf", "docx", "png", "jpg", "jpeg"]
        ),
    )

    document_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row([drop_zone]),  # Row forces drop_zone to fill width
                ft.Row(
                    [file_name_text, clear_file_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
                file_error_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=0, vertical=8),
    )

    # ------------------------------------------------------------------ #
    #  Web Panel (Task 3.2)                                               #
    # ------------------------------------------------------------------ #

    url_error_text = ft.Text(
        "URL must start with http:// or https://",
        size=state.font_sp() - 2,
        color=ft.colors.RED_400,
        visible=False,
    )

    progress_ring = ft.ProgressRing(visible=False, width=24, height=24)

    def on_url_change(e):
        val = url_field.value or ""
        valid = is_valid_url(val) if val else False
        url_valid[0] = valid
        url_error_text.visible = bool(val) and not valid
        page.update()

    url_field = ft.TextField(
        hint_text="Paste a government website URL",
        border_color=accent,
        border_radius=8,
        border_width=2,
        bgcolor=state.surface_color(),
        color=state.text_color(),
        hint_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
        on_change=on_url_change,
    )

    web_panel = ft.Container(
        content=ft.Column(
            [
                url_field,
                url_error_text,
                progress_ring,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    # ------------------------------------------------------------------ #
    #  Context Input Area + Back button (Task 3.3)                        #
    # ------------------------------------------------------------------ #

    # Light grey panel background (visible when a mode is active)
    PANEL_BG = "#F0F0F0" if state.theme_mode == "Light" else "#2A2A2A"

    # Slide-up panel — always in the tree, offset drives show/hide
    panel_container = ft.Container(
        content=ft.Column(
            [document_panel, web_panel],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor=PANEL_BG,
        border_radius=ft.border_radius.only(top_left=20, top_right=20),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        offset=ft.transform.Offset(0, 1),  # start hidden below
        animate_offset=ft.animation.Animation(250, ft.AnimationCurve.EASE_OUT),
        visible=False,
    )

    # ------------------------------------------------------------------ #
    #  set_mode (Task 3.3)                                                #
    # ------------------------------------------------------------------ #

    def set_mode(mode):
        # Toggle: tapping the already-active card collapses the panel
        if mode is not None and active_mode[0] == mode:
            mode = None
        active_mode[0] = mode
        document_panel.visible = mode == "document"
        web_panel.visible = mode == "web"
        # Slide up when showing, slide down when hiding
        if mode is not None:
            panel_container.visible = True
            panel_container.offset = ft.transform.Offset(0, 0)
        else:
            panel_container.offset = ft.transform.Offset(0, 1)
            # hide after animation completes (250ms)
            import threading
            def _hide():
                import time; time.sleep(0.26)
                panel_container.visible = False
                page.update()
            threading.Thread(target=_hide, daemon=True).start()
        # Update card active styling
        doc_card.bgcolor = (
            ft.colors.with_opacity(0.12, accent) if mode == "document" else state.surface_color()
        )
        web_card.bgcolor = (
            ft.colors.with_opacity(0.12, accent) if mode == "web" else state.surface_color()
        )
        page.update()

    # ------------------------------------------------------------------ #
    #  Chat bubble list                                                    #
    # ------------------------------------------------------------------ #

    BUBBLE_USER_BG   = accent
    BUBBLE_BOT_BG    = state.surface_color()
    BUBBLE_USER_FG   = ft.colors.WHITE if state.theme_mode == "Light" else "#121212"
    BUBBLE_BOT_FG    = state.text_color()
    BUBBLE_STATUS_FG = ft.colors.with_opacity(0.6, state.text_color())

    chat_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        auto_scroll=True,
    )

    def _add_bubble(text: str, role: str = "bot") -> None:
        """
        role: "user" | "bot" | "status"
        status = small centred pill for pipeline progress steps.
        """
        if role == "user":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_USER_FG, size=state.font_sp(), selectable=True),
                bgcolor=BUBBLE_USER_BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                max_width=300,
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.END, expand=True)

        elif role == "status":
            content = ft.Container(
                content=ft.Text(
                    text,
                    color=BUBBLE_STATUS_FG,
                    size=state.font_sp() - 2,
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                ),
                bgcolor=ft.colors.with_opacity(0.06, accent),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.CENTER, expand=True)

        else:  # bot
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_BOT_FG, size=state.font_sp(), selectable=True),
                bgcolor=BUBBLE_BOT_BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                max_width=300,
                border=ft.border.all(1, ft.colors.with_opacity(0.12, accent)),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.START, expand=True)

        chat_list.controls.append(bubble)

    # ------------------------------------------------------------------ #
    #  Chat Bar (Task 5.1)                                                #
    # ------------------------------------------------------------------ #

    # --- Chat history ---
    chat_history: list = []  # list of message strings

    # --- Chat field ---
    chat_field = ft.TextField(
        hint_text="Ask a question...",
        expand=True,
        min_lines=1,
        max_lines=4,
        border_color=ft.colors.TRANSPARENT,
        bgcolor=ft.colors.TRANSPARENT,
        color=state.text_color(),
        hint_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
        content_padding=ft.padding.symmetric(horizontal=8, vertical=14),
    )

    def on_chat_submit(e):
        msg = (chat_field.value or "").strip()
        if not msg:
            return
        _add_bubble(msg, "user")
        chat_field.value = ""
        mic_icon.name = ft.icons.MIC_ROUNDED
        page.update()

    chat_field.on_submit = on_chat_submit

    def on_chat_change(e):
        has_text = bool((chat_field.value or "").strip())
        mic_icon.name = ft.icons.SEND_ROUNDED if has_text else ft.icons.MIC_ROUNDED
        page.update()

    chat_field.on_change = on_chat_change

    def on_mic_or_send(_):
        if (chat_field.value or "").strip():
            on_chat_submit(None)

    # --- Pulse ring that animates while recording ---
    pulse_ring = ft.Container(
        width=48,
        height=48,
        border_radius=24,
        bgcolor=ft.colors.with_opacity(0.0, ft.colors.RED_400),
        animate=ft.animation.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
    )

    mic_icon = ft.Icon(
        ft.icons.MIC_ROUNDED,
        color=ft.colors.WHITE if state.theme_mode == "Light" else "#121212",
        size=24,
    )

    mic_circle = ft.Container(
        content=mic_icon,
        width=48,
        height=48,
        border_radius=24,
        bgcolor=accent,
        alignment=ft.alignment.center,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    def _start_recording(_):
        if (chat_field.value or "").strip():
            return

        is_recording[0] = True

        # UI updates (keep yours)
        chat_field.hint_text = "Recording..."
        mic_circle.bgcolor = ft.colors.RED_400
        page.update()

        _pulse(expand=False)

        # ✅ START AUDIO STREAM
        stream.start()
        session.start_recording()

    def _pulse(expand: bool):
        if not is_recording[0]:
            return
        if expand:
            pulse_ring.width = 68
            pulse_ring.height = 68
            pulse_ring.bgcolor = ft.colors.with_opacity(0.3, ft.colors.RED_400)
        else:
            pulse_ring.width = 80
            pulse_ring.height = 80
            pulse_ring.bgcolor = ft.colors.with_opacity(0.0, ft.colors.RED_400)
        page.update()
        import threading
        threading.Timer(0.6, _pulse, kwargs={"expand": not expand}).start()

    def _stop_recording(_):
        was_recording = is_recording[0]
        is_recording[0] = False

        # Reset UI
        chat_field.hint_text = "Ask a question..."
        mic_circle.bgcolor = accent
        page.update()

        if (chat_field.value or "").strip():
            on_chat_submit(None)

        elif was_recording:
            stream.stop()

            # 🚨 Run heavy processing in background thread
            def process():
                session.stop_recording()
                results = session.results

                dialect = results.get("dialect")
                question = results.get("question")
                query = results.get("query")

                # ✅ CALL YOUR MAIN LOGIC HERE
                response = process_voice_result(dialect, question, query)

                # 👉 Update UI safely
                def update_ui():
                    # You can push into chat UI instead
                    chat_field.value = question or ""
                    
                    print("Dialect:", dialect)
                    print("Question:", question)
                    print("Query:", query)
                    print("Response:", response)

                    page.update()

                # Flet API compatibility: `call_from_thread` doesn't exist in all versions.
                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_ui)
                else:
                    update_ui()

            # `page.run_thread()` is not available in all Flet versions.
            # Use a plain daemon thread and marshal UI updates via `call_from_thread`.
            import threading
            threading.Thread(target=process, daemon=True).start()

    mic_btn = ft.GestureDetector(
        content=ft.Stack(
            [
                ft.Container(  # centre the pulse ring
                    content=pulse_ring,
                    alignment=ft.alignment.center,
                    width=48,
                    height=48,
                ),
                mic_circle,
            ],
            width=48,
            height=48,
        ),
        on_tap_down=_start_recording,
        on_tap_up=_stop_recording,
    )

    chat_bar = ft.Container(
        content=chat_field,
        expand=True,
        border_radius=20,
        bgcolor=state.surface_color(),
        border=ft.border.all(2, accent),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        margin=ft.margin.only(left=16, bottom=8, top=8),
    )

    mic_container = ft.Container(
        content=mic_btn,
        margin=ft.margin.only(left=5, right=16, bottom=8, top=8),
    )

    # ------------------------------------------------------------------ #
    #  PTT Session + full pipeline                                        #
    # ------------------------------------------------------------------ #

    def _ui(fn):
        fn()  # Flet 0.19.0 — page.update() is thread-safe

    def _add_bubble_safe(text: str, role: str = "bot"):
        def _do():
            _add_bubble(text, role)
            page.update()
        _ui(_do)

    def _on_stt_status(msg: str):
        _add_bubble_safe(msg, "status")

    def _on_stt_error(exc: Exception):
        def _do():
            is_recording[0] = False
            chat_field.hint_text = "Ask a question..."
            _add_bubble(f"⚠️ {exc}", "status")
            page.update()
        _ui(_do)

    def _on_stt_result(results: dict):
        question = results.get("question") or results.get("raw") or ""

        def _do():
            # Keep is_recording[0] True and mic visuals in recording state
            # while the pipeline runs; pipeline callbacks will reset them.
            _add_bubble(question, "user")
            page.update()
        _ui(_do)

        # Always run the full pipeline after STT
        _run_main_pipeline(results)

    def _reset_mic_visuals():
        """Restore mic button to default (accent) state."""
        def _do():
            is_recording[0] = False
            chat_field.hint_text = "Ask a question..."
            mic_circle.bgcolor = accent
            mic_circle.width = 48
            mic_circle.height = 48
            mic_circle.border_radius = 24
            pulse_ring.bgcolor = ft.colors.with_opacity(0.0, ft.colors.RED_400)
            pulse_ring.width = 48
            pulse_ring.height = 48
            pulse_ring.border_radius = 24
            page.update()
        _ui(_do)

    def _run_main_pipeline(stt_result: dict):
        import threading as _threading
        from engine.speech.main import run_pipeline_with_stt_result  # noqa: PLC0415

        def on_status(msg: str):
            _add_bubble_safe(msg, "status")

        def on_result(answer: str, links: list, dialect: str, question: str):
            _reset_mic_visuals()
            _add_bubble_safe(answer, "bot")

        def on_error(exc: Exception):
            _reset_mic_visuals()
            _add_bubble_safe(f"⚠️ {exc}", "status")

        _threading.Thread(
            target=run_pipeline_with_stt_result,
            args=(stt_result, on_status, on_result, on_error, "my"),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------ #
    #  AppBar                                                              #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Wire FilePicker into page.overlay                                  #
    # ------------------------------------------------------------------ #

    page.overlay.append(file_picker)
    page.update()

    # ------------------------------------------------------------------ #
    #  Assemble final view                                                 #
    # ------------------------------------------------------------------ #

    return ft.View(
        route="/home",
        appbar=appbar,
        controls=[
            ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                greeting,
                                ft.Container(height=16),
                                ft.Row(
                                    [doc_card, web_card],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=16,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(horizontal=24, vertical=24),
                    ),
                    chat_list,          # expands to fill remaining space
                    panel_container,
                    ft.Row(
                        [chat_bar, mic_container],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        ],
        padding=0,
        bgcolor=state.bg_color(),
    )
