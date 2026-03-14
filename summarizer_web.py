"""
Document & Website Summarizer - Web Interface
"""

from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
from document_summariser_v6_gemini import DocumentSummarizer
from pathlib import Path

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    </style>
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
                
                <button type="submit" class="btn" id="docBtn">
                    📝 Summarize Document
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
                    <label for="question">Ask a question about this website (RAG)</label>
                    <input type="text" name="question" id="question" placeholder="e.g. What are the key eligibility requirements?">
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
            • Automatic language detection and complex table recognition<br>
            • Supports PDF and images (PNG, JPG, JPEG, BMP, TIFF)<br>
            • Website summarization extracts main content<br>
            • GPU acceleration for faster processing
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
        
        function showResult(data) {
            document.getElementById('originalWords').textContent = data.word_count;
            document.getElementById('summaryWords').textContent = data.summary_word_count;
            
            const reduction = 100 - (data.summary_word_count / data.word_count * 100);
            document.getElementById('reduction').textContent = reduction.toFixed(1) + '%';
            
            document.getElementById('summaryText').textContent = data.summary;
            document.getElementById('result').classList.add('show');
        }
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

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Bridge Document Summarizer - Web Interface")
    print("Docling + Google Gemini 2.0 Flash")
    print("=" * 60)
    print("\n✅ Server starting...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop the server\n")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
