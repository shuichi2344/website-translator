# Bridge 🌉

AI-powered document and website summarizer for ASEAN government websites - making public services accessible to everyone through simple language summaries.

**Part of:** Inclusive Citizen ASEAN Project (VHACK 2026)  
**Feature:** Bridge - Government Website Summarizer

---

## 🎯 Project Overview

Bridge automatically detects ASEAN government websites and provides AI-powered summaries in simple language (5th-grade reading level) across 12 ASEAN languages. Available as both a web interface and browser extension.

### Key Features

- ✅ **Auto-detects ASEAN government websites** (`.gov.my`, `.gov.sg`, `.go.id`, etc.)
- ✅ **AI-powered summarization** using Google Gemini 2.0 Flash
- ✅ **Simple language** - summaries written for 10-year-olds
- ✅ **Smart web crawling** - automatically crawls 3 sublinks for comprehensive summaries
- ✅ **500% faster scraping** with Firecrawl caching (1-day cache for government sites)
- ✅ **Advanced document processing** with Docling (PDFs, images, complex tables)
- ✅ **12 ASEAN languages** supported
- ✅ **Three interfaces:** Web UI, Browser Extension, Bookmarklet
- ✅ **Cross-browser support:** Chrome, Brave, Edge, Opera, Safari, Firefox
- ✅ **Copy & Read Aloud** features built-in

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **API Keys** (free tiers available):
   - Google Gemini API: https://aistudio.google.com/apikey (1500 requests/day free)
   - Firecrawl API: https://firecrawl.dev (500 credits/month free)

### Installation

```bash
# 1. Clone the repository
cd vhack2026-live-translator

# 2. Install Python dependencies
pip install flask docling firecrawl-py google-genai deep-translator langdetect beautifulsoup4 requests python-dotenv pillow

# 3. Set up API keys
# Create .env file with:
GEMINI_API_KEY="your-gemini-api-key"
FIRECRAWL_API_KEY="your-firecrawl-api-key"

# 4. Create extension icons (one-time setup)
python create_icons.py

# 5. Start the server
python summarizer_web.py
```

Server will start at `http://localhost:5000`

---

## 📱 Usage

### Option 1: Web Interface (Easiest)

1. Start the server: `python summarizer_web.py`
2. Open browser: `http://localhost:5000`
3. Choose:
   - **Document tab**: Upload PDF or images
   - **Website tab**: Enter government website URL
4. Select target language
5. Click "Summarize"

**Features:**
- Upload documents (PDF, PNG, JPG, JPEG, BMP, TIFF)
- Enter website URLs
- Automatic crawling of 3 sublinks
- Translation to 12 ASEAN languages
- Word count statistics
- Copy summary to clipboard

### Option 2: Browser Extension (Chrome/Brave/Edge/Opera)

