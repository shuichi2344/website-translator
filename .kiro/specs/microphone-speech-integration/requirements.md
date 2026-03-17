# Requirements Document

## Introduction

This feature integrates `engine/speech/main.py` into the microphone button on the home view
(`app/views/home.py`). Currently the microphone button always starts a push-to-talk recording
session regardless of context. The new behaviour is conditional: when no action card (document
or web) is selected, pressing the microphone button triggers the full speech pipeline defined
in `engine/speech/main.py` — recording audio, transcribing it, detecting dialect, normalising
the query, searching official government sources, and returning an answer as chat bubbles.
When a card is selected the existing behaviour is unchanged.

## Glossary

- **Home_View**: The Flet view built by `build_home_view()` in `app/views/home.py`
- **Mic_Button**: The `GestureDetector`/`mic_btn` widget in the chat bar of Home_View
- **Speech_Pipeline**: The end-to-end pipeline in `engine/speech/main.py` that accepts an STT
  result dict and produces a final answer via web scraping, embedding, and LLM response generation
- **PTTSession**: The push-to-talk class in `engine/speech/speech_to_text.py` that records audio
  and produces a result dict with keys `dialect`, `question`, and `query`
- **STT_Result**: A dict with keys `dialect` (str), `question` (str), and `query` (str) produced
  by PTTSession after audio processing
- **Active_Card**: The currently selected action card — either `"document"` or `"web"`;
  `None` when no card is selected
- **No_Card_Mode**: The state where `active_mode[0]` is `None` (no card selected)
- **Card_Mode**: The state where `active_mode[0]` is `"document"` or `"web"`
- **Chat_List**: The `ft.ListView` widget that displays conversation bubbles in Home_View
- **Status_Bubble**: A centred italic pill bubble (role `"status"`) used for pipeline progress messages
- **User_Bubble**: A right-aligned bubble (role `"user"`) showing the transcribed question
- **Bot_Bubble**: A left-aligned bubble (role `"bot"`) showing the pipeline answer
- **run_pipeline_with_stt_result**: A function to be added to `engine/speech/main.py` that
  accepts an STT_Result dict and callback functions, and runs the Speech_Pipeline on a
  background thread

## Requirements

### Requirement 1: Conditional Mic Button Behaviour

**User Story:** As a user, I want the microphone button to behave differently depending on
whether I have selected a document or web card, so that the correct pipeline is triggered
for my current context.

#### Acceptance Criteria

1. WHILE Active_Card is `None`, WHEN the user presses the Mic_Button, THE Home_View SHALL
   start a PTTSession recording session and display the recording visual state (red pulse animation).
2. WHILE Active_Card is `"document"` or `"web"`, WHEN the user presses the Mic_Button,
   THE Home_View SHALL behave exactly as it does today (start recording for the card-specific
   context) without invoking the Speech_Pipeline.
3. WHEN the chat field contains text and the user taps the Mic_Button, THE Home_View SHALL
   submit the typed text regardless of Active_Card state.

### Requirement 2: Speech Pipeline Integration in No-Card Mode

**User Story:** As a user with no card selected, I want to speak a question and receive an
answer from official government sources, so that I can get information hands-free.

#### Acceptance Criteria

1. WHEN a PTTSession recording completes in No_Card_Mode, THE Home_View SHALL pass the
   STT_Result to the Speech_Pipeline via `run_pipeline_with_stt_result`.
2. WHEN the Speech_Pipeline receives an STT_Result, THE Speech_Pipeline SHALL execute the
   following steps in order: government link discovery, web chunk extraction, ChromaDB
   ingestion, semantic query, and LLM response generation.
3. WHEN the Speech_Pipeline begins processing, THE Home_View SHALL display a Status_Bubble
   for each major pipeline step (e.g. "Searching official sources...", "Generating answer...").
4. WHEN the Speech_Pipeline completes successfully, THE Home_View SHALL display the
   transcribed question as a User_Bubble and the final answer as a Bot_Bubble.
