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
load_dotenv()

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
    Main chat endpoint with RAG integration
    Handles both website Q&A and general chat
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
            title = message[:50] + "..." if len(message) > 50 else message
            conversation_id = rag_integration.create_conversation(user_id, title)
        
        # Save user message with embedding
        if conversation_id:
            rag_integration.save_user_message(conversation_id, message)
        
        # Get context using RAG
        context = None
        if conversation_id:
            context = rag_integration.get_context_for_response(
                query=message,
                conversation_id=conversation_id,
                include_history=True
            )
        
        # Generate response using existing summarizer
        summarizer = DocumentSummarizer(target_lang=target_lang)
        
        if url:
            # Website Q&A with RAG context
            result = summarizer.rag_qa_website(url, message)
        else:
            # General Q&A (could integrate with other sources)
            result = {'summary': 'Response generation not yet implemented for general chat'}
        
        # Save bot response
        if conversation_id and result:
            bot_message = result.get('summary', result.get('answer', ''))
            rag_integration.save_bot_message(conversation_id, bot_message)
        
        # Add context info to response
        if result and context:
            result['context_used'] = len(context.get('relevant_messages', []))
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
    Server-side TTS using gTTS (Google Text-to-Speech).
    Supports all ASEAN languages. Returns audio/mpeg.
    Accepts JSON: { "text": "...", "lang": "ta" }
    """
    if not GTTS_AVAILABLE:
        print("❌ gTTS not available")
        return jsonify({'success': False, 'error': 'gTTS module not installed'}), 500

    try:
        data = request.get_json(force=True)
        text = (data.get('text') or '').strip()
        lang = (data.get('lang') or 'en').strip()

        if not text:
            print("❌ No text provided")
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        print(f"🔊 TTS request: lang={lang}, text_length={len(text)}")
        print(f"   First 100 chars: {text[:100]}")

        # gTTS lang code map — handles variants
        # Supported: en, ms, id, vi, th, zh-CN, zh-TW, ta, tl, my, km
        # NOT supported by gTTS: lo (Lao) - will fall back to English
        lang_map = {
            'zh-cn': 'zh-CN',
            'zh-tw': 'zh-TW',
            'tl':    'tl',   # Filipino/Tagalog
            'ta':    'ta',   # Tamil
            'my':    'my',   # Burmese/Myanmar
            'km':    'km',   # Khmer
            'lo':    'en',   # Lao → fallback to English (not supported by gTTS)
            'vi':    'vi',   # Vietnamese
            'th':    'th',   # Thai
            'id':    'id',   # Indonesian
            'ms':    'ms',   # Malay
            'en':    'en',   # English
        }
        gtts_lang = lang_map.get(lang, 'en')  # Default to English if unknown
        
        if lang == 'lo':
            print(f"   ⚠️  Lao (lo) not supported by gTTS, falling back to English")
        
        print(f"   Using gTTS lang code: {gtts_lang}")

        print("   Creating gTTS object...")
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        
        print("   Generating audio...")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.read()

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
    print("Docling + Google Gemini 2.0 Flash + MySQL + ChromaDB")
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
