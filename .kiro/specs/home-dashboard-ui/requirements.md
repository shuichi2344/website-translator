# Requirements Document

## Introduction

This feature redesigns the `/home` screen of the ASEAN Gov Chat Flet application into a sleek, high-end mobile dashboard. The design continues the minimalist iOS aesthetic established in the login screen, using a stark white / sophisticated slate-gray palette with vibrant accent colors used sparingly. The layout follows a **Progressive Disclosure** principle: the screen opens with two large, rounded action cards at its center; when the user activates a card, a context-specific input area (URL field or file drag-and-drop zone) glides up from below the cards, just above the persistent bottom chat bar. The bottom of the screen always shows a single-line text input chat bar with a microphone / speech-input icon on the far right.

## Glossary

- **Dashboard**: The redesigned `/home` screen of the App.
- **Action_Card**: One of the two large, rounded interactive cards displayed in the center of the Dashboard — either "Analyze Document / Image" or "Extract from Web Link."
- **Document_Card**: The Action_Card that triggers the file drag-and-drop input area.
- **Web_Card**: The Action_Card that triggers the URL input area.
- **Context_Input_Area**: The context-specific input panel (URL field or file drag-and-drop zone) that slides up above the Chat_Bar when an Action_Card is activated.
- **Chat_Bar**: The persistent single-line text input bar fixed at the bottom of the Dashboard, containing a text field and a microphone icon for speech input.
- **Speech_Input**: Voice-to-text input triggered by tapping the microphone icon in the Chat_Bar.
- **Progressive_Disclosure**: A UX pattern where secondary controls are revealed only when the user needs them, keeping the initial view uncluttered.
- **Accent_Color**: A vibrant color used sparingly for borders, icons, and interactive highlights (e.g. a muted indigo or teal derived from the existing `ACCENT` token).
- **Surface_Color**: The card and input background color derived from `state.surface_color()`.
- **App**: The Flet-based Python AI chatbot application.
- **AppState**: The existing application state dataclass in `app/state.py`.
- **Theme_Mode**: The User's chosen display mode — Light_Mode or Dark_Mode — as stored in AppState.

---

## Requirements

### Requirement 1: Dashboard Layout and Visual Hierarchy

**User Story:** As a user, I want a clean, uncluttered home screen that immediately shows me what I can do, so that I can start a task without confusion.

#### Acceptance Criteria

1. THE Dashboard SHALL display two Action_Cards centered vertically in the main content area, with equal width and equal height.
2. THE Dashboard SHALL render each Action_Card with a `border_radius` of 20 and a subtle Accent_Color border.
3. THE Dashboard SHALL display a prominent icon and a short label on each Action_Card — "Analyze Document / Image" (using `ft.icons.UPLOAD_FILE_OUTLINED`) and "Extract from Web Link" (using `ft.icons.LANGUAGE_OUTLINED`).
4. THE Dashboard SHALL use a white (`#FFFFFF`) background in Light_Mode and a dark (`#121212`) background in Dark_Mode, consistent with the existing Theme_Mode system.
5. THE Dashboard SHALL apply soft drop-shadow or elevation styling to each Action_Card to convey depth without harsh contrast.
6. THE Dashboard SHALL display the App's name or a greeting text above the Action_Cards as a page header.
7. THE Dashboard SHALL maintain the existing AppBar with the app title centered and a profile icon on the right, consistent with the current `build_home_view` implementation.

---

### Requirement 2: Persistent Chat Bar

**User Story:** As a user, I want a chat input bar always visible at the bottom of the screen, so that I can type or speak a question at any time without navigating away.

#### Acceptance Criteria

1. THE Chat_Bar SHALL be fixed at the bottom of the Dashboard at all times, regardless of which Action_Card (if any) is active.
2. THE Chat_Bar SHALL contain a single-line text input field that accepts free-text questions.
3. THE Chat_Bar SHALL display a microphone icon (`ft.icons.CHAT_BUBBLE_OUTLINE_ROUNDED` customized for speech input) on the far right of the Chat_Bar.
4. WHEN the user taps the microphone icon, THE Chat_Bar SHALL activate Speech_Input mode.
5. THE Chat_Bar SHALL use the Surface_Color as its background and the Accent_Color for its border and icon tint.
6. THE Chat_Bar SHALL render with a `border_radius` of 20 to match the Action_Card aesthetic.
7. WHEN the user submits text via the Chat_Bar, THE Dashboard SHALL append the message to the chat history and display the AI response.

---

### Requirement 3: Progressive Disclosure — Context Input Area

**User Story:** As a user, I want the relevant input controls to appear only after I choose an action, so that the screen stays clean until I need them.

#### Acceptance Criteria

