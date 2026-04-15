"""
Document & Website Summarizer - API Backend
Integrated with MySQL + ChromaDB for user management and RAG
API-only backend for browser extension and Flet desktop app
"""

import sys
import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pathlib import Path
import io

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from engine.search
from engine.search.document_summariser_v6_gemini import DocumentSummarizer
from engine.search.speech_to_text import transcribe_audio

# Database imports
try:
    from engine.database.auth_handler import AuthHandler
    from engine.database.rag_integration import RAGIntegration
    DB_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Database imports not available: {e}")
    DB_IMPORTS_AVAILABLE = False
    AuthHandler = None
    RAGIntegration = None

# TTS imports
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("⚠️  gTTS not available - text-to-speech will be disabled")

# Windows consoles are often cp1252, which crashes on emoji output from dependencies.
# Make stdout/stderr Unicode-safe by replacing unencodable characters.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database handlers
if DB_IMPORTS_AVAILABLE:
    try:
        auth_handler = AuthHandler()
        rag_integration = RAGIntegration()
        print("✅ Database handlers initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("   App will run without database features")
        auth_handler = None
        rag_integration = None
else:
    print("⚠️  Database modules not imported - running without database features")
    auth_handler = None
    rag_integration = None

# ── ffmpeg PATH fix ───────────────────────────────────────────────────────────
# winget installs ffmpeg but the new PATH entry only takes effect after a shell
# restart.  We probe known locations and inject the bin dir into os.environ so
# pydub, subprocess, and the transformers pipeline all find it immediately.
def _ensure_ffmpeg_on_path():
    import shutil
    if shutil.which("ffmpeg"):
        return  # already on PATH

    candidates = [
        # winget / Gyan package (Windows)
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
        ),
        # chocolatey
        r"C:\ProgramData\chocolatey\bin",
        # manual install
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
    ]
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "ffmpeg.exe")):
            os.environ["PATH"] = candidate + os.pathsep + os.environ.get("PATH", "")
            print(f"✅ ffmpeg found and added to PATH: {candidate}")
            return

    print("⚠️  ffmpeg not found — audio conversion may fail")

_ensure_ffmpeg_on_path()

