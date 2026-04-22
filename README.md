# Bridge — ASEAN Government Information Assistant

A multilingual AI assistant that helps users access government information across ASEAN countries. Available as a **Flet desktop app**, **Chrome/Edge browser extension**, and **Telegram bot**.

Bridge simplifies access to government services by providing AI-powered answers to questions about passports, visas, permits, and official documents in 12 languages. Whether you're renewing your passport, applying for a visa, or navigating government forms, Bridge fetches real-time information from official sources and delivers clear, contextual answers.

---

## Key Features

### Multilingual Support
- **12 ASEAN Languages**: English, Bahasa Melayu, Bahasa Indonesia, Sundanese, Thai, Vietnamese, Filipino/Tagalog, Burmese, Khmer, Lao, Chinese (Simplified), Tamil
- **Dialect Recognition**: Understands Manglish, Singlish, Taglish, and other regional variations
- **Auto-Translation**: Seamlessly translates between languages for cross-border queries

### Intelligent Document Processing
- **PDF & DOCX Q&A**: Upload government forms and ask questions about requirements, fields, or procedures
- **Image Analysis**: Extract text and information from photos of documents using Gemini Vision
- **Form Extraction**: Automatically parse and understand complex government forms
- **Document Summarization**: Get concise summaries of lengthy official documents

### Real-Time Government Data
- **Live Web Scraping**: Fetches current information from official ASEAN government websites
- **SerpAPI Integration**: Searches across government portals for the most relevant answers
- **Firecrawl**: Extracts clean, structured data from government web pages
- **Source Attribution**: Every answer includes reference links to official sources

### Voice Interaction
- **Speech-to-Text**: Local Whisper model for accurate voice recognition in multiple languages
- **Text-to-Speech**: Natural-sounding voice responses using Edge TTS and gTTS
- **Hands-Free Mode**: Perfect for elderly users or accessibility needs

### RAG (Retrieval-Augmented Generation)
- **Vector Database**: ChromaDB stores embeddings for fast semantic search
- **Multi-Level Caching**: Reduces API calls and improves response times
- **Context-Aware**: Maintains conversation history for follow-up questions
- **Hybrid Search**: Combines keyword and semantic search for better accuracy

### Performance & Scalability
- **GPU Acceleration**: 3–5× faster inference with NVIDIA CUDA support
- **CPU Fallback**: Automatically switches to CPU if GPU unavailable
- **Concurrent Processing**: Handles multiple users simultaneously (Telegram bot)
- **Async Architecture**: Non-blocking operations for responsive UI

### User Experience
- **Minimalistic UI**: Clean, accessible design optimized for elderly and non-technical users
- **Light/Dark Mode**: Comfortable viewing in any lighting condition
- **Onboarding Tutorial**: First-time user walkthrough with preferences setup
- **Adjustable Font Sizes**: Small, Medium, Large options for accessibility
- **Cross-Platform**: Desktop app, browser extension, and mobile-friendly Telegram bot

---

## Supported Countries

Malaysia · Indonesia · Thailand · Vietnam · Philippines · Myanmar · Cambodia · Laos · Singapore · Brunei · Timor-Leste

---

## How It Works

Bridge uses a sophisticated RAG (Retrieval-Augmented Generation) pipeline to deliver accurate, contextual answers:

1. **User Query**: User asks a question via desktop app, Telegram, or browser extension
2. **Language Detection**: Automatically detects the query language and user's country context
3. **Embedding Generation**: Converts the query into a vector embedding using Sentence-Transformers
4. **Vector Search**: Searches ChromaDB for relevant cached information and document chunks
5. **Web Search** (if needed): Fetches real-time data from government websites using SerpAPI + Firecrawl
6. **Context Assembly**: Combines cached data, web results, and conversation history
7. **LLM Processing**: Sends context to Groq/Gemini for natural language generation
8. **Response Delivery**: Returns formatted answer with source links in the user's language
9. **Caching**: Stores embeddings and results for faster future queries

### Architecture Diagram

