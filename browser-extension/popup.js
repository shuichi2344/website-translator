// Popup script for extension settings

// Load saved language preference
chrome.storage.sync.get('targetLang', (data) => {
  if (data.targetLang) {
    document.getElementById('targetLang').value = data.targetLang;
  }
});

// Save language preference when changed
document.getElementById('targetLang').addEventListener('change', (e) => {
  chrome.storage.sync.set({ targetLang: e.target.value }, () => {
    console.log('Language preference saved:', e.target.value);
  });
});

// Check server status
async function checkServerStatus() {
  const statusDiv = document.getElementById('status');
  
  try {
    const response = await fetch('http://localhost:5000/', {
      method: 'GET',
      mode: 'no-cors' // Allow checking even if CORS is not configured
    });
    
    // If we get here without error, server is running
    statusDiv.className = 'status';
    statusDiv.innerHTML = `
      <div class="dot"></div>
      <span>Server running ✓</span>
    `;
  } catch (error) {
    statusDiv.className = 'status error';
    statusDiv.innerHTML = `
      <div class="dot error"></div>
      <span>Server offline - Start Flask server</span>
    `;
  }
}

// Check status on popup open
checkServerStatus();

// Recheck every 5 seconds
setInterval(checkServerStatus, 5000);
