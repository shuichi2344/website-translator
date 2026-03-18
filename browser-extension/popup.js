// Load saved language preference
chrome.storage.sync.get('targetLang', ({ targetLang }) => {
  const sel = document.getElementById('targetLang');
  if (targetLang) {
    sel.value = targetLang;
  } else {
    // First run — persist the default value so content.js can always read it
    chrome.storage.sync.set({ targetLang: sel.value });
  }
});

// Persist language choice immediately on change
document.getElementById('targetLang').addEventListener('change', (e) => {
  chrome.storage.sync.set({ targetLang: e.target.value });
});

// Server status check
async function checkServer() {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  const box  = document.getElementById('status');

  try {
    await fetch('http://localhost:5000/', { method: 'GET', mode: 'no-cors' });
    dot.className  = 'dot';
    text.textContent = 'Server running ✓';
    box.className  = 'status';
  } catch {
    dot.className  = 'dot error';
    text.textContent = 'Server offline — run: python summarizer_web.py';
    box.className  = 'status error';
  }
}

checkServer();
setInterval(checkServer, 5000);
