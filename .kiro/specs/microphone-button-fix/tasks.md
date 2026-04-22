# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Background Thread UI Updates Silently Dropped
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate `page.run_thread()` does not exist in Flet 0.19.0
  - **Scoped PBT Approach**: Scope the property to the four concrete failing call sites — `on_status`, `_on_stt_result`, `_on_stt_error`, `on_result` — each fired from a background thread
  - Mock `flet.Page` WITHOUT a `run_thread` attribute (matches Flet 0.19.0 reality)
  - For each of the four call sites, invoke the callback from a background thread and assert the bubble appears in `chat_list.controls`
  - Bug condition: `call_context.caller IN [PTTSession._process, _pipeline_with_result] AND call_context.thread != UI_THREAD AND page.run_thread IS NOT DEFINED`
  - Expected behavior: bubble with correct text and role is appended to `chat_list` and `page.update()` is called
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with `AttributeError: 'Page' object has no attribute 'run_thread'` and `chat_list.controls` remains empty — this proves the bug exists
  - Document counterexamples found (e.g. `on_status("Transcribing audio...")` → `chat_list` empty, `AttributeError` raised)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Text Submit and UI Interactions Unchanged
  - **IMPORTANT**: Follow observation-first methodology — run UNFIXED code first, observe outputs, then encode as properties
  - Observe: `on_chat_submit("hello")` adds a user bubble and clears `chat_field` on unfixed code
  - Observe: tapping mic while `chat_field` has text calls `on_chat_submit` rather than starting recording on unfixed code
  - Observe: `_start_recording()` / `_stop_recording()` toggle the mic icon and pulse animation correctly on unfixed code
  - Observe: document/web panel open/close is unaffected by `_ui()` on unfixed code
  - Write property-based tests: for all non-background-thread UI interactions (where `isBugCondition` is false), behavior is identical before and after the fix
  - Non-bug condition: inputs that do NOT involve a background-thread call through `_ui()` — mouse clicks, keyboard input, panel toggles, mic animation state changes
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for broken `_ui()` helper in `app/views/home.py`

  - [x] 3.1 Implement the fix
    - In `app/views/home.py`, locate the `_ui(fn)` helper defined inside `build_home_view`
    - Replace `page.run_thread(fn)` with `fn()` directly
    - Updated helper: `def _ui(fn): fn()  # Flet 0.19.0 — page.update() is thread-safe`
    - No other files need to change — `_add_bubble_safe`, `_on_stt_status`, `_on_stt_error`, `_on_stt_result`, `on_status`, `on_result` are all already correct
    - _Bug_Condition: `isBugCondition(ctx)` where `ctx.caller IN [PTTSession._process, _pipeline_with_result] AND ctx.thread != UI_THREAD AND page.run_thread IS NOT DEFINED`_
    - _Expected_Behavior: every `_add_bubble_safe(text, role)` call appends a bubble to `chat_list` and calls `page.update()` successfully_
    - _Preservation: all inputs where `isBugCondition` is false (text submit, mic animation, panel open/close) produce identical behavior before and after the fix_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Background Thread UI Updates Appear in Chat
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (bubble appended, `page.update()` called)
    - When this test passes, it confirms the fix is correct
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — no more `AttributeError`, bubbles appear in `chat_list`)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Text Submit and UI Interactions Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions — text submit, mic animation, panel behaviors all unchanged)
    - Confirm all tests still pass after fix

- [x] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite and confirm both the bug condition test and preservation tests pass
  - Ensure all tests pass; ask the user if any questions arise
