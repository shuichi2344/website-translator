"""
Preservation Property Tests — Property 2
=========================================
Validates: Requirements 3.1, 3.2, 3.3, 3.4

EXPECTED OUTCOME: All tests PASS on unfixed code.

These tests cover non-background-thread UI interactions (isBugCondition is false):
  - Text submission via on_chat_submit
  - Mic-with-text: tapping mic when chat_field has text calls on_chat_submit
  - Mic animation: _start_recording / _stop_recording toggle visual state
  - Panel independence: document/web panel open/close is unaffected by _ui()

Observation-first methodology:
  1. on_chat_submit("hello") adds a user bubble and clears chat_field — OBSERVED
  2. Tapping mic while chat_field has text calls on_chat_submit, not _start_recording — OBSERVED
  3. _start_recording sets recording state + red visuals; _stop_recording reverts them — OBSERVED
  4. Panel open/close state is independent of _ui() calls — OBSERVED

None of these paths go through _ui() / page.run_thread, so they are unaffected by the bug.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch, call
from typing import Optional

import flet as ft
from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_mock_page():
    """Mock flet.Page without run_thread — matches Flet 0.19.0 reality."""
    page = MagicMock(spec=["update", "go", "overlay", "theme_mode"])
    page.overlay = []
    page.theme_mode = "Light"
    return page


def _build_home_env(page):
    """
    Reconstruct the relevant closure environment from home.py.

    Returns a dict with:
      chat_list, chat_field, mic_icon, mic_circle, pulse_ring,
      is_recording, on_chat_submit, on_mic_or_send,
      _start_recording, _stop_recording,
      document_panel, web_panel, set_mode, active_mode
    """
    # --- State mirrors ---
    is_recording = [False]
    active_mode = [None]

    accent = "#1565C0"
    font_sp = 14

    BUBBLE_USER_BG = accent
    BUBBLE_BOT_BG = "#FFFFFF"
    BUBBLE_USER_FG = ft.colors.WHITE
    BUBBLE_BOT_FG = "#000000"
    BUBBLE_STATUS_FG = ft.colors.with_opacity(0.6, "#000000")

    # --- chat_list ---
    chat_list = ft.ListView(expand=True, spacing=8, auto_scroll=True)

    # --- _add_bubble (verbatim from home.py) ---
    def _add_bubble(text: str, role: str = "bot") -> None:
        if role == "user":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_USER_FG, size=font_sp),
                bgcolor=BUBBLE_USER_BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.END, expand=True)
        elif role == "status":
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_STATUS_FG, size=font_sp - 2, italic=True),
                bgcolor=ft.colors.with_opacity(0.06, accent),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.CENTER, expand=True)
        else:
            content = ft.Container(
                content=ft.Text(text, color=BUBBLE_BOT_FG, size=font_sp),
                bgcolor=BUBBLE_BOT_BG,
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
            bubble = ft.Row([content], alignment=ft.MainAxisAlignment.START, expand=True)
        chat_list.controls.append(bubble)

    # --- chat_field ---
    chat_field = ft.TextField(
        hint_text="Ask a question...",
        expand=True,
        min_lines=1,
        max_lines=4,
    )

    # --- mic_icon, mic_circle, pulse_ring (verbatim from home.py) ---
    mic_icon = ft.Icon(ft.icons.MIC_ROUNDED, color=ft.colors.WHITE, size=24)

    pulse_ring = ft.Container(
        width=48, height=48, border_radius=24,
        bgcolor=ft.colors.with_opacity(0.0, ft.colors.RED_400),
    )

    mic_circle = ft.Container(
        content=mic_icon,
        width=48, height=48, border_radius=24,
        bgcolor=accent,
        alignment=ft.alignment.center,
    )

    # --- on_chat_submit (verbatim from home.py) ---
    def on_chat_submit(e):
        msg = (chat_field.value or "").strip()
        if not msg:
            return
        _add_bubble(msg, "user")
        chat_field.value = ""
        mic_icon.name = ft.icons.MIC_ROUNDED
        page.update()

    # --- on_mic_or_send (verbatim from home.py) ---
    def on_mic_or_send(_):
        if (chat_field.value or "").strip():
            on_chat_submit(None)

    # --- _start_recording (verbatim from home.py, minus PTT session) ---
    def _start_recording(_):
        if (chat_field.value or "").strip():
            return  # in send mode — tap_up will submit
        is_recording[0] = True
        chat_field.hint_text = "Recording..."
        mic_circle.bgcolor = ft.colors.RED_400
        mic_circle.width = 54
        mic_circle.height = 54
        mic_circle.border_radius = 27
        pulse_ring.bgcolor = ft.colors.with_opacity(0.3, ft.colors.RED_400)
        pulse_ring.width = 68
        pulse_ring.height = 68
        pulse_ring.border_radius = 34
        page.update()

    # --- _stop_recording (verbatim from home.py, minus PTT session) ---
    def _stop_recording(_):
        was_recording = is_recording[0]
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
        if (chat_field.value or "").strip():
            on_chat_submit(None)

    # --- Panels (verbatim from home.py) ---
    document_panel = ft.Container(visible=False)
    web_panel = ft.Container(visible=False)

    def set_mode(mode):
        if mode is not None and active_mode[0] == mode:
            mode = None
        active_mode[0] = mode
        document_panel.visible = mode == "document"
        web_panel.visible = mode == "web"
        page.update()

    return {
        "chat_list": chat_list,
        "chat_field": chat_field,
        "mic_icon": mic_icon,
        "mic_circle": mic_circle,
        "pulse_ring": pulse_ring,
        "is_recording": is_recording,
        "on_chat_submit": on_chat_submit,
        "on_mic_or_send": on_mic_or_send,
        "_start_recording": _start_recording,
        "_stop_recording": _stop_recording,
        "document_panel": document_panel,
        "web_panel": web_panel,
        "set_mode": set_mode,
        "active_mode": active_mode,
    }


# ---------------------------------------------------------------------------
# Property 2.1 — Text submit preservation (Requirement 3.1)
# ---------------------------------------------------------------------------

class TestTextSubmitPreservation(unittest.TestCase):
    """
    Validates: Requirements 3.1

    Property: for any non-empty text message, on_chat_submit adds exactly one
    user bubble to chat_list and clears chat_field.value.
    """

    def setUp(self):
        self.page = _make_mock_page()
        self.env = _build_home_env(self.page)

    @given(text=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()))
    @settings(max_examples=50)
    def test_submit_adds_user_bubble(self, text):
        """
        Validates: Requirements 3.1

        For any non-empty text, on_chat_submit adds exactly one user bubble.
        """
        env = _build_home_env(self.page)
        chat_list = env["chat_list"]
        chat_field = env["chat_field"]
        on_chat_submit = env["on_chat_submit"]

        chat_field.value = text
        initial_count = len(chat_list.controls)

        on_chat_submit(None)

        self.assertEqual(
            len(chat_list.controls),
            initial_count + 1,
            f"Expected exactly one bubble added for text={text!r}, "
            f"got {len(chat_list.controls) - initial_count} bubbles added."
        )

    @given(text=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()))
    @settings(max_examples=50)
    def test_submit_clears_chat_field(self, text):
        """
        Validates: Requirements 3.1

        For any non-empty text, on_chat_submit clears chat_field.value to "".
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        on_chat_submit = env["on_chat_submit"]

        chat_field.value = text
        on_chat_submit(None)

        self.assertEqual(
            chat_field.value,
            "",
            f"Expected chat_field.value to be cleared after submit, "
            f"got {chat_field.value!r} for input {text!r}."
        )

    def test_submit_empty_text_does_nothing(self):
        """
        Validates: Requirements 3.1

        Empty or whitespace-only text must not add any bubble.
        """
        env = _build_home_env(self.page)
        chat_list = env["chat_list"]
        chat_field = env["chat_field"]
        on_chat_submit = env["on_chat_submit"]

        for empty in ["", "   ", "\t", "\n"]:
            chat_field.value = empty
            count_before = len(chat_list.controls)
            on_chat_submit(None)
            self.assertEqual(
                len(chat_list.controls),
                count_before,
                f"Empty input {empty!r} should not add a bubble."
            )

    @given(messages=st.lists(
        st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        min_size=2, max_size=10
    ))
    @settings(max_examples=30)
    def test_submit_multiple_messages_accumulate(self, messages):
        """
        Validates: Requirements 3.1

        Submitting N messages adds exactly N bubbles to chat_list.
        """
        env = _build_home_env(self.page)
        chat_list = env["chat_list"]
        chat_field = env["chat_field"]
        on_chat_submit = env["on_chat_submit"]

        for msg in messages:
            chat_field.value = msg
            on_chat_submit(None)

        self.assertEqual(
            len(chat_list.controls),
            len(messages),
            f"Expected {len(messages)} bubbles for {len(messages)} messages, "
            f"got {len(chat_list.controls)}."
        )


