# Microphone Button Fix — Bugfix Design

## Overview

The microphone button on the home page (`app/views/home.py`) silently fails to display any
status bubbles or results after recording. The root cause is a single helper function `_ui()`
that calls `page.run_thread()`, which does not exist in Flet 0.19.0. Every UI update marshalled
through this helper from a background thread raises an `AttributeError` that is swallowed,
leaving the chat list empty after the mic is released.

The fix is minimal: replace `page.run_thread(fn)` with a direct call pattern that is compatible
with Flet 0.19.0. In Flet 0.19.0, calling `page.update()` directly from a background thread is
safe and sufficient — no special marshalling helper is needed.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — a UI update callback is dispatched
  from a background thread via `_ui()` / `page.run_thread()`, which does not exist in Flet 0.19.0
- **Property (P)**: The desired behavior — every bubble added via `_add_bubble_safe()` must appear
  in `chat_list` and the page must visually update
- **Preservation**: Existing text-submit, mic animation, and panel behaviors that must remain
  unchanged by the fix
- **`_ui(fn)`**: The broken helper in `app/views/home.py` that calls `page.run_thread(fn)`
- **`_add_bubble_safe(text, role)`**: The thread-safe bubble dispatcher that calls `_ui()`
- **`PTTSession`**: The push-to-talk class in `engine/speech/speech_to_text.py` that runs
  transcription on a background thread and fires `on_status` / `on_result` / `on_error` callbacks
- **`_pipeline_with_result`**: The full gov-search → RAG → answer pipeline in `engine/speech/main.py`
  that fires `on_status` and `on_result` callbacks from a background thread

## Bug Details

### Bug Condition

The bug manifests whenever a background thread (PTTSession or pipeline) calls `_add_bubble_safe()`
to push a UI update. The `_ui()` helper attempts `page.run_thread(fn)`, which raises
`AttributeError: 'Page' object has no attribute 'run_thread'` in Flet 0.19.0. The exception is
not caught, so the update is silently dropped.

**Formal Specification:**
```
FUNCTION isBugCondition(call_context)
  INPUT: call_context — describes who is calling _add_bubble_safe and from where
  OUTPUT: boolean

  RETURN call_context.caller IN [PTTSession._process, _pipeline_with_result]
         AND call_context.thread != UI_THREAD
         AND page.run_thread IS NOT DEFINED   -- Flet 0.19.0
END FUNCTION
```

### Examples

- User presses mic, speaks, releases → "Transcribing audio..." status bubble **never appears**
  (expected: status bubble visible in chat list)
- STT completes → user's transcribed question bubble **never appears**
  (expected: user bubble with transcribed text visible)
- Pipeline fires `on_status("Searching official government sources...")` → **no bubble**
  (expected: status pill visible in chat list)
- Pipeline fires `on_result(answer, ...)` → bot answer bubble **never appears**
  (expected: bot bubble with answer visible)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Typing a message and pressing Enter or the send button must continue to add a user bubble
  without touching the microphone or STT pipeline
- When the chat field contains text, tapping the mic button must continue to submit the typed
  text instead of starting a recording session
- Holding and releasing the mic button must continue to show the red pulsing animation during
  recording and revert to the default mic icon after release
- The document panel (file picker, drop zone) and web panel (URL field) must continue to
  function independently of this fix

**Scope:**
All inputs that do NOT involve a background-thread UI callback (i.e., `isBugCondition` is false)
must be completely unaffected. This includes:
- Mouse clicks on action cards, send button, file picker
- Keyboard text input and Enter-to-submit
- Panel open/close animations
- Theme and font size state

## Hypothesized Root Cause

Based on code inspection of `app/views/home.py` lines ~290–295:

1. **Non-existent API**: `page.run_thread()` was used as a thread-marshalling helper but this
   method does not exist on `flet.Page` in version 0.19.0. The correct approach in Flet 0.19.0
   is to call `page.update()` directly from the background thread — Flet's internal event loop
   handles thread safety.

2. **Silent failure**: Python's `AttributeError` is raised inside the background thread but
   nothing catches it at the call site in `_add_bubble_safe`, so the exception is swallowed and
   the UI never updates.

3. **All downstream callbacks broken**: Because `_add_bubble_safe` is the single path for all
   background-thread UI updates (`_on_stt_status`, `_on_stt_error`, `_on_stt_result`,
   `on_status`, `on_result`, `on_error` in the pipeline), every single bubble is affected.

## Correctness Properties

Property 1: Bug Condition — Background Thread UI Updates Appear in Chat

