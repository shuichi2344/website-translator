# Bridge — ASEAN Government Information Assistant

A multilingual AI assistant that helps users access government information across ASEAN countries. Available as a **Flet desktop app**, **Chrome/Edge browser extension**, and **Telegram bot**.

---

## Features

- **Multilingual**: 11 ASEAN languages — English, Bahasa Melayu, Bahasa Indonesia, Thai, Vietnamese, Filipino/Tagalog, Burmese, Khmer, Lao, Chinese (Simplified), Tamil — plus dialect support (Manglish, Singlish, Taglish, etc.)
- **RAG Architecture**: Query → Embedding → ChromaDB → LLM → Response, with multi-level caching
- **Government Data**: Real-time fetching from official ASEAN government websites via SerpAPI + Firecrawl
- **Document Q&A**: Upload PDFs or DOCX files and ask questions (Docling + RAG)
- **Image Analysis**: Gemini Vision for image understanding
- **Voice I/O**: Local Whisper speech-to-text, Edge TTS / gTTS text-to-speech in multiple languages
- **URL Summarization**: One-click summaries of any website
- **GPU Acceleration**: 3–5× faster with NVIDIA GPU; automatic CPU fallback
- **Concurrent Multi-user**: Thread-pool-based handling for the Telegram bot

---

## Supported Countries

Malaysia · Indonesia · Thailand · Vietnam · Philippines · Myanmar · Cambodia · Laos · Singapore · Brunei · Timor-Leste

---

## Three Deployment Options

| Mode | Entry Point | Notes |
|------|-------------|-------|
| 🖥️ Desktop App | `python main.py` | Full UI with voice input/output |
| 💬 Telegram Bot | `python telegram_bot_server.py` | No webhook needed — polling-based |
| 🌐 Browser Extension | Load `browser-extension/` unpacked | Chrome / Edge, Manifest v3 |

---

## Tech Stack

| Layer | Libraries / Services |
|-------|----------------------|
| Desktop UI | Flet 0.19 |
| LLM | Groq (Llama 4 Scout, Llama 3.3-70b, Llama 3.1-8b), Google Gemini, Ollama (local fallback) |
| Embeddings | Sentence-Transformers, Hugging Face |
| Vector DB | ChromaDB |
| Document Processing | Docling, PyMuPDF (fitz), Pillow |
| Web Scraping | Firecrawl, BeautifulSoup |
| Speech | Whisper (STT), Edge TTS / gTTS (TTS), SoundDevice, PyDub |
| Translation | Deep-Translator |
| Database | MySQL + bcrypt auth |
| Search | SerpAPI |
| Messaging | python-telegram-bot 21.0, Twilio (WhatsApp) |

---

## Prerequisites

- Python 3.10+
- MySQL Server
- API keys (see [Environment Variables](#environment-variables))

---

## Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd vhack2026-live-translator

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env          # then fill in your keys

# 5. Set up the MySQL database
# Follow the instructions in DATABASE_SETUP.md
```

### Optional: GPU Acceleration

```bash
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Running

### Desktop App

```bash
python main.py
```

### Telegram Bot

```bash
python telegram_bot_server.py
```

No ngrok or webhook setup required — the bot uses long-polling.

### Browser Extension

1. Open Chrome or Edge and go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `browser-extension/` folder

---

## Environment Variables

Create a `.env` file in the project root with the following keys:

```env
# Required
GEMINI_API_KEY=
GROQ_API_KEY=
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=ai_chatbot
TELEGRAM_BOT_TOKEN=

# Optional
SERP_API_KEY=
FIRECRAWL_API_KEY=
HUGGINGFACE_TOKEN=
HF_TOKEN=
POPPLER_PATH=          # Windows only — path to Poppler bin folder
GOOGLE_APPLICATION_CREDENTIALS=   # For Google Cloud Speech (if used)
```

---

## Project Structure

```
bridge/
├── main.py                     # Desktop app entry point
├── telegram_bot_server.py      # Telegram bot entry point
├── requirements.txt
├── .env
│
├── app/                        # Flet desktop UI
│   ├── views/                  # home, login, onboarding, preferences, profile
│   ├── components/             # Reusable UI controls and theme
│   ├── router.py
│   ├── state.py
│   ├── splash.py
│   └── preloader.py
│
├── engine/                     # Core AI engine
│   ├── database/               # MySQL handler, ChromaDB singleton, RAG integration, auth
│   ├── speech/                 # STT, TTS, embeddings, response generation, gov mapping
│   ├── search/                 # Document summarizer, web summarizer, speech-to-text
│   ├── insert_doc/             # Document ingestion, LLM extraction, form writing
│   └── gpu_accelerator.py
│
├── telegram_bot/               # Telegram bot handler
├── browser-extension/          # Chrome/Edge extension (Manifest v3)
├── document_db/                # Sample PDF documents
├── JSON_storage/               # Extracted form schemas (JSON)
├── chroma_db/                  # ChromaDB vector store (auto-generated)
└── user_prefs/                 # Per-user preference files
```

---

## Database Setup

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for the full MySQL schema and setup instructions.

---

## Telegram Bot Quick Start

See [TELEGRAM_QUICK_START.md](TELEGRAM_QUICK_START.md) for step-by-step Telegram bot setup.
