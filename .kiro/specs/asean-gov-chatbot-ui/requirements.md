# Requirements Document

## Introduction

This feature covers a complete UI redesign and new onboarding flow for an existing Flet (Python) AI chatbot application. The app helps users summarise and answer questions based on ASEAN government websites and documents. The redesign targets elderly and less tech-savvy users, adopting a minimalistic, clean aesthetic (white background, black text, iOS/Instagram-inspired style). A first-time onboarding tutorial and a post-tutorial preferences setup screen are introduced as part of this feature. The app also supports a Light/Dark Mode toggle for visual comfort, and includes a Browser Extension that allows users to summarise and query government web pages directly from their browser.

## Glossary

- **App**: The Flet-based Python AI chatbot application.
- **User**: A person who has registered and logged into the App.
- **New_User**: A User who is logging in for the very first time after completing registration.
- **Returning_User**: A User who has previously completed the onboarding flow.
- **Onboarding_Flow**: The sequence of screens shown exclusively to a New_User immediately after first login, consisting of the Tutorial and the Preferences_Setup.
- **Tutorial**: The multi-page walkthrough that introduces the App's core functionalities to a New_User.
- **Tutorial_Page**: A single screen within the Tutorial containing a title, illustration or icon, and a short description.
- **Preferences_Setup**: The screen shown after the Tutorial where the User selects their Language, Country, and Font_Size.
- **Language**: The User's preferred display language for the App's UI and AI responses.
- **Country**: The ASEAN country the User is associated with, used to contextualise government document queries.
- **Font_Size**: The User's preferred text size, chosen from Small, Medium, or Large, for accessibility.
- **Onboarding_State**: A persisted flag stored per User indicating whether the Onboarding_Flow has been completed.
- **Home_Screen**: The main chat interface of the App, shown after login (or after onboarding for New_Users).
- **Profile_Screen**: The screen where the User can view and edit their account details and preferences.
- **Theme**: The visual style of the App — white background, black text, minimal colour accents, large touch targets.
- **Theme_Mode**: The User's chosen display mode, either Light_Mode or Dark_Mode.
- **Light_Mode**: A display mode using a white (`#FFFFFF`) background with black (`#000000`) primary text.
- **Dark_Mode**: A display mode using a dark background (e.g. `#121212`) with light primary text (e.g. `#FFFFFF`).
- **Browser_Extension**: A companion browser add-on for the App that integrates with the user's web browser to provide AI-powered summarisation and chat on government web pages.
- **Page_Summary**: An AI-generated summary of the content of the currently active government web page, produced by the Browser_Extension.
- **In_Browser_Chat**: The AI chatbot interface embedded within the Browser_Extension sidebar, allowing the User to ask questions about the current page or any government document.

---

## Requirements

### Requirement 1: Minimalistic UI Theme

**User Story:** As an elderly or less tech-savvy user, I want a clean, simple interface with high contrast and large touch targets, so that I can use the app comfortably without confusion.

#### Acceptance Criteria

1. THE App SHALL use a white (`#FFFFFF`) background and black (`#000000`) primary text colour across all screens.
2. THE App SHALL use a single accent colour (e.g. a muted blue or grey) for interactive elements such as buttons and links.
3. THE App SHALL render all primary action buttons with a minimum height of 52 logical pixels and a minimum width of 200 logical pixels.
4. THE App SHALL use a default body font size of at least 16sp.
5. THE App SHALL remove all dark-mode, neon, or gradient colour schemes from the existing UI.
6. WHEN the User's selected Font_Size is Small, THE App SHALL render body text at 14sp.
7. WHEN the User's selected Font_Size is Medium, THE App SHALL render body text at 16sp.
8. WHEN the User's selected Font_Size is Large, THE App SHALL render body text at 20sp.
9. THE App SHALL apply the User's selected Font_Size to all text elements across all screens after Preferences_Setup is completed.

---

### Requirement 2: Onboarding State Tracking

**User Story:** As a returning user, I want the tutorial to be shown only once, so that I am not interrupted by onboarding screens on subsequent logins.

#### Acceptance Criteria

1. THE App SHALL persist the Onboarding_State for each User locally after the Onboarding_Flow is completed.
2. WHEN a New_User logs in for the first time, THE App SHALL route the User to the Onboarding_Flow before the Home_Screen.
3. WHEN a Returning_User logs in, THE App SHALL route the User directly to the Home_Screen, bypassing the Onboarding_Flow.
4. IF the Onboarding_State cannot be read, THEN THE App SHALL treat the User as a New_User and display the Onboarding_Flow.

---

### Requirement 3: Multi-Page Tutorial

