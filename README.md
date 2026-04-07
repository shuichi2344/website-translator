# Bridge AI Assistant - ASEAN Government Information System

A multilingual AI assistant that helps users access government information across ASEAN countries. Available as a Flet desktop app, browser extension, and Telegram bot.

## 🌟 Features

- **Multilingual Support**: 9+ ASEAN languages (English, Malay, Indonesian, Thai, Vietnamese, Filipino, Burmese, Khmer, Lao)
- **Government Data**: Real-time fetching from official government websites
- **Voice Input**: Speech-to-text using local Whisper model
- **Document Q&A**: Upload PDFs/DOCX and ask questions
- **Image Analysis**: AI-powered image understanding with Gemini Vision
- **URL Summarization**: Instant summaries of any website
- **GPU Acceleration**: 3-5x faster with NVIDIA GPU (automatic CPU fallback)

## 📦 Three Deployment Options

### 1. 🖥️ Flet Desktop App
Full-featured desktop application with voice input and TTS.

### 2. 🌐 Browser Extension
Chrome/Edge extension for summarizing government websites on-the-fly.

### 3. 💬 Telegram Bot
Conversational bot accessible from any device.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL Server
- API Keys:
  - Google Gemini API (required)
  - SerpAPI (for government search)
  - Firecrawl API (for web scraping)
  - Hugging Face Token (for embeddings)
  - Telegram Bot Token (for Telegram bot)

### Installation

```bash
# 1. Clone repository
git clone <your-repo-url>
cd vhack2026-live-translator

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Copy .env.example to .env and fill in your API keys

# 5. Set up MySQL database
# Run the SQL scripts in DATABASE_SETUP.md
```

### Optional: GPU Acceleration

For 3-5x faster performance with NVIDIA GPU:

```bash
# Uninstall CPU-only PyTorch
pip uninstall -y torch torchvision torchaudio

# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

See [GPU_SETUP.md](GPU_SETUP.md) for details.

---

## 🖥️ 1. Flet Desktop App

### Features
- Voice input with push-to-talk
- Text-to-speech in multiple languages
- Document upload and Q&A
- User authentication
- Conversation history
- Multilingual UI

### Running

```bash
python main.py
```

### Usage
1. Create account or login
2. Select your country and language
3. Ask questions via text or voice
4. Upload documents for analysis

---

## 🌐 2. Browser Extension

### Features
- Automatic government website detection
- One-click page summarization
- Q&A about webpage content
- Multilingual summaries
- Text-to-speech for summaries

### Installation

1. Open Chrome/Edge
2. Go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `browser-extension` folder

### Usage
1. Visit any government website
2. Click the Bridge icon
3. Select your language
4. Choose "Summarise Page" or "Ask Question"

### Supported Browsers
- Chrome
- Edge
- Brave
- Any Chromium-based browser

---

## 💬 3. Telegram Bot

### Features
- Text messages with government data
- Voice message transcription
- Document upload (PDF, DOCX)
- Image analysis with Gemini Vision
- URL summarization
- Interactive onboarding
- Multilingual responses

### Setup

1. **Create Bot with BotFather**
   ```
   1. Open Telegram, search @BotFather
   2. Send /newbot
   3. Follow instructions
   4. Copy the token
   ```

2. **Configure Token**
   ```bash
   # Add to .env
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

3. **Run Bot**
   ```bash
   python telegram_bot_server.py
   ```

### Usage
1. Search for your bot on Telegram
2. Send `/start`
3. Select country and language
4. Start asking questions!

### Commands
- `/start` - Setup country and language
- `/help` - Show help message
- `/settings` - Change preferences

### Supported Input Types
- 📝 Text messages
- 🎤 Voice messages (transcribed locally)
- 📄 Documents (PDF, DOCX, DOC, TXT)
- 🖼️ Images (analyzed with Gemini Vision)
- 🔗 URLs (summarized automatically)

---

## 🗄️ Database Setup

### MySQL Tables

The system uses 4 main tables:

1. **users** - User accounts
2. **conversations** - Chat sessions
3. **messages** - Message history
4. **ChromaDB** - Vector embeddings

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for SQL scripts.

---

## 🔑 API Keys Configuration

Create a `.env` file with:

```env
# Required
GEMINI_API_KEY=your_gemini_key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_chatbot

# Optional but recommended
SERP_API_KEY=your_serpapi_key
FIRECRAWL_API_KEY=your_firecrawl_key
HF_TOKEN=your_huggingface_token

# For Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_token
```

### Getting API Keys

