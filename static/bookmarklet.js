// Bridge Bookmarklet - Universal browser support
// This script is loaded when the bookmarklet is clicked

(function() {
  'use strict';
  
  // Check if already loaded
  if (window.bridgeBookmarkletLoaded) {
    console.log('Bridge bookmarklet already loaded');
    return;
  }
  window.bridgeBookmarkletLoaded = true;
  
  let summaryPanel = null;
  let isGenerating = false;
  
  // Create floating summary button
  function showFloatingButton(url) {
    // Remove existing button if any
    const existingBtn = document.getElementById('bridge-summary-btn');
    if (existingBtn) {
      existingBtn.remove();
    }
    
    // Create floating button
    const button = document.createElement('div');
    button.id = 'bridge-summary-btn';
    button.innerHTML = `
      <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 999999;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 16px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 10px;
        transition: transform 0.2s;
      " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
        <span style="font-size: 20px;">📄</span>
        <span>Summarize This Page</span>
      </div>
    `;
    
    button.addEventListener('click', () => {
      generateAndShowSummary(url);
    });
    
    document.body.appendChild(button);
  }
  
  // Generate and display summary
  async function generateAndShowSummary(url) {
    if (isGenerating) return;
    
    isGenerating = true;
    showLoadingPanel();
    
    try {
      const formData = new FormData();
      formData.append('url', url);
      formData.append('target_lang', 'en');
      formData.append('crawl_depth', '1');
      formData.append('max_sublinks', '3');
      
      const response = await fetch('http://localhost:5000/summarize/website', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate summary');
      }
      
      const data = await response.json();
      
      if (data.success) {
        showSummaryPanel(data);
      } else {
        showErrorPanel(data.error || 'Unknown error');
      }
    } catch (error) {
      showErrorPanel(error.message);
    } finally {
      isGenerating = false;
    }
  }
  
  // Show loading panel
  function showLoadingPanel() {
    removeExistingPanel();
    
    summaryPanel = document.createElement('div');
    summaryPanel.id = 'bridge-summary-panel';
    summaryPanel.innerHTML = `
      <div style="
        position: fixed;
        top: 20px;
        right: 20px;
        width: 400px;
        max-height: 80vh;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 999998;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      ">
        <div style="
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        ">
          <h3 style="margin: 0; font-size: 18px;">Bridge Summary</h3>
          <button id="bridge-close-btn" style="
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
          ">×</button>
        </div>
        <div style="padding: 20px; text-align: center;">
          <div style="
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
          "></div>
          <p style="color: #666; margin-top: 10px;">Generating summary...</p>
          <p style="color: #999; font-size: 12px;">Crawling 3 sublinks for comprehensive summary</p>
        </div>
      </div>
      <style>
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
    
    document.body.appendChild(summaryPanel);
    
    // Add close button handler
    document.getElementById('bridge-close-btn').addEventListener('click', removeExistingPanel);
  }
  
  // Show summary panel
  function showSummaryPanel(data) {
    removeExistingPanel();
    
    summaryPanel = document.createElement('div');
    summaryPanel.id = 'bridge-summary-panel';
    summaryPanel.innerHTML = `
      <div style="
        position: fixed;
        top: 20px;
        right: 20px;
        width: 450px;
        max-height: 80vh;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 999998;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        display: flex;
        flex-direction: column;
      ">
        <div style="
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        ">
          <div>
            <h3 style="margin: 0; font-size: 18px;">Bridge Summary</h3>
            <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.9;">
              ${data.word_count} words → ${data.summary_word_count} words
            </p>
          </div>
          <button id="bridge-close-btn" style="
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
          ">×</button>
        </div>
        <div style="
          padding: 20px;
          overflow-y: auto;
          flex: 1;
          line-height: 1.6;
        ">
          <div style="white-space: pre-wrap; color: #333; font-size: 14px;">
${data.summary}
          </div>
        </div>
        <div style="
          padding: 15px 20px;
          background: #f8f9fa;
          border-top: 1px solid #e0e0e0;
          display: flex;
          gap: 10px;
        ">
          <button id="bridge-copy-btn" style="
            flex: 1;
            padding: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
          ">📋 Copy</button>
          <button id="bridge-speak-btn" style="
            flex: 1;
            padding: 10px;
            background: #764ba2;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
          ">🔊 Read Aloud</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(summaryPanel);
    
    // Add event handlers
    document.getElementById('bridge-close-btn').addEventListener('click', removeExistingPanel);
    document.getElementById('bridge-copy-btn').addEventListener('click', () => {
      navigator.clipboard.writeText(data.summary);
      const btn = document.getElementById('bridge-copy-btn');
      btn.textContent = '✓ Copied!';
      setTimeout(() => btn.textContent = '📋 Copy', 2000);
    });
    document.getElementById('bridge-speak-btn').addEventListener('click', () => {
      const utterance = new SpeechSynthesisUtterance(data.summary);
      speechSynthesis.speak(utterance);
    });
  }
  
  // Show error panel
  function showErrorPanel(error) {
    removeExistingPanel();
    
    summaryPanel = document.createElement('div');
    summaryPanel.id = 'bridge-summary-panel';
    summaryPanel.innerHTML = `
      <div style="
        position: fixed;
        top: 20px;
        right: 20px;
        width: 400px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 999998;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      ">
        <div style="
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        ">
          <h3 style="margin: 0; font-size: 18px;">Bridge Summary</h3>
          <button id="bridge-close-btn" style="
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
          ">×</button>
        </div>
        <div style="padding: 20px; text-align: center;">
          <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
          <p style="color: #666; margin: 10px 0;">Failed to generate summary</p>
          <p style="color: #999; font-size: 12px;">${error}</p>
          <p style="color: #999; font-size: 12px; margin-top: 10px;">
            Make sure the Flask server is running at http://localhost:5000
          </p>
        </div>
      </div>
    `;
    
    document.body.appendChild(summaryPanel);
    
    document.getElementById('bridge-close-btn').addEventListener('click', removeExistingPanel);
  }
  
  // Remove existing panel
  function removeExistingPanel() {
    if (summaryPanel) {
      summaryPanel.remove();
      summaryPanel = null;
    }
  }
  
  // Show the button immediately
  showFloatingButton(window.location.href);
  
  console.log('Bridge bookmarklet loaded successfully!');
})();