**User Story:** As a new user, I want a guided walkthrough of the app's features, so that I understand how to use it before I start.

#### Acceptance Criteria

1. THE Tutorial SHALL consist of at least five Tutorial_Pages covering: (1) a welcome message, (2) how to ask questions about government documents, (3) how to select a country for contextualised answers, (4) how to upload or link to a document or website, and (5) an introduction to the Browser_Extension, explaining how to use the "Summarise this page" button and the In_Browser_Chat sidebar on government websites.
2. WHEN the User is on any Tutorial_Page that is not the first, THE Tutorial SHALL display a "Back" button that navigates to the previous Tutorial_Page.
3. WHEN the User is on any Tutorial_Page that is not the last, THE Tutorial SHALL display a "Next" button that navigates to the next Tutorial_Page.
4. WHEN the User is on the last Tutorial_Page, THE Tutorial SHALL display a "Get Started" button that navigates to the Preferences_Setup screen.
5. THE Tutorial SHALL display a page indicator (e.g. dots) showing the User's current position within the Tutorial.
6. WHEN the User taps "Back" on the first Tutorial_Page, THE App SHALL have no "Back" button visible on that page.
7. THE Tutorial SHALL display each Tutorial_Page with a prominent icon or illustration, a short title (maximum 8 words), and a description (maximum 40 words).

---

### Requirement 4: Preferences Setup — Language Selection

**User Story:** As a new user, I want to select my preferred language, so that the app communicates with me in a language I understand.

#### Acceptance Criteria

1. THE Preferences_Setup SHALL present the User with a scrollable list or grid of supported languages to select from.
2. THE Preferences_Setup SHALL include at minimum the following languages: English, Bahasa Melayu, Bahasa Indonesia, Thai, Vietnamese, Filipino/Tagalog, Burmese, Khmer, Lao, Chinese (Simplified), and Tamil.
3. THE App SHALL require the User to select exactly one Language before proceeding from the language selection step.
4. WHEN the User selects a Language, THE App SHALL visually highlight the selected Language option.
5. THE App SHALL persist the selected Language to the User's profile after Preferences_Setup is completed.

---

### Requirement 5: Preferences Setup — Country Selection

**User Story:** As a new user, I want to select my country, so that the app can surface relevant government information for my region.

#### Acceptance Criteria

1. THE Preferences_Setup SHALL present the User with a list of ASEAN countries to select from.
2. THE Preferences_Setup SHALL include the following countries: Malaysia, Indonesia, Thailand, Vietnam, Philippines, Myanmar, Cambodia, Laos, Singapore, Brunei, and Timor-Leste.
3. THE App SHALL require the User to select exactly one Country before proceeding from the country selection step.
4. WHEN the User selects a Country, THE App SHALL visually highlight the selected Country option.
5. THE App SHALL persist the selected Country to the User's profile after Preferences_Setup is completed.

---

### Requirement 6: Preferences Setup — Font Size Selection

**User Story:** As an elderly or visually impaired user, I want to choose a comfortable font size, so that I can read the app's content without strain.

#### Acceptance Criteria

1. THE Preferences_Setup SHALL present the User with three Font_Size options: Small, Medium, and Large.
2. THE Preferences_Setup SHALL display a live text preview that updates as the User selects each Font_Size option.
3. THE App SHALL default to Medium if the User does not explicitly select a Font_Size.
4. WHEN the User selects a Font_Size, THE App SHALL visually highlight the selected option.
5. THE App SHALL persist the selected Font_Size to the User's profile after Preferences_Setup is completed.

---

### Requirement 7: Preferences Setup — Completion and Navigation

**User Story:** As a new user, I want to confirm my preferences and proceed to the app, so that my setup is saved and I can start using the chatbot.

#### Acceptance Criteria

1. THE Preferences_Setup SHALL display a "Confirm" or "Done" button that is only enabled after the User has selected a Language, a Country, and a Font_Size.
2. WHEN the User taps the "Confirm" button, THE App SHALL save all selected preferences to the User's profile.
3. WHEN the User taps the "Confirm" button, THE App SHALL mark the Onboarding_State as completed.
4. WHEN the User taps the "Confirm" button, THE App SHALL navigate the User to the Home_Screen.
5. IF saving preferences fails, THEN THE App SHALL display an inline error message and SHALL NOT navigate away from the Preferences_Setup screen.

---

### Requirement 8: Profile Screen — Preferences Editing

**User Story:** As a returning user, I want to update my language, country, font size, and display mode preferences from my profile, so that I can change them at any time.

#### Acceptance Criteria