```
┌─────────────┐
│   User      │
│  (Desktop/  │
│  Telegram/  │
│  Browser)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Application Layer               │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │  Flet UI │  │ Telegram │  │Browser ││
│  │          │  │   Bot    │  │  Ext   ││
│  └──────────┘  └──────────┘  └────────┘│
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Engine Layer                    │
│  ┌──────────────────────────────────┐   │
│  │  Response Generation             │   │
│  │  (Groq/Gemini LLM)              │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  RAG Integration                 │   │
│  │  (Embeddings + Vector Search)    │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Document Processing             │   │
│  │  (Docling, PyMuPDF, Gemini)     │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Web Scraping                    │   │
│  │  (SerpAPI, Firecrawl)           │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Speech Processing               │   │
│  │  (Whisper STT, Edge TTS)        │   │
│  └──────────────────────────────────┘   │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Data Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ ChromaDB │  │  MySQL   │  │ Local  ││
│  │ (Vector) │  │  (Auth)  │  │ Files  ││
│  └──────────┘  └──────────┘  └────────┘│
└─────────────────────────────────────────┘
```

---

## Three Deployment Options

| Mode | Entry Point | Use Case | Features |
|------|-------------|----------|----------|
| 🖥️ **Desktop App** | `python main.py` | Full-featured local application | Voice I/O, document upload, onboarding tutorial, preferences |
| 💬 **Telegram Bot** | `python telegram_bot_server.py` | Mobile-friendly messaging | Voice messages, photo analysis, document Q&A, no installation |
| 🌐 **Browser Extension** | Load `browser-extension/` unpacked | In-browser assistance | Page summarization, contextual chat, one-click access |

---

## Tech Stack

### Frontend & UI
- **Flet 0.19**: Cross-platform desktop UI framework (Python)
- **Browser Extension**: Manifest v3 for Chrome/Edge
- **Telegram Bot API**: python-telegram-bot 21.0

### AI & Machine Learning
- **LLMs**: 
  - Groq Llama 4 Scout (17B) — Primary model for all deployments
  - Groq Llama 3.1-8b-instant — Backup model
  - Google Gemini 1.5 Flash — Vision and multimodal capabilities
  - Ollama qwen2.5:7b — Local fallback for offline use
- **Embeddings**: Sentence-Transformers, Hugging Face models
- **Vector Database**: ChromaDB for semantic search
- **GPU Acceleration**: PyTorch with CUDA 11.8 support

### Document & Data Processing
- **Document Parsing**: Docling, PyMuPDF (fitz), Pillow
- **Web Scraping**: Firecrawl (structured extraction), BeautifulSoup4
- **Search**: SerpAPI for government website queries
- **Translation**: Deep-Translator for multilingual support

### Speech & Audio
- **Speech-to-Text**: OpenAI Whisper (local model)
- **Text-to-Speech**: Edge TTS, gTTS
- **Audio Processing**: SoundDevice, PyDub, NumPy

### Backend & Storage
- **Database**: MySQL with bcrypt authentication
- **File Storage**: Local filesystem for documents and user preferences
- **Caching**: Multi-level caching (ChromaDB + in-memory)

### APIs & Services
- **SerpAPI**: Government website search
- **Firecrawl**: Web content extraction
- **Groq API**: Fast LLM inference
- **Google Gemini API**: Vision and advanced reasoning

---

## Prerequisites

Before installing Bridge, ensure you have:

