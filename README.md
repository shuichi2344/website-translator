# Bridge - ASEAN Government Information Assistant

Bridge is an AI-powered assistant that helps ASEAN citizens access and understand government information in their preferred language. It consists of two main components:

1. **Desktop Application (Flet)** - Full-featured app with document/website summarization and voice chat
2. **Browser Extension (Chrome)** - Real-time government website summarization with Q&A

## 🌟 Features

### Desktop Application
- 🔐 User authentication with MySQL database
- 📄 Document summarization (PDF, DOCX, images)
- 🌐 Website summarization with automatic crawling
- 🤖 AI-powered Q&A on documents and websites
- 🎤 Voice chat with speech-to-text and text-to-speech
- 🌍 Support for 11 ASEAN languages
- 💾 Conversation history with RAG (Retrieval-Augmented Generation)
- 👤 User profiles with country and language preferences
- 🎨 Modern UI with purple-pink-mint gradient theme

### Browser Extension
- 🔍 Automatic detection of ASEAN government websites
- 📝 One-click summarization in any ASEAN language
- 💬 Interactive Q&A with voice and text input
- 🔊 Text-to-speech with pause/resume controls
- 🎯 Language picker before summarization
- 📱 Clean, scrollable chat interface
- 🔗 Source references for all responses

## 🌏 Supported Languages & Countries

### Languages
- 🇬🇧 English
- 🇲🇾 Bahasa Melayu (Malaysian Malay)
- 🇮🇩 Bahasa Indonesia (Indonesian)
- 🇹🇭 Thai (ภาษาไทย)
- 🇻🇳 Vietnamese (Tiếng Việt)
- 🇵🇭 Filipino/Tagalog
- 🇲🇲 Burmese (မြန်မာဘာသာ)
- 🇰🇭 Khmer (ភាសាខ្មែរ)
- 🇱🇦 Lao (ພາສາລາວ)
- 🇨🇳 Chinese (Simplified) (简体中文)
- 🇮🇳 Tamil (தமிழ்)

### Countries
Malaysia, Indonesia, Thailand, Vietnam, Philippines, Myanmar, Cambodia, Laos, Singapore, Brunei, Timor-Leste

**Personalized Experience**: Responses are generated in your selected language, and government sources are filtered by your selected country.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Extension                         │
│  (content.js, background.js, popup.js)                      │
│  - Detects gov websites                                      │
│  - UI overlay with chat interface                            │
│  - Voice input/output with pause/resume                      │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP (localhost:5000)
┌────────────────────▼────────────────────────────────────────┐
│                  Flask Backend Server                        │
│              (engine/search/summarizer_web.py)               │
│  - Authentication (register/login)                           │
│  - Website/document processing                               │
│  - AI summarization (Gemini 2.0 Flash)                       │
│  - RAG-based Q&A with ChromaDB                              │
│  - Speech-to-text (Whisper)                                  │
│  - Text-to-speech (edge-tts)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐    ┌──────────▼──────────┐
│  Desktop App   │    │   Data Storage      │
│  (main.py)     │    │  - MySQL (users,    │
│  - Flet UI     │    │    conversations,   │
│  - User auth   │    │    messages)        │
│  - Profiles    │    │  - ChromaDB         │
│  - Voice chat  │    │    (embeddings)     │
└────────────────┘    └─────────────────────┘
```

## 📋 Prerequisites

### Required Software
- **Python 3.12** or higher
- **MySQL 8.0** or higher (or XAMPP/WAMP)
- **Chrome/Brave/Edge** browser (for extension)

### API Keys (Free Tiers Available)
1. **Google Gemini API** - [Get from Google AI Studio](https://aistudio.google.com/apikey)
   - Free tier: 1,500 requests/day
2. **Firecrawl API** - [Get from Firecrawl](https://firecrawl.dev)
   - Free tier: 500 credits/month
3. **Hugging Face Token** - [Get from Hugging Face](https://huggingface.co/settings/tokens)
   - Required for embedding models
4. **SerpAPI Key** - [Get from SerpAPI](https://serpapi.com/)
   - Free tier: 100 searches/month
   - Required for "Ask a Question" feature

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd vhack2026-live-translator
```

### Step 2: Set Up MySQL Database