1. Start the server: `python summarizer_web.py`
2. Open browser extensions page:
   - Chrome: `chrome://extensions/`
   - Brave: `brave://extensions/`
   - Edge: `edge://extensions/`
   - Opera: `opera://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select `browser-extension` folder
6. Visit any ASEAN government website
7. Click the floating "📄 Summarize This Page" button

**Features:**
- Auto-detects government websites
- Floating button appears automatically
- Summary panel with stats
- Copy & Read Aloud buttons
- Close and reopen anytime

### Option 3: Bookmarklet (Safari/Firefox/Any Browser)

1. Start the server: `python summarizer_web.py`
2. Create a new bookmark
3. Name it: "📄 Summarize Page"
4. Paste this as the URL:

```javascript
javascript:(function(){if(window.location.hostname.match(/\.gov\.(my|sg|id|th|ph|vn|mm|kh|la|bn)|\.go\.(id|th)/)){var s=document.createElement('script');s.src='http://localhost:5000/static/bookmarklet.js';document.body.appendChild(s);}else{alert('This only works on government websites!');}})();
```

5. Visit any ASEAN government website
6. Click the bookmarklet

**Works on:**
- Safari (macOS, iOS)
- Firefox
- Chrome, Brave, Edge, Opera
- Mobile browsers

---

## 🛠️ Technology Stack

### Backend
- **Python 3.8+** - Core language
- **Flask** - Web server
- **Docling 2.79** - Advanced PDF/document processing with table recognition
- **Google Gemini 2.0 Flash** - AI summarization (gemini-3-flash-preview)
- **Firecrawl** - Enhanced web scraping with 500% faster caching
- **BeautifulSoup4** - HTML parsing (fallback)
- **deep-translator** - Multi-language translation
- **langdetect** - Automatic language detection

### Frontend
- **HTML5/CSS3/JavaScript** - Web interface
- **Browser Extension (Manifest V3)** - Chrome/Brave/Edge/Opera
- **Bookmarklet** - Universal browser support

### AI & Processing
- **Google Gemini API** - Abstractive summarization
- **Ollama (llama3.2)** - Fallback AI (optional)
- **Firecrawl Cache** - 1-day cache for government sites (500% faster)

---

## 📦 Project Structure

```
vhack2026-live-translator/
├── browser-extension/              # Browser extension
│   ├── manifest.json              # Extension config
│   ├── background.js              # Service worker (detection)
│   ├── content.js                 # Page script (UI)
│   ├── popup.html/js              # Extension popup
│   ├── icons/                     # Extension icons
│   ├── README.md                  # Extension docs
│   ├── TESTING_GUIDE.md           # How to test
│   ├── WHAT_TO_EXPECT.md          # Visual guide
│   ├── CROSS_BROWSER.md           # Browser compatibility
│   └── BROWSER_SUPPORT.md         # Quick reference
├── static/
│   └── bookmarklet.js             # Universal bookmarklet script
├── uploads/                        # Temporary file uploads
├── document_summariser_v6_gemini.py  # Core summarizer
├── summarizer_web.py              # Flask web server
├── create_icons.py                # Icon generator
├── test_extension.py              # Setup verification
├── .env                           # API keys (create this)
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

---

## 🌍 Supported Languages

### ASEAN Languages (Full Support)
- **English** (`en`)
- **Malay** (`ms`) - Malaysia, Brunei
- **Indonesian** (`id`)
- **Vietnamese** (`vi`)
- **Thai** (`th`)
- **Chinese Simplified** (`zh-cn`)
- **Chinese Traditional** (`zh-tw`)
- **Tamil** (`ta`)
- **Tagalog/Filipino** (`tl`)
- **Burmese/Myanmar** (`my`)
- **Khmer** (`km`) - Cambodia
- **Lao** (`lo`)

---

## 🌐 Supported Government Domains

The extension automatically detects these government domains:

- **Malaysia**: `.gov.my`, `.mygov.my`
- **Singapore**: `.gov.sg`
- **Indonesia**: `.go.id`, `.gov.id`
- **Thailand**: `.go.th`, `.gov.th`
- **Philippines**: `.gov.ph`
- **Vietnam**: `.gov.vn`
- **Myanmar**: `.gov.mm`
- **Cambodia**: `.gov.kh`
- **Laos**: `.gov.la`
- **Brunei**: `.gov.bn`

---

## 🧪 Testing

### Quick Verification

```bash
# Run automated setup check
python test_extension.py
```

Should show all ✅ green checkmarks.

### Test Websites

Try these ASEAN government sites:
- Malaysia: https://www.gov.my
- Singapore: https://www.gov.sg
- Indonesia: https://www.go.id
- Thailand: https://www.go.th
- Philippines: https://www.gov.ph

### What to Expect

1. **Web Interface**: Form appears, upload/enter URL, get summary
2. **Browser Extension**: Purple button appears bottom-right on gov sites
3. **Bookmarklet**: Click bookmark, button appears, click for summary

See `browser-extension/TESTING_GUIDE.md` for detailed testing instructions.

---

## ⚡ Performance

### Firecrawl Fast Scraping

- **First request**: Normal speed (~3 seconds)
- **Subsequent requests**: 500% faster (~0.5 seconds)
- **Cache duration**: 1 day (optimal for government sites)
- **Auto-refresh**: Scrapes fresh when cache expires