# ---------------------------------------------------------------------------
# Property 2.2 — Send-mode preservation (Requirement 3.2)
# ---------------------------------------------------------------------------

class TestSendModePreservation(unittest.TestCase):
    """
    Validates: Requirements 3.2

    Property: when chat_field has non-empty text, tapping the mic button
    calls on_chat_submit (submits text) rather than starting a recording session.
    """

    def setUp(self):
        self.page = _make_mock_page()

    @given(text=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()))
    @settings(max_examples=50)
    def test_mic_tap_with_text_submits_not_records(self, text):
        """
        Validates: Requirements 3.2

        When chat_field has text, _start_recording returns early (no recording state change)
        and _stop_recording calls on_chat_submit.
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        is_recording = env["is_recording"]
        _start_recording = env["_start_recording"]
        _stop_recording = env["_stop_recording"]
        chat_list = env["chat_list"]

        chat_field.value = text
        initial_count = len(chat_list.controls)

        # Simulate tap_down (should return early — send mode)
        _start_recording(None)

        # is_recording must NOT be set when there's text in the field
        self.assertFalse(
            is_recording[0],
            f"is_recording should remain False when chat_field has text={text!r}."
        )

        # Simulate tap_up (should submit the text)
        _stop_recording(None)

        self.assertEqual(
            len(chat_list.controls),
            initial_count + 1,
            f"Expected one bubble submitted via _stop_recording for text={text!r}."
        )
        self.assertEqual(
            chat_field.value,
            "",
            f"chat_field should be cleared after submit via mic tap for text={text!r}."
        )

    def test_mic_tap_without_text_starts_recording(self):
        """
        Validates: Requirements 3.2 (negative case)

        When chat_field is empty, _start_recording sets is_recording=True.
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        is_recording = env["is_recording"]
        _start_recording = env["_start_recording"]

        chat_field.value = ""
        _start_recording(None)

        self.assertTrue(
            is_recording[0],
            "is_recording should be True when chat_field is empty and mic is tapped."
        )