#### Option A: Using XAMPP/WAMP
1. Download and install [XAMPP](https://www.apachefriends.org/) or [WAMP](https://www.wampserver.com/)
2. Start Apache and MySQL services
3. Open phpMyAdmin (http://localhost/phpmyadmin)
4. Create a new database named `ai_chatbot`
5. Import or run the following SQL:

#### Option B: Using MySQL Directly
1. Download and install [MySQL](https://dev.mysql.com/downloads/mysql/)
2. Open MySQL command line or MySQL Workbench
3. Run the following SQL:

```sql
CREATE DATABASE ai_chatbot;
USE ai_chatbot;

CREATE TABLE users (
    user_id CHAR(36) PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    country VARCHAR(50),
    language VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE conversations (
    conversation_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36),
    title VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE messages (
    message_id CHAR(36) PRIMARY KEY,
    conversation_id CHAR(36),
    sender ENUM('user', 'bot'),
    message_text TEXT,
    embedding_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX idx_user_id ON conversations(user_id);
CREATE INDEX idx_conversation_id ON messages(conversation_id);
CREATE INDEX idx_embedding_id ON messages(embedding_id);
```

### Step 3: Set Up Python Environment

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

**Note**: Installation may take 5-10 minutes as it downloads AI models and dependencies.

### Step 4: Configure Environment Variables

Create a `.env` file in the project root with your API keys and database credentials:

```env
# Google Gemini API Key (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here

# Firecrawl API Key (REQUIRED)
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# Hugging Face Token (REQUIRED)
HF_TOKEN=your_huggingface_token_here

# SerpAPI Key (REQUIRED for Ask a Question feature)
SERP_API_KEY=your_serpapi_key_here

# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password_here
MYSQL_DATABASE=ai_chatbot
```

**Important**: Replace all placeholder values with your actual API keys and MySQL password.

### Step 5: Install Browser Extension

1. Open Chrome/Brave/Edge browser
2. Navigate to `chrome://extensions/`
3. Enable **"Developer mode"** (toggle in top right corner)
4. Click **"Load unpacked"**
5. Select the `browser-extension` folder from this project
6. The Bridge extension icon (🌉) should appear in your toolbar

**Permissions Required**:
- Active Tab: To read current page content
- Storage: To save user preferences
- Microphone: For voice input feature

## 🎯 Usage

### Starting the System

#### 1. Start MySQL Database
- **XAMPP/WAMP**: Start MySQL service from control panel
- **MySQL**: Ensure MySQL service is running

#### 2. Start Flask Backend Server

The Flask server must be running for both the desktop app and browser extension to work.

**Windows:**
```bash
.venv\Scripts\python engine\search\summarizer_web.py
```

**macOS/Linux:**
```bash
source .venv/bin/activate
python engine/search/summarizer_web.py
```

You should see:
```
============================================================
Bridge API Backend - Document Summarizer
API-only server for browser extension and Flet app
Docling + Google Gemini 2.0 Flash + MySQL + ChromaDB
============================================================

✅ Connected to MySQL database
gTTS available: True
Database available: True

API Server starting on http://localhost:5000

Available endpoints:
  • /api/register, /api/login - Authentication
  • /api/chat - RAG-powered chat
  • /summarize/document, /summarize/website - Summarization
  • /qa/document, /qa/website - Q&A
  • /speech-to-text, /tts - Speech services
```

**Keep this terminal window open** while using the application.

#### 3. Start Desktop Application (Optional)

In a **new terminal window**:

**Windows:**
```bash
.venv\Scripts\python main.py
```

**macOS/Linux:**
```bash
source .venv/bin/activate
python main.py
```

### Using the Desktop Application

#### First-Time Setup
1. **Register**: Enter your name, email, and password
2. **Onboarding**: 
   - Watch the tutorial (optional)
   - Select your country (e.g., Malaysia, Indonesia)
   - Select your language (e.g., English, Bahasa Melayu)
3. **Home Screen**: Start using the app

#### Features

**Document Summarization**:
1. Click "Analyze Document / Image"
2. Upload a PDF, DOCX, or image file
3. Select target language
4. Click "Summarize Document"
5. View summary with word count reduction

**Website Summarization**:
1. Click "Extract from Web Link"
2. Paste a government website URL
3. Select target language
4. Click "Summarize Website"
5. View summary from crawled pages

**Ask Questions**:
1. After uploading a document or entering a URL
2. Type your question in the chat box
3. Click "Ask a Question"
4. Get AI-powered answers with sources

**Voice Chat**:
1. Press and hold the microphone button
2. Speak your question
3. Release to process
4. Listen to the response with the speaker button

**Profile Settings**:
1. Click the profile icon (top right)
2. Change your language or country
3. Changes sync to database automatically
4. Log out when done

### Using the Browser Extension

#### Setup
1. Ensure Flask server is running at `http://localhost:5000`
2. Navigate to any ASEAN government website
   - Examples: 
     - Malaysia: https://www.malaysia.gov.my
     - Singapore: https://www.gov.sg
     - Indonesia: https://www.indonesia.go.id

#### Features

**Summarization**:
1. A purple floating button (🤖 Bridge Assistant) appears on government websites
2. Click the button to open the language picker
3. Select "📄 Summarise Page" and choose your language
4. Wait for the AI to generate a summary
5. View the summary with source references

**Ask Questions**:
1. Click "💬 Ask Question" from the language picker
2. Type your question or use the microphone (🎤)
3. Get instant answers based on the website content
4. View source links for verification

**Text-to-Speech**:
1. Click the "🔊 Listen" button on any bot response
2. Button changes to "⏸️ Pause" while playing
3. Click again to pause/resume
4. Audio automatically cleans up after playback

**Chat History**:
- All conversations are saved to the database
- Linked to your user account
- Accessible across sessions

### Supported Government Domains

The extension automatically detects these domains:
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
- **Timor-Leste**: `.gov.tl`
- **Generic**: `government.`, `ministry.`, `parliament.`

## 🔧 How It Works

### User Personalization
1. **Country Selection**: Filters government sources to your selected country
2. **Language Selection**: Generates all responses in your preferred language
3. **Database Sync**: Preferences saved to MySQL and loaded on login

### Summarization Pipeline
1. **Web Scraping**: Firecrawl extracts content (crawls up to 3 subpages)
2. **Embedding**: Content chunked and embedded using SentenceTransformer
3. **Vector Storage**: Embeddings stored in ChromaDB for semantic search
4. **AI Summarization**: Gemini 2.0 Flash generates summary in target language
5. **Delivery**: Summary sent to browser extension or desktop app

### Q&A Pipeline (RAG)
1. **Question Processing**: User question embedded using SentenceTransformer
2. **Semantic Search**: ChromaDB retrieves most relevant content chunks
3. **Context Building**: Combines relevant chunks with conversation history
4. **RAG Generation**: Gemini generates answer using retrieved context
5. **Language Translation**: Answer generated in user's preferred language
6. **Storage**: Question and answer saved to MySQL + ChromaDB

### Speech Features
- **Speech-to-Text**: Whisper model via Transformers pipeline
- **Text-to-Speech**: edge-tts with multiple voice fallbacks
  - Supports pause/resume with pygame mixer
  - Automatic cleanup of temporary audio files

### Database Integration
- **MySQL**: Stores users, conversations, messages (structured data)
- **ChromaDB**: Stores embeddings for semantic search (vector data)
- **Linking**: `message_id` = `embedding_id` for seamless integration
- **RAG**: Combines semantic search with conversation context

## 🐛 Troubleshooting

### Database Issues

**Problem**: `Error connecting to MySQL: Access denied`
**Solution**: 
1. Check MYSQL_PASSWORD in `.env` file
2. Verify MySQL service is running
3. Test connection: `mysql -u root -p`

**Problem**: `Table 'ai_chatbot.users' doesn't exist`
**Solution**: Run the SQL schema creation script (see Step 2)

### Flask Server Issues

**Problem**: `ModuleNotFoundError: No module named 'flask'`
**Solution**: 
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

**Problem**: `Address already in use (Port 5000)`
**Solution**: 
1. Kill existing process: `taskkill /F /IM python.exe` (Windows)
2. Or change port in `summarizer_web.py`

**Problem**: `Database available: False`
**Solution**: Check MySQL connection settings in `.env`

### Browser Extension Issues

**Problem**: Extension doesn't detect government website
**Solution**: 
1. Check if domain matches patterns in `background.js`
2. Reload the extension from `chrome://extensions/`
3. Refresh the webpage

**Problem**: "Failed to fetch" error
**Solution**: 
1. Ensure Flask server is running at `http://localhost:5000`
2. Check browser console for CORS errors
3. Verify `host_permissions` in `manifest.json`

**Problem**: Text-to-speech not working
**Solution**: 
1. Check Flask server logs for TTS errors
2. Ensure edge-tts is installed: `pip install edge-tts`
3. Try different voice fallbacks

### Desktop App Issues

**Problem**: App won't start
**Solution**: 
```bash
pip install --upgrade flet
```

**Problem**: "Thinking..." indicator never disappears
**Solution**: 
1. Check Flask server is running
2. Verify API keys in `.env`
3. Check terminal for error messages

**Problem**: Voice recording not working
**Solution**: 
1. Grant microphone permissions
2. Install sounddevice: `pip install sounddevice`
3. Check audio input device settings

## 📊 Rate Limits & Quotas

### Gemini API (Free Tier)
- **Limit**: 1,500 requests per day
- **Reset**: Midnight UTC
- **Exceeded**: Returns error message

### Firecrawl API (Free Tier)
- **Limit**: 500 credits per month
- **Usage**: 1 credit = 1 page scraped
- **Extension**: Uses 3 credits per summary (crawls 3 pages)

### SerpAPI (Free Tier)
- **Limit**: 100 searches per month
- **Usage**: 1 search per question
- **Exceeded**: Returns "no sources found" message

### MySQL Database
- **No limits** (local database)
- **Storage**: Depends on disk space
- **Performance**: Indexed for fast queries

### ChromaDB
- **No limits** (local vector database)
- **Storage**: Depends on disk space
- **Performance**: Optimized for semantic search

## 📁 Project Structure

```
vhack2026-live-translator/
├── app/                          # Desktop application (Flet)
│   ├── components/               # UI components
│   │   ├── controls.py          # Reusable controls
│   │   └── theme.py             # Theme configuration
│   ├── views/                   # Application screens
│   │   ├── login.py             # Login/register screen
│   │   ├── onboarding.py        # First-time setup
│   │   ├── home.py              # Main chat interface
│   │   ├── preferences.py       # Settings (unused)
│   │   └── profile.py           # User profile
│   ├── preloader.py             # Module preloading
│   ├── splash.py                # Splash screen
│   ├── router.py                # Navigation logic
│   └── state.py                 # Application state
├── browser-extension/           # Chrome extension
│   ├── background.js            # Service worker (detection)
│   ├── content.js               # Content script (UI overlay)
│   ├── popup.js                 # Extension popup
│   ├── popup.html               # Popup UI
│   ├── manifest.json            # Extension config
│   └── icons/                   # Extension icons
├── engine/                      # Backend processing
│   ├── database/                # Database handlers
│   │   ├── mysql_handler.py    # MySQL operations
│   │   ├── auth_handler.py     # Authentication
│   │   ├── rag_integration.py  # RAG system
│   │   └── chroma_singleton.py # ChromaDB singleton
│   ├── search/                  # Document processing
│   │   ├── document_summariser_v6_gemini.py  # Core summarization
│   │   ├── summarizer_web.py                 # Flask server
│   │   └── speech_to_text.py                 # Audio processing
│   └── speech/                  # Voice processing
│       ├── main.py              # Voice pipeline
│       ├── government_mapping.py # Gov website search
│       ├── response_gen.py      # AI response generation
│       ├── text_to_speech.py    # TTS
│       ├── web_scraping.py      # Content extraction
│       ├── embedding.py         # Embeddings
│       └── chroma_config.py     # ChromaDB config
├── chroma_db/                   # Vector database storage
├── user_prefs/                  # User preferences (JSON)
├── uploads/                     # Temporary file uploads
├── main.py                      # Desktop app entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
├── DATABASE_SETUP.md            # Database setup guide
├── DATABASE_MESSAGE_STORAGE.md  # Message storage docs
├── FLET_DATABASE_INTEGRATION.md # Flet integration docs
├── FULL_INTEGRATION_GUIDE.md    # Complete integration guide
└── USER_COUNTRY_LANGUAGE_UPDATE.md # Personalization docs
```

## 🛠️ Technologies Used

### Frontend
- **Flet 0.19.0** - Desktop UI framework (Python)
- **Vanilla JavaScript** - Browser extension

### Backend
- **Flask** - Web server and API
- **Docling** - Document processing
- **BeautifulSoup4** - HTML parsing
- **Firecrawl** - Enhanced web scraping

### AI/ML
- **Google Gemini 2.0 Flash** - Primary LLM
- **SentenceTransformers** - Text embeddings (all-MiniLM-L6-v2)
- **Whisper** - Speech recognition
- **edge-tts** - Text-to-speech (11 languages)

### Storage
- **MySQL 8.0** - Relational database (users, conversations, messages)
- **ChromaDB** - Vector database (embeddings, semantic search)
- **JSON** - User preferences (local files)

### Other
- **bcrypt** - Password hashing
- **SerpAPI** - Government website search
- **pygame** - Audio playback with pause/resume

## 🤝 Contributing

This project was built for vHack 2026. Contributions are welcome!

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Python: Follow PEP 8
- JavaScript: Use ES6+ features
- Comments: Explain complex logic

## 📄 License

[Add your license here]

## 🙏 Credits

Built with ❤️ for ASEAN citizens to better understand their government information.

### Team
[Add your team members here]

### Special Thanks
- Google Gemini for AI capabilities
- Firecrawl for web scraping
- Hugging Face for embedding models
- SerpAPI for government website search

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the documentation files in the project
3. Open an issue on GitHub
4. Contact the development team

## 🔐 Security Notes

- Passwords are hashed using bcrypt (never stored in plain text)
- API keys should never be committed to version control
- Database credentials should be kept secure
- User data is stored locally (not sent to external servers except AI APIs)

## 🚀 Future Enhancements

- [ ] Multi-user support with role-based access
- [ ] Export conversation history
- [ ] Mobile app (iOS/Android)
- [ ] Offline mode with cached responses
- [ ] Advanced analytics dashboard
- [ ] Integration with more government portals
- [ ] Support for more languages
- [ ] Voice commands for navigation

---

**Version**: 1.0.0  
**Last Updated**: April 2026  
**Status**: Production Ready
