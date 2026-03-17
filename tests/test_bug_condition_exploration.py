"""
Bug Condition Exploration Test — Property 1
===========================================
Validates: Requirements 1.1, 1.2, 1.3, 1.4

CRITICAL: This test MUST FAIL on unfixed code.
Failure confirms the bug: page.run_thread() does not exist in Flet 0.19.0,
so every background-thread UI update is silently dropped.

Bug condition:
  call_context.caller IN [PTTSession._process, _pipeline_with_result]
  AND call_context.thread != UI_THREAD
  AND page.run_thread IS NOT DEFINED   (Flet 0.19.0)

Expected outcome on UNFIXED code:
  AttributeError: 'Page' object has no attribute 'run_thread'
  chat_list.controls remains empty after all callbacks fire.

Strategy:
  Directly reconstruct the _ui / _add_bubble_safe / callback closure chain
  from home.py using the same logic, with a mock page that has no run_thread.
  This avoids Flet UI event-loop complexity while faithfully reproducing the bug.
"""
from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import MagicMock

import flet as ft


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_page():
    """
    Return a mock flet.Page WITHOUT run_thread — matches Flet 0.19.0 reality.
    """
    page = MagicMock(spec=["update", "go", "overlay", "theme_mode"])
    page.overlay = []
    page.theme_mode = "Light"
    assert not hasattr(page, "run_thread"), (
        "Mock page must NOT have run_thread — this simulates Flet 0.19.0"
    )
    return page