- **Gemini**: https://aistudio.google.com/apikey (Free: 1500 requests/day)
- **SerpAPI**: https://serpapi.com/ (Free: 100 searches/month)
- **Firecrawl**: https://firecrawl.dev (Free: 500 credits/month)
- **Hugging Face**: https://huggingface.co/settings/tokens (Free)
- **Telegram**: @BotFather on Telegram (Free)

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐      │
│  │   Flet   │  │ Browser  │  │   Telegram Bot   │      │
│  │   App    │  │Extension │  │                  │      │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘      │
└───────┼─────────────┼─────────────────┼────────────────┘
        │             │                 │
        └─────────────┴─────────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │      Engine Layer              │
        │  ┌──────────────────────────┐  │
        │  │  GPU Accelerator         │  │
        │  │  (Auto CPU Fallback)     │  │
        │  └──────────────────────────┘  │
        │  ┌──────────────────────────┐  │
        │  │  Speech Processing       │  │
        │  │  - Whisper STT           │  │
        │  │  - Edge TTS              │  │
        │  └──────────────────────────┘  │
        │  ┌──────────────────────────┐  │
        │  │  Document Processing     │  │
        │  │  - Docling               │  │
        │  │  - Gemini Vision         │  │
        │  └──────────────────────────┘  │
        │  ┌──────────────────────────┐  │
        │  │  RAG Integration         │  │
        │  │  - ChromaDB              │  │
        │  │  - EmbeddingGemma        │  │
        │  └──────────────────────────┘  │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │      Data Layer                │
        │  ┌──────────┐  ┌────────────┐ │
        │  │  MySQL   │  │  ChromaDB  │ │
        │  │ Database │  │   Vectors  │ │
        │  └──────────┘  └────────────┘ │
        └───────────────────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │    External APIs               │
        │  • Google Gemini               │
        │  • SerpAPI                     │
        │  • Firecrawl                   │
        │  • Government Websites         │
        └───────────────────────────────┘
```

---

## 🎯 Supported Countries

- 🇲🇾 Malaysia
- 🇸🇬 Singapore
- 🇮🇩 Indonesia
- 🇹🇭 Thailand
- 🇻🇳 Vietnam
- 🇵🇭 Philippines
- 🇲🇲 Myanmar
- 🇰🇭 Cambodia
- 🇱🇦 Laos
- 🇧🇳 Brunei

---

## 🌍 Supported Languages

- English
- Bahasa Melayu
- Bahasa Indonesia
- Thai (ไทย)
- Vietnamese (Tiếng Việt)
- Filipino/Tagalog
- Burmese (မြန်မာ)
- Khmer (ខ្មែរ)
- Lao (ລາວ)

---

## 📈 Performance

| Component | CPU | GPU (RTX 3060) |
|-----------|-----|----------------|
| Embeddings | 2.5s | 0.4s |
| Voice Transcription | 8s | 2s |
| Document Processing | 15s | 8s |
| Overall Response | 15-20s | 5-8s |

---

## 🐛 Troubleshooting

### Common Issues

**1. "No module named 'X'"**
```bash
pip install -r requirements.txt
```

**2. MySQL connection error**
- Check MySQL is running
- Verify credentials in `.env`
- Ensure database exists

**3. GPU not detected**
- Install CUDA-enabled PyTorch (see GPU_SETUP.md)
- Check NVIDIA drivers: `nvidia-smi`

**4. Telegram bot not responding**
- Verify token in `.env`
- Check bot is running: `python telegram_bot_server.py`
- Ensure you clicked "Start" in Telegram

**5. Browser extension not working**
- Check Flask server is running: `python engine/search/summarizer_web.py`
- Verify extension is loaded in `chrome://extensions/`

---

## 📝 Project Structure

```
vhack2026-live-translator/
├── app/                    # Flet desktop app
│   ├── components/         # UI components
│   ├── views/             # App screens
│   └── router.py          # Navigation
├── browser-extension/      # Chrome extension
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   ├── content.js
│   └── background.js
├── telegram_bot/          # Telegram bot
│   └── message_handler.py
├── engine/                # Core engine
│   ├── database/         # MySQL & ChromaDB
│   ├── search/           # Document processing
│   ├── speech/           # STT & TTS
│   └── gpu_accelerator.py
├── main.py               # Flet app entry
├── telegram_bot_server.py # Telegram bot entry
└── requirements.txt      # Dependencies
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Google Gemini for AI capabilities
- OpenAI Whisper for speech recognition
- Docling for document processing
- ChromaDB for vector storage
- Flet for desktop UI framework

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check [TELEGRAM_QUICK_START.md](TELEGRAM_QUICK_START.md) for Telegram bot help
- See [GPU_SETUP.md](GPU_SETUP.md) for GPU configuration

---

**Built for vHack 2026** 🚀