1. THE Profile_Screen SHALL display the User's currently saved Language, Country, Font_Size, and Theme_Mode.
2. THE Profile_Screen SHALL provide an edit control for each preference (Language, Country, Font_Size, Theme_Mode).
3. WHEN the User updates a preference on the Profile_Screen, THE App SHALL persist the updated value immediately.
4. WHEN the User updates the Font_Size on the Profile_Screen, THE App SHALL apply the new Font_Size to all text elements without requiring a restart.
5. WHEN the User updates the Theme_Mode on the Profile_Screen, THE App SHALL apply the new Theme_Mode to all screens immediately without requiring a restart.

---

### Requirement 9: Accessibility and Touch Target Standards

**User Story:** As an elderly user with limited dexterity, I want all interactive elements to be easy to tap, so that I don't accidentally press the wrong thing.

#### Acceptance Criteria

1. THE App SHALL render all tappable controls (buttons, list items, toggles) with a minimum touch target size of 48×48 logical pixels.
2. THE App SHALL maintain a minimum contrast ratio of 4.5:1 between text and its background on all screens.
3. THE App SHALL use plain, non-technical labels for all buttons and navigation elements (e.g. "Next", "Back", "Done", "Ask a Question").
4. THE App SHALL avoid displaying more than three interactive elements in a single row on any screen.

---

### Requirement 10: Light/Dark Mode Toggle

**User Story:** As a user, I want to switch between a light and dark display mode, so that I can use the app comfortably in different lighting conditions.

#### Acceptance Criteria

1. THE App SHALL support two Theme_Mode options: Light_Mode and Dark_Mode.
2. WHEN the User selects Light_Mode, THE App SHALL render all screens with a white (`#FFFFFF`) background and black (`#000000`) primary text.
3. WHEN the User selects Dark_Mode, THE App SHALL render all screens with a dark background (e.g. `#121212`) and light primary text (e.g. `#FFFFFF`).
4. THE Profile_Screen SHALL provide a toggle control that allows the User to switch between Light_Mode and Dark_Mode.
5. WHEN the User toggles the Theme_Mode, THE App SHALL apply the change to all screens immediately without requiring a restart.
6. THE App SHALL persist the User's selected Theme_Mode to the User's profile so that it is restored on subsequent logins.
7. IF no Theme_Mode preference has been saved, THEN THE App SHALL default to Light_Mode.
8. THE App SHALL maintain a minimum contrast ratio of 4.5:1 between primary text and background in both Light_Mode and Dark_Mode.

---

### Requirement 11: Browser Extension — Page Summarisation

**User Story:** As a user browsing a government website, I want a "Summarise this page" button to appear in my browser, so that I can quickly get an AI-generated summary of the page content without leaving the site.

#### Acceptance Criteria

1. WHEN the User is viewing a government website in the browser with the Browser_Extension installed, THE Browser_Extension SHALL display a visible "Summarise this page" button overlaid on or adjacent to the page.
2. WHEN the User clicks the "Summarise this page" button, THE Browser_Extension SHALL extract the text content of the current page and send it to the AI backend.
3. WHEN the AI backend returns a result, THE Browser_Extension SHALL display the Page_Summary in a sidebar or overlay panel within the browser.
4. THE Page_Summary SHALL be presented in plain language suitable for elderly and less tech-savvy users.
5. IF the AI backend fails to return a summary, THEN THE Browser_Extension SHALL display a descriptive error message and provide a "Try again" option.
6. WHEN the current page is not a government website, THE Browser_Extension SHALL NOT display the "Summarise this page" button.

---

### Requirement 12: Browser Extension — In-Browser AI Chatbot

**User Story:** As a user browsing a government website, I want to ask questions about the page or related government documents directly in my browser, so that I can get contextual answers without switching to the main app.

#### Acceptance Criteria

1. THE Browser_Extension SHALL provide an In_Browser_Chat sidebar that the User can open while viewing any government website.
2. WHEN the User submits a question in the In_Browser_Chat, THE Browser_Extension SHALL send the question along with the current page content as context to the AI backend.
3. WHEN the AI backend returns a response, THE Browser_Extension SHALL display the response in the In_Browser_Chat sidebar.
4. THE In_Browser_Chat SHALL maintain the conversation history for the duration of the current browser session.
5. THE In_Browser_Chat SHALL allow the User to ask questions about any government document or website link they are currently viewing.
6. IF the AI backend fails to return a response, THEN THE Browser_Extension SHALL display a descriptive error message in the In_Browser_Chat and provide a "Try again" option.
7. THE In_Browser_Chat SHALL apply the User's saved Theme_Mode (Light_Mode or Dark_Mode) to its interface.