5. IF the Speech_Pipeline raises an exception, THEN THE Home_View SHALL display a Status_Bubble
   containing a human-readable error description and SHALL restore the Mic_Button to its
   default visual state.

### Requirement 3: `run_pipeline_with_stt_result` Function

**User Story:** As a developer, I want a clean callable entry point into the speech pipeline
that accepts an STT result and callback functions, so that the UI layer can invoke the pipeline
without importing internal pipeline steps.

#### Acceptance Criteria

1. THE Speech_Pipeline SHALL expose a function `run_pipeline_with_stt_result(stt_result,
   on_status, on_result, on_error, country_suffix)` in `engine/speech/main.py`.
2. WHEN `run_pipeline_with_stt_result` is called, THE Speech_Pipeline SHALL invoke
   `on_status(message: str)` for each major processing step before it begins.
3. WHEN `run_pipeline_with_stt_result` completes successfully, THE Speech_Pipeline SHALL
   invoke `on_result(answer: str, links: list, dialect: str, question: str)` exactly once.
4. IF `run_pipeline_with_stt_result` encounters an unrecoverable error, THEN THE
   Speech_Pipeline SHALL invoke `on_error(exception: Exception)` exactly once and SHALL
   NOT invoke `on_result`.
5. THE Speech_Pipeline SHALL accept `country_suffix` as a parameter and SHALL use it for
   government link discovery instead of a module-level constant.

### Requirement 4: PTTSession Callback Interface

**User Story:** As a developer, I want PTTSession to fire callbacks for status, result, and
error events, so that the UI can react to recording progress without polling.

#### Acceptance Criteria

1. THE PTTSession SHALL accept `on_result`, `on_error`, and `on_status` as constructor
   parameters.
2. WHEN PTTSession completes audio processing, THE PTTSession SHALL invoke
   `on_result(stt_result: dict)` with the STT_Result dict.
3. IF PTTSession encounters an error during recording or processing, THEN THE PTTSession
   SHALL invoke `on_error(exception: Exception)`.
4. WHEN PTTSession begins transcription or LLM processing, THE PTTSession SHALL invoke
   `on_status(message: str)` with a human-readable progress message.
5. THE PTTSession SHALL invoke each callback from the background processing thread, and
   THE Home_View SHALL be responsible for marshalling UI updates to the Flet UI thread.

### Requirement 5: Thread Safety and UI Updates

**User Story:** As a developer, I want all pipeline callbacks to safely update the Flet UI
from background threads, so that chat bubbles appear reliably without race conditions.

#### Acceptance Criteria

1. WHEN a background thread invokes `_add_bubble_safe(text, role)`, THE Home_View SHALL
   append the bubble to Chat_List and call `page.update()` using a method compatible with
   Flet 0.19.0.
2. WHILE the Speech_Pipeline is running, THE Home_View SHALL keep the Mic_Button in its
   recording visual state until `on_result` or `on_error` is received.
3. WHEN `on_result` or `on_error` is received, THE Home_View SHALL restore the Mic_Button
   to its default visual state (accent colour, standard size, no pulse ring).

### Requirement 6: No Regression on Existing Behaviour

**User Story:** As a developer, I want all existing home view interactions to continue working
after this integration, so that the feature does not break the document or web card flows.

#### Acceptance Criteria

1. WHEN the user selects the document card and uses the file picker, THE Home_View SHALL
   continue to display the document panel and accept file uploads without invoking the
   Speech_Pipeline.
2. WHEN the user selects the web card and enters a URL, THE Home_View SHALL continue to
   validate the URL and display the web panel without invoking the Speech_Pipeline.
3. WHEN the user types a message and presses Enter, THE Home_View SHALL continue to add a
   User_Bubble and clear the chat field without invoking the Speech_Pipeline.
4. WHEN the user switches between No_Card_Mode and Card_Mode, THE Home_View SHALL correctly
   update the Mic_Button behaviour for the new mode without requiring a page reload.