# ═══════════════════════════════════════════════════════════════════════════
# API-ONLY BACKEND - No Web Interface
# All endpoints are for browser extension and Flet desktop app
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/register', methods=['POST'])
def register():
    """Register new user"""
    if not auth_handler:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        data = request.get_json()
        result = auth_handler.register_user(
            name=data.get('name'),
            email=data.get('email'),
            password=data.get('password'),
            country=data.get('country'),
            language=data.get('language', 'en')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    if not auth_handler:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        data = request.get_json()
        result = auth_handler.login_user(
            email=data.get('email'),
            password=data.get('password')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    """Get user profile"""
    if not auth_handler:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        profile = auth_handler.get_user_profile(user_id)
        if profile:
            return jsonify({'success': True, 'profile': profile})
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profile/<user_id>', methods=['PUT'])
def update_profile(user_id):
    """Update user profile"""
    if not auth_handler:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        data = request.get_json()
        result = auth_handler.update_user_profile(
            user_id=user_id,
            name=data.get('name'),
            country=data.get('country'),
            language=data.get('language')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════
# CHAT & RAG ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create new conversation"""
    if not rag_integration:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        data = request.get_json()
        conversation_id = rag_integration.create_conversation(
            user_id=data.get('user_id'),
            title=data.get('title', 'New Conversation')
        )
        if conversation_id:
            return jsonify({'success': True, 'conversation_id': conversation_id})
        return jsonify({'success': False, 'error': 'Failed to create conversation'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/conversations/<user_id>', methods=['GET'])
def get_conversations(user_id):
    """Get all user conversations"""
    if not rag_integration:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        conversations = rag_integration.mysql.get_user_conversations(user_id)
        return jsonify({'success': True, 'conversations': conversations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages/<conversation_id>', methods=['GET'])
def get_messages(conversation_id):
    """Get conversation messages"""
    if not rag_integration:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    
    try:
        messages = rag_integration.get_conversation_history(conversation_id)
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint following RAG architecture:
    1. Query → Embedding
    2. Embedding → Vector Database (ChromaDB)
    3. Vector Database → Relevant Data
    4. Relevant Data + Query → LLM
    5. LLM → Response
    
    Only fetch fresh data (A→B→C→D) if Vector Database has no relevant data
    """
    if not rag_integration:
        # Fallback to old behavior if database not available
        return qa_website()
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        conversation_id = data.get('conversation_id')
        message = data.get('message') or data.get('question')
        url = data.get('url')
        target_lang = data.get('targetLang', 'en')
        
        if not message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400
        
        # Create conversation if new
        if not conversation_id and user_id:
            conversation_id = rag_integration.create_conversation(user_id, "New Chat")
        
        # Save user message with embedding
        if conversation_id:
            rag_integration.save_user_message(conversation_id, message)
            
            # Update conversation title if this is the first message
            try:
                messages = rag_integration.get_conversation_history(conversation_id)
                if messages and len(messages) == 1:  # Only user message exists
                    # Generate title from first message (max 50 chars)
                    title = message[:50] + "..." if len(message) > 50 else message
                    rag_integration.update_conversation_title(conversation_id, title)
            except Exception as e:
                print(f"⚠️ Failed to update conversation title: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # RAG RETRIEVAL PHASE
        # Step 1: Query → Embedding
        # Step 2: Embedding → Vector Database
        # Step 3: Vector Database → Relevant Data
        # ═══════════════════════════════════════════════════════════════════
        
        # Get user's country for filtering ChromaDB results
        user_country = None
        if user_id and auth_handler:
            try:
                user_profile = auth_handler.get_user_profile(user_id)
                if user_profile:
                    user_country = user_profile.get('country')
                    print(f"👤 User country: {user_country}")
            except Exception as e:
                print(f"⚠️ Failed to get user country: {e}")
        
        print("\n🔍 [RAG Step 1-3] Querying Vector Database (ChromaDB)...")
        relevant_chunks = []
        cached_sources = []
        
        try:
            from engine.speech.embedding import query_from_chroma
            from engine.speech.response_gen import generate_final_response, get_dialect_from_language
            
            # Query ChromaDB with embedded question
            # min_similarity=0.4 means we need at least 40% similarity
            # Filter by user's country to prevent wrong-country answers
            relevant_chunks, cached_sources = query_from_chroma(message, top_k=5, min_similarity=0.4, country=user_country)
            
            if relevant_chunks and len(relevant_chunks) >= 3:
                print(f"✅ Found {len(relevant_chunks)} relevant chunks in Vector Database")
                if cached_sources:
                    print(f"   📎 From {len(cached_sources)} source URLs")
            else:
                if relevant_chunks:
                    print(f"ℹ️ Found {len(relevant_chunks)} chunks but below threshold (need 3+)")
                else:
                    print("ℹ️ No relevant data found in Vector Database")
                
        except Exception as e:
            print(f"⚠️ Error querying Vector Database: {e}")
            relevant_chunks = []
            cached_sources = []
        
        # ═══════════════════════════════════════════════════════════════════
        # GENERATION PHASE (if we have data in Vector Database)
        # Step 4: Relevant Data + Query → LLM
        # Step 5: LLM → Response
        # ═══════════════════════════════════════════════════════════════════
        
        if relevant_chunks and len(relevant_chunks) >= 3:
            print(f"\n🤖 [RAG Step 4-5] Generating response from Vector Database...")
            
            # Map language code to full language name
            lang_map = {
                'en': 'English', 'ms': 'Bahasa Melayu', 'id': 'Bahasa Indonesia',
                'th': 'Thai', 'vi': 'Vietnamese', 'tl': 'Filipino/Tagalog',
                'my': 'Burmese', 'km': 'Khmer', 'lo': 'Lao', 'ta': 'Tamil',
                'zh-cn': 'Chinese (Simplified)'
            }
            language_name = lang_map.get(target_lang, 'English')
            dialect = get_dialect_from_language(language_name)
            
            # Generate answer from Vector Database data
            cached_answer = generate_final_response(message, relevant_chunks, dialect)
            print("✅ Response generated from cached Vector Database data")
            
            result = {
                'answer': cached_answer,
                'summary': cached_answer,
                'sources': cached_sources if cached_sources else [],
                'cached': True
            }
            
            # Save bot response
            if conversation_id:
                rag_integration.save_bot_message(conversation_id, cached_answer)
            
            result['conversation_id'] = conversation_id
            return jsonify({'success': True, 'data': result})
        
        # ═══════════════════════════════════════════════════════════════════
        # DATA PREPARATION PHASE (Only if Vector Database is empty)
        # Step A: Raw Data Sources
        # Step B: Information Extraction
        # Step C: Chunking
        # Step D: Embedding → Store in Vector Database
        # ═══════════════════════════════════════════════════════════════════
        
        print(f"\n📡 [Data Preparation] Vector Database has insufficient data, fetching fresh sources...")
        summarizer = DocumentSummarizer(target_lang=target_lang)
        
        if url:
            # Step A-B: Extract from website
            print(f"[Step A-B] Extracting information from website...")
            result = summarizer.rag_qa_website(url, message)
            
            # Step C-D: Store in Vector Database
            if result and result.get('sources'):
                try:
                    from engine.speech.embedding import ingest_to_chroma
                    from datetime import datetime
                    doc_id = f"browser_web_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    # Store with user's country if available
                    ingest_to_chroma(doc_id, result['sources'], country=user_country)
                    country_info = f" (country: {user_country})" if user_country else ""
                    print(f"✅ [Step D] Stored website content in Vector Database{country_info}")
                except Exception as e:
                    print(f"⚠️ Failed to store in Vector Database: {e}")
        else:
            # General Q&A - not yet implemented
            result = {'summary': 'Response generation not yet implemented for general chat'}
        
        # Save bot response
        if conversation_id and result:
            bot_message = result.get('summary', result.get('answer', ''))
            rag_integration.save_bot_message(conversation_id, bot_message)
        
        # Add context info to response
        if result:
            result['conversation_id'] = conversation_id
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (Document & Website Summarization)
# ═══════════════════════════════════════════════════════════════════════════
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (Document & Website Summarization)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/summarize/document', methods=['POST'])
def summarize_document():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        target_lang = request.form.get('target_lang', 'en')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process
        summarizer = DocumentSummarizer(target_lang=target_lang)
        result = summarizer.process_document(filepath)
        
        # Clean up
        os.remove(filepath)
        
        if result:
            return jsonify({
                'success': True,
                'summary': result['summary'],
                'word_count': result['word_count'],
                'summary_word_count': result['summary_word_count'],
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to process document'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/summarize/website', methods=['POST'])
def summarize_website():
    try:
        url = request.form.get('url')
        target_lang = request.form.get('target_lang', 'en')
        crawl_depth = int(request.form.get('crawl_depth', 0))
        max_sublinks = int(request.form.get('max_sublinks', 3))
        
        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        # Process
        summarizer = DocumentSummarizer(target_lang=target_lang)
        result = summarizer.process_website(url, crawl_depth=crawl_depth, max_sublinks=max_sublinks)
        
        if result:
            return jsonify({
                'success': True,
                'summary': result['summary'],
                'word_count': result['word_count'],
                'summary_word_count': result['summary_word_count'],
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to process website'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/qa/website', methods=['POST'])
def qa_website():
    try:
        url = request.form.get('url')
        question = request.form.get('question', '').strip()
        target_lang = request.form.get('target_lang', 'en')

        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})

        summarizer = DocumentSummarizer(target_lang=target_lang)
        result = summarizer.rag_qa_website(url, question)

        if result:
            return jsonify({
                'success': True,
                'summary': result['summary'],
                'word_count': result['word_count'],
                'summary_word_count': result['summary_word_count'],
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to answer question for website'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/qa/document', methods=['POST'])
def qa_document():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        question = request.form.get('question', '').strip()
        target_lang = request.form.get('target_lang', 'en')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with RAG Q&A
        summarizer = DocumentSummarizer(target_lang=target_lang)
        result = summarizer.rag_qa_document(filepath, question)
        
        # Clean up
        os.remove(filepath)
        
        if result:
            return jsonify({
                'success': True,
                'summary': result['summary'],
                'word_count': result['word_count'],
                'summary_word_count': result['summary_word_count'],
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to answer question for document'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/speech-to-text', methods=['POST'])
def handle_speech():
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio'})

    audio_file = request.files['audio']
    original_filename = audio_file.filename or 'recording'
    ext = os.path.splitext(original_filename)[1].lower() or '.webm'
    raw_path = os.path.join(app.config['UPLOAD_FOLDER'], f"live_speech_raw{ext}")
    wav_path = os.path.join(app.config['UPLOAD_FOLDER'], "live_speech.wav")
    audio_file.save(raw_path)

    try:
        text = _transcribe_raw_audio(raw_path, wav_path)
        return jsonify({'success': True, 'text': text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        for p in (raw_path, wav_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


def _transcribe_raw_audio(raw_path: str, wav_path: str) -> str:
    """
    Convert raw browser audio (webm/ogg/mp4) to PCM WAV then transcribe.
    Strategy (in order):
      1. pydub + ffmpeg  → clean 16kHz mono WAV  → soundfile → Whisper
      2. ffmpeg directly via subprocess           → clean WAV → soundfile → Whisper
      3. Pass raw file directly to Whisper pipeline (it calls ffmpeg internally)
    """
    import numpy as np

    # ── Strategy 1: pydub ────────────────────────────────────────────────────
    try:
        from pydub import AudioSegment
        import shutil as _shutil
        # Explicitly point pydub at the ffmpeg binary in case PATH isn't updated yet
        _ffmpeg = _shutil.which("ffmpeg")
        if _ffmpeg:
            AudioSegment.converter = _ffmpeg
            AudioSegment.ffmpeg = _ffmpeg
            AudioSegment.ffprobe = _ffmpeg.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
        seg = AudioSegment.from_file(raw_path)
        seg = seg.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        seg.export(wav_path, format="wav")
        print("✅ pydub conversion succeeded")
        return _run_whisper_on_wav(wav_path)
    except Exception as e1:
        print(f"⚠️  pydub failed: {e1}")

    # ── Strategy 2: ffmpeg subprocess ────────────────────────────────────────
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                wav_path
            ],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            print("✅ ffmpeg subprocess conversion succeeded")
            return _run_whisper_on_wav(wav_path)
        else:
            print(f"⚠️  ffmpeg subprocess failed: {result.stderr.decode(errors='replace')}")
    except FileNotFoundError:
        print("⚠️  ffmpeg not found on PATH")
    except Exception as e2:
        print(f"⚠️  ffmpeg subprocess error: {e2}")

    # ── Strategy 3: feed raw file directly to Whisper pipeline ───────────────
    # transformers' pipeline accepts a file path and calls ffmpeg internally
    print("⚠️  Falling back to direct Whisper pipeline on raw file")
    from speech_to_text import get_asr_pipe
    asr = get_asr_pipe()
    res = asr(raw_path, generate_kwargs={"task": "transcribe"}, chunk_length_s=30, stride_length_s=5)
    raw_text = (res.get("text") or "").strip()
    return raw_text


def _run_whisper_on_wav(wav_path: str) -> str:
    """Load a PCM WAV with soundfile and run Whisper on it."""
    import numpy as np
    import soundfile as sf
    from speech_to_text import get_asr_pipe, SAMPLING_RATE, _resample_linear

    samples, sr = sf.read(wav_path, dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = samples.astype(np.float32, copy=False)
    if sr != SAMPLING_RATE:
        samples = _resample_linear(samples, sr, SAMPLING_RATE)

    pad = int(0.5 * SAMPLING_RATE)
    samples = np.concatenate([np.zeros(pad, dtype=np.float32), samples, np.zeros(pad, dtype=np.float32)])

    asr = get_asr_pipe()
    res = asr(samples, generate_kwargs={"task": "transcribe"}, chunk_length_s=30, stride_length_s=5)
    return (res.get("text") or "").strip()

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Server-side TTS using edge-tts (Microsoft Edge Text-to-Speech).
    Supports all ASEAN languages with neural voices.
    Returns audio/mpeg.
    Accepts JSON: { "text": "...", "lang": "en" }
    """
    try:
        import asyncio
        import edge_tts
        import tempfile
        import os
        
        data = request.get_json(force=True)
        text = (data.get('text') or '').strip()
        lang = (data.get('lang') or 'en').strip()

        if not text:
            print("❌ No text provided")
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        print(f"🔊 TTS request: lang={lang}, text_length={len(text)}")
        print(f"   First 100 chars: {text[:100]}")

        # Map language codes to full language names
        lang_code_to_name = {
            'en': 'English',
            'ms': 'Bahasa Melayu',
            'id': 'Bahasa Indonesia',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'tl': 'Filipino/Tagalog',
            'my': 'Burmese',
            'km': 'Khmer',
            'lo': 'Lao',
            'zh-cn': 'Chinese (Simplified)',
            'ta': 'Tamil'
        }
        
        language_name = lang_code_to_name.get(lang, 'English')
        print(f"   Language: {language_name}")
        
        # Get voices for the language
        from engine.speech.language_voice_mapping import get_voices_for_language
        voices = get_voices_for_language(language_name)
        print(f"   Trying voices: {voices}")
        
        # Generate audio using edge-tts
        async def generate_audio():
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_path = temp_file.name
            temp_file.close()
            
            last_error = None
            for voice in voices:
                try:
                    print(f"   Attempting voice: {voice}")
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(temp_path)
                    print(f"✅ TTS generated with voice: {voice}")
                    return temp_path  # Success
                except Exception as e:
                    last_error = e
                    print(f"⚠️ Voice {voice} failed: {e}")
                    continue
            
            # If all voices failed, raise the last error
            if last_error:
                raise last_error
            
            raise Exception("No voices available")
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_path = loop.run_until_complete(generate_audio())
        finally:
            loop.close()
        
        # Read audio file
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Clean up temp file
        try:
            os.unlink(audio_path)
        except:
            pass
        
        print(f"✅ TTS generated {len(audio_bytes)} bytes")
        return Response(audio_bytes, mimetype='audio/mpeg')

    except Exception as e:
        print(f"❌ TTS error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Bridge API Backend - Document Summarizer")
    print("API-only server for browser extension and Flet app")
    print("Docling + Google Gemini 3.0 Flash + MySQL + ChromaDB")
    print("=" * 60)
    print(f"\nPython executable: {sys.executable}")
    print(f"gTTS available: {GTTS_AVAILABLE}")
    print(f"Database available: {DB_IMPORTS_AVAILABLE}")
    print("\nAPI Server starting on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  • /api/register, /api/login - Authentication")
    print("  • /api/chat - RAG-powered chat")
    print("  • /summarize/document, /summarize/website - Summarization")
    print("  • /qa/document, /qa/website - Q&A")
    print("  • /speech-to-text, /tts - Speech services")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