1. WHEN the user taps the Document_Card, THE Dashboard SHALL reveal the Context_Input_Area containing a file drag-and-drop zone above the Chat_Bar.
2. WHEN the user taps the Web_Card, THE Dashboard SHALL reveal the Context_Input_Area containing a URL text field above the Chat_Bar.
3. THE Context_Input_Area SHALL animate into view (slide up) from below the Action_Cards, appearing between the Action_Cards and the Chat_Bar.
4. WHEN the Context_Input_Area is visible, THE Dashboard SHALL visually indicate which Action_Card is active (e.g. highlighted border or filled background).
5. THE Context_Input_Area SHALL include a dismiss or "Back" control that hides the Context_Input_Area and returns the Dashboard to its default state.
6. WHILE the Context_Input_Area is visible, THE Action_Cards SHALL remain visible above it so the user can switch modes without tapping "Back" first.
7. IF the user taps the inactive Action_Card while the Context_Input_Area is visible, THEN THE Dashboard SHALL switch the Context_Input_Area to the input type corresponding to the newly tapped card.

---

### Requirement 4: Document / Image Input

**User Story:** As a user, I want to drag and drop or select a file from my device, so that I can analyze a government document or image.

#### Acceptance Criteria

1. WHEN the Document_Card is active, THE Context_Input_Area SHALL display a clearly labeled drag-and-drop zone with a file icon and the label "Drop a file here, or tap to browse."
2. WHEN the user selects a file, THE Context_Input_Area SHALL display the selected file's name and a remove/clear control.
3. THE Context_Input_Area SHALL accept common document and image formats: PDF, DOCX, PNG, JPG, and JPEG.
4. IF the user selects a file with an unsupported format, THEN THE Dashboard SHALL display an inline error message specifying the accepted formats.
5. WHEN a valid file is selected, THE Context_Input_Area SHALL enable a "Analyze" submit button styled with the Accent_Color.

---

### Requirement 5: Web Link Input

**User Story:** As a user, I want to paste a government website URL, so that the app can extract and summarize information from that page.

#### Acceptance Criteria

1. WHEN the Web_Card is active, THE Context_Input_Area SHALL display a URL text field with the placeholder "Paste a government website URL."
2. WHEN the user enters text in the URL field, THE Dashboard SHALL validate that the input begins with `http://` or `https://`.
3. IF the URL field contains text that does not begin with `http://` or `https://`, THEN THE Dashboard SHALL display an inline validation error below the URL field.
4. WHEN a valid URL is entered, THE Context_Input_Area SHALL enable an "Extract" submit button styled with the Accent_Color.
5. WHEN the user submits a valid URL, THE Dashboard SHALL display a loading indicator while the extraction is in progress.

---

### Requirement 6: Theme Consistency

**User Story:** As a user, I want the dashboard to look and feel consistent with the rest of the app, so that the experience feels polished and unified.

#### Acceptance Criteria

1. THE Dashboard SHALL derive all colors from the existing `AppState` helper methods (`bg_color()`, `text_color()`, `surface_color()`) and the `ACCENT` / `ACCENT_DARK` tokens in `app/components/theme.py`.
2. WHEN the user changes Theme_Mode on the Profile_Screen, THE Dashboard SHALL reflect the updated theme immediately without requiring a restart.
3. THE Dashboard SHALL use the User's selected Font_Size (via `state.font_sp()`) for all text elements.
4. THE Dashboard SHALL not introduce any new hardcoded color values outside of the existing theme token system.

---

### Requirement 7: Accessibility and Touch Targets

**User Story:** As a user with limited dexterity or visual impairment, I want all interactive elements to be easy to tap and clearly labeled, so that I can use the dashboard without frustration.

#### Acceptance Criteria

1. THE Dashboard SHALL render each Action_Card with a minimum height of 140 logical pixels and a minimum width of 140 logical pixels.
2. THE Dashboard SHALL render the Chat_Bar text input with a minimum height of 52 logical pixels.
3. THE Dashboard SHALL render the microphone icon button with a minimum touch target of 48×48 logical pixels.
4. THE Dashboard SHALL provide a visible focus indicator on all interactive elements when navigated via keyboard or assistive technology.
5. THE Dashboard SHALL use plain, descriptive labels on all buttons and cards (no icons-only controls without accompanying text labels).

---

### Requirement 8: Speech Input

**User Story:** As a user who prefers voice interaction, I want to tap a microphone button and speak my question, so that I don't have to type.

#### Acceptance Criteria

1. WHEN the user taps the microphone icon in the Chat_Bar, THE Dashboard SHALL request microphone permission if not already granted.
2. WHEN microphone permission is granted and Speech_Input is active, THE Chat_Bar SHALL display a visual indicator (e.g. animated pulse or color change) to show that recording is in progress.
3. WHEN the user stops speaking, THE Dashboard SHALL transcribe the speech and populate the Chat_Bar text field with the transcribed text.
4. IF microphone permission is denied, THEN THE Dashboard SHALL display an inline message explaining that microphone access is required for speech input.
5. WHEN Speech_Input produces a transcription, THE Dashboard SHALL allow the user to review and edit the text before submitting.
