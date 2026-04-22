# Implementation Plan: Home Dashboard UI

## Overview

Rebuild `app/views/home.py` into a Progressive Disclosure dashboard using Flet. The implementation proceeds in layers: core layout → action cards → context input area → chat bar → speech input → theme/accessibility polish. All tests live in `tests/views/test_home_dashboard.py`.

## Tasks

- [x] 1. Define ephemeral state and helper utilities
  - [x] 1.1 Add `DashboardState` closure variables and `is_valid_url` / `is_valid_extension` pure functions in `app/views/home.py`
    - Declare `active_mode`, `selected_file`, `url_valid`, `is_recording` as mutable closure vars
    - Implement `is_valid_url(s: str) -> bool` — returns `True` iff `s` starts with `"http://"` or `"https://"`
    - Implement `is_valid_extension(ext: str) -> bool` — returns `True` iff `ext.lower()` is in `{".pdf", ".docx", ".png", ".jpg", ".jpeg"}`
    - _Requirements: 4.3, 5.2_

  - [ ]* 1.2 Write property test for `is_valid_url`
    - **Property 9: URL validation and submit button state are consistent**
    - **Validates: Requirements 5.2, 5.3, 5.4**

  - [ ]* 1.3 Write property test for `is_valid_extension`
    - **Property 8: File format validation is consistent**
    - **Validates: Requirements 4.3, 4.4, 4.5**

- [x] 2. Implement Action Cards and greeting header
  - [x] 2.1 Implement `action_card(title, icon, mode, state, accent, on_click_fn)` factory and greeting `ft.Text` in `app/views/home.py`
    - `border_radius=20`, `border=ft.border.all(2, accent)`, `min_height=140`, `min_width=140`
    - `shadow` with `blur_radius=12`, low-opacity black
    - Active state: `bgcolor` switches to `ft.colors.with_opacity(0.12, accent)`
    - Greeting text: `"How can I help you today?"` sized at `state.font_sp() + 8`, `weight=BOLD`
    - Icons: `ft.icons.UPLOAD_FILE_OUTLINED` (Document), `ft.icons.LANGUAGE_OUTLINED` (Web)
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 3.4, 7.1, 7.5_

  - [ ]* 2.2 Write property test for Action Cards structure
    - **Property 1: Action Cards always present with correct structure**
    - **Validates: Requirements 1.1, 1.2, 1.3, 7.1, 7.5**

  - [ ]* 2.3 Write unit tests for Action Cards
    - `test_action_card_icons` — verify correct icon constants on each card
    - `test_appbar_structure` — AppBar has `center_title=True` and profile `IconButton` in actions
    - `test_greeting_text_present` — greeting `ft.Text` present above cards
    - _Requirements: 1.3, 1.6, 1.7_

- [x] 3. Implement the Context Input Area
  - [x] 3.1 Implement Document Panel inside Context Input Area in `app/views/home.py`
    - Dashed drop-zone `ft.Container` with file icon and label `"Drop a file here, or tap to browse"`
    - Wire `ft.FilePicker` into `page.overlay`; accepted extensions `.pdf .docx .png .jpg .jpeg`
    - Selected-file name display + clear button
    - Inline error `ft.Text` for unsupported formats (hidden by default)
    - `"Analyze"` `ft.ElevatedButton` disabled until valid file selected, styled with `ACCENT`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.2 Implement Web Panel inside Context Input Area in `app/views/home.py`
    - `ft.TextField` placeholder `"Paste a government website URL"`, `on_change` calls `is_valid_url`
    - Inline error `ft.Text` below field (hidden when valid or empty)
    - `"Extract"` `ft.ElevatedButton` disabled until URL valid, styled with `ACCENT`
    - `ft.ProgressRing` hidden by default; shown on submit
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.3 Implement `set_mode(mode)` and Back button wiring
    - `set_mode(None | "document" | "web")` mutates `active_mode`, toggles panel visibility, updates card active styling, calls `page.update()`
    - `"← Back"` `ft.TextButton` calls `set_mode(None)`
    - Switching from one active card to the other swaps panels without going through Idle
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6, 3.7_

  - [ ]* 3.4 Write property tests for Context Input Area visibility
    - **Property 4: Chat Bar always present regardless of active mode**
    - **Property 5: Tapping an Action Card reveals the correct Context Input panel**
    - **Property 6: Action Cards remain visible while Context Input Area is active**
    - **Property 7: Switching active card changes the Context Input panel**
    - **Validates: Requirements 2.1, 3.1, 3.2, 3.6, 3.7**

  - [ ]* 3.5 Write unit tests for Context Input Area
    - `test_document_panel_label` — drop-zone text present
    - `test_url_field_placeholder` — URL field placeholder correct
    - `test_back_button_present` — back control present in Context Input Area
    - `test_loading_indicator_on_submit` — `ft.ProgressRing` visible after valid URL submit
    - _Requirements: 3.5, 4.1, 5.1, 5.5_

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement the Chat Bar
  - [x] 5.1 Build Chat Bar `ft.Container` in `app/views/home.py`
    - `border_radius=20`, `bgcolor=state.surface_color()`, `border=ft.border.all(2, accent)`
    - `ft.TextField` with `expand=True`, `min_height=52`
    - `ft.IconButton` with `icon=ft.icons.MIC_ROUNDED`, `width=48`, `height=48`
    - On text submit: append message to chat history list, trigger AI response stub, call `page.update()`
    - Silently ignore empty submissions
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 7.2, 7.3_

  - [ ]* 5.2 Write property tests for Chat Bar
    - **Property 4: Chat Bar always present regardless of active mode**
    - **Property 10: Chat submission grows the chat history**
    - **Validates: Requirements 2.1, 2.7**

  - [ ]* 5.3 Write unit tests for Chat Bar
    - `test_chat_bar_mic_icon` — ends with `MIC_ROUNDED` `IconButton`
    - `test_chat_bar_text_field_present` — contains `TextField`
    - `test_chat_bar_border_radius` — `border_radius=20`
    - `test_chat_bar_min_height` — `TextField` `min_height >= 52`
    - `test_mic_button_touch_target` — `width=48, height=48`
    - _Requirements: 2.2, 2.3, 2.5, 2.6, 7.2, 7.3_

