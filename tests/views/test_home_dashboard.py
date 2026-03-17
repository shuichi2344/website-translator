"""Tests for the home dashboard UI — Tasks 1-3 checkpoint.

Covers:
- Pure utility functions: is_valid_url, is_valid_extension
- build_home_view returns an ft.View without raising
"""
from __future__ import annotations

import flet as ft
import pytest

from app.views.home import is_valid_url, is_valid_extension, build_home_view
from app.state import AppState


# ---------------------------------------------------------------------------
# Minimal mock for ft.Page (no real Flet event loop needed)
# ---------------------------------------------------------------------------

class MockPage:
    def __init__(self):
        self.overlay = []
        self.route = "/home"

    def update(self):
        pass

    def go(self, route):
        pass


# ---------------------------------------------------------------------------
# is_valid_url
# ---------------------------------------------------------------------------

class TestIsValidUrl:
    def test_http_url(self):
        assert is_valid_url("http://example.com") is True

    def test_https_url(self):
        assert is_valid_url("https://example.com") is True

    def test_ftp_url(self):
        assert is_valid_url("ftp://example.com") is False

    def test_empty_string(self):
        assert is_valid_url("") is False

    def test_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_partial_http(self):
        assert is_valid_url("http:/") is False

    def test_https_with_path(self):
        assert is_valid_url("https://gov.my/page?q=1") is True


# ---------------------------------------------------------------------------
# is_valid_extension
# ---------------------------------------------------------------------------

class TestIsValidExtension:
    def test_pdf_lowercase(self):
        assert is_valid_extension(".pdf") is True

    def test_pdf_uppercase(self):
        assert is_valid_extension(".PDF") is True

    def test_docx(self):
        assert is_valid_extension(".docx") is True

    def test_png(self):
        assert is_valid_extension(".png") is True

    def test_jpg(self):
        assert is_valid_extension(".jpg") is True

    def test_jpeg(self):
        assert is_valid_extension(".jpeg") is True

    def test_exe_rejected(self):
        assert is_valid_extension(".exe") is False

    def test_txt_rejected(self):
        assert is_valid_extension(".txt") is False

    def test_mixed_case(self):
        assert is_valid_extension(".Pdf") is True

    def test_empty_string(self):
        assert is_valid_extension("") is False


# ---------------------------------------------------------------------------
# build_home_view — smoke test (no real Flet page needed)
# ---------------------------------------------------------------------------

class TestBuildHomeView:
    def test_returns_ft_view(self):
        page = MockPage()
        state = AppState()
        view = build_home_view(page, state)
        assert isinstance(view, ft.View)

    def test_view_route_is_home(self):
        page = MockPage()
        state = AppState()
        view = build_home_view(page, state)
        assert view.route == "/home"

    def test_file_picker_added_to_overlay(self):
        page = MockPage()
        state = AppState()
        build_home_view(page, state)
        assert any(isinstance(c, ft.FilePicker) for c in page.overlay)

    def test_dark_mode_builds_without_error(self):
        page = MockPage()
        state = AppState(theme_mode="Dark")
        view = build_home_view(page, state)
        assert isinstance(view, ft.View)

    def test_large_font_builds_without_error(self):
        page = MockPage()
        state = AppState(font_size="Large")
        view = build_home_view(page, state)
        assert isinstance(view, ft.View)
