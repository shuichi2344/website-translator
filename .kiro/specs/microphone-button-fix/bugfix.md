# Bugfix Requirements Document

## Introduction

The microphone button on the home page appears to start recording (visual feedback activates) but no status bubbles appear during processing, and no result is ever shown in the chat. The root cause is that `home.py` uses `page.run_thread()` to marshal UI updates from background threads back onto the Flet UI thread, but `page.run_thread()` does not exist in Flet 0.19.0. This means every callback from the STT and pipeline threads that attempts to add a bubble or update the page silently fails, leaving the UI frozen after the mic button is released.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the user presses and releases the microphone button THEN the system shows recording visuals but never displays any status bubbles during STT processing

1.2 WHEN the STT background thread calls `_add_bubble_safe()` to report progress THEN the system raises an `AttributeError` because `page.run_thread()` does not exist in Flet 0.19.0, silently swallowing the update

1.3 WHEN the STT processing completes and `_on_stt_result` fires THEN the system fails to add the transcribed user bubble to the chat list because the UI thread callback mechanism is broken

1.4 WHEN the pipeline background thread calls `on_status` or `on_result` callbacks THEN the system does not render any status or answer bubbles in the chat

### Expected Behavior (Correct)

2.1 WHEN the user presses and releases the microphone button THEN the system SHALL display status bubbles in the chat list for each processing step (e.g. "Transcribing audio...", "Analysing dialect...", "Searching official government sources...")

2.2 WHEN a background thread calls `_add_bubble_safe()` THEN the system SHALL safely marshal the UI update onto the Flet UI thread using a method compatible with Flet 0.19.0 (e.g. calling `page.update()` directly from the thread, or using `page.invoke_async` / a thread-safe queue pattern)

2.3 WHEN the STT processing completes THEN the system SHALL add the transcribed question as a user bubble in the chat list

2.4 WHEN the pipeline completes THEN the system SHALL display the final answer as a bot bubble in the chat list

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the user types a message and presses Enter or the send button THEN the system SHALL CONTINUE TO add the message as a user bubble without invoking the microphone or STT pipeline

3.2 WHEN the user taps the microphone button while text is already in the chat field THEN the system SHALL CONTINUE TO submit the typed text instead of starting a recording session

3.3 WHEN the microphone button is held and released THEN the system SHALL CONTINUE TO show the red pulsing animation during recording and revert to the default mic icon after release

3.4 WHEN the document or web panel is open THEN the system SHALL CONTINUE TO function independently of the microphone button fix
