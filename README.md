# Bridge - ASEAN Government Website Summarizer

Bridge is an AI-powered tool that automatically detects and summarizes ASEAN government websites in simple language. It consists of two main components:

1. **Desktop Application** - A Flet-based UI for document and website summarization
2. **Browser Extension** - Chrome extension for real-time government website summarization with voice interaction

## Features

### Desktop Application
- 📄 Document summarization (PDF, DOCX, PPTX, etc.)
- 🌐 Website summarization with automatic crawling
- 🤖 AI-powered Q&A on documents and websites
- 🌍 Support for all 12 ASEAN languages
- 🎨 Modern iOS/Instagram-style UI with purple-to-blue gradient

### Browser Extension
- 🔍 Automatic detection of ASEAN government websites
- 📝 One-click summarization in any ASEAN language
- 💬 Interactive Q&A with voice input
- 🔊 Text-to-speech in 11 ASEAN languages (Lao uses English fallback)
- 🎯 Language picker before summarization
- 📱 Clean, unified scrollable interface

## Supported Languages

All 12 ASEAN languages:
- 🇬🇧 English
- 🇲🇾 Malay (Bahasa Melayu)
- 🇮🇩 Indonesian (Bahasa Indonesia)
- 🇻🇳 Vietnamese (Tiếng Việt)
- 🇹🇭 Thai (ภาษาไทย)
- 🇨🇳 Chinese Simplified (简体中文)
- 🇹🇼 Chinese Traditional (繁體中文)
- 🇮🇳 Tamil (தமிழ்)
- 🇵🇭 Filipino/Tagalog
- 🇲🇲 Burmese (မြန်မာဘာသာ)
- 🇰🇭 Khmer (ភាសាខ្មែរ)
- 🇱🇦 Lao (ພາສາລາວ) - TTS uses English fallback

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Extension                         │
│  (content.js, background.js, popup.js)                      │
│  - Detects gov websites                                      │
│  - UI overlay with language picker                           │
│  - Voice input/output                                        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP (localhost:5000)
┌────────────────────▼────────────────────────────────────────┐
│                  Flask Backend Server                        │
│              (engine/search/summarizer_web.py)               │
│  - Website/document processing                               │
│  - AI summarization (Gemini + Ollama fallback)              │
│  - RAG-based Q&A                                             │
│  - Speech-to-text (Whisper)                                  │
│  - Text-to-speech (gTTS)                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐    ┌──────────▼──────────┐
│  Desktop App   │    │   AI Services       │
│  (main.py)     │    │  - Gemini API       │
│  - Flet UI     │    │  - Ollama (local)   │
│  - User prefs  │    │  - ChromaDB         │
│  - Profiles    │    │  - Firecrawl        │
└────────────────┘    └─────────────────────┘
```

## Prerequisites

### Required Software
- **Python 3.12** or higher
- **ffmpeg** (for audio processing)
- **Ollama** (for local LLM fallback)
- **Chrome/Brave/Edge** browser (for extension)

### API Keys (Free Tiers Available)
1. **Google Gemini API** - Get from [Google AI Studio](https://aistudio.google.com/apikey)
   - Free tier: 1,500 requests/day
2. **Firecrawl API** - Get from [Firecrawl](https://firecrawl.dev)
   - Free tier: 500 credits/month
3. **Hugging Face Token** - Get from [Hugging Face](https://huggingface.co/settings/tokens)
   - Required for EmbeddingGemma model

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vhack2026-live-translator
```

### 2. Install ffmpeg

**Windows (using winget):**
```bash
winget install Gyan.FFmpeg
```

After installation, restart your terminal or add ffmpeg to PATH manually.

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Debian/Ubuntu
sudo yum install ffmpeg  # CentOS/RHEL
```

### 3. Install Ollama

Download and install from [ollama.com](https://ollama.com)

After installation, pull the required model:
```bash
ollama pull llama3.2
```

### 4. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Firecrawl API Key
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# Hugging Face Token
HF_TOKEN=your_huggingface_token_here
```

### 6. Install Browser Extension

1. Open Chrome/Brave/Edge
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `browser-extension` folder from this project
6. The Bridge extension icon should appear in your toolbar

## Usage

### Starting the Flask Backend Server

The Flask server must be running for both the desktop app and browser extension to work.

```bash
# Make sure you're in the project root directory
cd C:\Projects\vhack2026-live-translator

# Activate virtual environment (if not already activated)
.venv\Scripts\activate

# Start the Flask server
.venv\Scripts\python.exe engine\search\summarizer_web.py
```

You should see:
```
============================================================
Bridge Document Summarizer - Web Interface
Docling + Google Gemini 2.0 Flash
============================================================
Python executable: C:\Projects\vhack2026-live-translator\.venv\Scripts\python.exe
gTTS available: True

Server starting...
Open your browser and go to: http://localhost:5000
```

**Important:** Keep this terminal window open while using the application.

### Using the Desktop Application

1. Start the Flask server (see above)
2. In a new terminal, activate the virtual environment:
   ```bash
   .venv\Scripts\activate
   ```
3. Run the desktop app:
   ```bash
   python main.py
   ```
4. The Flet UI will open with:
   - Login screen
   - Onboarding flow
   - Home screen with document/website summarization
   - Preferences and profile settings

### Using the Browser Extension

1. **Ensure Flask server is running** at `http://localhost:5000`
2. Navigate to any ASEAN government website (e.g., `https://www.malaysia.gov.my`)
3. A purple floating button (🌉) will appear in the bottom-right corner
4. Click the button to open the language picker
5. Select your desired language
6. Wait for the summary to load
7. Use the action buttons:
   - **🔄 Re-summarize** - Generate summary in a different language
   - **🔊 Read Aloud** - Text-to-speech (button shows loading state)
   - **🎤 Voice Input** - Ask questions using your microphone
   - **💬 Text Input** - Type questions in the input box