### Processing Times

- **Document upload**: 10-30 seconds (depends on size)
- **Website scraping**: 0.5-3 seconds (with cache)
- **AI summarization**: 5-15 seconds
- **Total**: ~15-45 seconds for complete summary

---

## 🔧 Configuration

### API Keys (.env file)

```bash
# Required for AI summarization
GEMINI_API_KEY="your-gemini-api-key-here"

# Optional but recommended for faster scraping
FIRECRAWL_API_KEY="your-firecrawl-api-key-here"
```

### Cache Settings

Edit `document_summariser_v6_gemini.py`:

```python
# Current: 1 day cache (optimal for government sites)
cache_max_age = 86400000  # milliseconds

# Options:
# 1 hour: 3600000
# 1 day: 86400000 (default)
# 1 week: 604800000
# No cache: 0 (slower, not recommended)
```

---

## 📋 Features in Detail

### Document Processing
- PDF support with complex table recognition
- Image support (PNG, JPG, JPEG, BMP, TIFF)
- Automatic language detection
- Layout preservation
- OCR for scanned documents

### Website Summarization
- Automatic crawling of 3 sublinks
- Smart content extraction
- Firecrawl caching for speed
- BeautifulSoup fallback

### AI Summarization
- Google Gemini 2.0 Flash (primary)
- Ollama llama3.2 (fallback, optional)
- 5 bullet points in simple language
- Written for 10-year-old comprehension
- Automatic chunking for long documents

### Translation
- 12 ASEAN languages
- Automatic language detection
- Google Translate integration
- Preserves formatting

---

## 🐛 Troubleshooting

### Extension won't load
- Check all icon files exist in `browser-extension/icons/`
- Run `python create_icons.py` to recreate icons
- Reload extension in browser

### "Server offline" error
- Make sure Flask server is running: `python summarizer_web.py`
- Check `http://localhost:5000` in browser
- Verify port 5000 isn't blocked

### Summary generation fails
- Check API keys in `.env` file
- Verify internet connection
- Check Flask terminal for error messages
- Try a different government website

### Button doesn't appear
- Verify URL contains government domain (`.gov.my`, etc.)
- Refresh the page
- Check browser console (F12) for errors

---

## 📝 Development

### Adding More Government Domains

Edit `browser-extension/background.js`:

```javascript
const GOV_DOMAINS = [
  '.gov.my',
  '.your-new-domain.here',
  // ...
];
```

### Customizing Summary Length

Edit `document_summariser_v6_gemini.py`:

```python
# Change num_sentences parameter
summary = self.summarize_text(text, num_sentences=5)  # Default: 5
```

### Running in Production

For production deployment:
1. Use a production WSGI server (gunicorn, waitress)
2. Set up HTTPS
3. Configure proper CORS settings
4. Use environment variables for API keys
5. Set up rate limiting

---

## 🤝 Integration

This module can be integrated into larger ASEAN citizen service platforms:

```
inclusive_citizen_ASEAN/
├── speech-engine/        # Voice interface
├── bridge/               # This module
│   ├── backend/          # Python Flask service
│   └── extension/        # Browser extension
└── mobile-app/           # Mobile interface
```

---

## 📄 License

This project is part of VHACK 2026 hackathon submission.

---

## 👥 Team

**Bridge Module**  
**Project:** Inclusive Citizen ASEAN  
**Hackathon:** VHACK 2026 - Case Study 4

---

## 🙏 Acknowledgments

- VHACK 2026 organizers
- Google Gemini AI team
- Firecrawl team
- Docling developers
- Open source community

---

## 📚 Additional Documentation

- `browser-extension/README.md` - Extension documentation
- `browser-extension/TESTING_GUIDE.md` - Detailed testing guide
- `browser-extension/WHAT_TO_EXPECT.md` - Visual guide
- `browser-extension/CROSS_BROWSER.md` - Browser compatibility
- `FAST_SCRAPING_INFO.md` - Firecrawl performance details

---

**Status:** 🟢 Production Ready  
**Last Updated:** March 14, 2026  
**Version:** 2.0.0
