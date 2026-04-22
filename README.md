# Bridge - ASEAN Government Information Assistant

Bridge is an AI-powered multilingual assistant that helps users access government information across ASEAN countries. It automatically detects and summarizes government websites, answers questions about official documents, and provides real-time information in 12 languages. Available as a desktop application, Telegram bot, and browser extension.

## Features

### Desktop Application
- 📄 Document Q&A (PDF, DOCX, images)
- 🌐 Website summarization with automatic crawling
- 🤖 AI-powered RAG-based responses
- 🎤 Voice input with local Whisper STT
- 🔊 Text-to-speech in 12 ASEAN languages
- 🎨 Modern iOS/Instagram-style UI with Light/Dark mode
- 👤 User authentication and profiles
- 🎓 First-time onboarding tutorial
- ⚙️ Customizable preferences (language, country, font size)

### Telegram Bot
- 💬 Text message support with natural language understanding
- 🎤 Voice message transcription (local Whisper)
- 📄 Document analysis (PDF, DOCX)
- 🖼️ Image analysis with Gemini Vision
- 🌍 Multi-user concurrent processing
- 🔄 No webhook required (polling-based)
- 🎯 Interactive country and language selection

### Browser Extension
- 🔍 Automatic detection of ASEAN government websites
- 📝 One-click page summarization
- 💬 In-browser AI chat sidebar
- 🎤 Voice input for questions
- 🔊 Text-to-speech responses
- 🌐 Context-aware answers based on current page
- 🎯 Language picker before summarization

## Supported Languages

All 12 ASEAN languages with dialect support:

- 🇬🇧 English (+ Manglish, Singlish)
- 🇲🇾 Bahasa Melayu (Malaysian Malay)
- 🇮🇩 Bahasa Indonesia (Indonesian)
- 🇮🇩 Sundanese (Basa Sunda)
- 🇻🇳 Vietnamese (Tiếng Việt)
- 🇹🇭 Thai (ภาษาไทย)
- 🇨🇳 Chinese Simplified (简体中文)
- 🇮🇳 Tamil (தமிழ்)
- 🇵🇭 Filipino/Tagalog (+ Taglish)
- 🇲🇲 Burmese (မြန်မာဘာသာ)
- 🇰🇭 Khmer (ភាសាខ្មែរ)
- 🇱🇦 Lao (ພາສາລາວ)

## Supported Countries

