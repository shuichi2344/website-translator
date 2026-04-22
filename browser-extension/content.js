// Content script — injects floating button and summary panel on gov websites

let summaryPanel = null;
let isGenerating = false;
let currentUrl = window.location.href;  // Always initialised to current page URL
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// ─── Listen for background script messages ───────────────────────────────────
chrome.runtime.onMessage.addListener((request) => {
  if (request.action === 'showSummaryButton') {
    showFloatingButton(request.url);
  }
});

// ─── Floating "Summarise This Page" button ───────────────────────────────────
function showFloatingButton(url) {
  if (document.getElementById('bridge-fab')) return;

  const fab = document.createElement('div');
  fab.id = 'bridge-fab';
  fab.innerHTML = `
    <div id="bridge-fab-inner">
      <span style="font-size:18px;">🤖</span>
      <span>Bridge Assistant</span>
    </div>
  `;

  const style = document.createElement('style');
  style.textContent = `
    #bridge-fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 2147483647;
    }
    #bridge-fab-inner {
      display: flex;
      align-items: center;
      gap: 10px;
      background: linear-gradient(135deg, #0066CC 0%, #6B5FD9 25%, #E991CC 75%, #7DD3C0 100%);
      color: #fff;
      padding: 14px 22px;
      border-radius: 50px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      cursor: pointer;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 15px;
      font-weight: 600;
      transition: transform 0.15s, box-shadow 0.15s;
      user-select: none;
    }
    #bridge-fab-inner:hover {
      transform: scale(1.04);
      box-shadow: 0 6px 24px rgba(0,0,0,0.35);
    }
    #bridge-fab-inner:active { transform: scale(0.97); }
  `;

  document.head.appendChild(style);
  fab.addEventListener('click', () => showLanguagePickerPanel(url));
  document.body.appendChild(fab);
}

// ─── Language picker panel (shown before summarising) ────────────────────────
const LANG_OPTIONS = [
  { value: 'en',    label: 'English' },
  { value: 'ms',    label: 'Malay' },
  { value: 'id',    label: 'Indonesian' },
  { value: 'vi',    label: 'Vietnamese' },
  { value: 'th',    label: 'Thai' },
  { value: 'zh-cn', label: 'Chinese (Simplified)' },
  { value: 'zh-tw', label: 'Chinese (Traditional)' },
  { value: 'ta',    label: 'Tamil' },
  { value: 'tl',    label: 'Tagalog / Filipino' },
  { value: 'my',    label: 'Burmese / Myanmar' },
  { value: 'km',    label: 'Khmer' },
  { value: 'lo',    label: 'Lao' },
];

