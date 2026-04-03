from __future__ import annotations

import os
import threading

import flet as ft

from app.state import AppState
from app.components.theme import ACCENT, ACCENT_DARK, accent_gradient, GRAD_START, GRAD_END, GRAD_START_DARK, GRAD_END_DARK
from app.preloader import get_modules

# Import RAG integration for message storage (singleton pattern)
_rag_instance = None
RAG_AVAILABLE = False

def get_rag_instance():
    """Get or create RAG instance (singleton)"""
    global _rag_instance, RAG_AVAILABLE
    if _rag_instance is None:
        try:
            from engine.database.rag_integration import RAGIntegration
            _rag_instance = RAGIntegration()
            RAG_AVAILABLE = True
            print("✅ RAG integration initialized")
        except Exception as e:
            print(f"⚠️ RAG integration not available: {e}")
            _rag_instance = None
            RAG_AVAILABLE = False
    return _rag_instance

def _get_preloaded_modules():
    """Get preloaded modules from cache"""
    modules = get_modules()
    return (
        modules.get('create_session'),
        modules.get('process_voice_result'),
        modules.get('speak_answer'),
        modules.get('DocumentSummarizer'),
        modules.get('transcribe_audio')
    )

def is_valid_url(s: str) -> bool:
    """Return True iff *s* starts with 'http://' or 'https://'."""
    return s.startswith("http://") or s.startswith("https://")