Malaysia · Indonesia · Thailand · Vietnam · Philippines · Myanmar · Cambodia · Laos · Singapore · Brunei · Timor-Leste

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Extension                         │
│  (content.js, background.js, popup.js)                      │
│  - Detects gov websites                                      │
│  - UI overlay with language picker                           │
│  - Voice input/output                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────┐
│                    │         Desktop App                     │
│                    │         (main.py)                       │
│                    │         - Flet UI                       │
│                    │         - User profiles                 │
│                    │         - Onboarding                    │
└────────────────────┼────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────┐
│                    │      Telegram Bot                       │
│                    │      (telegram_bot_server.py)           │
│                    │      - Message handling                 │
│                    │      - Voice/photo processing           │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Engine Layer                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Response Generation (engine/speech/response_gen.py) │   │
│  │  - Llama 4 Scout (primary)                          │   │
│  │  - Llama 3.1-8b (backup)                            │   │
│  │  - Ollama qwen2.5:7b (local fallback)               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  RAG Integration (engine/database/rag_integration.py)│   │
│  │  - ChromaDB vector search                            │   │
│  │  - Sentence-Transformers embeddings                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Document Processing                                 │   │
│  │  - Docling (PDF/DOCX)                               │   │
│  │  - Gemini Vision (images)                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Web Scraping (engine/speech/web_scraping.py)       │   │
│  │  - SerpAPI (government search)                       │   │
│  │  - Firecrawl (content extraction)                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Speech Processing                                   │   │
│  │  - Whisper STT (local)                              │   │
│  │  - Edge TTS / gTTS (multilingual)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────────┐  │
│  │ ChromaDB │  │  MySQL   │  │ Local  │  │ User Prefs   │  │
│  │ (Vector) │  │  (Auth)  │  │ Files  │  │ (JSON)       │  │
│  └──────────┘  └──────────┘  └────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required Software
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **MySQL Server 8.0+** - [Download](https://dev.mysql.com/downloads/mysql/)
- **Git** - For cloning the repository

### Optional (Recommended)
- **Ollama** - For local LLM fallback - [Download](https://ollama.com)
- **NVIDIA GPU with CUDA 11.8+** - For 3-5× faster inference
- **Poppler** (Windows only) - For PDF processing - [Download](https://github.com/oschwartz10612/poppler-windows/releases/)

### API Keys (Free Tiers Available)

1. **Groq API** - Get from [Groq Console](https://console.groq.com/)
   - Free tier: 30 requests/minute
   - Used for: Llama 4 Scout inference

2. **Google Gemini API** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Free tier: 60 requests/minute
   - Used for: Vision, document processing, backup LLM

3. **SerpAPI** (Optional) - Get from [SerpAPI](https://serpapi.com/)
   - Free tier: 100 searches/month
   - Used for: Government website search

4. **Firecrawl API** (Optional) - Get from [Firecrawl](https://firecrawl.dev/)
   - Free tier: 500 pages/month
   - Used for: Enhanced web scraping

5. **Hugging Face Token** (Optional) - Get from [Hugging Face](https://huggingface.co/settings/tokens)
   - Free tier: Unlimited for public models
   - Used for: Embedding models

6. **Telegram Bot Token** (For Telegram deployment) - Get from [@BotFather](https://t.me/BotFather)
   - Free
   - Used for: Telegram bot integration

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/bridge-asean-assistant.git
cd bridge-asean-assistant
```

### 2. Set Up Python Environment

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

### 3. Install Ollama (Optional but Recommended)

Download and install from [ollama.com](https://ollama.com)

After installation, pull the required model:

```bash
ollama pull qwen2.5:7b
```

### 4. Set Up MySQL Database

1. Install MySQL Server
2. Create the database and tables:

```sql
CREATE DATABASE ai_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_chatbot;

-- Create users table
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    language VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create conversations table
CREATE TABLE conversations (
    conversation_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create messages table
CREATE TABLE messages (
    message_id VARCHAR(255) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required - LLM APIs (at least one)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Required - MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ai_chatbot

# Required for Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Optional - Web Scraping
SERP_API_KEY=your_serpapi_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here

# Optional - Embeddings
HUGGINGFACE_TOKEN=your_hf_token_here
HF_TOKEN=your_hf_token_here

# Optional - Windows PDF Processing
POPPLER_PATH=C:\path\to\poppler\Library\bin

# Optional - Ollama
OLLAMA_HOST=http://localhost:11434
```

### 6. GPU Acceleration (Optional)

If you have an NVIDIA GPU, install CUDA-enabled PyTorch:

```bash
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

This provides 3-5× faster inference for embeddings and local models.

### 7. Install Browser Extension

1. Open Chrome/Brave/Edge
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `browser-extension` folder from this project
6. The Bridge extension icon should appear in your toolbar

## Usage

### Starting the Desktop Application

```bash
# Activate virtual environment (if not already activated)
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Run the desktop app
python main.py
```

The Flet UI will open with:
- Login screen with user authentication
- Onboarding tutorial for first-time users
- Home screen with chat interface
- Document upload and Q&A
- Website summarization
- Voice input/output
- Preferences and profile settings

### Starting the Telegram Bot

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows

# Run the Telegram bot
python telegram_bot_server.py
```

The bot uses long-polling (no webhook or ngrok required). Just:
1. Search for your bot in Telegram
2. Send `/start`
3. Select your country and language
4. Start asking questions!

**Telegram Bot Features:**
- Text messages with natural language
- Voice messages (automatic transcription)
- Photo analysis (Gemini Vision)
- Document Q&A (PDF, DOCX)
- Inline buttons for easy navigation

**Setup Instructions:**
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy the bot token and add it to your `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   ```
4. Run `python telegram_bot_server.py`
5. Search for your bot in Telegram and send `/start`

### Using the Browser Extension

1. Navigate to any ASEAN government website
2. The Bridge extension will automatically detect it
3. Click the extension icon or the floating button
4. Select your preferred language
5. Get an instant summary of the page
6. Use the chat sidebar to ask questions
7. Enable voice input for hands-free interaction

**Supported Government Domains:**
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

## How It Works

### RAG Pipeline

1. **User Query** - User asks a question via desktop app, Telegram, or browser extension
2. **Language Detection** - Automatically detects query language and user's country context
3. **Embedding Generation** - Converts query to vector using Sentence-Transformers
4. **Vector Search** - Searches ChromaDB for relevant cached information
5. **Web Search** (if needed) - Fetches real-time data from government websites (SerpAPI + Firecrawl)
6. **Context Assembly** - Combines cached data, web results, and conversation history
7. **LLM Processing** - Sends context to Llama 4 Scout for natural language generation
8. **Response Delivery** - Returns formatted answer with source links in user's language
9. **Caching** - Stores embeddings and results for faster future queries

### Model Hierarchy

**Primary:** Llama 4 Scout (17B) via Groq
- Fast inference (< 2 seconds)
- 3 retry attempts with exponential backoff
- Optimized for multilingual ASEAN content

**Backup:** Llama 3.1-8b-instant via Groq
- Activates if primary fails or rate limited
- Faster but less accurate

**Local Fallback:** Ollama qwen2.5:7b
- Runs on your machine
- No API limits
- Slower but always available

### Speech Features

**Speech-to-Text:**
- Local Whisper model (base)
- Supports all 12 languages
- No API calls required
- Runs on CPU or GPU

**Text-to-Speech:**
- Edge TTS for natural voices
- gTTS as fallback
- Language-specific voice mapping
- Sundanese uses Indonesian voice

## Troubleshooting

### Desktop App Issues

**Problem:** App won't start
**Solution:** 
```bash
# Ensure Flet is installed
pip install flet==0.19.0

# Check Python version
python --version  # Should be 3.10+
```

**Problem:** MySQL connection failed
**Solution:**
- Check `.env` file for correct credentials
- Ensure MySQL server is running: `mysql -u root -p`
- Verify database exists: `SHOW DATABASES;`

**Problem:** Voice input not working
**Solution:**
```bash
# Install audio dependencies
pip install sounddevice soundfile pydub

# Check microphone permissions in system settings
```

### Telegram Bot Issues

**Problem:** Bot not responding
**Solution:**
- Check bot token in `.env`
- Ensure bot is not running in another terminal
- Check firewall settings
- Verify internet connection

**Problem:** Voice messages fail to transcribe
**Solution:**
```bash
# Ensure Whisper model is downloaded
python -c "import whisper; whisper.load_model('base')"
```

**Problem:** Rate limit errors
**Solution:**
- Wait a few minutes for rate limits to reset
- Use a different Groq API key
- Ollama will automatically activate as fallback

### Browser Extension Issues

**Problem:** Extension doesn't detect government website
**Solution:**
- Check if domain matches patterns in `background.js`
- Reload the extension
- Clear browser cache

**Problem:** Summary fails to load
**Solution:**
- Check browser console for errors (F12)
- Verify API keys in `.env`
- Ensure internet connection

**Problem:** Text-to-speech not working
**Solution:**
- Check browser audio permissions
- Try a different language
- Lao uses English fallback (expected behavior)

### GPU Issues

**Problem:** CUDA out of memory
**Solution:**
```python
# Edit engine/gpu_accelerator.py
USE_GPU = False  # Force CPU mode
```

**Problem:** GPU not detected
**Solution:**
```bash
# Check CUDA installation
nvidia-smi

# Reinstall PyTorch with CUDA
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### ChromaDB Issues

**Problem:** Collection not found
**Solution:**
```bash
# Delete and reinitialize ChromaDB
rm -rf chroma_db/  # Linux/macOS
# rmdir /s chroma_db  # Windows

# Restart the application
```

## Rate Limits & Quotas

### Groq API (Free Tier)
- 30 requests per minute
- 14,400 requests per day
- Resets every minute
- Falls back to Ollama when exceeded

### Gemini API (Free Tier)
- 60 requests per minute
- 1,500 requests per day
- Resets at midnight UTC
- Used for vision and backup

### SerpAPI (Free Tier)
- 100 searches per month
- 1 search = 1 government website query
- Resets monthly

### Firecrawl API (Free Tier)
- 500 credits per month
- 1 credit = 1 page scraped
- Extension uses 3 credits per summary

### Ollama (Local)
- No limits
- Runs on your machine
- Speed depends on hardware

## Project Structure

```
bridge/
│
├── main.py                          # Desktop app entry point
├── telegram_bot_server.py           # Telegram bot entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables
├── README.md                        # This file
├── map.json                         # Configuration mappings
│
├── app/                             # Desktop Application
│   ├── components/                  # UI components
│   │   ├── controls.py              # Custom buttons, inputs
│   │   └── theme.py                 # Light/Dark theme
│   ├── views/                       # Application screens
│   │   ├── login.py                 # Login screen
│   │   ├── onboarding.py            # Tutorial
│   │   ├── preferences.py           # Settings
│   │   ├── home.py                  # Main chat
│   │   └── profile.py               # User profile
│   ├── router.py                    # Navigation
│   ├── state.py                     # App state
│   ├── splash.py                    # Loading screen
│   └── preloader.py                 # Module preloading
│
├── telegram_bot/                    # Telegram Bot
│   ├── message_handler.py           # Message processing
│   └── __init__.py
│
├── browser-extension/               # Chrome Extension
│   ├── manifest.json                # Extension config
│   ├── background.js                # Service worker
│   ├── content.js                   # Page interaction
│   ├── popup.html                   # Popup UI
│   ├── popup.js                     # Popup logic
│   └── icons/                       # Extension icons
│
├── engine/                          # Core AI Engine
│   ├── database/                    # Database layer
│   │   ├── mysql_handler.py         # MySQL operations
│   │   ├── chroma_singleton.py      # ChromaDB singleton
│   │   ├── rag_integration.py       # RAG pipeline
│   │   └── auth_handler.py          # Authentication
│   │
│   ├── speech/                      # Speech processing
│   │   ├── response_gen.py          # LLM generation
│   │   ├── speech_to_text.py        # Whisper STT
│   │   ├── text_to_speech.py        # Edge TTS / gTTS
│   │   ├── embedding.py             # Embeddings
│   │   ├── web_scraping.py          # SerpAPI + Firecrawl
│   │   ├── government_mapping.py    # Country mappings
│   │   ├── language_voice_mapping.py # TTS voices
│   │   └── chroma_config.py         # ChromaDB config
│   │
│   ├── search/                      # Document search
│   │   ├── document_summariser_v6_gemini.py  # PDF/DOCX Q&A
│   │   ├── summarizer_web.py        # URL summarization
│   │   └── speech_to_text.py        # Alternative STT
│   │
│   ├── insert_doc/                  # Document ingestion
│   │   ├── document_manager.py      # User docs
│   │   ├── system_document_manager.py # System docs
│   │   ├── document_LLM.py          # LLM extraction
│   │   ├── write_doc.py             # Doc writing
│   │   └── translate.py             # Translation
│   │
│   └── gpu_accelerator.py           # GPU detection
│
├── chroma_db/                       # Vector database (auto-generated)
├── document_db/                     # Sample documents
├── JSON_storage/                    # Form schemas
├── user_prefs/                      # User preferences
└── uploads/                         # Temp uploads
```

## Technologies Used

### Frontend
- **Flet 0.19.0** - Cross-platform desktop UI
- **Vanilla JavaScript** - Browser extension
- **Telegram Bot API** - python-telegram-bot 21.0

### AI/ML
- **Groq Llama 4 Scout (17B)** - Primary LLM
- **Groq Llama 3.1-8b-instant** - Backup LLM
- **Google Gemini 1.5 Flash** - Vision & multimodal
- **Ollama qwen2.5:7b** - Local fallback
- **Sentence-Transformers** - Text embeddings
- **OpenAI Whisper** - Speech recognition
- **Edge TTS / gTTS** - Text-to-speech

### Backend
- **Flask** - Web server (for browser extension)
- **MySQL** - User authentication
- **ChromaDB** - Vector database
- **bcrypt** - Password hashing

### Document Processing
- **Docling** - PDF/DOCX parsing
- **PyMuPDF (fitz)** - PDF extraction
- **Pillow** - Image processing
- **BeautifulSoup4** - HTML parsing

### Web Scraping
- **SerpAPI** - Government search
- **Firecrawl** - Content extraction
- **Requests** - HTTP client

### Translation
- **Deep-Translator** - Multi-language support

## Performance Optimization

### Enable GPU Acceleration
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
Result: 3-5× faster inference

### Use Faster Embedding Models
Edit `engine/speech/chroma_config.py`:
```python
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

### Reduce Token Limits
Edit `engine/speech/response_gen.py`:
```python
GROQ_MAX_TOKENS = 512  # Default: 1024
```

### Enable Caching
ChromaDB caching is enabled by default. Responses are cached for 24 hours.

## Contributing

This project was built for vHack 2026. Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Credits

Built with ❤️ for ASEAN citizens to better understand their government services.

**vHack 2026 Project**

### Acknowledgments
- **Groq** - Fast LLM inference
- **Google Gemini** - Vision and multimodal AI
- **Flet** - Cross-platform UI framework
- **ChromaDB** - Vector storage
- **OpenAI Whisper** - Speech recognition
- **SerpAPI & Firecrawl** - Web scraping
- ASEAN governments for open access to public information

## Support

For issues or questions:
- Open an issue on [GitHub](https://github.com/yourusername/bridge-asean-assistant/issues)
- Email: support@bridge-assistant.com
- Telegram: [@BridgeSupport](https://t.me/BridgeSupport)

## Roadmap

- [ ] WhatsApp integration
- [ ] Mobile app (iOS/Android)
- [ ] Offline mode with local LLMs
- [ ] Multi-document comparison
- [ ] Form auto-fill from user profile
- [ ] Voice cloning for personalized TTS
- [ ] Real-time translation during calls
- [ ] Integration with government APIs
- [ ] Blockchain-based document verification

---

**Built with ❤️ for ASEAN citizens | vHack 2026**