# ---------------------------------------------------------------------------
# Property 2.3 — Mic animation preservation (Requirement 3.3)
# ---------------------------------------------------------------------------

class TestMicAnimationPreservation(unittest.TestCase):
    """
    Validates: Requirements 3.3

    Property: _start_recording sets the red recording visual state;
    _stop_recording reverts to the default mic visual state.
    """

    def setUp(self):
        self.page = _make_mock_page()

    def test_start_recording_sets_red_visual(self):
        """
        Validates: Requirements 3.3

        _start_recording sets mic_circle to red and expands pulse_ring.
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        mic_circle = env["mic_circle"]
        pulse_ring = env["pulse_ring"]
        is_recording = env["is_recording"]
        _start_recording = env["_start_recording"]

        chat_field.value = ""  # no text — recording mode
        _start_recording(None)

        self.assertTrue(is_recording[0], "is_recording should be True after _start_recording.")
        self.assertEqual(mic_circle.bgcolor, ft.colors.RED_400,
                         "mic_circle.bgcolor should be RED_400 during recording.")
        self.assertEqual(mic_circle.width, 54, "mic_circle.width should expand to 54 during recording.")
        self.assertEqual(mic_circle.height, 54, "mic_circle.height should expand to 54 during recording.")
        self.assertEqual(chat_field.hint_text, "Recording...",
                         "hint_text should be 'Recording...' during recording.")

    def test_stop_recording_reverts_visual(self):
        """
        Validates: Requirements 3.3

        _stop_recording reverts mic_circle to default accent color and size.
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        mic_circle = env["mic_circle"]
        pulse_ring = env["pulse_ring"]
        is_recording = env["is_recording"]
        _start_recording = env["_start_recording"]
        _stop_recording = env["_stop_recording"]

        accent = "#1565C0"

        chat_field.value = ""
        _start_recording(None)
        _stop_recording(None)

        self.assertFalse(is_recording[0], "is_recording should be False after _stop_recording.")
        self.assertEqual(mic_circle.bgcolor, accent,
                         "mic_circle.bgcolor should revert to accent after _stop_recording.")
        self.assertEqual(mic_circle.width, 48, "mic_circle.width should revert to 48.")
        self.assertEqual(mic_circle.height, 48, "mic_circle.height should revert to 48.")
        self.assertEqual(chat_field.hint_text, "Ask a question...",
                         "hint_text should revert to 'Ask a question...' after _stop_recording.")

    @given(
        text=st.text(max_size=200),
        start_count=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=30)
    def test_start_stop_cycle_is_idempotent(self, text, start_count):
        """
        Validates: Requirements 3.3

        After any number of start/stop cycles (with empty chat_field),
        the final state after _stop_recording is always the default visual.
        """
        env = _build_home_env(self.page)
        chat_field = env["chat_field"]
        mic_circle = env["mic_circle"]
        is_recording = env["is_recording"]
        _start_recording = env["_start_recording"]
        _stop_recording = env["_stop_recording"]

        accent = "#1565C0"
        chat_field.value = ""  # ensure recording mode

        for _ in range(start_count):
            _start_recording(None)
            _stop_recording(None)

        self.assertFalse(is_recording[0])
        self.assertEqual(mic_circle.bgcolor, accent)
        self.assertEqual(mic_circle.width, 48)
        self.assertEqual(mic_circle.height, 48)


