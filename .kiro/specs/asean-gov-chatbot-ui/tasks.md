# Implementation Plan: ASEAN Gov Chatbot UI

## Overview

Refactor `main.py` into the `app/` package structure, implement `AppState` with local JSON persistence,
build all screens with the new minimalistic theme, wire light/dark mode and font size, implement
reusable accessible components, and cover everything with unit and property-based tests.

## Tasks

- [x] 1. Scaffold the `app/` package and install test dependencies
  - Create `app/__init__.py`, `app/views/`, `app/components/` directories with empty `__init__.py` files
  - Create `tests/` directory with empty `__init__.py`
  - Add `hypothesis` and `pytest` to `requirements.txt`
  - _Requirements: 1.1_

- [x] 2. Implement `AppState` and JSON persistence (`app/state.py`)
  - [x] 2.1 Implement `AppState` dataclass with all fields and derived helpers (`font_sp`, `bg_color`, `text_color`, `surface_color`)
    - Fields: `username`, `language`, `country`, `font_size`, `theme_mode`, `onboarding_complete`
    - _Requirements: 1.6, 1.7, 1.8, 2.1, 8.1, 10.1_
  - [x] 2.2 Implement `load_state(username)` and `save_state(state)` with atomic write, corrupt-file fallback, and field validation
    - `save_state` writes to a temp file then renames; catches `OSError` and raises `PreferencesSaveError`
    - `load_state` catches `FileNotFoundError` and `json.JSONDecodeError`, returns default `AppState` with `onboarding_complete=False`
    - Invalid field values are reset to defaults on load
    - _Requirements: 2.1, 2.4, 7.2, 7.3, 7.5_
  - [ ]* 2.3 Write unit tests for `AppState` and persistence (`tests/test_state.py`)
    - Test `font_sp()` returns 14/16/20 for Small/Medium/Large
    - Test `bg_color()`/`text_color()` for both theme modes
    - Test `load_state` on missing file returns `onboarding_complete=False`
    - Test `load_state` on corrupt JSON returns `onboarding_complete=False`
    - Test `save_state` then `load_state` round-trip equality
    - _Requirements: 1.6, 1.7, 1.8, 2.1, 2.4_
  - [ ]* 2.4 Write property test: Preferences persistence round-trip (Property 2)
    - `# Feature: asean-gov-chatbot-ui, Property 2: Preferences persistence round-trip`
    - For any valid `AppState`, `load_state(save_state(state).username)` must equal original state
    - Use `@settings(max_examples=200)`
    - _Requirements: 2.1, 4.5, 5.5, 6.5, 7.2, 7.3, 8.3, 10.6_
  - [ ]* 2.5 Write property test: Font size mapping correctness (Property 1)
    - `# Feature: asean-gov-chatbot-ui, Property 1: Font size mapping correctness`
    - For any valid `font_size`, `font_sp()` returns exactly 14, 16, or 20
    - _Requirements: 1.6, 1.7, 1.8, 1.9_

- [x] 3. Implement theme helpers and accessible controls (`app/components/`)
  - [x] 3.1 Implement `app/components/theme.py` with `ACCENT`, `ACCENT_DARK` constants and `apply_theme(page, state)`
    - `apply_theme` sets `page.theme_mode` and `page.bgcolor` then calls `page.update()`
    - _Requirements: 1.1, 1.2, 8.5, 10.2, 10.3, 10.5_
  - [x] 3.2 Implement `app/components/controls.py` with `primary_button`, `selection_tile`, and `dot_indicator`
    - `primary_button`: min height 52px, min width 200px, accent bgcolor
    - `selection_tile`: min 48×48px touch target, visual highlight when `selected=True`
    - `dot_indicator(total, current)`: row of `total` dots, one filled at `current`
    - _Requirements: 1.3, 3.5, 9.1, 9.4_
  - [ ]* 3.3 Write unit tests for theme helpers and controls (`tests/test_theme.py`)
    - Test `apply_theme` sets correct `page.bgcolor` for Light and Dark
    - Test `primary_button` height/width attributes
    - Test `selection_tile` highlights selected item
    - Test `dot_indicator` returns correct number of dots with correct filled state
    - _Requirements: 1.1, 1.2, 1.3, 3.5, 9.1_
  - [ ]* 3.4 Write property test: Theme colour correctness (Property 8)
    - `# Feature: asean-gov-chatbot-ui, Property 8: Theme colour correctness`
    - For `theme_mode="Light"`, `bg_color()="#FFFFFF"` and `text_color()="#000000"`; for `"Dark"`, luminance checks
    - _Requirements: 8.5, 10.2, 10.3, 10.5_
  - [ ]* 3.5 Write property test: Contrast ratio compliance (Property 9)
    - `# Feature: asean-gov-chatbot-ui, Property 9: Contrast ratio compliance`
    - WCAG relative luminance formula; contrast ratio >= 4.5:1 for both modes
    - _Requirements: 9.2, 10.8_
  - [ ]* 3.6 Write property test: Touch target minimum size (Property 10)
    - `# Feature: asean-gov-chatbot-ui, Property 10: Touch target minimum size`
    - `primary_button` height >= 52, width >= 200; `selection_tile` height >= 48, width >= 48
    - _Requirements: 1.3, 9.1_
  - [ ]* 3.7 Write property test: Dot indicator correctness (Property 6)
    - `# Feature: asean-gov-chatbot-ui, Property 6: Dot indicator correctness`
    - For any `n` and `i` in `[0, n-1]`, row has exactly `n` dots, exactly one filled at position `i`
    - _Requirements: 3.5_