_For any_ call to `_add_bubble_safe(text, role)` originating from a background thread
(PTTSession or pipeline), the fixed `_ui()` helper SHALL successfully append a bubble with
the given text and role to `chat_list` and call `page.update()`, making the bubble visible
to the user.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation — Text Submit and UI Interactions Unchanged

_For any_ input where the bug condition does NOT hold (text submission via Enter/send button,
mic animation state changes, panel open/close, file picker interactions), the fixed code SHALL
produce exactly the same behavior as the original code, preserving all existing UI interactions
that do not involve background-thread bubble dispatch.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `app/views/home.py`

**Function**: `_ui(fn)` (defined inside `build_home_view`)

**Specific Changes**:

1. **Remove `page.run_thread(fn)`**: Delete the call to the non-existent method.

2. **Call `fn()` directly**: In Flet 0.19.0, background threads can safely call `page.update()`
   directly. The `_add_bubble_safe` wrapper already wraps the mutation + update in a closure `_do`,
   so calling `fn()` (i.e., `_do()`) directly from the background thread is correct and safe.

3. **Updated `_ui` helper**:
   ```python
   def _ui(fn):
       """Run fn() — in Flet 0.19.0, page.update() is thread-safe."""
       fn()
   ```

   This is the minimal one-line change. No new dependencies, no queue, no async machinery.

4. **No changes needed elsewhere**: `_add_bubble_safe`, `_on_stt_status`, `_on_stt_error`,
   `_on_stt_result`, and the pipeline callbacks all already call `_ui()` correctly — only the
   implementation of `_ui` itself is wrong.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate
the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm
or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write unit tests that mock `flet.Page` without a `run_thread` attribute, invoke
`_add_bubble_safe()` from a background thread, and assert that the bubble was appended to
`chat_list`. Run these tests on the UNFIXED code to observe `AttributeError` and confirm the
root cause.

**Test Cases**:
1. **Status bubble from PTTSession**: Simulate `on_status("Transcribing audio...")` callback
   firing from a background thread — assert bubble appears in `chat_list` (fails on unfixed code)
2. **User bubble from STT result**: Simulate `_on_stt_result({"question": "test"})` — assert
   user bubble with "test" appears (fails on unfixed code)
3. **Pipeline status bubble**: Simulate `on_status("Searching official government sources...")`
   from pipeline thread — assert status pill appears (fails on unfixed code)
4. **Pipeline result bubble**: Simulate `on_result("answer", [], "", "q")` — assert bot bubble
   appears (fails on unfixed code)

**Expected Counterexamples**:
- `AttributeError: 'Page' object has no attribute 'run_thread'` raised in background thread
- `chat_list.controls` remains empty after all callbacks fire

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces
the expected behavior.

**Pseudocode:**
```
FOR ALL call_context WHERE isBugCondition(call_context) DO
  result := _add_bubble_safe_fixed(call_context.text, call_context.role)
  ASSERT chat_list contains bubble with call_context.text
  ASSERT page.update() was called
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function
produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT behavior_original(input) = behavior_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for text submission and UI interactions,
then write property-based tests capturing that behavior.

**Test Cases**:
1. **Text submit preservation**: Verify `on_chat_submit` adds a user bubble and clears the field
   on unfixed code, then assert the same after fix
2. **Mic animation preservation**: Verify `_start_recording` / `_stop_recording` toggle visual
   state correctly on unfixed code, then assert the same after fix
3. **Send-mode preservation**: Verify that when `chat_field` has text, tapping mic calls
   `on_chat_submit` rather than starting recording — assert unchanged after fix
4. **Panel independence**: Verify document/web panel open/close is unaffected by the fix

### Unit Tests

- Test `_add_bubble_safe` with a mock `Page` that has no `run_thread` (unfixed) vs. one that
  supports direct `update()` (fixed)
- Test each bubble role ("user", "bot", "status") is appended with correct styling
- Test edge cases: empty text, very long text, rapid successive calls from multiple threads

### Property-Based Tests

- Generate random sequences of `(text, role)` pairs dispatched from background threads and
  verify all bubbles appear in `chat_list` in order
- Generate random non-mic UI interactions (text input, panel toggles) and verify behavior is
  identical before and after the fix
- Test that concurrent calls to `_add_bubble_safe` from multiple threads do not corrupt
  `chat_list.controls`

### Integration Tests

- Full mic press → release → STT → pipeline flow: verify all expected bubbles appear in sequence
- Interleave text submission with mic usage: verify both paths work independently
- Verify the red pulse animation starts on press and stops on release with the fix applied
