# Live Website Translator 🌐

Auto-translation system for Malaysian government websites - making public services accessible to everyone.

**Part of:** Inclusive Citizen ASEAN Project (VHACK 2026)  
**Feature:** Live Translator Module

---

## 🎯 Project Overview

This module provides real-time translation of government websites for both desktop and mobile platforms. It automatically detects Malaysian government websites and offers seamless translation to help citizens access public services in their preferred language.

### Key Features

- ✅ Auto-detects Malaysian government websites (`.gov.my` domains)
- ✅ Real-time translation with full website interactivity
- ✅ Supports 100+ languages via Google Translate
- ✅ Preserves website design and functionality
- ✅ Works on desktop browsers and mobile devices
- ✅ No API costs (uses googletrans)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Chrome browser
- Internet connection

### Installation

```bash
# Clone the repository
git clone https://github.com/[your-username]/live-translator.git
cd live-translator

# Install dependencies
pip install -r requirements.txt

# Run the translator
python prototype_translation_v3_auto.py
```

### Usage

```bash
python prototype_translation_v3_auto.py

# Enter a Malaysian government website:
# Example: https://www.jpj.gov.my/myjpj/

# Select target language:
# Example: en (English)

# Browser opens with translated content!
```

---

## 📦 Project Structure

```
live-translator/
├── prototype_translation_v3_auto.py  # Main translation script
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
├── .gitignore                         # Git ignore rules
└── .kiro/                            # Specs and documentation
    └── specs/
        ├── web-scraping-translation/
        └── realtime-text-translation-overlay/
```

---

## 🛠️ Technology Stack

- **Translation:** Google GNMT via googletrans (4.0.0rc1)
- **Browser Automation:** Selenium WebDriver
- **Web Scraping:** BeautifulSoup4
- **Languages:** Python 3.8+

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

### Phase 2: Auto-Detection (In Progress)
- [ ] Browser extension for desktop
- [ ] Auto-detect government websites
- [ ] One-click translation
- [ ] Mobile browser app

### Phase 3: Advanced Features (Planned)
- [ ] OCR overlay for mobile
- [ ] Offline translation mode
- [ ] Translation memory/caching
- [ ] Multi-language support

---

## 🤝 Integration with Main Project

This module will be integrated into the **Inclusive Citizen ASEAN** project:

```
inclusive_citizen_ASEAN/
├── speech-engine/        # Teammate's module
└── live-translator/      # This module
```

**Integration Branch:** `feat/live-translator`  
**Target Branch:** `main_dev`

---

## 🐛 Known Issues

- Rate limits: ~100-200 requests/hour (googletrans limitation)
- Requires Chrome browser
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
- Add translation caching

---

## 📄 License

This project is part of VHACK 2026 hackathon submission.

---

## 👥 Team

**Live Translator Module Lead:** [Your Name]  
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
**Last Updated:** March 8, 2026