function showLanguagePickerPanel(url) {
  removeExistingPanel();
  injectPanelStyles();

  summaryPanel = document.createElement('div');
  summaryPanel.id = 'bridge-panel';
  summaryPanel.innerHTML = `
    <div id="bridge-panel-inner">
      <div id="bridge-panel-header">
        <div id="bridge-panel-title">📄 Bridge</div>
        <button id="bridge-close-btn" aria-label="Close">✕</button>
      </div>
      <div id="bridge-scroll-area">
        <div id="bridge-panel-body">
          <p style="font-size:14px;font-weight:600;color:#333;margin:0 0 14px;">Choose your language:</p>
          <div id="bridge-lang-grid"></div>
          <p style="font-size:14px;font-weight:600;color:#333;margin:20px 0 10px;">What would you like to do?</p>
          <div style="display:flex;gap:10px;padding-bottom:20px;">
            <button id="bridge-action-summarise" class="bridge-action-btn">📄 Summarise Page</button>
            <button id="bridge-action-ask" class="bridge-action-btn">💬 Ask Question</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(summaryPanel);
  document.getElementById('bridge-close-btn').addEventListener('click', removeExistingPanel);

  // Build language grid
  const grid = document.getElementById('bridge-lang-grid');
  chrome.storage.sync.get('targetLang', ({ targetLang: saved = 'en' }) => {
    LANG_OPTIONS.forEach(({ value, label }) => {
      const btn = document.createElement('button');
      btn.className = 'bridge-lang-pick-btn' + (value === saved ? ' selected' : '');
      btn.textContent = label;
      btn.dataset.value = value;
      btn.addEventListener('click', () => {
        // Update selection visually
        document.querySelectorAll('.bridge-lang-pick-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        chrome.storage.sync.set({ targetLang: value });
      });
      grid.appendChild(btn);
    });

    // Action buttons
    document.getElementById('bridge-action-summarise').addEventListener('click', () => {
      generateAndShowSummary(url);
    });
    
    document.getElementById('bridge-action-ask').addEventListener('click', () => {
      showQuestionPanel(url);
    });
  });
}

// ─── Question-only panel (no summary needed) ─────────────────────────────────
function showQuestionPanel(url) {
  currentUrl = url;
  createPanelShell('💬 Ask Questions');
  
  document.getElementById('bridge-panel-body').innerHTML = `
    <p style="text-align:center;color:#666;margin:20px 0;">Ask me a question about this website.</p>
  `;

  // Show Q&A input immediately
  const inputRow = document.getElementById('bridge-qa-input-row');
  inputRow.style.display = 'flex';

  document.getElementById('bridge-send-btn').addEventListener('click', submitQuestion);
  document.getElementById('bridge-qa-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitQuestion();
  });
  document.getElementById('bridge-mic-btn').addEventListener('click', toggleMic);
}

// ─── Fetch summary and display panel ─────────────────────────────────────────
async function generateAndShowSummary(url) {
  if (isGenerating) return;
  currentUrl = url;
  isGenerating = true;
  showLoadingPanel('Generating summary…', 'Crawling sublinks for a comprehensive result');

  try {
    // Read language from in-panel selector if it exists, otherwise from storage
    const sel = document.getElementById('bridge-lang-select');
    const { targetLang: stored = 'en' } = await chrome.storage.sync.get('targetLang');
    const targetLang = (sel && sel.value) ? sel.value : stored;

    console.log('[Bridge] Summarising with targetLang:', targetLang);

    const response = await chrome.runtime.sendMessage({
      action: 'generateSummary',
      url,
      targetLang
    });

    if (response.success) {
      showSummaryPanel(response.data);
    } else {
      showErrorPanel(response.error);
    }
  } catch (err) {
    showErrorPanel(err.message);
  } finally {
    isGenerating = false;
  }
}

// ─── Shared panel shell ───────────────────────────────────────────────────────
function createPanelShell(titleHtml) {
  removeExistingPanel();
  injectPanelStyles();

  summaryPanel = document.createElement('div');
  summaryPanel.id = 'bridge-panel';
  summaryPanel.innerHTML = `
    <div id="bridge-panel-inner">
      <div id="bridge-panel-header">
        <div id="bridge-panel-title">${titleHtml}</div>
        <button id="bridge-close-btn" aria-label="Close">✕</button>
      </div>
      <div id="bridge-lang-bar">
        <label for="bridge-lang-select">🌐 Language:</label>
        <select id="bridge-lang-select">
          <option value="en">English</option>
          <option value="ms">Malay</option>
          <option value="id">Indonesian</option>
          <option value="vi">Vietnamese</option>
          <option value="th">Thai</option>
          <option value="zh-cn">Chinese (Simplified)</option>
          <option value="zh-tw">Chinese (Traditional)</option>
          <option value="ta">Tamil</option>
          <option value="tl">Tagalog / Filipino</option>
          <option value="my">Burmese / Myanmar</option>
          <option value="km">Khmer</option>
          <option value="lo">Lao</option>
        </select>
      </div>
      <div id="bridge-scroll-area">
        <div id="bridge-panel-body"></div>
        <div id="bridge-panel-footer" style="display:none;"></div>
        <div id="bridge-chat-log"></div>
      </div>
      <div id="bridge-qa-input-row" style="display:none;">
        <input id="bridge-qa-input" type="text" placeholder="Ask a question about this page…" />
        <button class="bridge-icon-btn" id="bridge-mic-btn" title="Speak your question">🎤</button>
        <button class="bridge-icon-btn" id="bridge-send-btn" title="Send">➤</button>
      </div>
    </div>
  `;

  document.body.appendChild(summaryPanel);
  document.getElementById('bridge-close-btn').addEventListener('click', removeExistingPanel);

  // Load saved language into the in-panel selector and persist changes
  chrome.storage.sync.get('targetLang', ({ targetLang }) => {
    const sel = document.getElementById('bridge-lang-select');
    if (sel && targetLang) sel.value = targetLang;
  });
  document.getElementById('bridge-lang-select').addEventListener('change', (e) => {
    chrome.storage.sync.set({ targetLang: e.target.value });
    // Re-summarise immediately with the new language if we have a URL
    if (currentUrl) generateAndShowSummary(currentUrl);
  });

  return summaryPanel;
}

function injectPanelStyles() {
  if (document.getElementById('bridge-panel-styles')) return;
  const s = document.createElement('style');
  s.id = 'bridge-panel-styles';
  s.textContent = `
    #bridge-panel {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 2147483646;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    #bridge-panel-inner {
      width: 420px;
      max-height: 80vh;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      border: 1.5px solid #e0e0e0;
    }
    #bridge-panel-header {
      background: linear-gradient(135deg, #0066CC 0%, #6B5FD9 25%, #E991CC 75%, #7DD3C0 100%);
      color: #fff;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    #bridge-panel-title { font-size: 16px; font-weight: 700; }
    #bridge-panel-title small {
      display: block;
      font-size: 11px;
      font-weight: 400;
      opacity: 0.7;
      margin-top: 2px;
    }
    #bridge-close-btn {
      background: rgba(255,255,255,0.15);
      border: none;
      color: #fff;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    #bridge-close-btn:hover { background: rgba(255,255,255,0.3); }
    #bridge-lang-bar {
      background: #f8f8f8;
      border-bottom: 1px solid #e8e8e8;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    #bridge-lang-bar label {
      font-size: 12px;
      font-weight: 600;
      color: #555;
      white-space: nowrap;
    }
    #bridge-lang-select {
      flex: 1;
      padding: 6px 10px;
      border: 1.5px solid #d0d0d0;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      background: #fff;
      color: #111;
      cursor: pointer;
      outline: none;
      transition: border-color 0.15s;
    }
    #bridge-lang-select:focus { border-color: #6B5FD9; }
    #bridge-lang-select option { background: #fff; color: #111; }

    /* Single unified scroll area */
    #bridge-scroll-area {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }
    #bridge-panel-body {
      padding: 20px 20px 0;
      line-height: 1.7;
      color: #222;
      font-size: 14px;
      flex-shrink: 0;
    }
    #bridge-panel-footer {
      padding: 12px 20px;
      display: flex;
      gap: 10px;
      flex-shrink: 0;
    }
    #bridge-chat-log {
      flex: 1;
      padding: 8px 16px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    /* Input bar — always pinned at bottom */
    #bridge-qa-input-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      background: #fff;
      border-top: 1px solid #e8e8e8;
      flex-shrink: 0;
    }
    .bridge-btn {
      flex: 1;
      padding: 10px;
      background: #6B5FD9;
      color: #fff;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      transition: opacity 0.15s;
    }
    .bridge-btn:hover { opacity: 0.8; }
    .bridge-spinner {
      width: 36px; height: 36px;
      border: 3px solid #e0e0e0;
      border-top-color: #6B5FD9;
      border-radius: 50%;
      animation: bridge-spin 0.8s linear infinite;
      margin: 24px auto 12px;
    }
    @keyframes bridge-spin {
      to { transform: rotate(360deg); }
    }
    .bridge-stat-row {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
    }
    .bridge-stat {
      flex: 1;
      background: #f5f5f5;
      border-radius: 8px;
      padding: 10px;
      text-align: center;
    }
    .bridge-stat-val { font-size: 20px; font-weight: 700; color: #6B5FD9; }
    .bridge-stat-lbl { font-size: 11px; color: #888; margin-top: 2px; }

    /* ── Q&A section ── */
    .bridge-bubble {
      max-width: 85%;
      padding: 8px 12px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
      word-break: break-word;
    }
    .bridge-bubble.user {
      align-self: flex-end;
      background: #6B5FD9;
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .bridge-bubble.bot {
      align-self: flex-start;
      background: #fff;
      color: #222;
      border: 1px solid #e0e0e0;
      border-bottom-left-radius: 4px;
    }
    .bridge-bubble.bot ol,
    .bridge-bubble.bot ul {
      margin: 4px 0 0 16px;
      padding: 0;
    }
    .bridge-bubble.bot li { margin-bottom: 4px; }
    .bridge-bubble.bot p:last-child { margin-bottom: 0; }
    .bridge-bubble.thinking {
      align-self: flex-start;
      background: #f0f0f0;
      color: #888;
      font-style: italic;
      border-bottom-left-radius: 4px;
    }
    #bridge-qa-input {
      flex: 1;
      padding: 9px 12px;
      border: 1.5px solid #e0e0e0;
      border-radius: 20px;
      font-size: 13px;
      outline: none;
      font-family: inherit;
      background: #fff;
      color: #111;
      transition: border-color 0.15s;
    }
    #bridge-qa-input:focus { border-color: #6B5FD9; }
    #bridge-qa-input::placeholder { color: #aaa; }
    .bridge-icon-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
      transition: opacity 0.15s, transform 0.1s;
    }
    .bridge-icon-btn:hover { opacity: 0.85; transform: scale(1.05); }
    .bridge-icon-btn:active { transform: scale(0.95); }
    #bridge-send-btn {
      background: #6B5FD9;
      color: #fff;
    }
    #bridge-mic-btn {
      background: #f0f0f0;
      color: #555;
    }
    #bridge-mic-btn.recording {
      background: #fee2e2;
      color: #dc2626;
      animation: bridge-mic-pulse 1s ease-in-out infinite;
    }
    @keyframes bridge-mic-pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.4); }
      50%       { box-shadow: 0 0 0 6px rgba(220,38,38,0); }
    }
    /* ── Language picker grid ── */
    #bridge-lang-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .bridge-lang-pick-btn {
      padding: 10px 8px;
      border: 1.5px solid #e0e0e0;
      border-radius: 10px;
      background: #fff;
      color: #333;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      text-align: left;
      transition: border-color 0.15s, background 0.15s;
      font-family: inherit;
    }
    .bridge-lang-pick-btn:hover {
      border-color: #6B5FD9;
      background: #F0EDFF;
    }
    .bridge-lang-pick-btn.selected {
      border-color: #6B5FD9;
      background: #6B5FD9;
      color: #fff;
    }
    .bridge-action-btn {
      flex: 1;
      padding: 12px 16px;
      border: 1.5px solid #e0e0e0;
      border-radius: 10px;
      background: #fff;
      color: #333;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s;
      font-family: inherit;
    }
    .bridge-action-btn:hover {
      border-color: #6B5FD9;
      background: #F0EDFF;
      transform: translateY(-1px);
    }
  `;
  document.head.appendChild(s);
}

// ─── Loading panel ────────────────────────────────────────────────────────────
function showLoadingPanel(msg = 'Generating summary…', sub = '') {
  createPanelShell('Bridge Summary');
  // Pre-load the language selector so user can change it even during loading
  chrome.storage.sync.get('targetLang', ({ targetLang }) => {
    const sel = document.getElementById('bridge-lang-select');
    if (sel && targetLang) sel.value = targetLang;
  });
  document.getElementById('bridge-panel-body').innerHTML = `
    <div class="bridge-spinner"></div>
    <p style="text-align:center;color:#666;margin:0 0 6px;">${escapeHtml(msg)}</p>
    <p style="text-align:center;color:#aaa;font-size:12px;margin:0;">${escapeHtml(sub)}</p>
  `;
}

// ─── Summary panel ────────────────────────────────────────────────────────────
function showSummaryPanel(data) {
  const reduction = data.word_count > 0
    ? (100 - (data.summary_word_count / data.word_count * 100)).toFixed(0)
    : 0;

  createPanelShell(`
    Bridge Summary
    <small>${data.word_count} words → ${data.summary_word_count} words (${reduction}% shorter)</small>
  `);

  document.getElementById('bridge-panel-body').innerHTML = `
    <div class="bridge-stat-row">
      <div class="bridge-stat">
        <div class="bridge-stat-val">${data.word_count}</div>
        <div class="bridge-stat-lbl">Original words</div>
      </div>
      <div class="bridge-stat">
        <div class="bridge-stat-val">${data.summary_word_count}</div>
        <div class="bridge-stat-lbl">Summary words</div>
      </div>
      <div class="bridge-stat">
        <div class="bridge-stat-val">${reduction}%</div>
        <div class="bridge-stat-lbl">Shorter</div>
      </div>
    </div>
    <div style="white-space:pre-wrap;">${escapeHtml(data.summary)}</div>
  `;

  // ── Action buttons footer ──
  const footer = document.getElementById('bridge-panel-footer');
  footer.style.display = 'flex';
  footer.innerHTML = `
    <button class="bridge-btn" id="bridge-copy-btn">📋 Copy</button>
    <button class="bridge-btn" id="bridge-speak-btn">🔊 Read Aloud</button>
  `;

  document.getElementById('bridge-copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(data.summary).then(() => {
      const btn = document.getElementById('bridge-copy-btn');
      btn.textContent = '✓ Copied!';
      setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
    });
  });

  let isPlaying = false;
  let currentAudio = null;

  document.getElementById('bridge-speak-btn').addEventListener('click', async () => {
    const speakBtn = document.getElementById('bridge-speak-btn');
    
    // If already playing, toggle pause/resume
    if (isPlaying && currentAudio) {
      if (currentAudio.paused) {
        currentAudio.play();
        speakBtn.textContent = '⏸️ Pause';
      } else {
        currentAudio.pause();
        speakBtn.textContent = '▶️ Resume';
      }
      return;
    }

    // Stop any existing audio
    if (window.bridgeAudio) {
      window.bridgeAudio.pause();
      window.bridgeAudio = null;
    }

    const sel = document.getElementById('bridge-lang-select');
    const langCode = sel ? sel.value : 'en';

    console.log('[Bridge TTS] Requesting TTS for lang:', langCode);

    // Disable button and show loading state
    speakBtn.disabled = true;
    speakBtn.style.opacity = '0.5';
    speakBtn.style.cursor = 'not-allowed';
    const originalText = speakBtn.textContent;
    speakBtn.textContent = '🔄 Loading...';

    try {
      const response = await fetch('http://localhost:5000/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: data.summary,
          lang: langCode
        })
      });

      if (!response.ok) {
        throw new Error(`TTS server error: ${response.status}`);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      window.bridgeAudio = new Audio(audioUrl);
      currentAudio = window.bridgeAudio;
      
      window.bridgeAudio.onplay = () => {
        console.log('[Bridge TTS] Playback started');
        isPlaying = true;
        // Re-enable button when playing
        speakBtn.disabled = false;
        speakBtn.style.opacity = '1';
        speakBtn.style.cursor = 'pointer';
        speakBtn.textContent = '⏸️ Pause';
      };
      window.bridgeAudio.onended = () => {
        console.log('[Bridge TTS] Playback finished');
        URL.revokeObjectURL(audioUrl);
        isPlaying = false;
        currentAudio = null;
        // Reset button
        speakBtn.textContent = originalText;
      };
      window.bridgeAudio.onerror = (e) => {
        console.error('[Bridge TTS] Audio error:', e);
        isPlaying = false;
        currentAudio = null;
        // Re-enable button on error
        speakBtn.disabled = false;
        speakBtn.style.opacity = '1';
        speakBtn.style.cursor = 'pointer';
        speakBtn.textContent = originalText;
      };
      
      await window.bridgeAudio.play();
    } catch (error) {
      console.error('[Bridge TTS] Error:', error);
      alert('Text-to-speech failed. Make sure the Flask server is running at http://localhost:5000');
      isPlaying = false;
      currentAudio = null;
      // Re-enable button on error
      speakBtn.disabled = false;
      speakBtn.style.opacity = '1';
      speakBtn.style.cursor = 'pointer';
      speakBtn.textContent = originalText;
    }
  });

  // ── Show Q&A input bar and wire up events ──
  const inputRow = document.getElementById('bridge-qa-input-row');
  inputRow.style.display = 'flex';

  document.getElementById('bridge-send-btn').addEventListener('click', submitQuestion);
  document.getElementById('bridge-qa-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitQuestion();
  });
  document.getElementById('bridge-mic-btn').addEventListener('click', toggleMic);
}

// ─── Error panel ──────────────────────────────────────────────────────────────
function showErrorPanel(error) {
  createPanelShell('Bridge Summary');
  document.getElementById('bridge-panel-body').innerHTML = `
    <div style="text-align:center;padding:12px 0;">
      <div style="font-size:40px;margin-bottom:12px;">⚠️</div>
      <p style="color:#333;font-weight:600;margin:0 0 8px;">Could not generate summary</p>
      <p style="color:#888;font-size:12px;margin:0 0 8px;">${escapeHtml(error)}</p>
      <p style="color:#aaa;font-size:12px;margin:0;">Make sure the Flask server is running at<br><strong>http://localhost:5000</strong></p>
    </div>
  `;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function removeExistingPanel() {
  summaryPanel?.remove();
  summaryPanel = null;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Auto-check on page load ──────────────────────────────────────────────────
chrome.runtime.sendMessage(
  { action: 'isGovWebsite', url: window.location.href },
  (response) => {
    if (response?.isGov) showFloatingButton(window.location.href);
  }
);

// ─── Q&A: submit typed question ───────────────────────────────────────────────
async function submitQuestion() {
  const input = document.getElementById('bridge-qa-input');
  if (!input) return;
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  addBubble(question, 'user');
  const thinking = addBubble('Thinking…', 'thinking');

  try {
    const sel = document.getElementById('bridge-lang-select');
    const { targetLang: stored = 'en' } = await chrome.storage.sync.get('targetLang');
    const targetLang = sel ? sel.value : stored;
    const response = await chrome.runtime.sendMessage({
      action: 'askQuestion',
      url: currentUrl,
      question,
      targetLang
    });

    thinking.remove();
    
    // Check if response exists and has expected structure
    if (!response) {
      addBubble('⚠️ No response from server. Make sure the Flask server is running.', 'bot');
      return;
    }
    
    if (response.success) {
      const answer = response.data?.summary ?? response.data?.answer ?? JSON.stringify(response.data);
      addBubble(answer, 'bot');
    } else {
      addBubble(`⚠️ ${response.error || 'Unknown error occurred'}`, 'bot');
    }
  } catch (err) {
    thinking.remove();
    addBubble(`⚠️ ${err.message || 'Failed to get answer'}`, 'bot');
    console.error('[Bridge Q&A] Error:', err);
  }

  // Scroll unified area to bottom
  const scrollArea = document.getElementById('bridge-scroll-area');
  if (scrollArea) scrollArea.scrollTop = scrollArea.scrollHeight;
}

function addBubble(text, role) {
  const log = document.getElementById('bridge-chat-log');
  if (!log) return null;
  const el = document.createElement('div');
  el.className = `bridge-bubble ${role}`;
  
  if (role === 'bot') {
    // Bot message with speaker button at the bottom
    el.innerHTML = formatBotText(text);
    
    // Add a line break container
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'margin-top:8px;';
    
    // Speaker button with its own state
    const speakerBtn = document.createElement('button');
    let btnIsPlaying = false;
    let btnAudio = null;
    
    speakerBtn.innerHTML = '🔊 Listen';
    speakerBtn.title = 'Listen to this answer';
    speakerBtn.style.cssText = `
      background:transparent;
      border:1px solid #e0e0e0;
      border-radius:6px;
      padding:4px 10px;
      cursor:pointer;
      font-size:12px;
      transition:all 0.2s;
      color:#888;
      display:inline-block;
      font-family:inherit;
      font-weight:500;
    `;
    
    speakerBtn.addEventListener('mouseenter', () => {
      speakerBtn.style.background = '#f5f5f5';
      speakerBtn.style.borderColor = '#6B5FD9';
      speakerBtn.style.color = '#6B5FD9';
    });
    speakerBtn.addEventListener('mouseleave', () => {
      if (!btnIsPlaying) {
        speakerBtn.style.background = 'transparent';
        speakerBtn.style.borderColor = '#e0e0e0';
        speakerBtn.style.color = '#888';
      }
    });
    
    speakerBtn.addEventListener('click', async () => {
      // If already playing, toggle pause/resume
      if (btnIsPlaying && btnAudio) {
        if (btnAudio.paused) {
          btnAudio.play();
          speakerBtn.innerHTML = '⏸️ Pause';
          speakerBtn.title = 'Pause';
        } else {
          btnAudio.pause();
          speakerBtn.innerHTML = '▶️ Resume';
          speakerBtn.title = 'Resume';
        }
        return;
      }
      
      // Stop any existing audio
      if (window.bridgeAudio) {
        window.bridgeAudio.pause();
        window.bridgeAudio = null;
      }
      
      const sel = document.getElementById('bridge-lang-select');
      const langCode = sel ? sel.value : 'en';
      
      // Disable button and show loading
      speakerBtn.disabled = true;
      speakerBtn.style.opacity = '0.5';
      speakerBtn.style.cursor = 'not-allowed';
      speakerBtn.innerHTML = '🔄 Loading...';
      
      try {
        const response = await fetch('http://localhost:5000/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            lang: langCode
          })
        });
        
        if (!response.ok) {
          throw new Error(`TTS server error: ${response.status}`);
        }
        
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        window.bridgeAudio = new Audio(audioUrl);
        btnAudio = window.bridgeAudio;
        
        window.bridgeAudio.onplay = () => {
          btnIsPlaying = true;
          // Re-enable button when playing
          speakerBtn.disabled = false;
          speakerBtn.style.opacity = '1';
          speakerBtn.style.cursor = 'pointer';
          speakerBtn.innerHTML = '⏸️ Pause';
          speakerBtn.title = 'Pause';
        };
        window.bridgeAudio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          btnIsPlaying = false;
          btnAudio = null;
          speakerBtn.innerHTML = '🔊 Listen';
          speakerBtn.title = 'Listen to this answer';
        };
        window.bridgeAudio.onerror = (e) => {
          console.error('[Bridge TTS] Audio error:', e);
          btnIsPlaying = false;
          btnAudio = null;
          speakerBtn.disabled = false;
          speakerBtn.style.opacity = '1';
          speakerBtn.style.cursor = 'pointer';
          speakerBtn.innerHTML = '🔊 Listen';
          speakerBtn.title = 'Listen to this answer';
        };
        
        await window.bridgeAudio.play();
      } catch (error) {
        console.error('[Bridge TTS] Error:', error);
        alert('Text-to-speech failed. Make sure the Flask server is running.');
        btnIsPlaying = false;
        btnAudio = null;
        speakerBtn.disabled = false;
        speakerBtn.style.opacity = '1';
        speakerBtn.style.cursor = 'pointer';
        speakerBtn.innerHTML = '🔊 Listen';
        speakerBtn.title = 'Listen to this answer';
      }
    });
    
    // Append speaker button inside a container at the bottom
    buttonContainer.appendChild(speakerBtn);
    el.appendChild(buttonContainer);
    log.appendChild(el);
  } else {
    el.textContent = text;
    log.appendChild(el);
  }
  
  // Scroll the unified scroll area to bottom
  const scrollArea = document.getElementById('bridge-scroll-area');
  if (scrollArea) scrollArea.scrollTop = scrollArea.scrollHeight;
  return el;
}

function formatBotText(text) {
  if (!text) return '';

  // Split on numbered points like "1. " "2. " etc, or on newlines
  // First normalise: replace "1. " style inline numbering with newline-prefixed
  let formatted = text
    // Insert a newline before "1. ", "2. " etc when they appear mid-sentence
    .replace(/\s+(\d+)\.\s+/g, '\n$1. ')
    .trim();

  const lines = formatted.split('\n').map(l => l.trim()).filter(Boolean);

  if (lines.length <= 1) {
    // Single line — just escape and return
    return escapeHtml(text);
  }

  // Detect if lines are numbered (start with "1.", "2." etc)
  const isNumbered = lines.every(l => /^\d+\./.test(l));

  if (isNumbered) {
    const items = lines.map(l => `<li style="margin-bottom:6px;">${escapeHtml(l.replace(/^\d+\.\s*/, ''))}</li>`).join('');
    return `<ol style="margin:8px 0 8px 20px;padding:0;line-height:1.6;">${items}</ol>`;
  }

  // Check if lines start with bullet markers
  const hasBullets = lines.some(l => /^[-•*]/.test(l));
  
  if (hasBullets) {
    const items = lines.map(l => {
      const cleaned = l.replace(/^[-•*]\s*/, '');
      return `<li style="margin-bottom:6px;">${escapeHtml(cleaned)}</li>`;
    }).join('');
    return `<ul style="margin:8px 0 8px 20px;padding:0;line-height:1.6;">${items}</ul>`;
  }

  // Otherwise render as separate paragraphs
  return lines.map(l => `<p style="margin:0 0 8px 0;">${escapeHtml(l)}</p>`).join('');
}

// ─── Mic: record → speech-to-text → fill input ───────────────────────────────
async function toggleMic() {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      await transcribeAndFill(blob);
    };

    mediaRecorder.start();
    isRecording = true;

    const micBtn = document.getElementById('bridge-mic-btn');
    if (micBtn) {
      micBtn.classList.add('recording');
      micBtn.title = 'Stop recording';
      micBtn.textContent = '⏹';
    }
  } catch (err) {
    addBubble(`⚠️ Mic access denied: ${err.message}`, 'bot');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;

  const micBtn = document.getElementById('bridge-mic-btn');
  if (micBtn) {
    micBtn.classList.remove('recording');
    micBtn.title = 'Speak your question';
    micBtn.textContent = '🎤';
  }
}

async function transcribeAndFill(blob) {
  const input = document.getElementById('bridge-qa-input');
  if (input) input.placeholder = 'Transcribing…';

  try {
    // Convert blob to base64 data URL so background.js can fetch it
    const dataUrl = await blobToDataUrl(blob);
    const response = await chrome.runtime.sendMessage({
      action: 'speechToText',
      audioDataUrl: dataUrl
    });

    if (response.success && response.text) {
      if (input) {
        input.value = response.text;
        input.placeholder = 'Ask a question about this page…';
        input.focus();
      }
    } else {
      addBubble(`⚠️ Speech recognition failed: ${response.error}`, 'bot');
      if (input) input.placeholder = 'Ask a question about this page…';
    }
  } catch (err) {
    addBubble(`⚠️ ${err.message}`, 'bot');
    if (input) input.placeholder = 'Ask a question about this page…';
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