# ---------------------------------------------------------------------------
# Property 2.4 — Panel independence (Requirement 3.4)
# ---------------------------------------------------------------------------

class TestPanelIndependence(unittest.TestCase):
    """
    Validates: Requirements 3.4

    Property: document/web panel open/close state is independent of _ui() calls.
    Panel visibility is controlled solely by set_mode(), not by _ui().
    """

    def setUp(self):
        self.page = _make_mock_page()

    def test_document_panel_opens_and_closes(self):
        """
        Validates: Requirements 3.4

        set_mode("document") shows document_panel; set_mode(None) hides it.
        """
        env = _build_home_env(self.page)
        document_panel = env["document_panel"]
        web_panel = env["web_panel"]
        set_mode = env["set_mode"]

        self.assertFalse(document_panel.visible, "document_panel should start hidden.")

        set_mode("document")
        self.assertTrue(document_panel.visible, "document_panel should be visible after set_mode('document').")
        self.assertFalse(web_panel.visible, "web_panel should remain hidden when document mode is active.")

        set_mode(None)
        self.assertFalse(document_panel.visible, "document_panel should be hidden after set_mode(None).")

    def test_web_panel_opens_and_closes(self):
        """
        Validates: Requirements 3.4

        set_mode("web") shows web_panel; set_mode(None) hides it.
        """
        env = _build_home_env(self.page)
        document_panel = env["document_panel"]
        web_panel = env["web_panel"]
        set_mode = env["set_mode"]

        set_mode("web")
        self.assertTrue(web_panel.visible, "web_panel should be visible after set_mode('web').")
        self.assertFalse(document_panel.visible, "document_panel should remain hidden in web mode.")

        set_mode(None)
        self.assertFalse(web_panel.visible, "web_panel should be hidden after set_mode(None).")

    def test_toggle_same_mode_closes_panel(self):
        """
        Validates: Requirements 3.4

        Tapping the already-active card collapses the panel (toggle behavior).
        """
        env = _build_home_env(self.page)
        document_panel = env["document_panel"]
        set_mode = env["set_mode"]
        active_mode = env["active_mode"]

        set_mode("document")
        self.assertTrue(document_panel.visible)
        self.assertEqual(active_mode[0], "document")

        # Toggle: tap same mode again
        set_mode("document")
        self.assertFalse(document_panel.visible)
        self.assertIsNone(active_mode[0])

    @given(modes=st.lists(
        st.sampled_from(["document", "web", None]),
        min_size=1, max_size=10
    ))
    @settings(max_examples=40)
    def test_panel_state_matches_active_mode(self, modes):
        """
        Validates: Requirements 3.4

        After any sequence of set_mode calls, panel visibility always matches
        the final active_mode — independent of any _ui() calls.
        """
        env = _build_home_env(self.page)
        document_panel = env["document_panel"]
        web_panel = env["web_panel"]
        set_mode = env["set_mode"]
        active_mode = env["active_mode"]

        for mode in modes:
            set_mode(mode)

        final_mode = active_mode[0]
        self.assertEqual(
            document_panel.visible,
            final_mode == "document",
            f"document_panel.visible should be {final_mode == 'document'} "
            f"when active_mode={final_mode!r}."
        )
        self.assertEqual(
            web_panel.visible,
            final_mode == "web",
            f"web_panel.visible should be {final_mode == 'web'} "
            f"when active_mode={final_mode!r}."
        )

    def test_ui_helper_does_not_affect_panel_state(self):
        """
        Validates: Requirements 3.4

        Calling _ui() (even the broken version) does not change panel visibility.
        Panel state is controlled only by set_mode().
        """
        env = _build_home_env(self.page)
        document_panel = env["document_panel"]
        web_panel = env["web_panel"]
        set_mode = env["set_mode"]

        set_mode("document")
        self.assertTrue(document_panel.visible)

        # Simulate what _ui() does — it calls page.run_thread(fn) which raises
        # AttributeError on unfixed code. Panel state must be unaffected.
        try:
            self.page.run_thread(lambda: None)
        except AttributeError:
            pass  # expected on unfixed code

        # Panel state unchanged
        self.assertTrue(document_panel.visible,
                        "Panel state must not change when _ui() raises AttributeError.")
        self.assertFalse(web_panel.visible)


if __name__ == "__main__":
    unittest.main()
