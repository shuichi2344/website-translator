# Bridge 🌐

Auto-translation system for Malaysian government websites - making public services accessible to everyone.

**Part of:** Inclusive Citizen ASEAN Project (VHACK 2026)  
**Feature:** Bridge - Live Translator Module

---

## 🎯 Project Overview

This module provides real-time translation of government websites for both desktop and mobile platforms. It automatically detects Malaysian government websites and offers seamless translation to help citizens access public services in their preferred language.

### Key Features

- ✅ Auto-detects Malaysian government websites (`.gov.my` domains)
- ✅ Real-time translation with full website interactivity
- ✅ **AI-powered document summarization using Google Gemini**
- ✅ Supports 107 languages via Google Translate
- ✅ Preserves website design and functionality
- ✅ **Intelligent abstractive summaries with local AI**
- ✅ **Extract text from scanned documents with OCR**
- ✅ Mobile app with browser detection
- ✅ No database - all settings stored locally
- ✅ No API costs (uses googletrans + local AI)

---

## 🚀 Quick Start

### Website Translation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the translator
python prototype_translation_v3_auto.py

# Enter a Malaysian government website:
# Example: https://www.jpj.gov.my/myjpj/

# Select target language:
# Example: en (English)

# Browser opens with translated content!
```

### Document & Website Summarization

**Prerequisites:**
1. Get a Google Gemini API key:
   - Create a `.env` file (see `.env.example`) and add `GOOGLE_API_KEY` and (optionally) `GEMINI_MODEL`

**Web Interface (Recommended):**
```bash
python summarizer_web.py
# Open browser to http://localhost:5000
```

**Command Line:**
```bash
python document_summarizer.py
# Follow the prompts
```

See [SUMMARIZER_README.md](SUMMARIZER_README.md) for detailed instructions.

### Mobile App

```bash
cd live_translator_app
flutter pub get
flutter run -d chrome  # or android/ios
```

---

## 📦 Project Structure

```
bridge-translator/
├── live_translator_app/              # Flutter mobile app
│   ├── lib/
│   │   ├── main.dart                 # App entry point
│   │   ├── screens/                  # UI screens
│   │   ├── constants/                # Colors, languages, domains
│   │   ├── models/                   # Data models
│   │   └── services/                 # Storage & API services
│   └── pubspec.yaml
├── prototype_translation_v3_auto.py  # Website translation backend
├── document_summarizer.py            # Document/website summarizer (CLI)
├── summarizer_web.py                 # Summarizer web interface
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
├── SUMMARIZER_README.md              # Summarizer documentation
├── OLLAMA_SETUP.md                   # AI model setup guide
├── QUICK_START.md                     # Quick start guide
└── CHANGELOG.md                       # Version history
```

---

## 🛠️ Technology Stack

- **Translation:** Google GNMT via googletrans (4.0.0rc1)
- **Website Translation:** Selenium WebDriver, BeautifulSoup4
- **Document Processing:** Docling (OCR-enabled)
- **AI Summarization:** Google Gemini (e.g. `gemini-3.1-flash-lite-preview`)
- **Web Interface:** Flask
- **Mobile App:** Flutter/Dart
- **Languages:** Python 3.8+, Dart

---

## 🌍 Supported Languages

100+ languages including:
- English (`en`)
- Malay (`ms`)
- Chinese (`zh-cn`)
- Tamil (`ta`)
- Spanish (`es`)
- French (`fr`)
- And many more!

---

## 📋 Roadmap

### Phase 1: Core Functionality ✅
- [x] Basic website translation
- [x] Multi-page navigation support
- [x] Design preservation
- [x] Handle complex HTML elements

### Phase 2: Mobile App (In Progress)
- [x] Flutter mobile app UI
- [x] Language selection (107 languages)
- [x] Tutorial screens
- [x] Local storage (no database)
- [ ] Browser detection integration
- [ ] Auto-detect government websites
- [ ] One-tap translation

### Phase 3: Polish & Testing
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] User feedback integration

---

## 🤝 Integration with Main Project

This module will be integrated into the **Inclusive Citizen ASEAN** project:

```
inclusive_citizen_ASEAN/
├── speech-engine/        # Teammate's module
└── bridge/               # This module
    ├── backend/          # Python translation service
    └── mobile-app/       # Flutter app
```

**Integration Branch:** `feat/bridge-translator`  
**Target Branch:** `main_dev`

---

## 🐛 Known Issues & Limitations

- Rate limits: ~100-200 requests/hour (googletrans limitation)
- Requires Chrome browser for Python backend
- No database - all settings stored locally on device
- No OCR overlay - focuses on browser-based translation only
- Some dynamic content may need page refresh

---

## 📝 Development Notes

### Testing

Test on these Malaysian government sites:
- JPJ: https://www.jpj.gov.my/myjpj/
- Malaysia Portal: https://www.malaysia.gov.my/
- MITI: https://www.miti.gov.my/

### Rate Limits

googletrans is unofficial and has rate limits. For production:
- Consider Google Cloud Translation API
- Implement request throttling
- Note: No caching/database planned for this version

---

## 📄 License

This project is part of VHACK 2026 hackathon submission.

---

## 👥 Team

**Bridge Module Lead:** [Your Name]  
**Project:** Inclusive Citizen ASEAN  
**Hackathon:** VHACK 2026 - Case Study 4

---

## 📞 Contact

For questions or collaboration:
- GitHub: [your-github-username]
- Email: [your-email]

---

## 🙏 Acknowledgments

- VHACK 2026 organizers
- googletrans library maintainers
- Selenium WebDriver team

---

**Status:** 🟢 Active Development  
**Last Updated:** March 9, 2026
