"""
Document & Website Summarizer - Web Interface
"""

import sys
from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
from document_summariser_v6_gemini import DocumentSummarizer
from pathlib import Path
from speech_to_text import transcribe_audio

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
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bridge - Document Summarizer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .icon {
            font-size: 60px;
            margin-bottom: 20px;
        }
        
        h1 {
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .tab {
            padding: 15px 30px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
            font-weight: 600;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input[type="text"], input[type="url"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
        }
        
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        
        .file-input-label {
            display: block;
            padding: 15px;
            background: #f8f9fa;
            border: 2px dashed #ddd;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .file-input-label:hover {
            background: #e9ecef;
            border-color: #667eea;
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .result {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .result.show {
            display: block;
        }
        
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat {
            flex: 1;
            padding: 15px;
            background: white;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        
        .summary-box {
            background: white;
            padding: 20px;
            border-radius: 10px;
            line-height: 1.8;
            color: #333;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .note {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            font-size: 13px;
            color: #856404;
        }
        .mic-btn {
            padding: 0 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px; /* Matches the icon sizing of your other buttons */
        }

        .mic-btn:hover {
            box-shadow: 0 5px 15px rgba(118, 75, 162, 0.3);
        }

        .mic-btn:active {
            transform: translateY(0);
        }

        /* Optional: Red Pulse when active */
        .mic-btn.recording {
            background: linear-gradient(135deg, #ff4b2b 0%, #ff416c 100%);
            animation: mic-pulse 1.5s infinite;
        }

        @keyframes mic-pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 75, 43, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(255, 75, 43, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 75, 43, 0); }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">📄</div>
            <h1>Bridge Document Summarizer</h1>
            <p class="subtitle">ASEAN Multilingual Document & Website Summarizer with Docling + Google Gemini (Advanced AI Processing)</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('document')">📄 Document</button>
            <button class="tab" onclick="switchTab('website')">🌐 Website</button>
        </div>
        
        <!-- Document Tab -->
        <div id="document-tab" class="tab-content active">
            <form id="documentForm" onsubmit="summarizeDocument(event)">
                <div class="form-group">
                    <label>Upload Document</label>
                    <div class="file-input-wrapper">
                        <input type="file" name="file" id="file" accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff" required>
                        <label for="file" class="file-input-label">
                            <span id="file-label-text">📎 Click to select file (PDF or Images)</span>
                        </label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="doc_lang">Target Language (ASEAN)</label>
                    <select name="target_lang" id="doc_lang">
                        <option value="en">English</option>
                        <option value="ms">Malay</option>
                        <option value="id">Indonesian</option>
                        <option value="vi">Vietnamese</option>
                        <option value="th">Thai</option>
                        <option value="zh-cn">Chinese Simplified</option>
                        <option value="zh-tw">Chinese Traditional</option>
                        <option value="ta">Tamil</option>
                        <option value="tl">Tagalog/Filipino</option>
                        <option value="my">Burmese/Myanmar</option>
                        <option value="km">Khmer</option>
                        <option value="lo">Lao</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="doc_question" style="display: block; margin-bottom: 8px;">Ask a question about this document (RAG)</label>
                    <div style="display: flex; gap: 10px; align-items: stretch;">
                        <input type="text" name="question" id="doc_question"
                            placeholder="e.g. What are the main findings?"
                            style="flex-grow: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px;">
                        
                        <button type="button" class="mic-btn" id="doc_mic_btn"
                                style="padding: 0 40px; cursor: pointer; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; transition: transform 0.2s;">
                            <i class="fas fa-microphone"></i>
                        </button>
                    </div>
                </div>
                
                <button type="submit" class="btn" id="docBtn">
                    📝 Summarize Document
                </button>
                <button type="button" class="btn" style="margin-top: 10px;" id="docQaBtn" onclick="askDocumentQuestion()">
                    ❓ Ask Question about Document
                </button>
            </form>
        </div>
        
        <!-- Website Tab -->
        <div id="website-tab" class="tab-content">
            <form id="websiteForm" onsubmit="summarizeWebsite(event)">
                <div class="form-group">
                    <label for="url">Website URL</label>
                    <input type="url" name="url" id="url" placeholder="https://example.gov.my" required>
                    <small style="color: #666; display: block; margin-top: 5px;">
                        ℹ️ Will automatically crawl and summarize 3 additional sublinks
                    </small>
                </div>
                
                <div class="form-group">
                    <label for="web_lang">Target Language (ASEAN)</label>
                    <select name="target_lang" id="web_lang">
                        <option value="en">English</option>
                        <option value="ms">Malay</option>
                        <option value="id">Indonesian</option>
                        <option value="vi">Vietnamese</option>
                        <option value="th">Thai</option>
                        <option value="zh-cn">Chinese Simplified</option>
                        <option value="zh-tw">Chinese Traditional</option>
                        <option value="ta">Tamil</option>
                        <option value="tl">Tagalog/Filipino</option>
                        <option value="my">Burmese/Myanmar</option>
                        <option value="km">Khmer</option>
                        <option value="lo">Lao</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="question" style="display: block; margin-bottom: 8px;">Ask a question about this website (RAG)</label>
                    <div style="display: flex; gap: 10px; align-items: stretch;">
                        <input type="text" name="question" id="question"
                            placeholder="e.g. What are the main findings?"
                            style="flex-grow: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px;">
                        
                        <button type="button" class="mic-btn" id="web_mic_btn"
                                style="padding: 0 40px; cursor: pointer; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; transition: transform 0.2s;">
                            <i class="fas fa-microphone"></i>
                        </button>
                    </div>
                </div>
                
                <button type="submit" class="btn" id="webBtn">
                    📝 Summarize Website
                </button>
                <button type="button" class="btn" style="margin-top: 10px;" id="qaBtn" onclick="askWebsiteQuestion()">
                    ❓ Ask Question about Website
                </button>
            </form>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 10px; color: #666;">Processing... This may take a minute.</p>
        </div>
        
        <div class="result" id="result">
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="originalWords">0</div>
                    <div class="stat-label">Original Words</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="summaryWords">0</div>
                    <div class="stat-label">Summary Words</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="reduction">0%</div>
                    <div class="stat-label">Reduction</div>
                </div>
            </div>
            
            <h3 style="margin-bottom: 15px;">Summary:</h3>
            <div class="summary-box" id="summaryText"></div>
        </div>
        
        <div class="note">
            <strong>📝 Note:</strong><br>
            • Maximum file size: 50MB<br>
            • Docling + Google Gemini 2.0 Flash - Advanced AI summarization<br>
            • RAG Q&A: Ask specific questions about documents or websites<br>
            • Automatic language detection and complex table recognition<br>
            • Supports PDF and images (PNG, JPG, JPEG, BMP, TIFF)<br>
            • Website summarization extracts main content and crawls 3 sublinks<br>
            • Embeddings cached in ChromaDB for fast repeated queries
        </div>
    </div>
    
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tab + '-tab').classList.add('active');
            document.getElementById('result').classList.remove('show');
        }
        
        function toggleCrawlOptions() {
            // No longer needed - crawling is always enabled
        }
        
        document.getElementById('file').addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            if (fileName) {
                document.getElementById('file-label-text').textContent = '📎 ' + fileName;
            }
        });
        
        async function summarizeDocument(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const btn = document.getElementById('docBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            btn.disabled = true;
            loading.style.display = 'block';
            result.classList.remove('show');
            
            try {
                const response = await fetch('/summarize/document', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showResult(data);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        }
        
        async function summarizeWebsite(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            
            // Automatically enable crawling with 3 sublinks
            formData.append('crawl_depth', '1');
            formData.append('max_sublinks', '3');
            
            const btn = document.getElementById('webBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            btn.disabled = true;
            loading.style.display = 'block';
            result.classList.remove('show');
            
            try {
                const response = await fetch('/summarize/website', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showResult(data);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        }
        
        async function askWebsiteQuestion() {
            const urlInput = document.getElementById('url');
            const questionInput = document.getElementById('question');
            const langSelect = document.getElementById('web_lang');
            const btn = document.getElementById('qaBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');

            const url = urlInput.value.trim();
            const question = questionInput.value.trim();
            const targetLang = langSelect.value || 'en';

            if (!url) {
                alert('Please enter a website URL.');
                return;
            }
            if (!question) {
                alert('Please enter a question about the website.');
                return;
            }

            const formData = new FormData();
            formData.append('url', url);
            formData.append('question', question);
            formData.append('target_lang', targetLang);

            btn.disabled = true;
            loading.style.display = 'block';
            result.classList.remove('show');

            try {
                const response = await fetch('/qa/website', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    showResult(data);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        }

        async function askDocumentQuestion() {
            const fileInput = document.getElementById('file');
            const questionInput = document.getElementById('doc_question');
            const langSelect = document.getElementById('doc_lang');
            const btn = document.getElementById('docQaBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');

            const file = fileInput.files[0];
            const question = questionInput.value.trim();
            const targetLang = langSelect.value || 'en';

            if (!file) {
                alert('Please select a document file.');
                return;
            }
            if (!question) {
                alert('Please enter a question about the document.');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('question', question);
            formData.append('target_lang', targetLang);

            btn.disabled = true;
            loading.style.display = 'block';
            result.classList.remove('show');

            try {
                const response = await fetch('/qa/document', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    showResult(data);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        }
        
        function showResult(data) {
            document.getElementById('originalWords').textContent = data.word_count;
            document.getElementById('summaryWords').textContent = data.summary_word_count;
            
            const reduction = 100 - (data.summary_word_count / data.word_count * 100);
            document.getElementById('reduction').textContent = reduction.toFixed(1) + '%';
            
            document.getElementById('summaryText').textContent = data.summary;
            document.getElementById('result').classList.add('show');
        }

        let mediaRecorder;
        let audioChunks = [];

        let activeMicBtn = null;
        let activeQuestionInput = null;
        let audioContext;
        let mediaStream;
        let sourceNode;
        let processorNode;
        let recordedBuffers = [];
        let recordingSampleRate = 48000;

        async function startRecording(targetBtn, targetInput) {
            try {
                activeMicBtn = targetBtn || null;
                activeQuestionInput = targetInput || null;

                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                recordingSampleRate = audioContext.sampleRate;
                recordedBuffers = [];

                sourceNode = audioContext.createMediaStreamSource(mediaStream);
                // ScriptProcessor is deprecated but widely supported and simplest here
                processorNode = audioContext.createScriptProcessor(4096, 1, 1);

                processorNode.onaudioprocess = (e) => {
                    const input = e.inputBuffer.getChannelData(0);
                    recordedBuffers.push(new Float32Array(input));
                };

                sourceNode.connect(processorNode);
                processorNode.connect(audioContext.destination);

                if (activeMicBtn) activeMicBtn.classList.add('recording');
                console.log("Recording started...");
            } catch (err) {
                console.error("Mic access denied:", err);
                alert("Mic access denied: " + (err?.message || err));
            }
        }

        function _flattenFloat32(buffers) {
            let total = 0;
            for (const b of buffers) total += b.length;
            const out = new Float32Array(total);
            let offset = 0;
            for (const b of buffers) {
                out.set(b, offset);
                offset += b.length;
            }
            return out;
        }

        function _resampleLinearFloat32(input, srcRate, dstRate) {
            if (srcRate === dstRate) return input;
            const ratio = dstRate / srcRate;
            const newLength = Math.max(1, Math.round(input.length * ratio));
            const output = new Float32Array(newLength);
            const scale = (input.length - 1) / (newLength - 1);
            for (let i = 0; i < newLength; i++) {
                const idx = i * scale;
                const idx0 = Math.floor(idx);
                const idx1 = Math.min(idx0 + 1, input.length - 1);
                const frac = idx - idx0;
                output[i] = input[idx0] * (1 - frac) + input[idx1] * frac;
            }
            return output;
        }

        function _encodeWavMono16(samplesFloat32, sampleRate) {
            const buffer = new ArrayBuffer(44 + samplesFloat32.length * 2);
            const view = new DataView(buffer);

            function writeString(offset, str) {
                for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
            }

            // RIFF header
            writeString(0, "RIFF");
            view.setUint32(4, 36 + samplesFloat32.length * 2, true);
            writeString(8, "WAVE");

            // fmt chunk
            writeString(12, "fmt ");
            view.setUint32(16, 16, true); // PCM
            view.setUint16(20, 1, true); // format = PCM
            view.setUint16(22, 1, true); // channels = 1
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true); // byte rate
            view.setUint16(32, 2, true); // block align
            view.setUint16(34, 16, true); // bits per sample

            // data chunk
            writeString(36, "data");
            view.setUint32(40, samplesFloat32.length * 2, true);

            let offset = 44;
            for (let i = 0; i < samplesFloat32.length; i++, offset += 2) {
                let s = Math.max(-1, Math.min(1, samplesFloat32[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
            }
            return new Blob([view], { type: "audio/wav" });
        }

        async function _stopAndUpload() {
            try {
                const flat = _flattenFloat32(recordedBuffers);
                const resampled = _resampleLinearFloat32(flat, recordingSampleRate, 16000);
                const audioBlob = _encodeWavMono16(resampled, 16000);
                const formData = new FormData();
                formData.append('audio', audioBlob, 'temp_audio.wav');

                // Show processing state
                if (activeMicBtn) {
                    activeMicBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    activeMicBtn.disabled = true;
                }

                const response = await fetch('/speech-to-text', { method: 'POST', body: formData });
                const data = await response.json();

                if (!data?.success) {
                    alert('Speech-to-text failed: ' + (data?.error || 'Unknown error'));
                    return;
                }

                function _extractTranscript(payload) {
                    if (payload == null) return '';
                    // Common shapes:
                    // { success: true, text: "..." }
                    // { success: true, text: { text: "..."} }
                    // { success: true, question: "..." } etc.
                    let candidate =
                        payload.text ??
                        payload.question ??
                        payload.transcript ??
                        payload.transcription ??
                        '';

                    if (candidate == null) return '';
                    if (typeof candidate === 'string') return candidate;
                    if (typeof candidate === 'number' || typeof candidate === 'boolean') return String(candidate);

                    if (typeof candidate === 'object') {
                        const nested =
                            candidate.text ??
                            candidate.question ??
                            candidate.transcript ??
                            candidate.transcription ??
                            '';
                        if (typeof nested === 'string') return nested;
                        // Only write actual transcript strings into the input box.
                        return '';
                    }

                    return String(candidate);
                }

                const text = _extractTranscript(data).trim();
                if (text.length > 0) {
                    if (activeQuestionInput) {
                        activeQuestionInput.value = text;
                    }
                    // Some browsers/UI setups only refresh on input events
                    if (activeQuestionInput) {
                        activeQuestionInput.dispatchEvent(new Event('input', { bubbles: true }));
                        activeQuestionInput.focus();
                    }
                } else {
                    alert('No speech detected. Please try again and speak closer to the mic.');
                }
            } catch (err) {
                console.error('Speech-to-text error:', err);
                alert('Speech-to-text error: ' + (err?.message || err));
            } finally {
                // Reset UI
                if (activeMicBtn) {
                    activeMicBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                    activeMicBtn.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
                    activeMicBtn.disabled = false;
                    activeMicBtn.classList.remove('recording');
                }
            }
        }

        function stopRecording() {
            if (!audioContext) return;
            try {
                if (processorNode) processorNode.disconnect();
                if (sourceNode) sourceNode.disconnect();
                if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
                if (audioContext) audioContext.close();
            } catch (e) {
                console.warn("Stop recording cleanup error:", e);
            } finally {
                processorNode = null;
                sourceNode = null;
                mediaStream = null;
                audioContext = null;
            }
            console.log("Recording stopped.");
            _stopAndUpload();
        }

        function bindMicButton(buttonId, inputId) {
            const btn = document.getElementById(buttonId);
            const input = document.getElementById(inputId);
            if (!btn || !input) return;

            // Mouse Events
            btn.addEventListener('mousedown', () => startRecording(btn, input));
            btn.addEventListener('mouseup', stopRecording);

            // Touch Events (For Mobile support)
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault(); // Prevents long-press context menus
                startRecording(btn, input);
            });
            btn.addEventListener('touchend', stopRecording);

            // Accessibility: Stop if mouse leaves the button while holding
            btn.addEventListener('mouseleave', stopRecording);
        }

        bindMicButton('doc_mic_btn', 'doc_question');
        bindMicButton('web_mic_btn', 'question');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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

if __name__ == '__main__':
    print("=" * 60)
    print("Bridge Document Summarizer - Web Interface")
    print("Docling + Google Gemini 2.0 Flash")
    print("=" * 60)
    print("\nServer starting...")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