- **Python 3.10 or higher** ([Download](https://www.python.org/downloads/))
- **MySQL Server 8.0+** ([Download](https://dev.mysql.com/downloads/mysql/))
- **Git** (for cloning the repository)
- **API Keys** (see [Environment Variables](#environment-variables) section)

### Optional (for GPU acceleration)
- **NVIDIA GPU** with CUDA 11.8+ support
- **CUDA Toolkit 11.8** ([Download](https://developer.nvidia.com/cuda-11-8-0-download-archive))

### Optional (for PDF processing on Windows)
- **Poppler** ([Download](https://github.com/oschwartz10612/poppler-windows/releases/))

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/bridge-asean-assistant.git
cd bridge-asean-assistant
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Then edit `.env` and add your API keys (see [Environment Variables](#environment-variables) section below).

### Step 5: Set Up MySQL Database

Follow the detailed instructions in [DATABASE_SETUP.md](DATABASE_SETUP.md) to:
1. Create the database
2. Set up tables and schemas
3. Configure user authentication

Quick setup:
```sql
CREATE DATABASE ai_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_chatbot;

-- Run the SQL scripts from DATABASE_SETUP.md
```

### Step 6: Initialize ChromaDB

ChromaDB will be automatically initialized on first run. The vector database will be created in the `chroma_db/` directory.

### Step 7: (Optional) GPU Acceleration

If you have an NVIDIA GPU, uninstall the CPU version of PyTorch and install the CUDA version:

```bash
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

This provides 3–5× faster inference for embeddings and local models.

### Step 8: (Optional) Install Poppler (Windows only)

For PDF processing on Windows:
1. Download Poppler from [here](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract to a folder (e.g., `C:\poppler`)
3. Add the path to your `.env` file:
   ```env
   POPPLER_PATH=C:\poppler\Library\bin
   ```

---

## Running the Application

### Desktop App

Launch the full-featured Flet desktop application:

```bash
python main.py
```

Features:
- Voice input/output
- Document upload and Q&A
- Onboarding tutorial for new users
- Preferences management (language, country, font size, theme)
- Chat history

### Telegram Bot

Start the Telegram bot server (no webhook or ngrok required):

```bash
python telegram_bot_server.py
```

The bot uses long-polling, so it works without any additional setup. Just:
1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Add the token to your `.env` file
3. Run the server
4. Search for your bot in Telegram and send `/start`

Features:
- Text messages
- Voice messages (automatic transcription)
- Photo analysis
- Document Q&A (PDF, DOCX)
- Inline country and language selection

See [TELEGRAM_QUICK_START.md](TELEGRAM_QUICK_START.md) for detailed setup instructions.

### Browser Extension

Install the Chrome/Edge extension:

1. Open your browser and navigate to:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select the `browser-extension/` folder from this project

Features:
- One-click page summarization on government websites
- In-browser AI chat sidebar
- Contextual answers based on current page
- Syncs with your desktop app preferences

---

## Environment Variables

Create a `.env` file in the project root with the following configuration:

### Required Variables

```env
# LLM APIs (at least one required)
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ai_chatbot

# Telegram Bot (required for Telegram deployment)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### Optional Variables

```env
# Web Scraping & Search
SERP_API_KEY=your_serpapi_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here

# Hugging Face (for embeddings)
HUGGINGFACE_TOKEN=your_hf_token_here
HF_TOKEN=your_hf_token_here

# Windows PDF Processing
POPPLER_PATH=C:\path\to\poppler\Library\bin

# Google Cloud (if using Google Speech-to-Text)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Ollama (for local LLM fallback)
OLLAMA_HOST=http://localhost:11434
```

### How to Get API Keys

1. **Gemini API Key**: 
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in and create a new API key
   - Free tier: 60 requests/minute

2. **Groq API Key**:
   - Visit [Groq Console](https://console.groq.com/)
   - Sign up and navigate to API Keys
   - Free tier: 30 requests/minute

3. **SerpAPI Key**:
   - Visit [SerpAPI](https://serpapi.com/)
   - Sign up for a free account
   - Free tier: 100 searches/month

4. **Firecrawl API Key**:
   - Visit [Firecrawl](https://firecrawl.dev/)
   - Sign up and get your API key
   - Free tier: 500 pages/month

5. **Telegram Bot Token**:
   - Open Telegram and search for [@BotFather](https://t.me/BotFather)
   - Send `/newbot` and follow the instructions
   - Copy the token provided

6. **Hugging Face Token**:
   - Visit [Hugging Face](https://huggingface.co/settings/tokens)
   - Create a new access token
   - Free tier: unlimited for public models

---

## Project Structure

```
bridge/
│
├── main.py                          # Desktop app entry point
├── telegram_bot_server.py           # Telegram bot entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (create from .env.example)
├── README.md                        # This file
├── DATABASE_SETUP.md                # MySQL database setup guide
├── TELEGRAM_QUICK_START.md          # Telegram bot setup guide
│
├── app/                             # Flet Desktop Application
│   ├── views/                       # UI screens
│   │   ├── login.py                 # Login screen
│   │   ├── onboarding.py            # First-time user tutorial
│   │   ├── preferences.py           # Language/country/font setup
│   │   ├── home.py                  # Main chat interface
│   │   └── profile.py               # User profile and settings
│   ├── components/                  # Reusable UI components
│   │   ├── controls.py              # Custom buttons, inputs, etc.
│   │   └── theme.py                 # Light/dark mode theme definitions
│   ├── router.py                    # Navigation and routing logic
│   ├── state.py                     # Global application state
│   ├── splash.py                    # Splash screen with loading animation
│   └── preloader.py                 # Background module preloading
│
├── engine/                          # Core AI Engine
│   ├── database/                    # Database integrations
│   │   ├── mysql_handler.py         # MySQL connection and queries
│   │   ├── chroma_singleton.py      # ChromaDB vector store singleton
│   │   ├── rag_integration.py       # RAG pipeline implementation
│   │   └── auth_handler.py          # User authentication with bcrypt
│   │
│   ├── speech/                      # Speech processing
│   │   ├── speech_to_text.py        # Whisper STT implementation
│   │   ├── text_to_speech.py        # Edge TTS / gTTS implementation
│   │   ├── embedding.py             # Sentence-Transformers embeddings
│   │   ├── response_gen.py          # LLM response generation (Groq/Gemini)
│   │   ├── government_mapping.py    # Country-to-government-site mapping
│   │   ├── language_voice_mapping.py # Language-to-TTS-voice mapping
│   │   ├── web_scraping.py          # SerpAPI + Firecrawl integration
│   │   └── chroma_config.py         # ChromaDB configuration
│   │
│   ├── search/                      # Document and web search
│   │   ├── document_summariser_v6_gemini.py  # PDF/DOCX Q&A with Gemini
│   │   ├── summarizer_web.py        # URL summarization
│   │   ├── speech_to_text.py        # Alternative STT implementation
│   │   └── uploads/                 # Temporary file uploads
│   │
│   ├── insert_doc/                  # Document ingestion
│   │   ├── document_manager.py      # User document management
│   │   ├── system_document_manager.py # System document management
│   │   ├── document_LLM.py          # LLM-based document extraction
│   │   ├── write_doc.py             # Document writing utilities
│   │   └── translate.py             # Translation utilities
│   │
│   └── gpu_accelerator.py           # GPU detection and acceleration
│
├── telegram_bot/                    # Telegram Bot Integration
│   ├── message_handler.py           # Message processing and routing
│   └── __init__.py
│
├── browser-extension/               # Chrome/Edge Browser Extension
│   ├── manifest.json                # Extension manifest (v3)
│   ├── background.js                # Service worker
│   ├── content.js                   # Content script for page interaction
│   ├── popup.html                   # Extension popup UI
│   ├── popup.js                     # Popup logic
│   └── icons/                       # Extension icons (16, 48, 128px)
│
├── chroma_db/                       # ChromaDB Vector Store (auto-generated)
│   ├── chroma.sqlite3               # SQLite metadata
│   └── [collection-ids]/            # Vector embeddings
│
├── document_db/                     # Sample Government Documents
│   ├── Apex_Life_Beneficiary_Final.pdf
│   ├── Motor_Vehicle_Insurans_Claim_Form.pdf
│   └── BK-02 (Borang Kemas Kini Maklumat Permohonan STR).pdf
│
├── JSON_storage/                    # Extracted Form Schemas
│   ├── Apex_Life_Beneficiary.json
│   ├── Apex_Motor_Vehicle_Insurans_Claim_Form.json
│   └── lhdn_mystr_2026_updated.json
│
├── user_prefs/                      # User Preference Files
│   ├── user.json                    # Default user preferences
│   └── [username].json              # Per-user preference files
│
└── uploads/                         # Temporary file uploads (auto-cleaned)
```

### Key Directories Explained

- **app/**: Contains all Flet desktop UI code, including screens, components, and navigation
- **engine/**: Core AI functionality — RAG, embeddings, LLM calls, speech processing, web scraping
- **telegram_bot/**: Telegram bot-specific message handling and routing
- **browser-extension/**: Chrome/Edge extension for in-browser assistance
- **chroma_db/**: Persistent vector database for semantic search (auto-generated)
- **document_db/**: Sample government forms for testing and demonstration
- **JSON_storage/**: Extracted form schemas used for intelligent form filling
- **user_prefs/**: Per-user settings (language, country, font size, theme)

---

## Usage Examples

### Desktop App

1. **First-Time Setup**:
   - Launch the app with `python main.py`
   - Complete the onboarding tutorial
   - Select your country, language, and font size
   - Start chatting!

2. **Asking Questions**:
   ```
   User: "How do I renew my passport in Malaysia?"
   Bridge: [Searches Malaysian government websites]
          "To renew your Malaysian passport, you can..."
          [Provides step-by-step instructions with links]
   ```

3. **Document Q&A**:
   - Click "Upload Document"
   - Select a PDF or DOCX file
   - Ask questions: "What documents do I need for this form?"

4. **Voice Input**:
   - Click the microphone button
   - Speak your question
   - Bridge transcribes and responds with voice output

### Telegram Bot

1. **Setup**:
   ```
   /start
   [Select your country]
   [Select your language]
   ```

2. **Text Questions**:
   ```
   User: "Bagaimana cara memperbaharui pasport saya?"
   Bot: [Responds in Bahasa Melayu with relevant information]
   ```

3. **Voice Messages**:
   - Record a voice message in Telegram
   - Bot transcribes and responds

4. **Document Analysis**:
   - Send a PDF or photo of a document
   - Ask: "What is this form for?"

### Browser Extension

1. **Page Summarization**:
   - Visit a government website
   - Click the Bridge extension icon
   - Click "Summarise this page"
   - Get a concise summary

2. **Contextual Chat**:
   - Open the extension sidebar
   - Ask questions about the current page
   - Get answers based on page content

---

## Configuration

### User Preferences

User preferences are stored in `user_prefs/[username].json`:

```json
{
  "language": "English",
  "country": "Malaysia",
  "font_size": "Medium",
  "theme_mode": "Light",
  "voice_enabled": true,
  "auto_translate": false
}
```

### ChromaDB Configuration

ChromaDB settings are in `engine/speech/chroma_config.py`:

```python
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "government_docs"
```

### LLM Configuration

LLM settings are consistent across all deployment modes:

**Primary Model** (Desktop App & Telegram Bot):
```python
# Primary LLM (Groq Llama 4 Scout)
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TEMPERATURE = 0.4
GROQ_MAX_TOKENS = 1024

# Backup LLM
BACKUP_MODEL = "llama-3.1-8b-instant"

# Local Fallback (Ollama)
OLLAMA_MODEL = "qwen2.5:7b"
```

**Vision/Image Analysis**:
```python
# Groq Vision (Telegram bot)
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Gemini Vision (Desktop app & document processing)
GEMINI_VISION_MODEL = "gemini-1.5-flash"
```

**Model Hierarchy**:
1. Llama 4 Scout (primary, with 3 retry attempts)
2. Llama 3.1-8b-instant (backup if primary fails)
3. Ollama qwen2.5:7b (local fallback if all cloud models fail)

---

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'flet'"**
   - Solution: Activate your virtual environment and run `pip install -r requirements.txt`

2. **"MySQL connection failed"**
   - Solution: Check your `.env` file for correct MySQL credentials
   - Ensure MySQL server is running: `mysql -u root -p`

3. **"CUDA out of memory"**
   - Solution: Reduce batch size or switch to CPU mode
   - Edit `engine/gpu_accelerator.py` to force CPU: `USE_GPU = False`

4. **"Telegram bot not responding"**
   - Solution: Check your bot token in `.env`
   - Ensure the bot is not already running in another terminal
   - Check firewall settings

5. **"ChromaDB collection not found"**
   - Solution: Delete `chroma_db/` folder and restart the app
   - ChromaDB will reinitialize automatically

6. **"Whisper model download failed"**
   - Solution: Manually download the model:
     ```bash
     python -c "import whisper; whisper.load_model('base')"
     ```

7. **"PDF processing error on Windows"**
   - Solution: Install Poppler and set `POPPLER_PATH` in `.env`

### Performance Optimization

1. **Enable GPU Acceleration**:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Use Faster Embedding Models**:
   - Edit `engine/speech/chroma_config.py`
   - Change to: `EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`

3. **Reduce LLM Token Limits**:
   - Edit `engine/speech/response_gen.py`
   - Set: `GROQ_MAX_TOKENS = 512`

4. **Enable Caching**:
   - ChromaDB caching is enabled by default
   - Responses are cached for 24 hours

### Logging

Enable debug logging by setting in your `.env`:

```env
LOG_LEVEL=DEBUG
```

Logs are written to:
- Console (stdout)
- `logs/bridge.log` (if configured)

---

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linter
flake8 .

# Format code
black .
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Groq** for fast LLM inference
- **Google Gemini** for vision and multimodal capabilities
- **Flet** for the cross-platform UI framework
- **ChromaDB** for vector storage
- **OpenAI Whisper** for speech recognition
- **SerpAPI** and **Firecrawl** for web scraping
- ASEAN governments for providing open access to public information

---

**Built with ❤️ for ASEAN citizens for VHACK2026**