- [x] 6. Implement Speech Input
  - [x] 6.1 Implement `start_speech_input()` and result/error handlers in `app/views/home.py`
    - Mic button `on_click` sets `is_recording=True`, applies pulse visual on Chat Bar border, calls `page.update()`
    - On transcription result: set `chat_field.value = transcription`, `is_recording=False`, `page.update()`
    - On permission denied: show `ft.SnackBar` with explanation, reset `is_recording=False`
    - Platform dispatch: `page.eval_js` for web target; `page.run_task` + `speech_recognition` for mobile
    - _Requirements: 2.4, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 6.2 Write property tests for Speech Input
    - **Property 11: Speech transcription populates the Chat Bar field**
    - **Property 12: Mic button activates recording state**
    - **Validates: Requirements 8.3, 8.5, 2.4, 8.2**

  - [ ]* 6.3 Write unit tests for Speech Input
    - `test_recording_visual_indicator` — Chat Bar border/color changes when `is_recording=True`
    - `test_permission_denied_message` — permission-denied handler appends `SnackBar` to `page.overlay`
    - _Requirements: 8.2, 8.4_

- [x] 7. Apply theme consistency and accessibility polish
  - [x] 7.1 Audit all `ft.Text` sizes and colors in `app/views/home.py`
    - Replace any hardcoded colors with `state.bg_color()`, `state.text_color()`, `state.surface_color()`, `ACCENT`, or `ACCENT_DARK`
    - Ensure every `ft.Text` size is derived from `state.font_sp()`
    - Add `tooltip` or `semantics_label` to icon-only controls for accessibility
    - _Requirements: 6.1, 6.3, 6.4, 7.4, 7.5_

  - [ ]* 7.2 Write property tests for theme consistency
    - **Property 2: Theme mode determines background and surface colors**
    - **Property 3: Font size applied consistently**
    - **Validates: Requirements 1.4, 6.1, 6.2, 6.3**

- [x] 8. Wire everything into `build_home_view` and integrate with router
  - [x] 8.1 Assemble all components into the final `ft.View` in `app/views/home.py`
    - Stack: AppBar → content `ft.Column(expand=True)` with greeting + action cards → Context Input Area → Chat Bar
    - Register `ft.FilePicker` in `page.overlay` once at build time
    - Verify `app/router.py` routes `"/home"` to the updated `build_home_view`
    - _Requirements: 1.7, 3.3, 6.2_

  - [ ]* 8.2 Write integration tests
    - `test_full_view_builds_without_error` — `build_home_view` returns an `ft.View` without raising
    - `test_mode_cycle_document_web_idle` — simulate card taps through all three states and assert panel visibility
    - _Requirements: 1.1, 3.1, 3.2, 3.5_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- All property tests go in `tests/views/test_home_dashboard.py` using Hypothesis (`@given`, `@settings(max_examples=100)`)
- Tag each property test with `# Feature: home-dashboard-ui, Property N: <text>`
- No new color tokens — all colors from `AppState` helpers and `ACCENT`/`ACCENT_DARK`
- `ft.FilePicker` must be added to `page.overlay` before `page.update()` is called
