from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any

PREFS_DIR = "user_prefs"

ALLOWED_FONT_SIZES = ["Small", "Medium", "Large"]
ALLOWED_THEME_MODES = ["Light", "Dark"]
ALLOWED_LANGUAGES = [
    "English",
    "Bahasa Melayu",
    "Bahasa Indonesia",
    "Thai",
    "Vietnamese",
    "Filipino/Tagalog",
    "Burmese",
    "Khmer",
    "Lao",
    "Chinese (Simplified)",
    "Tamil",
]
ALLOWED_COUNTRIES = [
    "Malaysia",
    "Indonesia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Singapore",
    "Brunei",
    "Timor-Leste",
]


class PreferencesSaveError(Exception):
    """Raised when saving user preferences to disk fails."""


@dataclass
class AppState:
    username: str = ""
    user_id: str = ""  # MySQL user ID
    email: str = ""  # User email
    language: str = "English"
    country: str = "Malaysia"
    font_size: str = "Medium"
    theme_mode: str = "Light"
    onboarding_complete: bool = False
    conversation_id: str = ""  # Current conversation ID
    # Runtime-only (not persisted)
    session: Any | None = None
    stream: Any | None = None

    def font_sp(self) -> int:
        return {"Small": 14, "Medium": 16, "Large": 20}[self.font_size]

    def bg_color(self) -> str:
        return "#F5F3FF" if self.theme_mode == "Light" else "#0F0B1A"

    def text_color(self) -> str:
        return "#1E1B2E" if self.theme_mode == "Light" else "#EDE9FE"

    def surface_color(self) -> str:
        return "#EDE9FE" if self.theme_mode == "Light" else "#1C1730"


def load_state(username: str) -> AppState:
    """Load preferences from user_prefs/{username}.json.

    Returns a default AppState (onboarding_complete=False) if the file is
    missing or contains invalid JSON. Invalid field values are reset to their
    defaults rather than causing a crash.
    """
    path = os.path.join(PREFS_DIR, f"{username}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return AppState(onboarding_complete=False)

    defaults = AppState()

    language = data.get("language", defaults.language)
    if language not in ALLOWED_LANGUAGES:
        language = defaults.language

    country = data.get("country", defaults.country)
    if country not in ALLOWED_COUNTRIES:
        country = defaults.country

    font_size = data.get("font_size", defaults.font_size)
    if font_size not in ALLOWED_FONT_SIZES:
        font_size = defaults.font_size

    theme_mode = data.get("theme_mode", defaults.theme_mode)
    if theme_mode not in ALLOWED_THEME_MODES:
        theme_mode = defaults.theme_mode

    onboarding_complete = data.get("onboarding_complete", False)
    if not isinstance(onboarding_complete, bool):
        onboarding_complete = False

    return AppState(
        username=username,
        user_id=data.get("user_id", ""),
        email=data.get("email", ""),
        language=language,
        country=country,
        font_size=font_size,
        theme_mode=theme_mode,
        onboarding_complete=onboarding_complete,
    )


def save_state(state: AppState) -> None:
    """Atomically write state to user_prefs/{state.username}.json.

    Creates the directory if it does not exist. Writes to a temp file first,
    then renames to avoid partial writes. Raises PreferencesSaveError on any
    OSError.
    """
    try:
        os.makedirs(PREFS_DIR, exist_ok=True)
        target = os.path.join(PREFS_DIR, f"{state.username}.json")
        # Persist only user preferences; runtime objects like session/stream
        # are not JSON-serializable and should not be written to disk.
        data = {
            "username": state.username,
            "user_id": state.user_id,
            "email": state.email,
            "language": state.language,
            "country": state.country,
            "font_size": state.font_size,
            "theme_mode": state.theme_mode,
            "onboarding_complete": state.onboarding_complete,
        }
        dir_name = os.path.dirname(os.path.abspath(target))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, target)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as exc:
        raise PreferencesSaveError(f"Failed to save preferences: {exc}") from exc