### Supported Government Domains

The extension automatically detects these domains:
- Malaysia: `.gov.my`, `.mygov.my`
- Singapore: `.gov.sg`
- Indonesia: `.go.id`, `.gov.id`
- Thailand: `.go.th`, `.gov.th`
- Philippines: `.gov.ph`
- Vietnam: `.gov.vn`
- Myanmar: `.gov.mm`
- Cambodia: `.gov.kh`
- Laos: `.gov.la`
- Brunei: `.gov.bn`
- Timor-Leste: `.gov.tl`
- Generic: `government.`, `ministry.`, `parliament.`

## How It Works

### Summarization Pipeline

1. **Web Scraping** - Firecrawl extracts content from the website (crawls up to 3 subpages)
2. **Embedding** - Content is chunked and embedded using EmbeddingGemma-300M
3. **Vector Storage** - Embeddings stored in ChromaDB for semantic search
4. **AI Summarization** - Gemini 2.0 Flash generates summary (falls back to Ollama if rate limited)
5. **Translation** - Deep Translator converts to target language if needed
6. **Delivery** - Summary sent to browser extension or desktop app

### Q&A Pipeline

1. **Question Processing** - User question is embedded using EmbeddingGemma
2. **Semantic Search** - ChromaDB retrieves most relevant content chunks
3. **RAG Generation** - Gemini generates answer using retrieved context
4. **Translation** - Answer translated to target language
5. **Delivery** - Answer displayed in chat interface

### Speech Features

- **Speech-to-Text** - Uses Whisper model via Transformers pipeline
- **Text-to-Speech** - Uses gTTS (Google Text-to-Speech) for 11 languages
  - Lao falls back to English (not supported by gTTS)

## Troubleshooting

### Flask Server Issues

**Problem:** `gTTS available: False`
**Solution:** Make sure you're using the virtual environment's Python:
```bash
.venv\Scripts\python.exe engine\search\summarizer_web.py
```

**Problem:** `ModuleNotFoundError: No module named 'transformers'`
**Solution:** Install missing packages:
```bash
.venv\Scripts\pip install transformers torch sentence-transformers
```

**Problem:** `ffmpeg not found`
**Solution:** Install ffmpeg and restart terminal, or add to PATH manually.

### Browser Extension Issues

**Problem:** Extension doesn't detect government website
**Solution:** Check if the domain matches patterns in `background.js`. Reload the extension.

**Problem:** "Text-to-speech failed" error
**Solution:** Ensure Flask server is running at `http://localhost:5000`

**Problem:** Summary is in wrong language
**Solution:** This happens when Gemini hits rate limits and falls back to Ollama. Wait a few minutes or use a different Gemini API key.

### Desktop App Issues

**Problem:** App won't start
**Solution:** Ensure Flet is installed: `pip install flet==0.19.0`

**Problem:** UI looks broken
**Solution:** Update to latest Flet: `pip install --upgrade flet`

## Rate Limits & Quotas

### Gemini API (Free Tier)
- 1,500 requests per day
- Resets at midnight UTC
- Falls back to Ollama when exceeded

### Firecrawl API (Free Tier)
- 500 credits per month
- 1 credit = 1 page scraped
- Extension uses 3 credits per summary (crawls 3 pages)

### Ollama (Local)
- No limits
- Runs on your machine
- Slower than Gemini but always available

## Project Structure

```
vhack2026-live-translator/
├── app/                          # Desktop application
│   ├── components/               # UI components
│   │   ├── controls.py          # Reusable controls
│   │   └── theme.py             # Theme configuration
│   ├── views/                   # Application screens
│   │   ├── login.py
│   │   ├── onboarding.py
│   │   ├── home.py
│   │   ├── preferences.py
│   │   └── profile.py
│   ├── router.py                # Navigation logic
│   └── state.py                 # Application state
├── browser-extension/           # Chrome extension
│   ├── background.js            # Service worker
│   ├── content.js               # Content script (UI overlay)
│   ├── popup.js                 # Extension popup
│   ├── popup.html               # Popup UI
│   ├── manifest.json            # Extension config
│   └── icons/                   # Extension icons
├── engine/                      # Backend processing
│   └── search/
│       ├── document_summariser_v6_gemini.py  # Core summarization
│       ├── summarizer_web.py                 # Flask server
│       └── speech_to_text.py                 # Audio processing
├── chroma_db/                   # Vector database storage
├── user_prefs/                  # User preferences (JSON)
├── uploads/                     # Temporary file uploads
├── main.py                      # Desktop app entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
└── README.md                    # This file
```

## Technologies Used

### Frontend
- **Flet 0.19.0** - Desktop UI framework
- **Vanilla JavaScript** - Browser extension

### Backend
- **Flask** - Web server
- **Docling** - Document processing
- **BeautifulSoup4** - HTML parsing
- **Firecrawl** - Enhanced web scraping

### AI/ML
- **Google Gemini 2.0 Flash** - Primary LLM
- **Ollama (llama3.2)** - Fallback LLM
- **EmbeddingGemma-300M** - Text embeddings
- **Whisper** - Speech recognition
- **gTTS** - Text-to-speech

### Storage
- **ChromaDB** - Vector database
- **JSON** - User preferences

### Translation
- **Deep Translator** - Multi-language translation

## Contributing

This project was built for vHack 2026. Contributions are welcome!

## License

[Add your license here]

## Credits

Built with ❤️ for ASEAN citizens to better understand their government websites.

## Support

For issues or questions, please open an issue on GitHub or contact the development team.