- [x] 4. Implement the router (`app/router.py`)
  - Create `route_change` handler that maps routes to view builders and appends to `page.views`
  - Accept `AppState` instance; pass it to every view builder
  - Handle `/login`, `/onboarding`, `/preferences`, `/home`, `/profile`
  - _Requirements: 2.2, 2.3_
  - [ ]* 4.1 Write unit and property tests for post-login routing (`tests/test_routing.py`)
    - Unit test: `onboarding_complete=False` → route `/onboarding`
    - Unit test: `onboarding_complete=True` → route `/home`
    - Property test (Property 3): for any `AppState`, route is `/onboarding` iff `onboarding_complete=False`
    - `# Feature: asean-gov-chatbot-ui, Property 3: Post-login routing based on onboarding state`
    - _Requirements: 2.2, 2.3_

- [ ] 5. Checkpoint — Ensure all tests pass so far
  - Run `pytest tests/ -v` and confirm all tests pass. Ask the user if any questions arise.

- [x] 6. Implement the login view (`app/views/login.py`)
  - Build `build_login_view(page, state)` returning `ft.View("/login", ...)`
  - White background, centred column, username + password `ft.TextField`, `primary_button` for Login/Register
  - On login: call `load_state(username)`, set `state` fields, check `onboarding_complete`, call `page.go()` accordingly
  - Remove dark/neon/gradient styling from existing login UI; apply `state.bg_color()` and `state.text_color()`
  - Remove country dropdown from signup (country collected in preferences)
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 2.2, 2.3, 2.4_

- [x] 7. Implement the onboarding view (`app/views/onboarding.py`)
  - [x] 7.1 Define `TutorialPage` namedtuple and `TUTORIAL_PAGES` list (5 pages as specified in design)
    - _Requirements: 3.1, 3.7_
  - [x] 7.2 Build `build_onboarding_view(page, state)` with local `current_page` index, icon/title/description layout, `dot_indicator`, Back/Next/"Get Started" buttons
    - Back hidden on page 0; "Get Started" replaces "Next" on page 4
    - Navigation is in-view: increment `current_page` and call `page.update()`
    - On "Get Started": `page.go("/preferences")`
    - Apply `state.font_sp()`, `state.bg_color()`, `state.text_color()`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 1.4_
  - [ ]* 7.3 Write unit tests for onboarding (`tests/test_onboarding.py`)
    - Test `len(TUTORIAL_PAGES) >= 5`
    - Test each page: title <= 8 words, description <= 40 words, icon is not None
    - Test Back hidden on page 0, visible on pages 1–4
    - Test "Get Started" visible only on page 4
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7_
  - [ ]* 7.4 Write property test: Tutorial navigation button visibility (Property 4)
    - `# Feature: asean-gov-chatbot-ui, Property 4: Tutorial navigation button visibility`
    - For any index `i` in `[0, 4]`: Back visible iff `i > 0`; Next visible iff `i < 4`; "Get Started" visible iff `i == 4`
    - _Requirements: 3.2, 3.3, 3.4, 3.6_
  - [ ]* 7.5 Write property test: Tutorial page content constraints (Property 5)
    - `# Feature: asean-gov-chatbot-ui, Property 5: Tutorial page content constraints`
    - For every `TutorialPage`: title <= 8 words, description <= 40 words, icon not None
    - _Requirements: 3.1, 3.7_

