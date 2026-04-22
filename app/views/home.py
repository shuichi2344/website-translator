from __future__ import annotations

import os
import threading

import flet as ft

from app.state import AppState
from app.components.theme import ACCENT, ACCENT_DARK, accent_gradient, GRAD_START, GRAD_END, GRAD_START_DARK, GRAD_END_DARK
from app.preloader import get_modules
from engine.insert_doc.document_LLM import InclusiveCitizenAI

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

def _fetch_user_country(state: AppState) -> None:
    """Fetch the user's country from MySQL and update state. Silent on failure."""
    if not state.user_id:
        return
    try:
        from engine.database.auth_handler import AuthHandler
        auth = AuthHandler()
        profile = auth.get_user_profile(state.user_id)
        auth.close()
        if profile and profile.get("country"):
            state.country = profile["country"]
            print(f"[home] Country refreshed from DB: {state.country}")
    except Exception as e:
        print(f"[home] Could not fetch country from DB: {e}")


# Country name → ISO-3166 alpha-2 used by VOICE_MATRIX
_COUNTRY_CODE_MAP = {
    "Malaysia": "MY", "Indonesia": "ID", "Thailand": "TH",
    "Vietnam": "VN", "Philippines": "PH", "Myanmar": "MM",
    "Cambodia": "KH", "Laos": "LA", "Singapore": "SG",
    "Brunei": "BN", "Timor-Leste": "TL",
}


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
            try:
                state.session, state.stream = create_session()
            except Exception as e:
                print(f"⚠️ Could not initialize voice session (Whisper unavailable): {e}")
                state.session = None
                state.stream = None
    
    # Initialize or get conversation
    from datetime import datetime
    rag = get_rag_instance()
    if RAG_AVAILABLE and rag and state.user_id:
        if not state.conversation_id:
            # Create new conversation with default "New Chat" title
            state.conversation_id = rag.create_conversation(
                user_id=state.user_id,
                title="New Chat"
            )
            print(f"✅ Created conversation: {state.conversation_id}")
        else:
            print(f"✅ Using existing conversation: {state.conversation_id}")

    # Refresh country from MySQL in background (non-blocking)
    threading.Thread(target=_fetch_user_country, args=(state,), daemon=True).start()

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
    
    # Sidebar state
    sidebar_visible: list = [False]  # Sidebar visibility state
    conversations_list: list = []  # List of user conversations
    sidebar_width: list = [280]  # Sidebar width (adjustable)
    is_resizing: list = [False]  # Track if user is resizing sidebar

    LANG_CODE_MAP = {
        "English": "en",
        "Bahasa Melayu": "ms",
        "Bahasa Indonesia": "id",
        "Thai": "th",
        "Vietnamese": "vi",
        "Filipino/Tagalog": "tl",
        "Burmese": "my",
        "Khmer": "km",
        "Lao": "lo",
        "Tamil": "ta",
        "Chinese (Simplified)": "zh-cn",
    }

    accent = ACCENT_DARK if state.theme_mode == "Dark" else ACCENT
    _dark = state.theme_mode == "Dark"
    _grad = accent_gradient(_dark)
    _grad_colors = [GRAD_START_DARK, GRAD_END_DARK] if _dark else [GRAD_START, GRAD_END]

    # ------------------------------------------------------------------ #
    #  Circular selection button factory                                   #
    # ------------------------------------------------------------------ #
    def circle_btn(icon, label: str, mode: str, on_click_fn) -> ft.Column:
        btn = ft.Container(
            content=ft.Icon(icon, color=ft.colors.WHITE, size=28),
            width=64,
            height=64,
            border_radius=32,
            gradient=_grad,
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.colors.with_opacity(0.18, "#000000"),
            ),
            on_click=on_click_fn,
            animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        return ft.Column(
            [
                btn,
                ft.Text(
                    label,
                    size=state.font_sp() - 1,
                    color=state.text_color(),
                    text_align=ft.TextAlign.CENTER,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
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
    web_btn  = circle_btn(ft.icons.LANGUAGE,           "Website",    "web",      lambda _: set_mode("web"))
    media_btn = circle_btn(ft.icons.IMAGE,              "Image/File", "document", lambda _: set_mode("document"))
    form_btn  = circle_btn(ft.icons.INSERT_DRIVE_FILE,  "Form",       "form",     lambda _: set_mode("form"))

    # ------------------------------------------------------------------ #
    #  Shared ASEAN language selector (used in both panels)              #
    # ------------------------------------------------------------------ #

    ASEAN_LANGUAGES = [
        "English", "Bahasa Melayu", "Bahasa Indonesia", "Sundanese", "Thai", "Vietnamese",
        "Filipino/Tagalog", "Burmese", "Khmer", "Lao", "Tamil", "Chinese (Simplified)",
    ]

    _IV_YES_WORDS = (
        # English
        "yes", "yep", "yeah", "yup", "sure", "ok", "okay", "correct", "confirm",
        # Malay / Indonesian
        "ya", "ada", "betul", "boleh", "setuju", "iya", "oke", "benar",
        # Thai (romanised)
        "chai", "krub", "kha",
        # Vietnamese
        "vâng", "có", "đúng",
        # Filipino / Tagalog
        "oo", "opo", "sige",
        # Chinese
        "是", "好", "对", "可以",
        # Tamil
        "ஆம்", "சரி",
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
        "Docling + Google Gemini 3.0 Flash — Advanced AI summarization",
        "RAG Q&A: Ask specific questions about documents or websites",
        "Automatic language detection and complex table recognition",
        "Supports PDF and images (PNG, JPG, JPEG, BMP, TIFF)",
        "Website summarization extracts main content and crawls 3 sublinks",
        "Embeddings cached in ChromaDB for fast repeated queries",
    ]

    _WEB_NOTES = [
        "Maximum file size: 50MB",
        "Docling + Google Gemini 3.0 Flash — Advanced AI summarization",
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
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            tight=True,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
    )

    # ------------------------------------------------------------------ #
    #  Form Panel — progressive disclosure layout                         #
    # ------------------------------------------------------------------ #

    import json as _json

    # Load map.json once
    try:
        with open("map.json", "r") as _f:
            _map_data = _json.load(_f)
        _all_forms = _map_data.get("available_forms", [])
        for _form in _all_forms:
            if "country" not in _form:
                _form["country"] = "Malaysia"
    except Exception:
        _all_forms = []

    # Derive unique country list preserving order
    _seen = []
    for _form in _all_forms:
        c = _form.get("country", "Malaysia")
        if c not in _seen:
            _seen.append(c)
    _countries = _seen or ["Malaysia"]

    def _form_card(form: dict) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.DESCRIPTION_OUTLINED, color=accent, size=28),
                    ft.Text(
                        form.get("display_name", "Form"),
                        size=state.font_sp() - 1,
                        color=state.text_color(),
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            border=ft.border.all(1.5, accent),
            border_radius=14,
            bgcolor=state.surface_color(),
            padding=12,
            ink=True,
            on_click=lambda _, f=form: _on_form_selected(f),
        )

    def _add_card() -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.ADD_CIRCLE_OUTLINE, color=accent, size=32),
                    ft.Text(
                        "Add / Scan",
                        size=state.font_sp() - 1,
                        color=state.text_color(),
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            border=ft.border.all(1.5, ft.colors.with_opacity(0.4, accent)),
            border_radius=14,
            bgcolor=ft.colors.with_opacity(0.04, accent),
            padding=12,
            ink=True,
            on_click=lambda _: scan_picker.pick_files(
                dialog_title="Select a PDF form to scan",
                allowed_extensions=["pdf"],
            ),
        )

    # Empty state shown when no forms match the selected country
    _empty_state = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.icons.SEARCH_OFF_ROUNDED, color=ft.colors.with_opacity(0.35, accent), size=48),
                ft.Text(
                    "No forms found for this region",
                    size=state.font_sp(),
                    color=ft.colors.with_opacity(0.5, state.text_color()),
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.alignment.center,
        height=100,
        visible=False,
    )

    _FORM_TYPE_ICONS = {
        "government": ft.icons.ACCOUNT_BALANCE_OUTLINED,
        "insurance":  ft.icons.HEALTH_AND_SAFETY_OUTLINED,
        "healthcare": ft.icons.LOCAL_HOSPITAL_OUTLINED,
        "rental":     ft.icons.HOME_OUTLINED,
        "other":      ft.icons.DESCRIPTION_OUTLINED,
    }

    _form_grid = ft.Column(
        spacing=16,
        expand=False,
    )

    # Wrapper animates height + opacity after country is chosen
    _form_grid_wrapper = ft.Container(
        content=ft.Column(
            [_empty_state, _form_grid],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        height=0,
        opacity=0,
        animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN),
        animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    def _build_form_groups(forms: list):
        """Rebuild _form_grid with forms grouped by form_type."""
        _form_grid.controls.clear()

        # Group preserving insertion order
        groups: dict[str, list] = {}
        for f in forms:
            ft_key = (f.get("form_type") or "other").lower()
            groups.setdefault(ft_key, []).append(f)

        for ft_key, group_forms in groups.items():
            label = ft_key.replace("_", " ").title()
            icon  = _FORM_TYPE_ICONS.get(ft_key, ft.icons.DESCRIPTION_OUTLINED)

            group_grid = ft.GridView(
                runs_count=2,
                max_extent=180,
                child_aspect_ratio=1.1,
                spacing=10,
                run_spacing=10,
                expand=False,
                height=max(130, ((len(group_forms) + 1) // 2) * 130),
            )
            for form in group_forms:
                group_grid.controls.append(_form_card(form))

            _form_grid.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(icon, color=accent, size=16),
                                ft.Text(
                                    label,
                                    size=state.font_sp() - 1,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.colors.with_opacity(0.7, state.text_color()),
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        group_grid,
                    ],
                    spacing=6,
                )
            )

    def _on_country_change(e):
        country = _country_dropdown.value or ""
        forms = [f for f in _all_forms if f.get("country", "Malaysia") == country]

        if forms:
            _build_form_groups(forms)
            _empty_state.visible = False
            # Height: sum of per-group grids + headers
            total_rows = sum(((len([f for f in forms if (f.get("form_type") or "other").lower() == ft_key]) + 1) // 2)
                             for ft_key in dict.fromkeys((f.get("form_type") or "other").lower() for f in forms))
            grid_height = max(200, total_rows * 130 + len(dict.fromkeys((f.get("form_type") or "other").lower() for f in forms)) * 40)
        else:
            _form_grid.controls.clear()
            _empty_state.visible = True
            grid_height = 140

        _form_grid_wrapper.height = grid_height
        _form_grid_wrapper.opacity = 1
        panel_container.height = 120 + grid_height
        page.update()

    # Active form-filling session state
    _form_ai: list = [None]              # InclusiveCitizenAI instance
    _form_name: list = [None]            # display name of active form
    _form_filling: list = [False]        # True while a form session is running
    _form_confirming: list = [False]     # True while awaiting yes/no confirmation
    _form_map_entry: list = [None]       # map.json entry for the active form
    _form_sig_path: list = [None]        # temp PNG path for signature

    def _run_form_session(ai: InclusiveCitizenAI, display_name: str):
        """
        Runs the full form Q&A loop in a background thread.
        Handles regular questions, section confirmations, and auto-skips.
        """
        try:
            while True:
                result = ai.generate_question()

                # ── Form complete ────────────────────────────────────────
                if result is None:
                    tts_summary = ai.get_tts_summary()

                    def _done():
                        _form_filling[0] = False
                        _form_confirming[0] = True  # wait for yes/no
                        _add_bubble("✅ Here's a summary of your information:", "status")
                        _add_bubble(tts_summary, "bot")
                        page.update()
                    _ui_call(_done)
                    return

                # ── Optional section confirmation ────────────────────────
                if result.startswith("SECTION_CONFIRM:"):
                    confirm_q = result.split(":", 1)[1]
                    _ui_call(lambda q=confirm_q: (_add_bubble(q, "bot"), page.update()))

                    answer = ai.wait_for_answer(timeout=300.0)
                    if answer is None:
                        _ui_call(lambda: (_add_bubble("⏱️ Session timed out.", "status"), page.update()))
                        break
                    ai.confirm_section(answer)
                    continue  # loop back — generate_question will skip or proceed

                # ── Regular question ─────────────────────────────────────
                _ui_call(lambda q=result: (_add_bubble(q, "bot"), page.update()))

                answer = ai.wait_for_answer(timeout=300.0)
                if answer is None:
                    _ui_call(lambda: (_add_bubble("⏱️ Session timed out.", "status"), page.update()))
                    break

                extracted = ai.extract_and_save(answer)
                if extracted == "RETRY":
                    _ui_call(lambda: (
                        _add_bubble("I didn't catch that — could you try again?", "bot"),
                        page.update()
                    ))
                    # Index not advanced — loop will re-ask same question

        except Exception as exc:
            def _err():
                _form_filling[0] = False
                _form_ai[0] = None
                _add_bubble(f"⚠️ Form error: {exc}", "status")
                page.update()
            _ui_call(_err)
        finally:
            _form_filling[0] = False
            # Only clear _form_ai if we are NOT waiting for confirmation
            # (confirmation handler needs ai.responses to write the PDF)
            if not _form_confirming[0]:
                _form_ai[0] = None

    def _on_form_selected(form: dict):
        set_mode(None)
        # Reuse the same interview card UI used for scanned PDFs
        _run_in_thread(lambda: _ui_call(lambda: _open_interview_for_entry(form)))

    # Full ASEAN country list for the form country picker
    _ASEAN_COUNTRIES = [
        "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
        "Myanmar", "Philippines", "Singapore", "Thailand",
        "Timor-Leste", "Vietnam",
    ]

    _country_dropdown = ft.Dropdown(
        label="Select Country",
        hint_text="Choose a country",
        options=[ft.dropdown.Option(c) for c in _ASEAN_COUNTRIES],
        border_color=accent,
        border_radius=8,
        border_width=2,
        bgcolor=state.surface_color(),
        color=state.text_color(),
        label_style=ft.TextStyle(color=accent, size=state.font_sp() - 1),
        text_style=ft.TextStyle(color=state.text_color(), size=state.font_sp()),
        on_change=_on_country_change,
    )

    # Initially: dropdown centered, grid hidden
    form_panel = ft.Container(
        content=ft.Column(
            [
                ft.Container(expand=True),  # top spacer
                ft.Row(
                    [
                        ft.Container(content=_country_dropdown, expand=True),
                        ft.IconButton(
                            icon=ft.icons.ADD_CIRCLE_OUTLINE,
                            icon_color=accent,
                            icon_size=28,
                            tooltip="Add / Scan PDF",
                            on_click=lambda _: scan_picker.pick_files(
                                dialog_title="Select a PDF form to scan",
                                allowed_extensions=["pdf"],
                            ),
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                _form_grid_wrapper,
                ft.Container(expand=True),  # bottom spacer
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=10,
            expand=True,
        ),
        visible=False,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        expand=True,
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
        for btn in (doc_summarise_btn, web_summarise_btn):
            btn.disabled = loading
        page.update()

    def on_doc_summarise(_):
        filepath = selected_file[0]
        lang_code = LANG_CODE_MAP.get(state.language, "en")
        
        # Detect if the selected file is an image
        _img_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
        import os as _os
        _is_image = _os.path.splitext(filepath or "")[1].lower() in _img_exts

        # Hide the document panel immediately
        set_mode(None)
        
        _add_bubble(f"Summarising {'image' if _is_image else 'document'}: {selected_file_name[0]}", "user")
        # Add status indicator with real-time updates
        status_bubble = _add_bubble(f"{'🖼️ Processing image...' if _is_image else '📄 Processing document...'}", "status")
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Update status: Extracting text
                def _update_status_extract():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "🔍 Analysing image with Gemini Vision..." if _is_image else "📖 Extracting text..."
                        page.update()
                _ui_call(_update_status_extract)
                
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                
                # Update status: Summarizing
                def _update_status_summarize():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "✨ Summarizing content..."
                        page.update()
                _ui_call(_update_status_summarize)
                
                result = summarizer.process_document(filepath)
                if result:
                    summary = result.get("summary", "")
                    orig = result.get("word_count", 0)
                    summ = result.get("summary_word_count", 0)
                    reduction = round(100 - (summ / orig * 100)) if orig else 0
                    # Remove status bubble before adding result
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    # Use bot bubble with TTS support
                    label = "🖼️ Image Summary" if _is_image else "📄 Document Summary"
                    _add_bubble_safe(f"{label}  •  {orig:,}→{summ:,} words ({reduction}% reduction)\n\n{summary}", "bot", lang=state.language)
                    
                    # Save to database
                    rag = get_rag_instance()
                    if RAG_AVAILABLE and rag and state.conversation_id:
                        try:
                            rag.save_bot_message(state.conversation_id, f"{'Image' if _is_image else 'Document'} Summary: {summary}")
                        except Exception as e:
                            print(f"⚠️ Failed to save bot message: {e}")
                else:
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    _add_bubble_safe(f"⚠️ Failed to process {'image' if _is_image else 'document'}.", "status")
            except Exception as exc:
                def _remove_status():
                    if status_bubble in chat_list.controls:
                        chat_list.controls.remove(status_bubble)
                _ui_call(_remove_status)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    def on_doc_ask(_):
        question = (chat_field.value or "").strip()
        filepath = selected_file[0]
        lang_code = LANG_CODE_MAP.get(state.language, "en")

        if not question:
            return  # Silently ignore if no question

        # Hide the document panel immediately
        set_mode(None)

        # Show document attachment above the question (like ChatGPT/Gemini)
        doc_attachment = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.DESCRIPTION_OUTLINED, size=16, color=BUBBLE_USER_FG),
                ft.Text(selected_file_name[0], size=state.font_sp() - 2, color=BUBBLE_USER_FG, weight=ft.FontWeight.W_500),
            ], spacing=6),
            bgcolor=ft.colors.with_opacity(0.2, accent),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )
        attachment_row = ft.Row([doc_attachment], alignment=ft.MainAxisAlignment.END)
        chat_list.controls.append(attachment_row)
        
        _add_bubble(question, "user")
        # Add status indicator with real-time updates
        status_bubble = _add_bubble("📄 Processing document...", "status")
        chat_field.value = ""
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Update status: Extracting text
                def _update_status_extract():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "📖 Extracting text..."
                        page.update()
                _ui_call(_update_status_extract)
                
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                
                # Update status: Analyzing
                def _update_status_analyze():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "🔍 Analyzing content..."
                        page.update()
                _ui_call(_update_status_analyze)
                
                result = summarizer.rag_qa_document(filepath, question)
                
                # Update status: Generating answer
                def _update_status_generate():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "✨ Generating answer..."
                        page.update()
                _ui_call(_update_status_generate)
                
                if result:
                    # Remove status bubble before adding result
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    # Use bot bubble with TTS support instead of result
                    _add_bubble_safe(result.get("summary", ""), "bot", lang=state.language)
                    
                    # Save to database
                    rag = get_rag_instance()
                    if RAG_AVAILABLE and rag and state.conversation_id:
                        try:
                            rag.save_bot_message(state.conversation_id, result.get("summary", ""))
                        except Exception as e:
                            print(f"⚠️ Failed to save bot message: {e}")
                else:
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    _add_bubble_safe("⚠️ Could not answer that question.", "status")
            except Exception as exc:
                def _remove_status():
                    if status_bubble in chat_list.controls:
                        chat_list.controls.remove(status_bubble)
                _ui_call(_remove_status)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    def on_web_summarise(_):
        url = url_field.value or ""
        lang_code = LANG_CODE_MAP.get(state.language, "en")
        
        # Hide the website panel immediately
        set_mode(None)
        
        _add_bubble(f"Summarising: {url}", "user")
        # Add status indicator with real-time updates
        status_bubble = _add_bubble("🌐 Connecting to website...", "status")
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Update status: Retrieving content
                def _update_status_retrieve():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "📥 Retrieving content..."
                        page.update()
                _ui_call(_update_status_retrieve)
                
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                
                # Update status: Summarizing
                def _update_status_summarize():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "✨ Summarizing content..."
                        page.update()
                _ui_call(_update_status_summarize)
                
                result = summarizer.process_website(url, crawl_depth=1, max_sublinks=3)
                if result:
                    summary = result.get("summary", "")
                    orig = result.get("word_count", 0)
                    summ = result.get("summary_word_count", 0)
                    reduction = round(100 - (summ / orig * 100)) if orig else 0
                    # Remove status bubble before adding result
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    # Use bot bubble with TTS support
                    _add_bubble_safe(f"🌐 Website Summary  •  {orig:,}→{summ:,} words ({reduction}% reduction)\n\n{summary}", "bot", lang=state.language)
                    
                    # Save to database
                    rag = get_rag_instance()
                    if RAG_AVAILABLE and rag and state.conversation_id:
                        try:
                            rag.save_bot_message(state.conversation_id, f"Website Summary: {summary}")
                        except Exception as e:
                            print(f"⚠️ Failed to save bot message: {e}")
                else:
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
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
        lang_code = LANG_CODE_MAP.get(state.language, "en")

        if not question:
            return  # Silently ignore if no question

        # Hide the website panel immediately
        set_mode(None)

        # Show website attachment above the question (like ChatGPT/Gemini)
        web_attachment = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.LANGUAGE, size=16, color=BUBBLE_USER_FG),
                ft.Text(url if len(url) <= 50 else url[:47] + "...", size=state.font_sp() - 2, color=BUBBLE_USER_FG, weight=ft.FontWeight.W_500),
            ], spacing=6),
            bgcolor=ft.colors.with_opacity(0.2, accent),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )
        attachment_row = ft.Row([web_attachment], alignment=ft.MainAxisAlignment.END)
        chat_list.controls.append(attachment_row)
        
        _add_bubble(question, "user")
        # Add status indicator with real-time updates
        status_bubble = _add_bubble("🌐 Connecting to website...", "status")
        chat_field.value = ""
        page.update()

        def _work():
            _ui_call(lambda: _set_buttons_loading(True))
            try:
                # Update status: Retrieving content
                def _update_status_retrieve():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "📥 Retrieving content..."
                        page.update()
                _ui_call(_update_status_retrieve)
                
                # Use preloaded DocumentSummarizer
                _, _, _, DocumentSummarizer, _ = _get_preloaded_modules()
                summarizer = DocumentSummarizer(target_lang=lang_code)
                
                # Update status: Analyzing
                def _update_status_analyze():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "🔍 Analyzing content..."
                        page.update()
                _ui_call(_update_status_analyze)
                
                result = summarizer.rag_qa_website(url, question)
                
                # Update status: Generating answer
                def _update_status_generate():
                    if status_bubble in chat_list.controls:
                        status_bubble.controls[0].content.value = "✨ Generating answer..."
                        page.update()
                _ui_call(_update_status_generate)
                
                if result:
                    # Remove status bubble before adding result
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    # Use bot bubble with TTS support instead of result
                    _add_bubble_safe(result.get("summary", ""), "bot", lang=state.language)
                    
                    # Save to database
                    rag = get_rag_instance()
                    if RAG_AVAILABLE and rag and state.conversation_id:
                        try:
                            rag.save_bot_message(state.conversation_id, result.get("summary", ""))
                        except Exception as e:
                            print(f"⚠️ Failed to save bot message: {e}")
                else:
                    def _remove_status():
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                    _ui_call(_remove_status)
                    _add_bubble_safe("⚠️ Could not answer that question.", "status")
            except Exception as exc:
                def _remove_status():
                    if status_bubble in chat_list.controls:
                        chat_list.controls.remove(status_bubble)
                _ui_call(_remove_status)
                _add_bubble_safe(f"⚠️ {exc}", "status")
            finally:
                _ui_call(lambda: _set_buttons_loading(False))

        _run_in_thread(_work)

    doc_summarise_btn  = _action_btn("Summarize Document", ft.icons.AUTO_AWESOME_OUTLINED, on_doc_summarise)
    web_summarise_btn  = _action_btn("Summarize Website",  ft.icons.AUTO_AWESOME_OUTLINED,  on_web_summarise)

    def _refresh_summarise_btn():
        import os as _os
        _img_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
        _sel = selected_file[0] or ""
        _is_image = _os.path.splitext(_sel)[1].lower() in _img_exts

        has_input = (active_mode[0] == "document" and selected_file[0] is not None) or \
                    (active_mode[0] == "web" and url_valid[0])
        # Summarize buttons only enabled when there's valid input
        doc_summarise_btn.disabled = not has_input
        web_summarise_btn.disabled = not has_input
        # Update label to reflect image vs document
        doc_summarise_btn.text = "Summarize Image" if _is_image else "Summarize Document"
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
            form_panel,
            ft.Container(
                content=ft.Row(
                    [doc_summarise_btn, web_summarise_btn],
                    spacing=8,
                ),
                padding=ft.padding.only(top=4, bottom=8),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    # Panel container without loading overlay (using real-time status bubbles instead)
    panel_container = ft.Container(
        content=_panel_inner,
        bgcolor=PANEL_BG,
        border_radius=ft.border_radius.only(top_left=20, top_right=20),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        animate=ft.animation.Animation(250, ft.AnimationCurve.EASE_OUT),
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        visible=False,
    )

    _PANEL_OPEN_HEIGHT = 240  # height for document/image panel (drop zone + button)

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
        form_panel.visible = mode == "form"
        if mode is None:
            doc_summarise_btn.visible = False
            web_summarise_btn.visible = False
        else:
            doc_summarise_btn.visible = mode == "document"
            web_summarise_btn.visible = mode == "web"
            # Summarize disabled until valid input provided
            doc_summarise_btn.disabled = selected_file[0] is None
            web_summarise_btn.disabled = not url_valid[0]
        # Show/hide panel using height animation (no offset — avoids overlay issues)
        if mode is not None:
            panel_container.visible = True
            if mode == "form":
                panel_container.height = 120
            elif mode == "web":
                panel_container.height = 180
            else:
                panel_container.height = _PANEL_OPEN_HEIGHT
        else:
            # Reset form grid when closing
            _form_grid_wrapper.opacity = 0
            _form_grid_wrapper.height = 0
            _empty_state.visible = False
            _country_dropdown.value = None
            panel_container.height = 0
            def _hide():
                import time; time.sleep(0.26)
                panel_container.visible = False
                page.update()
            threading.Thread(target=_hide, daemon=True).start()
        # Update circle button active styling
        for btn_col, btn_mode in [(web_btn, "web"), (media_btn, "document"), (form_btn, "form")]:
            circle = btn_col.controls[0]
            circle.gradient = None if mode == btn_mode else _grad
            circle.bgcolor = ft.colors.with_opacity(0.25, accent) if mode == btn_mode else None
        page.update()

    # ------------------------------------------------------------------ #
    #  Chat bubble list                                                    #
    # ------------------------------------------------------------------ #

    BUBBLE_USER_BG   = accent
    BUBBLE_BOT_BG    = state.surface_color()
    BUBBLE_USER_FG   = ft.colors.WHITE
    BUBBLE_BOT_FG    = state.text_color()
    BUBBLE_STATUS_FG = ft.colors.with_opacity(0.6, state.text_color())
    
    # ------------------------------------------------------------------ #
    #  Sidebar - Conversation History                                     #
    # ------------------------------------------------------------------ #
    
    def load_conversations():
        """Load user's conversation history from database"""
        if not RAG_AVAILABLE or not rag or not state.user_id:
            return
        try:
            convos = rag.mysql.get_user_conversations(state.user_id)
            conversations_list.clear()
            conversations_list.extend(convos)
            refresh_sidebar()
        except Exception as e:
            print(f"⚠️ Failed to load conversations: {e}")
    
    def refresh_sidebar():
        """Refresh the sidebar conversation list"""
        sidebar_list.controls.clear()
        
        for convo in conversations_list:
            convo_id = convo.get('conversation_id')
            title = convo.get('title', 'Untitled Chat')
            created_at = convo.get('created_at', '')
            
            # Truncate title if too long
            display_title = title if len(title) <= 30 else title[:27] + "..."
            
            # Highlight active conversation
            is_active = convo_id == state.conversation_id
            
            convo_btn = ft.Container(
                content=ft.Column([
                    ft.Text(
                        display_title,
                        size=14,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                        color=accent if is_active else state.text_color(),
                    ),
                    ft.Text(
                        str(created_at)[:16] if created_at else "",
                        size=10,
                        color=ft.colors.GREY_500,
                    ),
                ], spacing=2, tight=True),
                padding=ft.padding.all(12),
                border_radius=8,
                bgcolor=ft.colors.with_opacity(0.1, accent) if is_active else None,
                on_click=lambda e, cid=convo_id: switch_conversation(cid),
                ink=True,
            )
            sidebar_list.controls.append(convo_btn)
        
        page.update()
    
    def switch_conversation(conversation_id: str):
        """Switch to a different conversation"""
        if conversation_id == state.conversation_id:
            return
        
        # Save current conversation_id
        state.conversation_id = conversation_id
        
        # Clear chat list
        chat_list.controls.clear()
        
        # Load conversation history
        if RAG_AVAILABLE and rag:
            try:
                messages = rag.get_conversation_history(conversation_id)
                for msg in messages:
                    sender = msg.get('sender', 'user')
                    text = msg.get('message_text', '')
                    
                    # Parse sources if they exist in the message
                    sources = []
                    if '\n\nReferences:\n' in text:
                        parts = text.split('\n\nReferences:\n')
                        text = parts[0]
                        if len(parts) > 1:
                            source_lines = parts[1].split('\n')
                            sources = [line.split('. ', 1)[1] if '. ' in line else line 
                                     for line in source_lines if line.strip()]
                    
                    role = "user" if sender == "user" else "bot"
                    _add_bubble(text, role, sources if sources else None)
            except Exception as e:
                print(f"⚠️ Failed to load conversation: {e}")
        
        refresh_sidebar()
        page.update()
    
    def create_new_chat():
        """Create a new conversation (only if current one has messages)"""
        if not RAG_AVAILABLE or not rag or not state.user_id:
            return
        
        # Check if current conversation is empty
        if state.conversation_id:
            try:
                messages = rag.get_conversation_history(state.conversation_id)
                if not messages or len(messages) == 0:
                    # Current conversation is empty, don't create a new one
                    print("⚠️ Current conversation is empty, not creating new chat")
                    return
            except Exception as e:
                print(f"⚠️ Failed to check conversation history: {e}")
        
        # Create new conversation
        new_convo_id = rag.create_conversation(
            user_id=state.user_id,
            title="New Chat"
        )
        
        if new_convo_id:
            state.conversation_id = new_convo_id
            chat_list.controls.clear()
            load_conversations()
            page.update()
            print(f"✅ Created new conversation: {new_convo_id}")
    
    # Resize handlers
    def on_resize_start(e):
        """Start resizing sidebar"""
        is_resizing[0] = True
    
    def on_resize_update(e: ft.DragUpdateEvent):
        """Update sidebar width while dragging"""
        if not is_resizing[0]:
            return
        
        # Calculate new width (minimum 200px, maximum 500px)
        new_width = sidebar_width[0] + e.delta_x
        new_width = max(200, min(500, new_width))
        
        sidebar_width[0] = new_width
        sidebar_container.width = new_width
        page.update()
    
    def on_resize_end(e):
        """End resizing sidebar"""
        is_resizing[0] = False
    
    # Resize handle (draggable divider)
    resize_handle = ft.GestureDetector(
        content=ft.Container(
            width=8,
            bgcolor=ft.colors.TRANSPARENT,
            border=ft.border.only(left=ft.BorderSide(2, ft.colors.with_opacity(0.3, accent))),
            expand=True,
        ),
        on_pan_start=on_resize_start,
        on_pan_update=on_resize_update,
        on_pan_end=on_resize_end,
        mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
    )
    
    # Sidebar list container
    sidebar_list = ft.Column(
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    
    # Store sidebar_with_handle reference in a list so it can be accessed before definition
    sidebar_with_handle_ref = [None]
    
    # Define toggle function that will be used by buttons
    def toggle_sidebar():
        """Toggle sidebar visibility"""
        sidebar_visible[0] = not sidebar_visible[0]
        if sidebar_with_handle_ref[0]:
            sidebar_with_handle_ref[0].visible = sidebar_visible[0]
        page.update()
    
    # Sidebar container
    sidebar_container = ft.Container(
        content=ft.Column([
            # Header with close button
            ft.Row([
                ft.Text(
                    "Conversations",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=state.text_color(),
                ),
                ft.IconButton(
                    icon=ft.icons.CLOSE,
                    icon_color=state.text_color(),
                    on_click=lambda _: toggle_sidebar(),
                    tooltip="Close",
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            # New Chat button
            ft.Container(
                content=ft.ElevatedButton(
                    "➕ New Chat",
                    on_click=lambda _: create_new_chat(),
                    style=ft.ButtonStyle(
                        bgcolor=accent,
                        color=ft.colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
                width=None,
            ),
            
            ft.Divider(height=1, color=ft.colors.with_opacity(0.2, state.text_color())),
            
            # Conversation list
            ft.Container(
                content=sidebar_list,
                expand=True,
            ),
        ], spacing=12, expand=True),
        width=280,
        padding=ft.padding.all(16),
        bgcolor=state.surface_color(),
    )
    
    # Sidebar with resize handle
    sidebar_with_handle = ft.Row(
        [sidebar_container, resize_handle],
        spacing=0,
        visible=False
    )
    
    # Store reference for toggle function
    sidebar_with_handle_ref[0] = sidebar_with_handle
    
    # Load conversations on startup
    if RAG_AVAILABLE and rag and state.user_id:
        threading.Thread(target=load_conversations, daemon=True).start()

    chat_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        auto_scroll=True,
    )

    def _add_bubble(text: str, role: str = "bot", sources: list = None, lang: str = None):
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
                border_radius=ft.border_radius.only(top_left=16, top_right=4, bottom_left=16, bottom_right=16),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            icon = ft.Icon(ft.icons.PERSON_ROUNDED, color=ft.colors.with_opacity(0.7, accent), size=18)
            bubble = ft.Row(
                [ft.Container(expand=True), content, icon],
                alignment=ft.MainAxisAlignment.END,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=6,
            )

        elif role == "result":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_USER_FG, size=state.font_sp(), selectable=True),
                gradient=_grad,
                border_radius=ft.border_radius.only(top_left=16, top_right=4, bottom_left=16, bottom_right=16),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                expand=True,
            )
            icon = ft.Icon(ft.icons.ARTICLE_OUTLINED, color=ft.colors.with_opacity(0.7, accent), size=18)
            bubble = ft.Row(
                [ft.Container(expand=True), content, icon],
                alignment=ft.MainAxisAlignment.END,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=6,
            )

        elif role == "status":
            content = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.SYNC_ROUNDED, color=accent, size=13),
                        ft.Text(
                            text,
                            color=BUBBLE_STATUS_FG,
                            size=state.font_sp() - 2,
                            italic=True,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    spacing=6,
                    tight=True,
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
                        import re as _re

                        # Strip summary/result header lines before speaking
                        # e.g. "🌐 Website Summary  •  1,196→25 words (98% reduction)\n\nHere is your summary:\n\n"
                        _tts_text = _re.sub(
                            r'^[^\n]*(?:Summary|Result|Reduction|reduction|summary)[^\n]*\n+(?:Here is[^\n]*\n+)?',
                            '', text, flags=_re.IGNORECASE
                        ).strip() or text

                        # Validate text
                        if not _tts_text or not _tts_text.strip():
                            raise ValueError("No text to speak")
                        
                        # Initialize pygame mixer if not already
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        
                        # Generate TTS audio file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        audio_file[0] = temp_file.name
                        temp_file.close()
                        
                        # Generate audio using speak_answer with country-aware voice
                        async def generate_audio():
                            from engine.speech.text_to_speech import VOICE_MATRIX
                            from engine.speech.language_voice_mapping import get_voices_for_language
                            country_code = _COUNTRY_CODE_MAP.get(state.country, "DEFAULT")
                            _LANG_TO_ISO = {
                                "English": "en",
                                "Bahasa Melayu": "ms", "Malay": "ms",
                                "Bahasa Indonesia": "id", "Indonesian": "id",
                                "Thai": "th",
                                "Vietnamese": "vi",
                                "Filipino/Tagalog": "tl", "Filipino": "tl", "Tagalog": "tl",
                                "Chinese (Simplified)": "zh",
                                "Tamil": "ta",
                                "Burmese": "my",
                                "Khmer": "km",
                                "Lao": "lo",
                            }
                            # Prefer the language the response was actually generated in (passed via
                            # lang param), fall back to the user's profile language.
                            _effective_lang = lang or state.language
                            lang_iso = _LANG_TO_ISO.get(_effective_lang, "en")
                            country_voices = VOICE_MATRIX.get(country_code, VOICE_MATRIX["DEFAULT"])
                            if isinstance(country_voices, str):
                                voice = country_voices
                            else:
                                voice = country_voices.get(lang_iso)
                                if not voice:
                                    # Country matrix doesn't have this language — use language_voice_mapping
                                    _ISO_TO_LANG = {v: k for k, v in _LANG_TO_ISO.items() if k in [
                                        "English", "Bahasa Melayu", "Bahasa Indonesia", "Thai",
                                        "Vietnamese", "Filipino/Tagalog", "Chinese (Simplified)",
                                        "Tamil", "Burmese", "Khmer", "Lao",
                                    ]}
                                    lang_name = _ISO_TO_LANG.get(lang_iso, "English")
                                    mapped = get_voices_for_language(lang_name)
                                    voice = mapped[0] if mapped else VOICE_MATRIX["DEFAULT"]
                            print(f"🎤 Voice selected: {voice} (lang_iso={lang_iso}, effective_lang={_effective_lang})")
                            last_error = None
                            for v in [voice, "en-US-AriaNeural"]:
                                try:
                                    communicate = edge_tts.Communicate(_tts_text, v)
                                    await communicate.save(audio_file[0])
                                    print(f"✅ TTS generated with voice: {v}")
                                    return
                                except Exception as e:
                                    last_error = e
                                    print(f"⚠️ Voice {v} failed: {e}")
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
                ft.Container(height=6),
                speaker_btn,
            ]

            # Add sources if provided
            if sources and len(sources) > 0:
                bubble_content.append(ft.Divider(height=8, color=ft.colors.with_opacity(0.1, accent)))
                bubble_content.append(
                    ft.Row(
                        [
                            ft.Icon(ft.icons.LINK_ROUNDED, color=accent, size=14),
                            ft.Text("Sources", color=BUBBLE_BOT_FG, size=state.font_sp() - 2,
                                    weight=ft.FontWeight.W_600),
                        ],
                        spacing=4,
                    )
                )
                for i, source in enumerate(sources, 1):
                    bubble_content.append(
                        ft.Row(
                            [
                                ft.Text(f"{i}.", color=ft.colors.with_opacity(0.5, accent),
                                        size=state.font_sp() - 2),
                                ft.Text(source, color=accent, size=state.font_sp() - 2,
                                        selectable=True,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=4,
                        )
                    )

            # Bot avatar + bubble layout
            avatar = ft.Container(
                content=ft.Icon(ft.icons.SMART_TOY_ROUNDED, color=ft.colors.WHITE, size=16),
                width=30, height=30,
                border_radius=15,
                gradient=_grad,
                alignment=ft.alignment.center,
            )

            content = ft.Container(
                content=ft.Column(bubble_content, spacing=4, tight=True),
                bgcolor=BUBBLE_BOT_BG,
                border_radius=ft.border_radius.only(top_left=4, top_right=16, bottom_left=16, bottom_right=16),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                expand=True,
                border=ft.border.all(1, ft.colors.with_opacity(0.12, accent)),
            )
            bubble = ft.Row(
                [avatar, content],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=8,
                expand=True,
            )

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

        # Form-filling session takes priority — just unblock the waiting session loop
        if _form_filling[0] and _form_ai[0] is not None:
            _add_bubble(msg, "user")
            chat_field.value = ""
            page.update()
            _form_ai[0].submit_answer(msg)
            return

        # Awaiting confirmation after form summary
        if _form_confirming[0]:
            _add_bubble(msg, "user")
            chat_field.value = ""
            page.update()
            _yes = any(w in msg.lower() for w in _IV_YES_WORDS)
            if _yes:
                _form_confirming[0] = False
                _sig_points.clear()
                _form_sig_path[0] = None
                sig_modal.open = True
                page.update()
            else:
                _form_confirming[0] = False
                _form_ai[0] = None
                _add_bubble("No problem — the form has been discarded. You can start again anytime.", "bot")
                page.update()
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
            status_bubble = _add_bubble("🔍 Searching knowledge base...", "status")
            chat_field.value = ""
            mic_icon.name = ft.icons.MIC_ROUNDED
            page.update()
            
            # Save user message to database
            rag = get_rag_instance()
            if RAG_AVAILABLE and rag and state.conversation_id:
                try:
                    rag.save_user_message(state.conversation_id, msg)
                    
                    # Update conversation title if this is the first message
                    messages = rag.get_conversation_history(state.conversation_id)
                    if messages and len(messages) == 1:  # Only user message exists
                        # Generate title from first message (max 50 chars)
                        title = msg[:50] + "..." if len(msg) > 50 else msg
                        rag.update_conversation_title(state.conversation_id, title)
                        # Reload conversations to show updated title
                        load_conversations()
                        page.update()
                        
                except Exception as e:
                    print(f"⚠️ Failed to save user message: {e}")
            
            def _process_text_question():
                try:
                    # Update status: Analyzing question
                    def _update_status_analyze():
                        if status_bubble in chat_list.controls:
                            status_bubble.controls[0].content.value = "🤔 Analyzing question..."
                            page.update()
                    _ui_call(_update_status_analyze)
                    
                    # Use preloaded modules
                    _, process_voice_result, _, _, _ = _get_preloaded_modules()
                    
                    # Update status: Retrieving information
                    def _update_status_retrieve():
                        if status_bubble in chat_list.controls:
                            status_bubble.controls[0].content.value = "📚 Retrieving information..."
                            page.update()
                    _ui_call(_update_status_retrieve)
                    
                    # Process the question with user's country and language preferences
                    print(f"Processing text question: {msg}")
                    print(f"User country: {state.country}, User language: {state.language}")

                    # Translate query to English for search if input is non-English
                    search_query = msg
                    try:
                        from fast_langdetect import detect as _fld
                        _res = _fld(msg.lower())
                        _iso = (_res[0].get("lang") if isinstance(_res, list) else _res.get("lang", "en")).lower()
                        if _iso != "en":
                            from engine.insert_doc.translate import translate as _tl
                            _translated = _tl(msg, "English")
                            if _translated and _translated.strip():
                                search_query = _translated
                                print(f"[home] Query translated: '{msg}' -> '{search_query}'")
                    except Exception as _e:
                        print(f"[home] Query detection/translation skipped: {_e}")
                    
                    # Update status: Generating answer
                    def _update_status_generate():
                        if status_bubble in chat_list.controls:
                            status_bubble.controls[0].content.value = "✨ Generating answer..."
                            page.update()
                    _ui_call(_update_status_generate)
                    
                    response = process_voice_result(
                        dialect="en",
                        question=msg,        # original language — used for response language detection
                        query=search_query,  # English — used for SerpAPI search
                        country=state.country,
                        language=state.language
                    )
                    print(f"Got response: {response}")
                    
                    # Update UI with response
                    def _show_response():
                        # Remove status bubble
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
                        
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
                        if status_bubble in chat_list.controls:
                            chat_list.controls.remove(status_bubble)
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
        elif _form_filling[0]:
            # Form-filling mode: capture raw audio for Whisper transcription
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
                        text = transcribe_audio(tmp_path, normalize_to_question=False, country=state.country or "Malaysia") if transcribe_audio else ""
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

        elif _form_filling[0]:
            # Stop the form-mode stream first
            sd_stream = _search_sd_stream[0]
            if sd_stream:
                sd_stream.stop()
                sd_stream.close()
                _search_sd_stream[0] = None

            # ── Form-filling mode: transcribe and submit as form answer ──
            def _form_transcribe():
                import numpy as np
                import soundfile as sf
                import tempfile, os

                def _set_processing():
                    is_processing[0] = True
                    chat_field.hint_text = "Transcribing..."
                    mic_icon.name = ft.icons.STOP_ROUNDED
                    mic_circle.gradient = None
                    mic_circle.bgcolor = ft.colors.GREY_400
                    page.update()
                _ui_call(_set_processing)

                try:
                    # Capture via sounddevice (same path as document/web mode)
                    text = ""
                    if _search_audio_chunks:
                        audio_np = np.concatenate(_search_audio_chunks, axis=0).flatten()
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                            tmp_path = f.name
                        sf.write(tmp_path, audio_np, 16000)
                        _, _, _, _, transcribe_audio = _get_preloaded_modules()
                        text = transcribe_audio(tmp_path, normalize_to_question=False, country=state.country or "Malaysia") if transcribe_audio else ""
                        os.remove(tmp_path)

                    def _done(t=text):
                        is_processing[0] = False
                        chat_field.hint_text = "Ask a question..."
                        mic_icon.name = ft.icons.MIC_ROUNDED
                        mic_circle.gradient = _grad
                        mic_circle.bgcolor = None
                        if t:
                            _add_bubble(t, "user")
                            chat_field.value = ""
                        page.update()
                        if t:
                            ai = _form_ai[0]
                            if ai:
                                ai.submit_answer(t)
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

            threading.Thread(target=_form_transcribe, daemon=True).start()

        else:
            stream.stop()

            def process():
                session.stop_recording()
                results = session.results

                dialect = results.get("dialect")
                question = results.get("question")   # English-normalized (used as query fallback)
                query = results.get("query")
                transcript = results.get("transcript") or question  # original language text

                # Add status indicator
                status_bubble = [None]
                
                def set_processing():
                    is_processing[0] = True
                    chat_field.hint_text = "Processing..."
                    mic_icon.name = ft.icons.STOP_ROUNDED
                    mic_circle.gradient = None
                    mic_circle.bgcolor = ft.colors.GREY_400
                    
                    # Show original transcript (user's language) in the bubble
                    if transcript:
                        _add_bubble(transcript, "user")
                    # Add status indicator with real-time updates
                    status_bubble[0] = _add_bubble("🔍 Searching knowledge base...", "status")
                    page.update()

                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(set_processing)
                else:
                    set_processing()

                # Update status: Analyzing question
                def update_status_analyze():
                    if status_bubble[0] and status_bubble[0] in chat_list.controls:
                        status_bubble[0].controls[0].content.value = "🤔 Analyzing question..."
                        page.update()
                
                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_status_analyze)
                else:
                    update_status_analyze()

                # ✅ CALL YOUR MAIN LOGIC HERE - Use preloaded modules
                _, process_voice_result, speak_answer, _, _ = _get_preloaded_modules()
                
                # Update status: Retrieving information
                def update_status_retrieve():
                    if status_bubble[0] and status_bubble[0] in chat_list.controls:
                        status_bubble[0].controls[0].content.value = "📚 Retrieving information..."
                        page.update()
                
                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_status_retrieve)
                else:
                    update_status_retrieve()
                
                # Update status: Generating answer
                def update_status_generate():
                    if status_bubble[0] and status_bubble[0] in chat_list.controls:
                        status_bubble[0].controls[0].content.value = "✨ Generating answer..."
                        page.update()
                
                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_status_generate)
                else:
                    update_status_generate()
                
                response = process_voice_result(
                    dialect=dialect,
                    question=transcript,  # original language — drives response language detection
                    query=query,          # English keywords — drives SerpAPI search
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

                    # Remove status bubble
                    if status_bubble[0] and status_bubble[0] in chat_list.controls:
                        chat_list.controls.remove(status_bubble[0])

                    if response:
                        _show_result_card(response)

                    print("Dialect:", dialect)
                    print("Transcript:", transcript)
                    print("Query:", query)
                    print("Response:", response)

                    page.update()

                if hasattr(page, "call_from_thread"):
                    page.call_from_thread(update_ui)
                else:
                    update_ui()
                # TTS is manual — user clicks 'Listen' on the bot bubble

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
            lang = payload.get("language")  # language the response was generated in
            _add_bubble(text, "bot", sources, lang=lang)
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

    def _add_bubble_safe(text: str, role: str = "bot", sources: list = None, lang: str = None):
        def _do():
            _add_bubble(text, role, sources, lang=lang)
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
                    [web_btn, media_btn, form_btn],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
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
        title=ft.Row(
            [
                ft.Icon(ft.icons.CHAT_BUBBLE_OUTLINE_ROUNDED, color=accent, size=20),
                ft.Text(
                    "Bridge",
                    color=state.text_color(),
                    size=state.font_sp() + 2,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        bgcolor=ft.colors.TRANSPARENT,
        center_title=True,
        leading=ft.IconButton(
            icon=ft.icons.MENU,
            icon_color=state.text_color(),
            on_click=lambda _: toggle_sidebar(),
            tooltip="Conversations",
        ),
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

    # ------------------------------------------------------------------ #
    #  Signature modal                                                     #
    # ------------------------------------------------------------------ #

    _sig_points: list = []       # list of (x, y) or None (pen-up)
    _sig_drawing: list = [False]

    sig_canvas = ft.GestureDetector(
        content=ft.Container(
            width=400,
            height=200,
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, accent),
            border_radius=8,
        ),
    )

    sig_canvas_stack = ft.Stack(
        [sig_canvas],
        width=400,
        height=200,
    )

    def _sig_on_pan_start(e: ft.DragStartEvent):
        _sig_points.append((e.local_x, e.local_y))
        _sig_drawing[0] = True

    def _sig_on_pan_update(e: ft.DragUpdateEvent):
        if _sig_drawing[0]:
            _sig_points.append((e.local_x, e.local_y))
            _redraw_sig()

    def _sig_on_pan_end(e: ft.DragEndEvent):
        _sig_points.append(None)  # pen-up marker
        _sig_drawing[0] = False

    sig_canvas.on_pan_start  = _sig_on_pan_start
    sig_canvas.on_pan_update = _sig_on_pan_update
    sig_canvas.on_pan_end    = _sig_on_pan_end

    def _redraw_sig():
        shapes = []
        prev = None
        for pt in _sig_points:
            if pt is None:
                prev = None
                continue
            if prev is not None:
                shapes.append(
                    ft.canvas.Line(
                        prev[0], prev[1], pt[0], pt[1],
                        paint=ft.Paint(color=ft.colors.BLACK, stroke_width=2),
                    )
                )
            prev = pt
        # Replace canvas content with drawn lines
        sig_canvas.content = ft.canvas.Canvas(
            shapes=shapes,
            width=400,
            height=200,
        )
        page.update()

    def _sig_clear(_):
        _sig_points.clear()
        sig_canvas.content = ft.Container(
            width=400, height=200,
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, accent),
            border_radius=8,
        )
        page.update()

    def _sig_save(_):
        import tempfile, os
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (400, 200), (255, 255, 255, 0))  # transparent bg
            draw = ImageDraw.Draw(img)
            prev = None
            for pt in _sig_points:
                if pt is None:
                    prev = None
                    continue
                if prev is not None:
                    draw.line([prev, pt], fill=(0, 0, 0, 255), width=2)
                prev = pt
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            _form_sig_path[0] = tmp.name
            _iv_sig_path[0] = tmp.name
            print(f"[signature] Saved → {tmp.name}")
        except Exception as e:
            print(f"[signature] Error saving: {e}")
            _form_sig_path[0] = None
            _iv_sig_path[0] = None

        sig_modal.open = False
        _sig_points.clear()
        sig_canvas.content = ft.Container(
            width=400, height=200,
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, accent),
            border_radius=8,
        )
        page.update()
        # Route to the correct write function depending on which flow is active
        if _iv_entry[0] is not None:
            _iv_do_write_pdf()
        else:
            _do_write_pdf()

    sig_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please sign below", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            [
                ft.Text("Draw your signature in the box:", size=12),
                ft.Container(
                    content=sig_canvas,
                    width=400,
                    height=200,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            tight=True,
            spacing=8,
        ),
        actions=[
            ft.TextButton("Clear", on_click=_sig_clear),
            ft.TextButton("Skip", on_click=lambda _: (
                setattr(sig_modal, 'open', False),
                page.update(),
                _iv_do_write_pdf() if _iv_entry[0] is not None else _do_write_pdf(),
            )),
            ft.ElevatedButton(
                "Save & Continue",
                on_click=_sig_save,
                style=ft.ButtonStyle(bgcolor=accent, color=ft.colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # ------------------------------------------------------------------ #
    #  PDF preview / download modal + helpers                             #
    # ------------------------------------------------------------------ #
    _pdf_out_path: list = [None]

    def _sanitise(s: str) -> str:
        import re
        return re.sub(r'[^\w\s-]', '', s).strip().replace(' ', '_')

    def _trigger_pdf_download():
        src = _pdf_out_path[0]
        if not src:
            return
        save_picker.save_file(
            dialog_title="Save PDF",
            file_name=os.path.basename(src),
            allowed_extensions=["pdf"],
        )

    def _on_save_result(e: ft.FilePickerResultEvent):
        import shutil
        src = _pdf_out_path[0]
        if not e.path or not src:
            return
        try:
            shutil.copy2(src, e.path)
            def _ok():
                pdf_preview_modal.open = False
                page.update()
                _run_in_thread(_show_success_overlay)
                # Clean up temp JSON schema created by document_manager.process_pdf
                schema = _iv_schema_to_delete[0]
                if schema and os.path.exists(schema):
                    try:
                        os.remove(schema)
                        print(f"[cleanup] Deleted temp schema: {schema}")
                    except Exception as ex:
                        print(f"[cleanup] Could not delete schema: {ex}")
                    _iv_schema_to_delete[0] = None
            _ui_call(_ok)
        except Exception as exc:
            _ui_call(lambda: (_add_bubble(f"⚠️ Save failed: {exc}", "status"), page.update()))

    save_picker = ft.FilePicker(on_result=_on_save_result)

    pdf_preview_modal = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.icons.PICTURE_AS_PDF, color=ft.colors.RED_400, size=22),
                ft.Text("PDF Ready", weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
        content=ft.Column(
            [
                ft.Text("Your form has been filled successfully.", size=13),
                ft.Text("", size=11, color=ft.colors.GREY_500, selectable=True),
            ],
            tight=True,
            spacing=6,
            width=380,
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda _: (
                    setattr(pdf_preview_modal, 'open', False),
                    page.update(),
                ),
            ),
            ft.ElevatedButton(
                "Download",
                icon=ft.icons.DOWNLOAD,
                on_click=lambda _: _trigger_pdf_download(),
                style=ft.ButtonStyle(bgcolor=accent, color=ft.colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # ------------------------------------------------------------------ #
    #  PDF success overlay (blur + checkmark, auto-fades)                 #
    # ------------------------------------------------------------------ #
    #  PDF success overlay (blur + checkmark, pop-in/pop-out)             #
    # ------------------------------------------------------------------ #
    _overlay_icon = ft.Icon(
        ft.icons.CHECK_CIRCLE_ROUNDED,
        color=ft.colors.with_opacity(0.0, ft.colors.GREEN_400),
        size=0,
    )
    _overlay_card = ft.Container(
        width=0,
        height=0,
        border_radius=999,
        bgcolor=ft.colors.with_opacity(0.18, ft.colors.WHITE),
        alignment=ft.alignment.center,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=32,
            color=ft.colors.with_opacity(0.35, ft.colors.WHITE),
            offset=ft.Offset(0, 0),
        ),
        content=_overlay_icon,
    )
    _success_overlay = ft.Container(
        visible=False,
        expand=True,
        bgcolor=ft.colors.with_opacity(0.0, "#000000"),
        alignment=ft.alignment.center,
        content=_overlay_card,
    )

    def _show_success_overlay():
        import time, math

        TARGET_CARD = 140
        TARGET_ICON = 80

        def _frame(card_sz, icon_sz, bg_op, icon_op):
            _overlay_card.width        = card_sz
            _overlay_card.height       = card_sz
            _overlay_card.border_radius = card_sz / 2
            _overlay_icon.size         = icon_sz
            _overlay_icon.color        = ft.colors.with_opacity(icon_op, ft.colors.GREEN_400)
            _success_overlay.bgcolor   = ft.colors.with_opacity(bg_op, "#000000")
            page.update()

        _success_overlay.visible = True
        page.update()

        # — pop in: scale 0 → 110% over 12 frames (~0.22s)
        POP_IN = 12
        for i in range(1, POP_IN + 1):
            t = i / POP_IN
            # ease-out cubic
            e = 1 - (1 - t) ** 3
            scale = e * 1.10
            _ui_call(lambda s=scale: _frame(
                TARGET_CARD * s, TARGET_ICON * s,
                min(t * 0.6, 0.55), min(t * 1.2, 1.0),
            ))
            time.sleep(0.018)

        # — settle: 110% → 100% over 5 frames
        SETTLE = 5
        for i in range(1, SETTLE + 1):
            t = i / SETTLE
            scale = 1.10 - 0.10 * t
            _ui_call(lambda s=scale: _frame(
                TARGET_CARD * s, TARGET_ICON * s, 0.55, 1.0,
            ))
            time.sleep(0.018)

        # — hold 2 s
        time.sleep(2.0)

        # — pop out: scale 100% → 0, fade bg over 14 frames (~0.25s)
        POP_OUT = 14
        for i in range(1, POP_OUT + 1):
            t = i / POP_OUT
            e = t ** 2          # ease-in quad
            scale = max(1.0 - e, 0)
            bg_op = max(0.55 * (1 - t), 0)
            icon_op = max(1.0 - t * 1.5, 0)
            _ui_call(lambda s=scale, b=bg_op, io=icon_op: _frame(
                TARGET_CARD * s, TARGET_ICON * s, b, io,
            ))
            time.sleep(0.018)

        def _hide():
            _success_overlay.visible = False
            _overlay_card.width  = 0
            _overlay_card.height = 0
            _overlay_icon.size   = 0
            page.update()
        _ui_call(_hide)

    def _do_write_pdf():
        ai    = _form_ai[0]
        entry = _form_map_entry[0]
        sig   = _form_sig_path[0]
        _form_ai[0] = None
        print(f"[_do_write_pdf] ai={ai} sig={sig} entry={entry}")

        def _write():
            try:
                from engine.insert_doc.write_doc import fill_pdf
                schema_path = entry.get("schema_file", "")
                pdf_path    = entry.get("pdf_file", "")
                if not schema_path or not pdf_path:
                    _ui_call(lambda: (_add_bubble("⚠️ No PDF template configured.", "status"), page.update()))
                    return

                # Build dynamic filename: [form_name]_[User_Name].pdf
                form_name  = _sanitise(_form_name[0] or "form")
                user_name  = _sanitise(
                    next((v for k, v in ai.responses.items() if "nama" in k.lower() and "bank" not in k.lower() and "pegawai" not in k.lower()), "")
                    or "user"
                )
                import os as _os
                out_dir  = _os.path.dirname(pdf_path)
                out_path = _os.path.join(out_dir, f"{form_name}_{user_name}.pdf")

                out = fill_pdf(
                    ai.responses, schema_path, pdf_path,
                    output_path=out_path,
                    input_bboxes=ai._input_bboxes,
                    signature_path=sig,
                )

                def _ok():
                    _pdf_out_path[0] = out
                    pdf_preview_modal.content.controls[1].value = out
                    pdf_preview_modal.open = True
                    page.update()
                    _run_in_thread(_show_success_overlay)
                _ui_call(_ok)
            except Exception as exc:
                def _err():
                    _add_bubble(f"⚠️ Failed to write PDF: {exc}", "status")
                    page.update()
                _ui_call(_err)

        _run_in_thread(_write)

    # ------------------------------------------------------------------ #
    #  Interview Modal — centered Card UI                                 #
    # ------------------------------------------------------------------ #

    # ── Question card (center of modal) ──────────────────────────────────
    _iv_question_text = ft.Text(
        "",
        size=state.font_sp() + 4,
        weight=ft.FontWeight.W_600,
        color=state.text_color(),
        text_align=ft.TextAlign.CENTER,
        no_wrap=False,
    )

    # ── Listen button (defined here so it can be embedded in the card) ───
    _iv_tts_playing:  list = [False]
    _iv_tts_loading:  list = [False]
    _iv_tts_paused:   list = [False]
    _iv_tts_audio:    list = [None]

    _iv_listen_btn = ft.TextButton(
        text="🔊 Listen",
        style=ft.ButtonStyle(
            color=accent,
            bgcolor=ft.colors.with_opacity(0.08, accent),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    _iv_help_icon = ft.Icon(ft.icons.HELP_OUTLINE_ROUNDED, color=accent, size=32)

    _iv_question_card = ft.Container(
        content=ft.Stack(
            [
                # ── Question content centred in the card ──────────────
                ft.Container(
                    content=ft.Column(
                        [
                            _iv_help_icon,
                            _iv_question_text,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=ft.padding.only(bottom=36),  # room for listen btn
                ),
                # ── Listen button pinned bottom-left ──────────────────
                ft.Container(
                    content=_iv_listen_btn,
                    alignment=ft.alignment.bottom_left,
                    left=0,
                    bottom=0,
                ),
            ],
            expand=True,
        ),
        width=420,
        height=220,
        border_radius=20,
        bgcolor=state.surface_color(),
        border=ft.border.all(2, accent),
        padding=ft.padding.symmetric(horizontal=16, vertical=16),
        shadow=ft.BoxShadow(
            blur_radius=24,
            spread_radius=0,
            color=ft.colors.with_opacity(0.10, "#000000"),
            offset=ft.Offset(0, 6),
        ),
        animate=ft.animation.Animation(250, ft.AnimationCurve.EASE_OUT),
    )

    # ── Last answer echo + status line ───────────────────────────────────
    _iv_last_answer_text = ft.Text(
        "",
        size=state.font_sp() - 1,
        color=ft.colors.with_opacity(0.6, state.text_color()),
        text_align=ft.TextAlign.CENTER,
        italic=True,
    )

    _iv_status_text = ft.Text(
        "",
        size=state.font_sp() - 2,
        color=accent,
        text_align=ft.TextAlign.CENTER,
        weight=ft.FontWeight.W_500,
    )

    _interview_progress_text = ft.Text(
        "",
        size=state.font_sp() - 2,
        color=ft.colors.with_opacity(0.45, state.text_color()),
        text_align=ft.TextAlign.CENTER,
    )

    _interview_title = ft.Text(
        "Interview",
        size=state.font_sp() + 2,
        weight=ft.FontWeight.BOLD,
        color=state.text_color(),
    )

    _interview_field = ft.TextField(
        hint_text="Type your answer...",
        expand=True,
        min_lines=1,
        max_lines=3,
        border_color=ft.colors.TRANSPARENT,
        bgcolor=ft.colors.TRANSPARENT,
        color=state.text_color(),
        hint_style=ft.TextStyle(color=ft.colors.with_opacity(0.45, state.text_color()), size=state.font_sp()),
        content_padding=ft.padding.symmetric(horizontal=8, vertical=14),
        text_align=ft.TextAlign.CENTER,
    )

    _interview_mic_icon = ft.Icon(ft.icons.MIC_ROUNDED, color=ft.colors.WHITE, size=22)
    _interview_mic_circle = ft.Container(
        content=_interview_mic_icon,
        width=48,
        height=48,
        border_radius=24,
        gradient=_grad,
        alignment=ft.alignment.center,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    # State for the interview modal session
    _iv_ai: list = [None]
    _iv_entry: list = [None]
    _iv_filling: list = [False]
    _iv_confirming: list = [False]
    _iv_editing: list = [False]        # True while user is picking a field to edit
    _iv_edit_key: list = [None]        # label key of the field being re-answered
    _iv_sig_path: list = [None]
    _iv_user_lang: list = ["English"]  # persists user language even after _iv_ai is cleared
    _iv_responses: list = [None]       # persists ai.responses after _iv_ai is cleared
    _iv_input_bboxes: list = [None]    # persists ai._input_bboxes after _iv_ai is cleared
    _iv_schema_to_delete: list = [None]
    _iv_audio_chunks: list = []
    _iv_sd_stream: list = [None]
    _iv_is_recording: list = [False]
    _iv_is_processing: list = [False]

    def _iv_set_question(text: str):
        """Update the centered question card and clear the previous answer."""
        _iv_question_text.value = text
        _iv_question_text.size = state.font_sp() + 4
        _iv_help_icon.visible = True
        _iv_question_card.border = ft.border.all(2, accent)
        _iv_last_answer_text.value = ""
        _iv_status_text.value = ""
        _interview_field.value = ""
        # Stop any ongoing TTS and reset the listen button
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        _iv_tts_playing[0] = False
        _iv_tts_loading[0] = False
        _iv_tts_paused[0] = False
        _iv_listen_btn.text = "🔊 Listen"
        _iv_listen_btn.disabled = False
        page.update()

    def _iv_set_status(text: str):
        """Show a status/info line below the card (replaces last-answer echo)."""
        _iv_status_text.value = text
        _iv_last_answer_text.value = ""
        page.update()

    def _iv_echo_answer(text: str):
        """Show the user's last answer below the card."""
        _iv_last_answer_text.value = text
        _iv_status_text.value = ""
        page.update()

    # Legacy helper kept so existing call-sites (_iv_run_session etc.) still work.
    # "bot" → updates question card; "user" → echoes answer; "status" → status line.
    def _iv_add_bubble(text: str, role: str = "bot"):
        if role == "user":
            _iv_echo_answer(text)
        elif role == "status":
            _iv_set_status(text)
        else:
            _iv_set_question(text)

    def _iv_close_modal():
        """Close the interview modal and clean up session state."""
        interview_modal.open = False
        _iv_ai[0] = None
        _iv_entry[0] = None
        _iv_filling[0] = False
        _iv_confirming[0] = False
        _iv_editing[0] = False
        _iv_edit_key[0] = None
        _iv_sig_path[0] = None
        _iv_user_lang[0] = "English"
        _iv_responses[0] = None
        _iv_input_bboxes[0] = None
        _iv_question_text.value = ""
        _iv_question_text.size = state.font_sp() + 4
        _iv_help_icon.visible = True
        _iv_last_answer_text.value = ""
        _iv_status_text.value = ""
        _interview_progress_text.value = ""
        _iv_lang_screen.visible = True
        _iv_qa_screen.visible = False
        # Restore card to original Stack layout in case edit picker replaced it
        _iv_question_card.content = ft.Stack(
            [
                ft.Container(
                    content=ft.Column(
                        [_iv_help_icon, _iv_question_text],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=ft.padding.only(bottom=36),
                ),
                ft.Container(
                    content=_iv_listen_btn,
                    alignment=ft.alignment.bottom_left,
                    left=0, bottom=0,
                ),
            ],
            expand=True,
        )
        _iv_question_card.height = 220
        _iv_question_card.border = ft.border.all(2, accent)
        page.update()

    def _iv_ui_t(phrase: str, language: str) -> str:
        """Translate a short UI phrase into the user's language. English is returned as-is."""
        if not language or language.lower() in ("english", "en"):
            return phrase
        from engine.insert_doc.translate import translate as _t
        return _t(phrase, language)

    def _iv_show_edit_picker():
        """Replace the card content with a scrollable list of answered fields to edit."""
        ai = _iv_ai[0]
        if not ai:
            return

        _iv_editing[0] = True   # picker is active
        _iv_edit_key[0] = None  # no specific field selected yet

        # Persist responses now — _iv_ai may be cleared before PDF is written
        _iv_responses[0] = dict(ai.responses)
        _iv_input_bboxes[0] = dict(ai._input_bboxes)

        def _pick(key):
            """User tapped a field chip — pre-fill the input and switch to edit mode."""
            _iv_editing[0] = True
            _iv_edit_key[0] = key
            current_val = ai.responses.get(key, "")
            _iv_help_icon.visible = False
            _iv_question_card.border = ft.border.all(2, ft.colors.ORANGE_400)
            _iv_last_answer_text.value = ""
            _iv_status_text.value = ""
            _interview_field.value = current_val
            _interview_field.read_only = False
            _interview_progress_text.value = ""
            # Replace card content with a clean editing indicator
            _iv_question_card.content = ft.Container(
                alignment=ft.alignment.center,
                expand=True,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.EDIT_ROUNDED, color=ft.colors.ORANGE_400, size=16),
                                ft.Text(
                                    "Editing",
                                    size=state.font_sp() - 2,
                                    color=ft.colors.ORANGE_400,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            key,
                            size=state.font_sp() + 1,
                            weight=ft.FontWeight.BOLD,
                            color=state.text_color(),
                            text_align=ft.TextAlign.CENTER,
                            no_wrap=False,
                        ),
                        ft.Container(
                            content=ft.Text(
                                current_val or "—",
                                size=state.font_sp() - 2,
                                color=ft.colors.with_opacity(0.55, state.text_color()),
                                text_align=ft.TextAlign.CENTER,
                                no_wrap=False,
                            ),
                            padding=ft.padding.symmetric(horizontal=12, vertical=4),
                            border_radius=8,
                            bgcolor=ft.colors.with_opacity(0.06, state.text_color()),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
            )
            _iv_question_card.height = 180
            page.update()

        chips = []
        for key, val in ai.responses.items():
            if not val or val == "-":
                continue
            chips.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(key, size=state.font_sp() - 2, weight=ft.FontWeight.W_600,
                                    color=state.text_color(), no_wrap=False, expand=True),
                            ft.Text(str(val)[:30] + ("…" if len(str(val)) > 30 else ""),
                                    size=state.font_sp() - 3,
                                    color=ft.colors.with_opacity(0.6, state.text_color()),
                                    no_wrap=True),
                        ],
                        spacing=8,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=10,
                    bgcolor=ft.colors.with_opacity(0.08, accent),
                    border=ft.border.all(1, ft.colors.with_opacity(0.2, accent)),
                    on_click=lambda e, k=key: _pick(k),
                    ink=True,
                )
            )

        _iv_question_card.content = ft.Column(
            [
                ft.Text("Tap a field to edit it:",
                        size=state.font_sp() - 1,
                        weight=ft.FontWeight.W_600, color=state.text_color()),
                ft.Column(chips, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        )
        _iv_question_card.height = 320
        _iv_question_card.border = ft.border.all(2, ft.colors.ORANGE_400)
        _iv_last_answer_text.value = "Tap a field to correct any misinformation, or type / say 'yes' to confirm."
        _iv_status_text.value = ""
        _interview_progress_text.value = ""
        page.update()

    def _iv_run_session(ai: InclusiveCitizenAI):
        """Background thread: drives the form Q&A loop inside the modal."""
        try:
            while True:
                result = ai.generate_question()

                if result is None:
                    # Form complete — go straight to edit picker
                    def _done():
                        _iv_filling[0] = False
                        _iv_help_icon.visible = False
                        _iv_status_text.value = ""
                        _interview_field.value = ""
                        _interview_progress_text.value = ""
                        page.update()
                        _iv_show_edit_picker()
                    _ui_call(_done)
                    return

                if result.startswith("SECTION_CONFIRM:"):
                    confirm_q = result.split(":", 1)[1]
                    _ui_call(lambda q=confirm_q: (_iv_add_bubble(q, "bot"), page.update()))
                    answer = ai.wait_for_answer(timeout=300.0)
                    if answer is None:
                        _ui_call(lambda: (_iv_add_bubble("⏱️ Session timed out.", "status"), page.update()))
                        break
                    ai.confirm_section(answer)
                    continue

                _ui_call(lambda q=result: (_iv_add_bubble(q, "bot"), page.update()))

                # Update progress
                answered, total = ai.progress
                _ui_call(lambda a=answered, t=total: (
                    setattr(_interview_progress_text, 'value', f"{a + 1} / {t}"),
                    page.update(),
                ))

                answer = ai.wait_for_answer(timeout=300.0)
                if answer is None:
                    _ui_call(lambda: (_iv_add_bubble("⏱️ Session timed out.", "status"), page.update()))
                    break

                extracted = ai.extract_and_save(answer)
                if extracted == "RETRY":
                    _ui_call(lambda: (_iv_add_bubble("I didn't catch that — could you try again?", "bot"), page.update()))

        except Exception as exc:
            def _err():
                _iv_filling[0] = False
                _iv_ai[0] = None
                _iv_add_bubble(f"⚠️ Error: {exc}", "status")
                page.update()
            _ui_call(_err)
        finally:
            _iv_filling[0] = False
            if not _iv_confirming[0] and not _iv_editing[0]:
                _iv_ai[0] = None

    def _iv_do_write_pdf():
        """Generate the filled PDF from interview responses."""
        ai    = _iv_ai[0]
        entry = _iv_entry[0]
        sig   = _iv_sig_path[0]
        _iv_ai[0] = None

        # Use persisted responses if ai is already cleared
        responses    = ai.responses    if ai else (_iv_responses[0] or {})
        input_bboxes = ai._input_bboxes if ai else (_iv_input_bboxes[0] or {})

        def _write():
            try:
                from engine.insert_doc.write_doc import fill_pdf
                schema_path = entry.get("schema_file", "")
                pdf_path    = entry.get("pdf_file", "")
                if not schema_path or not pdf_path:
                    _ui_call(lambda: (_iv_add_bubble("⚠️ No PDF template configured.", "status"), page.update()))
                    return

                form_name = _sanitise(_iv_entry[0].get("display_name", "form") if _iv_entry[0] else "form")
                user_name = _sanitise(
                    next((v for k, v in responses.items()
                          if "nama" in k.lower() and "bank" not in k.lower() and "pegawai" not in k.lower()), "")
                    or "user"
                )
                import os as _os
                out_dir  = _os.path.dirname(pdf_path)
                out_path = _os.path.join(out_dir, f"{form_name}_{user_name}.pdf")

                out = fill_pdf(
                    responses, schema_path, pdf_path,
                    output_path=out_path,
                    input_bboxes=input_bboxes,
                    signature_path=sig,
                )

                def _ok():
                    _pdf_out_path[0] = out
                    # Only delete schema if it was generated from a user-uploaded PDF
                    if entry and entry.get("_temp_schema"):
                        _iv_schema_to_delete[0] = schema_path
                    pdf_preview_modal.content.controls[1].value = out
                    pdf_preview_modal.open = True
                    _iv_close_modal()
                    page.update()
                    _run_in_thread(_show_success_overlay)
                _ui_call(_ok)
            except Exception as exc:
                _ui_call(lambda: (_iv_add_bubble(f"⚠️ Failed to write PDF: {exc}", "status"), page.update()))

        _run_in_thread(_write)

    def _iv_on_submit(e=None):
        msg = (_interview_field.value or "").strip()
        if not msg:
            return

        ai = _iv_ai[0]

        if _iv_filling[0] and ai is not None:
            _iv_add_bubble(msg, "user")
            _interview_field.value = ""
            page.update()
            ai.submit_answer(msg)
            return

        if _iv_confirming[0]:
            _iv_add_bubble(msg, "user")
            _interview_field.value = ""
            page.update()
            _yes = any(w in msg.lower() for w in _IV_YES_WORDS)
            if _yes:
                _iv_confirming[0] = False
                _iv_sig_path[0] = None
                # Open signature modal — _iv_do_write_pdf is called after signing/skipping
                _sig_points.clear()
                sig_modal.open = True
                page.update()
            else:
                _iv_confirming[0] = False
                _iv_show_edit_picker()
            return

        if _iv_editing[0]:
            key = _iv_edit_key[0]
            ai = _iv_ai[0]
            if msg.lower() in ("done", "siap") or any(w in msg.lower() for w in _IV_YES_WORDS):
                _iv_editing[0] = False
                _iv_edit_key[0] = None
                _interview_field.value = ""
                if key is None:
                    # User typed "done" from the picker — go straight to signature
                    _iv_confirming[0] = False
                    _iv_sig_path[0] = None
                    _sig_points.clear()
                    sig_modal.open = True
                    page.update()
                else:
                    # User typed "done" while editing a field — go back to picker
                    _iv_show_edit_picker()
            elif key and ai:
                # Save new value and return to picker
                _iv_add_bubble(msg, "user")
                _interview_field.value = ""
                ai.responses[key] = msg
                if _iv_responses[0] is not None:
                    _iv_responses[0][key] = msg
                _iv_editing[0] = False
                _iv_edit_key[0] = None
                _iv_show_edit_picker()
            return

    def _iv_on_field_change(e):
        has_text = bool((_interview_field.value or "").strip())
        _interview_mic_icon.name = ft.icons.SEND_ROUNDED if has_text else ft.icons.MIC_ROUNDED
        page.update()

    _interview_field.on_submit = _iv_on_submit
    _interview_field.on_change = _iv_on_field_change

    def _iv_mic_tap_down(_):
        if (_interview_field.value or "").strip():
            return
        if _iv_is_processing[0]:
            return
        import sounddevice as sd
        _iv_is_recording[0] = True
        _iv_audio_chunks.clear()
        _interview_field.hint_text = "Recording..."
        _interview_mic_circle.gradient = None
        _interview_mic_circle.bgcolor = ft.colors.RED_400
        page.update()
        _iv_sd_stream[0] = sd.InputStream(
            samplerate=16000, channels=1, dtype="float32",
            callback=lambda indata, *_: _iv_audio_chunks.append(indata.copy()),
        )
        _iv_sd_stream[0].start()

    def _iv_mic_tap_up(_):
        if not _iv_is_recording[0]:
            if (_interview_field.value or "").strip():
                _iv_on_submit()
            return

        _iv_is_recording[0] = False
        sd_stream = _iv_sd_stream[0]
        if sd_stream:
            sd_stream.stop()
            sd_stream.close()
            _iv_sd_stream[0] = None

        _interview_field.hint_text = "Type your answer..."
        _interview_mic_circle.gradient = _grad
        _interview_mic_circle.bgcolor = None
        page.update()

        def _transcribe():
            import numpy as np, soundfile as sf, tempfile, os as _os
            _iv_is_processing[0] = True
            _ui_call(lambda: (
                setattr(_interview_field, 'hint_text', 'Transcribing...'),
                setattr(_interview_mic_icon, 'name', ft.icons.STOP_ROUNDED),
                page.update(),
            ))
            try:
                text = ""
                if _iv_audio_chunks:
                    audio_np = np.concatenate(_iv_audio_chunks, axis=0).flatten()
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        tmp = f.name
                    sf.write(tmp, audio_np, 16000)
                    _, _, _, _, transcribe_audio = _get_preloaded_modules()
                    text = transcribe_audio(tmp, normalize_to_question=False, country=state.country or "Malaysia") if transcribe_audio else ""
                    _os.remove(tmp)
                    # Collapse spelled-out input before echoing and submitting
                    from engine.insert_doc.document_LLM import _collapse_spelled
                    _current_label = ""
                    _ai = _iv_ai[0]
                    if _ai and _ai.current_field_index < len(_ai.fields):
                        _f = _ai.fields[_ai.current_field_index]
                        _current_label = _f.get("label") or _f.get("original_label") or ""
                    text = _collapse_spelled(text, label=_current_label)

                def _done(t=text):
                    _iv_is_processing[0] = False
                    _interview_field.hint_text = "Type your answer..."
                    _interview_mic_icon.name = ft.icons.MIC_ROUNDED
                    _interview_mic_circle.gradient = _grad
                    _interview_mic_circle.bgcolor = None
                    if t:
                        _iv_add_bubble(t, "user")
                        page.update()
                        ai = _iv_ai[0]
                        if _iv_filling[0] and ai:
                            # Normal Q&A — unblock the session loop
                            ai.submit_answer(t)
                        elif _iv_confirming[0] and ai:
                            # Confirmation step
                            ai.submit_answer(t)
                        elif _iv_editing[0]:
                            # Edit picker — treat voice input as a typed answer
                            _interview_field.value = t
                            _iv_on_submit()
                    page.update()
                _ui_call(_done)
            except Exception as exc:
                def _err():
                    _iv_is_processing[0] = False
                    _interview_field.hint_text = "Type your answer..."
                    _interview_mic_icon.name = ft.icons.MIC_ROUNDED
                    _interview_mic_circle.gradient = _grad
                    _interview_mic_circle.bgcolor = None
                    _iv_add_bubble(f"⚠️ Transcription error: {exc}", "status")
                    page.update()
                _ui_call(_err)

        threading.Thread(target=_transcribe, daemon=True).start()

    _iv_mic_btn = ft.GestureDetector(
        content=_interview_mic_circle,
        on_tap_down=_iv_mic_tap_down,
        on_tap_up=_iv_mic_tap_up,
    )

    _iv_input_bar = ft.Container(
        content=_interview_field,
        expand=True,
        border_radius=24,
        bgcolor=state.surface_color(),
        border=ft.border.all(2, accent),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
    )

    def _iv_on_listen(_):
        if _iv_tts_paused[0]:
            try:
                import pygame
                pygame.mixer.music.unpause()
                _iv_tts_paused[0] = False
                _iv_tts_playing[0] = True
                _iv_listen_btn.text = "⏸️ Pause"
                page.update()
            except Exception as exc:
                print(f"[iv_tts] resume error: {exc}")
            return

        if _iv_tts_playing[0]:
            try:
                import pygame
                pygame.mixer.music.pause()
                _iv_tts_paused[0] = True
                _iv_tts_playing[0] = False
                _iv_listen_btn.text = "▶️ Resume"
                page.update()
            except Exception as exc:
                print(f"[iv_tts] pause error: {exc}")
            return

        if _iv_tts_loading[0]:
            return

        text = _iv_question_text.value or ""
        if not text.strip():
            return

        _iv_tts_loading[0] = True
        _iv_listen_btn.text = "🔄 Loading..."
        _iv_listen_btn.disabled = True
        page.update()

        def _speak():
            try:
                import asyncio as _asyncio
                from engine.speech.text_to_speech import speak_answer

                def _set_playing():
                    _iv_tts_loading[0] = False
                    _iv_tts_playing[0] = True
                    _iv_listen_btn.text = "⏸️ Pause"
                    _iv_listen_btn.disabled = False
                    page.update()
                _ui_call(_set_playing)

                country_code = _COUNTRY_CODE_MAP.get(state.country, "DEFAULT")
                # Use the interview language directly to avoid misdetection on short text
                _LANG_TO_ISO = {
                    "English": "en",
                    "Bahasa Melayu": "ms", "Malay": "ms",
                    "Bahasa Indonesia": "id", "Indonesian": "id",
                    "Thai": "th",
                    "Vietnamese": "vi",
                    "Filipino/Tagalog": "tl", "Filipino": "tl", "Tagalog": "tl",
                    "Chinese (Simplified)": "zh",
                    "Tamil": "ta",
                    "Burmese": "my",
                    "Khmer": "km",
                    "Lao": "lo",
                }
                _ai = _iv_ai[0]
                _user_lang = _ai.user_language if _ai else _iv_user_lang[0]
                _lang_iso = _LANG_TO_ISO.get(_user_lang, "en")
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                loop.run_until_complete(speak_answer(text, country_code, lang_override=_lang_iso))
                loop.close()

            except Exception as exc:
                print(f"[iv_tts] error: {exc}")
            finally:
                def _reset():
                    _iv_tts_loading[0] = False
                    _iv_tts_playing[0] = False
                    _iv_tts_paused[0] = False
                    _iv_listen_btn.text = "🔊 Listen"
                    _iv_listen_btn.disabled = False
                    page.update()
                _ui_call(_reset)

        _run_in_thread(_speak)

    _iv_listen_btn.on_click = _iv_on_listen

    # ── Language picker screen ────────────────────────────────────────────
    _iv_lang_selected: list = ["English"]

    _IV_IDLE_TEXT  = "#212121"

    _iv_lang_wrap = ft.Row(wrap=True, spacing=10, run_spacing=10)

    def _iv_build_lang_chips(selected: str):
        _iv_lang_wrap.controls.clear()
        for lang in ASEAN_LANGUAGES:
            is_sel = lang == selected
            _iv_lang_wrap.controls.append(
                ft.TextButton(
                    content=ft.Text(
                        lang,
                        size=state.font_sp(),
                        color="#5B23FF" if is_sel else _IV_IDLE_TEXT,
                        weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_400,
                    ),
                    on_click=lambda _, l=lang: _iv_select_lang(l),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    ),
                )
            )

    def _iv_select_lang(lang: str):
        _iv_lang_selected[0] = lang
        _iv_build_lang_chips(lang)
        page.update()

    _iv_build_lang_chips("English")

    _iv_lang_screen = ft.Container(
        visible=True,
        content=ft.Column(
            [
                ft.Text(
                    "Choose your language",
                    size=state.font_sp() + 3,
                    weight=ft.FontWeight.BOLD,
                    color=state.text_color(),
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Questions will be asked in the selected language.",
                    size=state.font_sp() - 1,
                    color=ft.colors.with_opacity(0.55, state.text_color()),
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=12),
                _iv_lang_wrap,
                ft.Container(height=16),
                ft.ElevatedButton(
                    "Start Interview",
                    icon=ft.icons.ARROW_FORWARD_ROUNDED,
                    on_click=lambda _: _iv_start_after_lang(),
                    style=ft.ButtonStyle(
                        bgcolor=accent,
                        color=ft.colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(vertical=14, horizontal=24),
                    ),
                    height=48,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # ── Q&A screen ────────────────────────────────────────────────────────
    _iv_qa_screen = ft.Container(
        visible=False,
        content=ft.Column(
            [
                ft.Container(
                    content=_iv_question_card,
                    alignment=ft.alignment.center,
                ),
                ft.Container(
                    content=ft.Column(
                        [_iv_last_answer_text, _iv_status_text],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    alignment=ft.alignment.center,
                    height=32,
                ),
                ft.Row(
                    [_iv_input_bar, _iv_mic_btn],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def _iv_start_after_lang():
        """Switch from language picker to Q&A screen and start the session."""
        lang = _iv_lang_selected[0]
        ai = _iv_ai[0]
        if ai:
            ai.set_language(lang)
        _iv_user_lang[0] = lang  # persist for TTS even after ai is cleared
        _iv_filling[0] = True
        _iv_lang_screen.visible = False
        _iv_qa_screen.visible = True
        _interview_progress_text.value = ""
        _iv_question_text.value = "Loading questions..."
        _iv_last_answer_text.value = ""
        _iv_status_text.value = ""
        page.update()
        _run_in_thread(lambda: _iv_run_session(ai))

    interview_modal = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.icons.ARTICLE_OUTLINED, color=accent, size=20),
                _interview_title,
                ft.Container(expand=True),
                _interview_progress_text,
                ft.Container(width=8),
                ft.IconButton(
                    icon=ft.icons.CLOSE,
                    icon_color=ft.colors.with_opacity(0.5, state.text_color()),
                    icon_size=18,
                    tooltip="Cancel",
                    on_click=lambda _: _iv_close_modal(),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            width=480,
            bgcolor=state.bg_color(),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=20),
            content=ft.Column(
                [_iv_lang_screen, _iv_qa_screen],
                tight=True,
                spacing=0,
            ),
        ),
        actions=[],
    )

    # ------------------------------------------------------------------ #
    #  Add / Scan — PDF form scanner (direct-to-interview flow)           #
    # ------------------------------------------------------------------ #
    _scan_status_snack = ft.SnackBar(content=ft.Text(""), open=False)
    page.overlay.append(_scan_status_snack)

    def _open_interview_for_entry(entry: dict):
        """Open the interview modal — show language picker first."""
        try:
            ai = InclusiveCitizenAI(
                entry["schema_file"],
                user_language=state.language or "English",
            )
            _iv_ai[0] = ai
            _iv_entry[0] = entry
            _iv_filling[0] = False   # not started yet — waiting for lang selection
            _iv_confirming[0] = False
            _interview_title.value = entry.get("display_name", "Interview")
            _interview_progress_text.value = ""
            # Reset to language picker screen
            _iv_lang_selected[0] = state.language or "English"
            _iv_build_lang_chips(_iv_lang_selected[0])
            _iv_lang_screen.visible = True
            _iv_qa_screen.visible = False
            _iv_question_text.value = ""
            _iv_question_text.size = state.font_sp() + 4
            _iv_help_icon.visible = True
            _iv_last_answer_text.value = ""
            _iv_status_text.value = ""
            interview_modal.open = True
            page.update()
        except Exception as exc:
            _scan_status_snack.content = ft.Text(f"Could not start interview: {exc}")
            _scan_status_snack.open = True
            page.update()

    def _on_scan_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        pdf_path = e.files[0].path
        if not pdf_path or not pdf_path.lower().endswith(".pdf"):
            _scan_status_snack.content = ft.Text("Please select a PDF file.")
            _scan_status_snack.open = True
            page.update()
            return

        # Show a scanning indicator immediately
        _scan_status_snack.content = ft.Text("Scanning PDF, please wait...")
        _scan_status_snack.open = True
        page.update()

        def _process():
            def _progress(msg: str):
                _ui_call(lambda m=msg: (
                    setattr(_scan_status_snack, 'content', ft.Text(m)),
                    setattr(_scan_status_snack, 'open', True),
                    page.update(),
                ))

            try:
                from engine.insert_doc.document_manager import process_pdf
                entry = process_pdf(
                    source_path=pdf_path,
                    on_progress=_progress,
                    country=state.country or "Malaysia",
                )
                # Skip the list — go straight to the interview modal
                _ui_call(lambda: _open_interview_for_entry(entry))
            except Exception as exc:
                _ui_call(lambda: (
                    setattr(_scan_status_snack, 'content', ft.Text(f"Scan failed: {exc}")),
                    setattr(_scan_status_snack, 'open', True),
                    page.update(),
                ))

        _run_in_thread(_process)

    scan_picker = ft.FilePicker(on_result=_on_scan_picked)

    page.overlay.append(file_picker)
    page.overlay.append(sig_modal)
    page.overlay.append(pdf_preview_modal)
    page.overlay.append(interview_modal)
    page.overlay.append(save_picker)
    page.overlay.append(_success_overlay)
    page.overlay.append(scan_picker)
    page.update()

    # ------------------------------------------------------------------ #
    #  Assemble final view                                                 #
    # ------------------------------------------------------------------ #

    return ft.View(
        route="/home",
        appbar=appbar,
        controls=[
            ft.Row([
                # Sidebar with resize handle
                sidebar_with_handle,

                # Main content
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
                            ft.Container(
                                content=ft.Text(
                                    "Bridge is an AI and can make mistakes.",
                                    size=state.font_sp() - 4,
                                    color=ft.colors.with_opacity(0.45, state.text_color()),
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                alignment=ft.alignment.center,
                                padding=ft.padding.only(top=2, bottom=4),
                            ),
                        ],
                        expand=True,
                        spacing=0,
                        tight=False,
                    ),
                ),
            ], spacing=0, expand=True),
        ],
        padding=0,
        bgcolor=state.bg_color(),
    )