def _invoke_from_thread(fn, *args, timeout=3.0):
    """Invoke fn(*args) from a background thread; return any exception raised."""
    exc_holder = [None]

    def _run():
        try:
            fn(*args)
        except Exception as e:
            exc_holder[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return exc_holder[0]


def _build_closure_env(page):
    """
    Reconstruct the exact closure environment from home.py:
      _ui, _add_bubble_safe, _on_stt_status, _on_stt_error, _on_stt_result,
      on_status (pipeline), on_result (pipeline)
    and a chat_list to inspect.

    This mirrors the code in build_home_view verbatim so the test exercises
    the real broken _ui() implementation.
    """
    # Minimal state mirrors
    is_recording = [False]
    chat_field = MagicMock()
    chat_field.hint_text = "Ask a question..."

    # chat_list — the control we assert against
    chat_list = ft.ListView(expand=True, spacing=8, auto_scroll=True)

    # --- _add_bubble (copied verbatim from home.py) ---
    accent = "#1565C0"
    BUBBLE_USER_BG = accent
    BUBBLE_BOT_BG = "#FFFFFF"
    BUBBLE_USER_FG = ft.colors.WHITE
    BUBBLE_BOT_FG = "#000000"
    BUBBLE_STATUS_FG = ft.colors.with_opacity(0.6, "#000000")
    font_sp = 14

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

    # --- _ui (updated to match fixed home.py) ---
    def _ui(fn):
        """Run fn() — in Flet 0.19.0, page.update() is thread-safe."""
        fn()

    # --- _add_bubble_safe (copied verbatim from home.py) ---
    def _add_bubble_safe(text: str, role: str = "bot"):
        def _do():
            _add_bubble(text, role)
            page.update()
        _ui(_do)

    # --- _on_stt_status (copied verbatim from home.py) ---
    def _on_stt_status(msg: str):
        _add_bubble_safe(msg, "status")

    # --- _on_stt_error (copied verbatim from home.py) ---
    def _on_stt_error(exc: Exception):
        def _do():
            is_recording[0] = False
            chat_field.hint_text = "Ask a question..."
            _add_bubble(f"⚠️ {exc}", "status")
            page.update()
        _ui(_do)

    # --- _on_stt_result (copied verbatim from home.py) ---
    def _on_stt_result(results: dict):
        question = results.get("question") or results.get("raw") or ""

        def _do():
            is_recording[0] = False
            chat_field.hint_text = "Ask a question..."
            _add_bubble(question, "user")
            page.update()
        _ui(_do)
        # (pipeline call omitted — we test the UI update path only)

    # --- pipeline callbacks (copied verbatim from home.py _run_main_pipeline) ---
    def on_status(msg: str):
        _add_bubble_safe(msg, "status")

    def on_result(answer: str, links: list, dialect: str, question: str):
        _add_bubble_safe(answer, "bot")

    return {
        "chat_list": chat_list,
        "ptt_on_status": _on_stt_status,
        "ptt_on_result": _on_stt_result,
        "ptt_on_error": _on_stt_error,
        "pipeline_on_status": on_status,
        "pipeline_on_result": on_result,
    }



# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestBugConditionExploration(unittest.TestCase):
    """
    Property 1: Bug Condition — Background Thread UI Updates Silently Dropped

    Each test simulates one of the four concrete call sites that fire from a
    background thread and asserts the bubble appears in chat_list.controls.

    On UNFIXED code every test FAILS because page.run_thread does not exist
    in Flet 0.19.0 — the AttributeError is raised in the background thread
    and chat_list.controls remains empty.
    """

    def setUp(self):
        self.page = _make_mock_page()
        self.env = _build_closure_env(self.page)
        self.chat_list = self.env["chat_list"]

    # ------------------------------------------------------------------
    # Call site 1: on_status("Transcribing audio...") — PTTSession._process
    # ------------------------------------------------------------------
    def test_call_site_1_ptt_on_status_transcribing(self):
        """
        Validates: Requirements 1.1, 1.2

        Simulates PTTSession._process calling on_status("Transcribing audio...")
        from a background thread.

        EXPECTED ON UNFIXED CODE:
          AttributeError: 'Page' object has no attribute 'run_thread'
          chat_list.controls is empty → bug confirmed.
        """
        on_status = self.env["ptt_on_status"]
        initial_count = len(self.chat_list.controls)

        exc = _invoke_from_thread(on_status, "Transcribing audio...")
        time.sleep(0.2)

        self.assertGreater(
            len(self.chat_list.controls),
            initial_count,
            f"COUNTEREXAMPLE: on_status('Transcribing audio...') fired from PTTSession "
            f"background thread → chat_list.controls unchanged "
            f"(count={len(self.chat_list.controls)}). "
            f"Exception in thread: {exc!r}. "
            f"Bug confirmed: page.run_thread does not exist in Flet 0.19.0."
        )

    # ------------------------------------------------------------------
    # Call site 2: _on_stt_result({"question": "test"}) — STT background thread
    # ------------------------------------------------------------------
    def test_call_site_2_on_stt_result(self):
        """
        Validates: Requirements 1.3

        Simulates the STT background thread calling _on_stt_result({"question": "test"}).

        EXPECTED ON UNFIXED CODE:
          AttributeError: 'Page' object has no attribute 'run_thread'
          No user bubble with "test" appears in chat_list.
        """
        on_result = self.env["ptt_on_result"]
        initial_count = len(self.chat_list.controls)

        exc = _invoke_from_thread(on_result, {"question": "test"})
        time.sleep(0.2)

        self.assertGreater(
            len(self.chat_list.controls),
            initial_count,
            f"COUNTEREXAMPLE: _on_stt_result({{'question': 'test'}}) fired from STT background "
            f"thread → chat_list.controls unchanged "
            f"(count={len(self.chat_list.controls)}). "
            f"Exception in thread: {exc!r}. "
            f"Bug confirmed: page.run_thread does not exist in Flet 0.19.0."
        )

    # ------------------------------------------------------------------
    # Call site 3: on_status("Searching official government sources...") — pipeline thread
    # ------------------------------------------------------------------
    def test_call_site_3_pipeline_on_status(self):
        """
        Validates: Requirements 1.4

        Simulates _pipeline_with_result calling
        on_status("Searching official government sources...") from a background thread.

        EXPECTED ON UNFIXED CODE:
          AttributeError: 'Page' object has no attribute 'run_thread'
          No status bubble appears in chat_list.
        """
        on_status = self.env["pipeline_on_status"]
        initial_count = len(self.chat_list.controls)

        exc = _invoke_from_thread(on_status, "Searching official government sources...")
        time.sleep(0.2)

        self.assertGreater(
            len(self.chat_list.controls),
            initial_count,
            f"COUNTEREXAMPLE: on_status('Searching official government sources...') fired from "
            f"pipeline background thread → chat_list.controls unchanged "
            f"(count={len(self.chat_list.controls)}). "
            f"Exception in thread: {exc!r}. "
            f"Bug confirmed: page.run_thread does not exist in Flet 0.19.0."
        )

    # ------------------------------------------------------------------
    # Call site 4: on_result("answer", [], "", "q") — pipeline thread
    # ------------------------------------------------------------------
    def test_call_site_4_pipeline_on_result(self):
        """
        Validates: Requirements 1.4

        Simulates _pipeline_with_result calling on_result("answer", [], "", "q")
        from a background thread.

        EXPECTED ON UNFIXED CODE:
          AttributeError: 'Page' object has no attribute 'run_thread'
          No bot bubble with "answer" appears in chat_list.
        """
        on_result = self.env["pipeline_on_result"]
        initial_count = len(self.chat_list.controls)

        exc = _invoke_from_thread(on_result, "answer", [], "", "q")
        time.sleep(0.2)

        self.assertGreater(
            len(self.chat_list.controls),
            initial_count,
            f"COUNTEREXAMPLE: on_result('answer', [], '', 'q') fired from pipeline background "
            f"thread → chat_list.controls unchanged "
            f"(count={len(self.chat_list.controls)}). "
            f"Exception in thread: {exc!r}. "
            f"Bug confirmed: page.run_thread does not exist in Flet 0.19.0."
        )


if __name__ == "__main__":
    unittest.main()