- [x] 8. Implement the preferences view (`app/views/preferences.py`)
  - [x] 8.1 Define `SUPPORTED_LANGUAGES` (11 languages) and `ASEAN_COUNTRIES` (11 countries) constants
    - _Requirements: 4.2, 5.2_
  - [x] 8.2 Build `build_preferences_view(page, state)` with three sections: language `selection_tile` list, country `selection_tile` list, font size row with live preview `ft.Text`
    - "Confirm" button disabled until all three fields are non-empty
    - On confirm: update `state`, call `save_state(state)`, set `state.onboarding_complete = True`, `page.go("/home")`
    - On `PreferencesSaveError`: render inline red error `ft.Text`, do not navigate
    - Apply `state.bg_color()`, `state.text_color()`, `state.font_sp()`
    - _Requirements: 4.1, 4.3, 4.4, 4.5, 5.1, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_
  - [ ]* 8.3 Write unit tests for preferences (`tests/test_preferences.py`)
    - Test `ASEAN_COUNTRIES` contains all 11 required countries
    - Test `SUPPORTED_LANGUAGES` contains all 11 required languages
    - Test Confirm button disabled when any field is unset
    - Test Confirm button enabled when all three fields are set
    - Test `PreferencesSaveError` shows inline error and does not navigate
    - _Requirements: 4.2, 4.3, 5.2, 5.3, 6.1, 7.1, 7.5_
  - [ ]* 8.4 Write property test: Confirm button enabled only when all preferences selected (Property 7)
    - `# Feature: asean-gov-chatbot-ui, Property 7: Confirm button enabled only when all preferences selected`
    - For any combination of language/country/font_size (including None), button enabled iff all three are non-None/non-empty
    - _Requirements: 4.3, 5.3, 7.1_

- [x] 9. Implement the home view (`app/views/home.py`)
  - Build `build_home_view(page, state)` by porting existing chat UI from `main.py`
  - Replace dark/neon/gradient styling with `state.bg_color()`, `state.text_color()`, `state.surface_color()`
  - Apply `state.font_sp()` to all text elements
  - Add profile icon button in AppBar that calls `page.go("/profile")`
  - Retain existing file/web mode selection and chat list functionality
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.9_

- [x] 10. Implement the profile view (`app/views/profile.py`)
  - Build `build_profile_view(page, state)` displaying current Language, Country, Font_Size, Theme_Mode
  - Language/Country: `ft.Dropdown` pre-populated with allowed values, current value pre-selected
  - Font_Size: row of three `selection_tile` buttons
  - Theme_Mode: `ft.Switch` (Light/Dark)
  - On any change: update `state`, call `save_state(state)`, call `apply_theme(page, state)` or rebuild font sizes, call `page.update()`
  - Logout button navigates to `/login`; Back button navigates to `/home`
  - Apply `state.bg_color()`, `state.text_color()`, `state.font_sp()`
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 10.1, 10.4, 10.5, 10.6_
  - [ ]* 10.1 Write unit tests for profile view (`tests/test_state.py` or new file)
    - Test profile view controls reflect `state.language`, `state.country`, `state.font_size`, `state.theme_mode`
    - Test updating theme mode calls `apply_theme` and `save_state`
    - Test updating font size calls `save_state` and `page.update`
    - _Requirements: 8.1, 8.3, 8.4, 8.5_
  - [ ]* 10.2 Write property test: Profile screen reflects AppState (Property 11)
    - `# Feature: asean-gov-chatbot-ui, Property 11: Profile screen reflects AppState`
    - For any `AppState`, profile view control values match all four preference fields
    - _Requirements: 8.1, 8.4_

- [x] 11. Wire everything together in `main.py` and `app/router.py`
  - Update `main.py` entry point to instantiate `AppState`, register `route_change` from `app/router.py`, and call `page.go("/login")`
  - Remove all old view-building code from `main.py` (now lives in `app/views/`)
  - Ensure `page.on_route_change` and `page.on_resize` are wired correctly
  - Verify `apply_theme` is called on startup with the loaded state
  - _Requirements: 1.1, 2.2, 2.3_

- [ ] 12. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/ -v` and confirm all tests pass. Ask the user if any questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis`; run with `pytest tests/ -v`
- Requirements 11 and 12 (Browser Extension) are explicitly out of scope
- Backend/AI/ChromaDB integration is out of scope — existing login logic is preserved as-is