def is_valid_extension(ext: str) -> bool:
    """Return True iff *ext* (case-insensitive) is an accepted document/image format."""
    return ext.lower() in {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def build_home_view(page: ft.Page, state: AppState) -> ft.View:
    """Build the /home view — Progressive Disclosure dashboard."""

    # Initialize session from preloaded modules
    if state.session is None:
        create_session, _, _, _, _ = _get_preloaded_modules()
        if create_session:
            state.session, state.stream = create_session()
    
    # Initialize or get conversation
    from datetime import datetime
    rag = get_rag_instance()
    if RAG_AVAILABLE and rag and state.user_id:
        if not state.conversation_id:
            # Create new conversation for this session
            state.conversation_id = rag.create_conversation(
                user_id=state.user_id,
                title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            print(f"✅ Created conversation: {state.conversation_id}")
        else:
            print(f"✅ Using existing conversation: {state.conversation_id}")

    session = state.session
    stream = state.stream

    # --- Ephemeral dashboard state (mutable via closures) ---
    active_mode: list = [None]    # None | "document" | "web"
    selected_file: list = [None]  # file path after picker
    selected_file_name: list = [None]  # display name
    url_valid: list = [False]     # True when URL passes validation
    is_recording: list = [False]  # True while STT is active
    is_processing: list = [False] # True while voice result is being processed
    _search_audio_chunks: list = []   # raw audio frames captured in search mode
    _search_sd_stream: list = [None]  # sounddevice InputStream handle

    LANG_CODE_MAP = {
        "English": "en", "Malay": "ms", "Indonesian": "id", "Thai": "th",
        "Vietnamese": "vi", "Filipino": "tl", "Burmese": "my", "Khmer": "km",
        "Lao": "lo", "Tamil": "ta", "Chinese (Simplified)": "zh-cn",
    }

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT
    _dark = state.theme_mode == "Dark"
    _grad = accent_gradient(_dark)
    _grad_colors = [GRAD_START_DARK, GRAD_END_DARK] if _dark else [GRAD_START, GRAD_END]

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

    # Track whether the cards header is visible
    _cards_visible: list = [True]

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
    #  Shared ASEAN language selector (used in both panels)              #
    # ------------------------------------------------------------------ #

    ASEAN_LANGUAGES = [
        "English", "Malay", "Indonesian", "Thai", "Vietnamese",
        "Filipino", "Burmese", "Khmer", "Lao", "Tamil", "Chinese (Simplified)",
    ]

    doc_lang_dropdown = ft.Dropdown(
        label="Target Language",
        hint_text="Select output language",
        options=[ft.dropdown.Option(lang) for lang in ASEAN_LANGUAGES],
        value="English",
        border_color=accent,
        border_radius=8,
        border_width=2,
        bgcolor=state.surface_color(),
        color=state.text_color(),
        label_style=ft.TextStyle(color=accent, size=state.font_sp() - 1),
        text_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    web_lang_dropdown = ft.Dropdown(
        label="Target Language",
        hint_text="Select output language",
        options=[ft.dropdown.Option(lang) for lang in ASEAN_LANGUAGES],
        value="English",
        border_color=accent,
        border_radius=8,
        border_width=2,
        bgcolor=state.surface_color(),
        color=state.text_color(),
        label_style=ft.TextStyle(color=accent, size=state.font_sp() - 1),
        text_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
    )

    # ------------------------------------------------------------------ #
    #  Notes helper — info icon with tooltip on hover                    #
    # ------------------------------------------------------------------ #

    def _info_tooltip(items: list[str]) -> ft.Tooltip:
        NOTE_COLOR = ft.colors.with_opacity(0.85, state.text_color())
        lines = "\n".join(f"• {item}" for item in items)
        return ft.Tooltip(
            message=lines,
            content=ft.Icon(
                ft.icons.INFO_OUTLINE_ROUNDED,
                color=accent,
                size=18,
            ),
            bgcolor=state.surface_color(),
            text_style=ft.TextStyle(color=NOTE_COLOR, size=state.font_sp() - 2),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            wait_duration=0,
        )

    _DOC_NOTES = [
        "Maximum file size: 50MB",
        "Docling + Google Gemini 2.0 Flash — Advanced AI summarization",
        "RAG Q&A: Ask specific questions about documents or websites",
        "Automatic language detection and complex table recognition",
        "Supports PDF and images (PNG, JPG, JPEG, BMP, TIFF)",
        "Website summarization extracts main content and crawls 3 sublinks",
        "Embeddings cached in ChromaDB for fast repeated queries",
    ]

    _WEB_NOTES = [
        "Maximum file size: 50MB",
        "Docling + Google Gemini 2.0 Flash — Advanced AI summarization",
        "RAG Q&A: Ask specific questions about documents or websites",
        "Automatic language detection and complex table recognition",
        "Supports PDF and images (PNG, JPG, JPEG, BMP, TIFF)",
        "Website summarization extracts main content and crawls 3 sublinks",
        "Embeddings cached in ChromaDB for fast repeated queries",
    ]

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
        selected_file_name[0] = None
        file_name_text.value = ""
        file_name_text.visible = False
        clear_file_btn.visible = False
        file_error_text.visible = False
        _drop_zone_idle.visible = True
        _drop_zone_selected.visible = False
        drop_zone.border = ft.border.all(2, accent)
        _refresh_summarise_btn()
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
                selected_file[0] = f.path
                selected_file_name[0] = f.name
                file_name_text.value = f.name
                file_name_text.visible = True
                clear_file_btn.visible = True
                file_error_text.visible = False
                # Show file name inside the drop zone
                _drop_zone_selected.controls[1].value = f.name
                _drop_zone_idle.visible = False
                _drop_zone_selected.visible = True
                drop_zone.border = ft.border.all(2, ft.colors.GREEN_400)
            else:
                selected_file[0] = None
                selected_file_name[0] = None
                file_name_text.visible = False
                clear_file_btn.visible = False
                file_error_text.visible = True
                _drop_zone_idle.visible = True
                _drop_zone_selected.visible = False
                drop_zone.border = ft.border.all(2, ft.colors.RED_400)
        _refresh_summarise_btn()
    file_picker.on_result = on_file_picked

    # Dashed drop-zone container
    # Drop-zone inner content — swapped when file is selected
    _drop_zone_idle = ft.Column(
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
    )

    _drop_zone_selected = ft.Column(
        [
            ft.Icon(ft.icons.INSERT_DRIVE_FILE_OUTLINED, color=accent, size=36),
            ft.Text(
                "",  # filled in on_file_picked
                size=state.font_sp(),
                color=state.text_color(),
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_500,
            ),
            ft.Text(
                "Tap to change file",
                size=state.font_sp() - 2,
                color=ft.colors.with_opacity(0.55, state.text_color()),
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4,
        visible=False,
    )

    drop_zone = ft.Container(
        content=ft.Stack(
            [
                ft.Container(content=_drop_zone_idle, alignment=ft.alignment.center, expand=True),
                ft.Container(content=_drop_zone_selected, alignment=ft.alignment.center, expand=True),
            ],
            expand=True,
        ),
        border=ft.border.all(2, accent),
        border_radius=12,
        bgcolor=state.surface_color(),
        padding=24,
        height=120,
        expand=True,
        on_click=lambda _: file_picker.pick_files(
            allowed_extensions=["pdf", "docx", "png", "jpg", "jpeg"]
        ),
    )

    document_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Container(expand=True), _info_tooltip(_DOC_NOTES)],
                    alignment=ft.MainAxisAlignment.END,
                ),
                ft.Row([drop_zone]),
                file_error_text,
                doc_lang_dropdown,
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
        _refresh_summarise_btn()

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
                ft.Row(
                    [ft.Container(expand=True), _info_tooltip(_WEB_NOTES)],
                    alignment=ft.MainAxisAlignment.END,
                ),
                url_field,
                url_error_text,
                web_lang_dropdown,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    # ------------------------------------------------------------------ #
    #  Action buttons (per mode)                                          #
    # ------------------------------------------------------------------ #

    def _action_btn(text, icon, on_click_fn) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text=text,
            icon=icon,
            on_click=on_click_fn,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=accent,
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(vertical=12, horizontal=20),
            ),
            height=48,
            expand=True,
        )

    def _run_in_thread(fn):
        threading.Thread(target=fn, daemon=True).start()

    def _ui_call(fn):
        if hasattr(page, "call_from_thread"):
            page.call_from_thread(fn)
        else:
            fn()

    def _set_buttons_loading(loading: bool):
        for btn in (doc_summarise_btn, doc_ask_btn, web_summarise_btn, web_ask_btn):
            btn.disabled = loading
        _panel_inner.opacity = 0.3 if loading else 1.0
        _loading_overlay.visible = loading
        page.update()

    def on_doc_summarise(_):
        filepath = selected_file[0]
        lang_code = LANG_CODE_MAP.get(doc_lang_dropdown.value or "English", "en")
        _add_bubble(f"Summarising document: {selected_file_name[0]}", "user")
        # Add thinking indicator
        thinking_bubble = _add_bubble("Thinking…", "status")
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                result = summarizer.process_document(filepath)
                if result:
                    summary = result.get("summary", "")
                    orig = result.get("word_count", 0)
                    summ = result.get("summary_word_count", 0)
                    reduction = round(100 - (summ / orig * 100)) if orig else 0
                    _ui_call(lambda: set_mode(None))
                    # Remove thinking bubble before adding result
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe(f"📄 Document Summary  •  {orig:,}→{summ:,} words ({reduction}% reduction)\n\n{summary}", "result")
                else:
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe("⚠️ Failed to process document.", "status")
            except Exception as exc:
                def _remove_thinking():
                    if thinking_bubble in chat_list.controls:
                        chat_list.controls.remove(thinking_bubble)
                _ui_call(_remove_thinking)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    def on_doc_ask(_):
        question = (chat_field.value or "").strip()
        filepath = selected_file[0]
        lang_code = LANG_CODE_MAP.get(doc_lang_dropdown.value or "English", "en")

        if not question:
            chat_field.hint_text = "Type your question then tap Ask a Question..."
            page.update()
            return

        _add_bubble(question, "user")
        # Add thinking indicator
        thinking_bubble = _add_bubble("Thinking…", "status")
        chat_field.value = ""
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                result = summarizer.rag_qa_document(filepath, question)
                if result:
                    _ui_call(lambda: set_mode(None))
                    # Remove thinking bubble before adding result
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe(result.get("summary", ""), "result")
                else:
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe("⚠️ Could not answer that question.", "status")
            except Exception as exc:
                def _remove_thinking():
                    if thinking_bubble in chat_list.controls:
                        chat_list.controls.remove(thinking_bubble)
                _ui_call(_remove_thinking)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    def on_web_summarise(_):
        url = url_field.value or ""
        lang_code = LANG_CODE_MAP.get(web_lang_dropdown.value or "English", "en")
        _add_bubble(f"Summarising: {url}", "user")
        # Add thinking indicator
        thinking_bubble = _add_bubble("Thinking…", "status")
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                result = summarizer.process_website(url, crawl_depth=1, max_sublinks=3)
                if result:
                    summary = result.get("summary", "")
                    orig = result.get("word_count", 0)
                    summ = result.get("summary_word_count", 0)
                    reduction = round(100 - (summ / orig * 100)) if orig else 0
                    _ui_call(lambda: set_mode(None))
                    # Remove thinking bubble before adding result
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe(f"🌐 Website Summary  •  {orig:,}→{summ:,} words ({reduction}% reduction)\n\n{summary}", "result")
                else:
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe("⚠️ Failed to process website.", "status")
            except Exception as exc:
                def _remove_thinking():
                    if thinking_bubble in chat_list.controls:
                        chat_list.controls.remove(thinking_bubble)
                _ui_call(_remove_thinking)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    def on_web_ask(_):
        question = (chat_field.value or "").strip()
        url = url_field.value or ""
        lang_code = LANG_CODE_MAP.get(web_lang_dropdown.value or "English", "en")

        if not question:
            chat_field.hint_text = "Type your question then tap Ask a Question..."
            page.update()
            return

        _add_bubble(question, "user")
        # Add thinking indicator
        thinking_bubble = _add_bubble("Thinking…", "status")
        chat_field.value = ""
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                result = summarizer.rag_qa_website(url, question)
                if result:
                    _ui_call(lambda: set_mode(None))
                    # Remove thinking bubble before adding result
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe(result.get("summary", ""), "result")
                else:
                    def _remove_thinking():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                    _ui_call(_remove_thinking)
                    _add_bubble_safe("⚠️ Could not answer that question.", "status")
            except Exception as exc:
                def _remove_thinking():
                    if thinking_bubble in chat_list.controls:
                        chat_list.controls.remove(thinking_bubble)
                _ui_call(_remove_thinking)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    doc_summarise_btn  = _action_btn("Summarize Document", ft.icons.AUTO_AWESOME_OUTLINED, on_doc_summarise)
    doc_ask_btn        = _action_btn("Ask a Question",     ft.icons.CHAT_OUTLINED,          on_doc_ask)
    web_summarise_btn  = _action_btn("Summarize Website",  ft.icons.AUTO_AWESOME_OUTLINED,  on_web_summarise)
    web_ask_btn        = _action_btn("Ask a Question",     ft.icons.CHAT_OUTLINED,          on_web_ask)

    def _refresh_summarise_btn():
        has_input = (active_mode[0] == "document" and selected_file[0] is not None) or \
                    (active_mode[0] == "web" and url_valid[0])
        # Summarize buttons only enabled when there's valid input
        doc_summarise_btn.disabled = not has_input
        web_summarise_btn.disabled = not has_input
        page.update()

    # ------------------------------------------------------------------ #
    #  Context Input Area + Back button (Task 3.3)                        #
    # ------------------------------------------------------------------ #

    # Light grey panel background (visible when a mode is active)
    PANEL_BG = "#EDE9FE" if state.theme_mode == "Light" else "#1C1730"

    # Inner column — the actual panel content
    _panel_inner = ft.Column(
        [
            document_panel,
            web_panel,
            ft.Container(
                content=ft.Row(
                    [doc_summarise_btn, doc_ask_btn, web_summarise_btn, web_ask_btn],
                    spacing=8,
                ),
                padding=ft.padding.only(top=4, bottom=8),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    # Loading overlay — 50% black scrim + centered spinner
    _loading_overlay = ft.Container(
        content=ft.ProgressRing(color=accent, width=40, height=40, stroke_width=4),
        alignment=ft.alignment.center,
        bgcolor=ft.colors.with_opacity(0.3, "#000000"),
        border_radius=ft.border_radius.only(top_left=20, top_right=20),
        visible=False,
        left=0,
        right=0,
        top=0,
        bottom=0,
    )

    # Stack: content behind, overlay on top
    panel_container = ft.Container(
        content=ft.Stack(
            [_panel_inner, _loading_overlay],
            expand=True,
        ),
        bgcolor=PANEL_BG,
        border_radius=ft.border_radius.only(top_left=20, top_right=20),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        animate=ft.animation.Animation(250, ft.AnimationCurve.EASE_OUT),
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        visible=False,
    )

    _PANEL_OPEN_HEIGHT = 320  # max height when panel is open

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
        if mode is None:
            doc_summarise_btn.visible = False
            doc_ask_btn.visible       = False
            web_summarise_btn.visible = False
            web_ask_btn.visible       = False
        else:
            doc_summarise_btn.visible = mode == "document"
            doc_ask_btn.visible       = mode == "document"
            web_summarise_btn.visible = mode == "web"
            web_ask_btn.visible       = mode == "web"
            # Summarize disabled until valid input provided
            doc_summarise_btn.disabled = selected_file[0] is None
            web_summarise_btn.disabled = not url_valid[0]
        # Show/hide panel using height animation (no offset — avoids overlay issues)
        if mode is not None:
            panel_container.visible = True
            panel_container.height = _PANEL_OPEN_HEIGHT
        else:
            panel_container.height = 0
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
    BUBBLE_USER_FG   = ft.colors.WHITE
    BUBBLE_BOT_FG    = state.text_color()
    BUBBLE_STATUS_FG = ft.colors.with_opacity(0.6, state.text_color())

    chat_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        auto_scroll=True,
    )

    def _add_bubble(text: str, role: str = "bot", sources: list = None):
        """
        role: "user" | "bot" | "status" | "result"
        result = right-aligned bot response (summarizer/Q&A output)
        status = small centred pill for pipeline progress steps.
        sources = list of source URLs to display as references
        Returns the bubble element so it can be removed later.
        """
        if role == "user":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_USER_FG, size=state.font_sp(), selectable=True),
                gradient=_grad,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.END, expand=True)

        elif role == "result":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_USER_FG, size=state.font_sp(), selectable=True),
                gradient=_grad,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                expand=True,
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
            # Track TTS state for this bubble
            is_playing = [False]
            is_loading = [False]
            is_paused = [False]
            audio_file = [None]  # Store temp audio file path
            
            # Speaker button
            def on_speaker_click(e):
                # If paused, resume
                if is_paused[0]:
                    try:
                        import pygame
                        pygame.mixer.music.unpause()
                        is_paused[0] = False
                        is_playing[0] = True
                        speaker_btn.text = "⏸️ Pause"
                        speaker_btn.disabled = False
                        speaker_btn.style.bgcolor = ft.colors.with_opacity(0.15, accent)
                        page.update()
                    except Exception as exc:
                        print(f"Resume error: {exc}")
                    return
                
                # If playing, pause
                if is_playing[0]:
                    try:
                        import pygame
                        pygame.mixer.music.pause()
                        is_paused[0] = True
                        is_playing[0] = False
                        speaker_btn.text = "▶️ Resume"
                        speaker_btn.disabled = False
                        speaker_btn.style.bgcolor = ft.colors.with_opacity(0.1, accent)
                        page.update()
                    except Exception as exc:
                        print(f"Pause error: {exc}")
                    return
                
                # If loading, ignore
                if is_loading[0]:
                    return
                
                # Start TTS
                is_loading[0] = True
                speaker_btn.text = "🔄 Loading..."
                speaker_btn.disabled = True
                speaker_btn.style.bgcolor = ft.colors.with_opacity(0.05, accent)
                page.update()
                
                # Run TTS in background
                def _speak():
                    try:
                        import pygame
                        import tempfile
                        import os
                        import asyncio as _asyncio
                        import edge_tts
                        
                        # Validate text
                        if not text or not text.strip():
                            raise ValueError("No text to speak")
                        
                        # Initialize pygame mixer if not already
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        
                        # Generate TTS audio file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        audio_file[0] = temp_file.name
                        temp_file.close()
                        
                        # Generate audio using edge-tts with language-appropriate voice
                        async def generate_audio():
                            # Get voices for user's selected language
                            from engine.speech.language_voice_mapping import get_voices_for_language
                            voices = get_voices_for_language(state.language)
                            
                            print(f"🔊 TTS for language: {state.language}")
                            print(f"🎤 Trying voices: {voices}")
                            
                            last_error = None
                            for voice in voices:
                                try:
                                    communicate = edge_tts.Communicate(text, voice)
                                    await communicate.save(audio_file[0])
                                    print(f"✅ TTS generated with voice: {voice}")
                                    return  # Success
                                except Exception as e:
                                    last_error = e
                                    print(f"⚠️ Voice {voice} failed: {e}")
                                    continue
                            
                            # If all voices failed, raise the last error
                            if last_error:
                                raise last_error
                        
                        loop = _asyncio.new_event_loop()
                        _asyncio.set_event_loop(loop)
                        loop.run_until_complete(generate_audio())
                        loop.close()
                        
                        # Update to playing state
                        def _set_playing():
                            is_loading[0] = False
                            is_playing[0] = True
                            speaker_btn.text = "⏸️ Pause"
                            speaker_btn.disabled = False
                            speaker_btn.style.bgcolor = ft.colors.with_opacity(0.15, accent)
                            page.update()
                        _ui_call(_set_playing)
                        
                        # Play audio using pygame
                        pygame.mixer.music.load(audio_file[0])
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                            # Check if paused
                            if is_paused[0]:
                                while is_paused[0]:
                                    pygame.time.Clock().tick(10)
                        
                        # Clean up audio file
                        try:
                            os.unlink(audio_file[0])
                        except:
                            pass
                        
                    except Exception as exc:
                        print(f"TTS error: {exc}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        # Reset button state
                        def _reset():
                            is_loading[0] = False
                            is_playing[0] = False
                            is_paused[0] = False
                            speaker_btn.text = "🔊 Listen"
                            speaker_btn.disabled = False
                            speaker_btn.style.bgcolor = ft.colors.with_opacity(0.1, accent)
                            page.update()
                        _ui_call(_reset)
                
                _run_in_thread(_speak)
            
            speaker_btn = ft.TextButton(
                text="🔊 Listen",
                on_click=on_speaker_click,
                disabled=False,
                style=ft.ButtonStyle(
                    color=accent,  # Purple accent color
                    bgcolor=ft.colors.with_opacity(0.1, accent),  # Light purple background
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    shape=ft.RoundedRectangleBorder(radius=8),
                    overlay_color=ft.colors.with_opacity(0.2, accent),  # Darker purple on hover
                ),
            )
            
            # Build content with text, speaker button, and optional sources
            bubble_content = [
                ft.Text(text, color=BUBBLE_BOT_FG, size=state.font_sp(), selectable=True),
                ft.Container(height=8),
                speaker_btn,
            ]
            
            # Add sources if provided
            if sources and len(sources) > 0:
                bubble_content.append(ft.Container(height=8))
                bubble_content.append(
                    ft.Text(
                        "References:",
                        color=BUBBLE_BOT_FG,
                        size=state.font_sp() - 2,
                        weight=ft.FontWeight.BOLD,
                    )
                )
                for i, source in enumerate(sources, 1):
                    bubble_content.append(
                        ft.Text(
                            f"{i}. {source}",
                            color=accent,
                            size=state.font_sp() - 2,
                            selectable=True,
                        )
                    )
            
            content = ft.Container(
                content=ft.Column(
                    bubble_content,
                    spacing=4,
                    tight=True,
                ),
                bgcolor=BUBBLE_BOT_BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                expand=True,
                border=ft.border.all(1, ft.colors.with_opacity(0.12, accent)),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.START, expand=True)

        chat_list.controls.append(bubble)
        return bubble

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
        
        # Check if we're in document or web mode
        current_mode = active_mode[0]
        
        if current_mode == "document" and selected_file[0]:
            # Document Q&A mode
            on_doc_ask(None)
        elif current_mode == "web" and url_valid[0]:
            # Web Q&A mode
            on_web_ask(None)
        else:
            # General chat mode - use voice processing pipeline
            _add_bubble(msg, "user")
            thinking_bubble = _add_bubble("Thinking…", "status")
            chat_field.value = ""
            mic_icon.name = ft.icons.MIC_ROUNDED
            page.update()
            
            # Save user message to database
            rag = get_rag_instance()
            if RAG_AVAILABLE and rag and state.conversation_id:
                try:
                    rag.save_user_message(state.conversation_id, msg)
                except Exception as e:
                    print(f"⚠️ Failed to save user message: {e}")
            
            def _process_text_question():
                try:
                    # Use preloaded modules
                    _, process_voice_result, _, _, _ = _get_preloaded_modules()
                    
                    # Process the question with user's country and language preferences
                    print(f"Processing text question: {msg}")
                    print(f"User country: {state.country}, User language: {state.language}")
                    response = process_voice_result(
                        dialect="en",  # Detected dialect (not used when language is specified)
                        question=msg,
                        query=msg,
                        country=state.country,
                        language=state.language
                    )
                    print(f"Got response: {response}")
                    
                    # Update UI with response
                    def _show_response():
                        # Remove thinking bubble
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                        
                        if response:
                            # response is now a dict with 'answer' and 'sources'
                            if isinstance(response, dict):
                                answer = response.get("answer", "")
                                sources = response.get("sources", [])
                                _add_bubble(answer, "bot", sources)
                                
                                # Save bot message to database
                                rag = get_rag_instance()
                                if RAG_AVAILABLE and rag and state.conversation_id:
                                    try:
                                        # Format response with sources for storage
                                        full_response = answer
                                        if sources:
                                            full_response += "\n\nReferences:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sources))
                                        rag.save_bot_message(state.conversation_id, full_response)
                                    except Exception as e:
                                        print(f"⚠️ Failed to save bot message: {e}")
                            else:
                                # Fallback for old format (string)
                                _add_bubble(str(response), "bot")
                                
                                # Save bot message to database
                                rag = get_rag_instance()
                                if RAG_AVAILABLE and rag and state.conversation_id:
                                    try:
                                        rag.save_bot_message(state.conversation_id, str(response))
                                    except Exception as e:
                                        print(f"⚠️ Failed to save bot message: {e}")
                        else:
                            _add_bubble("⚠️ Could not process your question.", "status")
                        
                        page.update()
                    
                    _ui_call(_show_response)
                    
                except Exception as exc:
                    def _show_error():
                        if thinking_bubble in chat_list.controls:
                            chat_list.controls.remove(thinking_bubble)
                        _add_bubble(f"⚠️ Error: {exc}", "status")
                        page.update()
                    _ui_call(_show_error)
                    print(f"Text question processing error: {exc}")
                    import traceback
                    traceback.print_exc()
            
            _run_in_thread(_process_text_question)

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
        color=ft.colors.WHITE,
        size=24,
    )

    mic_circle = ft.Container(
        content=mic_icon,
        width=48,
        height=48,
        border_radius=24,
        gradient=_grad,
        alignment=ft.alignment.center,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    def _start_recording(_):
        if (chat_field.value or "").strip():
            return
        if is_processing[0]:
            return

        is_recording[0] = True
        chat_field.hint_text = "Recording..."
        mic_circle.gradient = None
        mic_circle.bgcolor = ft.colors.RED_400
        page.update()

        if active_mode[0] in ("document", "web"):
            # Use sounddevice to capture raw audio for search transcription
            import sounddevice as sd
            _search_audio_chunks.clear()
            _search_sd_stream[0] = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32",
                callback=lambda indata, *_: _search_audio_chunks.append(indata.copy()),
            )
            _search_sd_stream[0].start()
        else:
            _pulse(expand=False)
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
        threading.Timer(0.6, _pulse, kwargs={"expand": not expand}).start()

    def _stop_recording(_):
        if is_processing[0]:
            return
        was_recording = is_recording[0]
        is_recording[0] = False

        chat_field.hint_text = "Ask a question..."
        mic_circle.gradient = _grad
        mic_circle.bgcolor = None
        page.update()

        if (chat_field.value or "").strip():
            on_chat_submit(None)
            return

        if not was_recording:
            return

        if active_mode[0] in ("document", "web"):
            # Stop the search-mode stream and transcribe
            sd_stream = _search_sd_stream[0]
            if sd_stream:
                sd_stream.stop()
                sd_stream.close()
                _search_sd_stream[0] = None

            def _transcribe_work():
                import numpy as np
                import soundfile as sf
                import tempfile, os

                def _set_mic_processing():
                    is_processing[0] = True
                    chat_field.hint_text = "Transcribing..."
                    mic_icon.name = ft.icons.STOP_ROUNDED
                    mic_circle.gradient = None
                    mic_circle.bgcolor = ft.colors.GREY_400
                    page.update()

                _ui_call(_set_mic_processing)

                try:
                    if _search_audio_chunks:
                        audio_np = np.concatenate(_search_audio_chunks, axis=0).flatten()
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                            tmp_path = f.name
                        sf.write(tmp_path, audio_np, 16000)
                        # Use preloaded transcribe_audio function
                        _, _, _, _, transcribe_audio = _get_preloaded_modules()
                        text = transcribe_audio(tmp_path, normalize_to_question=False) if transcribe_audio else ""
                        os.remove(tmp_path)
                    else:
                        text = ""

                    def _done():
                        is_processing[0] = False
                        chat_field.hint_text = "Ask a question..."
                        mic_icon.name = ft.icons.MIC_ROUNDED
                        mic_circle.gradient = _grad
                        mic_circle.bgcolor = None
                        if text:
                            chat_field.value = text
                        page.update()

                    _ui_call(_done)
                except Exception as exc:
                    def _err():
                        is_processing[0] = False
                        chat_field.hint_text = "Ask a question..."
                        mic_icon.name = ft.icons.MIC_ROUNDED
                        mic_circle.gradient = _grad
                        mic_circle.bgcolor = None
                        _add_bubble(f"⚠️ Transcription error: {exc}", "status")
                        page.update()
                    _ui_call(_err)

            threading.Thread(target=_transcribe_work, daemon=True).start()

        else:
            stream.stop()

            def process():
                session.stop_recording()
                results = session.results

                dialect = results.get("dialect")
                question = results.get("question")
                query = results.get("query")

                # Add thinking indicator
                thinking_bubble = [None]
                
                def set_processing():
                    is_processing[0] = True
                    chat_field.hint_text = "Processing..."
                    mic_icon.name = ft.icons.STOP_ROUNDED
                    mic_circle.gradient = None
                    mic_circle.bgcolor = ft.colors.GREY_400
                    
                    # Show transcript as user bubble
                    if question:
                        _add_bubble(question, "user")
                    # Add thinking indicator
                    thinking_bubble[0] = _add_bubble("Thinking…", "status")
                    page.update()

                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(set_processing)
                else:
                    set_processing()

                # ✅ CALL YOUR MAIN LOGIC HERE - Use preloaded modules
                _, process_voice_result, speak_answer, _, _ = _get_preloaded_modules()
                response = process_voice_result(
                    dialect=dialect,
                    question=question,
                    query=query,
                    country=state.country,
                    language=state.language
                )

                # 👉 Update UI safely
                def update_ui():
                    is_processing[0] = False
                    chat_field.hint_text = "Ask a question..."
                    mic_icon.name = ft.icons.MIC_ROUNDED
                    mic_circle.gradient = _grad
                    mic_circle.bgcolor = None
                    chat_field.value = ""

                    # Remove thinking bubble
                    if thinking_bubble[0] and thinking_bubble[0] in chat_list.controls:
                        chat_list.controls.remove(thinking_bubble[0])

                    if response:
                        _show_result_card(response)

                    print("Dialect:", dialect)
                    print("Question:", question)
                    print("Query:", query)
                    print("Response:", response)

                    page.update()

                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_ui)
                else:
                    update_ui()

                # Run TTS after UI has been updated (only speak the answer, not sources)
                if response:
                    import asyncio as _asyncio
                    loop = _asyncio.new_event_loop()
                    try:
                        # Extract just the answer text for TTS
                        answer_text = response.get("answer", "") if isinstance(response, dict) else str(response)
                        if answer_text:
                            loop.run_until_complete(speak_answer(answer_text, "MY"))
                    finally:
                        loop.close()

            # Use a plain daemon thread and marshal UI updates via `call_from_thread`.
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
    #  Result card                                                        #
    # ------------------------------------------------------------------ #

    _rc_title      = ft.Text("Response", size=state.font_sp() - 1, weight=ft.FontWeight.BOLD, color=accent)
    _rc_meta       = ft.Text("", size=state.font_sp() - 2, color=ft.colors.with_opacity(0.55, state.text_color()), visible=False)
    _rc_divider    = ft.Divider(height=1, color=ft.colors.with_opacity(0.12, accent), visible=False)
    _rc_body       = ft.Text("", size=state.font_sp(), color=state.text_color(), selectable=True)

    result_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.icons.AUTO_AWESOME_OUTLINED, color=accent, size=16),
                        _rc_title,
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_color=state.text_color(),
                            icon_size=16,
                            tooltip="Dismiss",
                            on_click=lambda _: _dismiss_result_card(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                _rc_meta,
                _rc_divider,
                _rc_body,
            ],
            spacing=6,
        ),
        bgcolor=state.surface_color(),
        border=ft.border.all(2, accent),
        border_radius=16,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        margin=ft.margin.symmetric(horizontal=16),
        visible=False,
    )

    def _show_result_card(payload, title: str = "Response"):
        """Voice response path — show as bot bubble with sources."""
        if isinstance(payload, dict):
            # New format with answer and sources
            text = payload.get("answer", payload.get("summary", ""))
            sources = payload.get("sources", [])
            _add_bubble(text, "bot", sources)
        else:
            # Old format (string)
            _add_bubble(str(payload), "bot")
        page.update()

    def _dismiss_result_card():
        result_card.visible = False
        page.update()

    # ------------------------------------------------------------------ #
    #  PTT Session + full pipeline                                        #
    # ------------------------------------------------------------------ #

    def _ui(fn):
        fn()  # Flet 0.19.0 — page.update() is thread-safe

    def _add_bubble_safe(text: str, role: str = "bot", sources: list = None):
        def _do():
            _add_bubble(text, role, sources)
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
            mic_circle.gradient = _grad
            mic_circle.bgcolor = None
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
        from engine.speech.main import run_pipeline_with_stt_result  # noqa: PLC0415

        def on_status(msg: str):
            _add_bubble_safe(msg, "status")

        def on_result(answer: str, links: list, dialect: str, question: str):
            _reset_mic_visuals()
            _add_bubble_safe(answer, "bot")

        def on_error(exc: Exception):
            _reset_mic_visuals()
            _add_bubble_safe(f"⚠️ {exc}", "status")

        threading.Thread(
            target=run_pipeline_with_stt_result,
            args=(stt_result, on_status, on_result, on_error, "my"),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------ #
    #  Cards header — hide on scroll up, reveal on scroll down           #
    # ------------------------------------------------------------------ #

    _CARDS_FULL_HEIGHT = 250  # approximate height of greeting + cards row

    _cards_header = ft.Container(
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
        animate_opacity=ft.animation.Animation(250, ft.AnimationCurve.EASE_IN_OUT),
        animate=ft.animation.Animation(250, ft.AnimationCurve.EASE_IN_OUT),
        height=_CARDS_FULL_HEIGHT,
        opacity=1,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    _DRAG_THRESHOLD = 10
    _drag_accum: list = [0.0]

    def _on_drag_update(e: ft.DragUpdateEvent):
        _drag_accum[0] += e.delta_y
        if _drag_accum[0] < -_DRAG_THRESHOLD and _cards_visible[0]:
            _drag_accum[0] = 0.0
            _cards_visible[0] = False
            _cards_header.height = 0
            _cards_header.opacity = 0
            page.update()
        elif _drag_accum[0] > _DRAG_THRESHOLD and not _cards_visible[0]:
            _drag_accum[0] = 0.0
            _cards_visible[0] = True
            _cards_header.height = _CARDS_FULL_HEIGHT
            _cards_header.opacity = 1
            page.update()

    def _on_list_scroll(e):
        pass  # unused, kept for safety

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
        bgcolor=ft.colors.TRANSPARENT,
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
            ft.Container(
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=(
                        ["#1A0F2E", "#0D1B3E"] if _dark
                        else ["#F5F3FF", "#EFF6FF"]
                    ),
                ),
                content=ft.Column(
                    [
                        _cards_header,
                        # Chat list wrapped in gesture detector for swipe detection
                        ft.GestureDetector(
                            content=chat_list,
                            on_vertical_drag_update=_on_drag_update,
                            expand=True,
                        ),
                        # Bottom section — always below the list, never overlaid
                        panel_container,
                        result_card,
                        ft.Row(
                            [chat_bar, mic_container],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                    tight=False,
                ),
            ),
        ],
        padding=0,
        bgcolor=state.bg_color(),
    )
