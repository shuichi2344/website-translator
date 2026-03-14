// Background service worker for detecting government websites

// List of government domain patterns for ASEAN countries
const GOV_DOMAINS = [
  // Malaysia
  '.gov.my', '.mygov.my',
  // Singapore
  '.gov.sg', '.sg',
  // Indonesia
  '.go.id', '.gov.id',
  // Thailand
  '.go.th', '.gov.th',
  // Philippines
  '.gov.ph',
  // Vietnam
  '.gov.vn',
  // Myanmar
  '.gov.mm',
  // Cambodia
  '.gov.kh',
  // Laos
  '.gov.la',
  // Brunei
  '.gov.bn',
  // General government patterns
  'government.', 'ministry.', 'parliament.'
];

// Check if URL is a government website
function isGovernmentWebsite(url) {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname.toLowerCase();
    
    return GOV_DOMAINS.some(domain => hostname.includes(domain));
  } catch (e) {
    return false;
  }
}

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only process when page is fully loaded
  if (changeInfo.status === 'complete' && tab.url) {
    if (isGovernmentWebsite(tab.url)) {
      console.log('Government website detected:', tab.url);
      
      // Send message to content script to show summary button
      chrome.tabs.sendMessage(tabId, {
        action: 'showSummaryButton',
        url: tab.url
      }).catch(err => {
        // Ignore errors if content script not ready
        console.log('Content script not ready yet');
      });
    }
  }
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'generateSummary') {
    generateSummary(request.url, request.targetLang)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'isGovWebsite') {
    sendResponse({ isGov: isGovernmentWebsite(request.url) });
  }
});

// Generate summary by calling the Flask backend
async function generateSummary(url, targetLang = 'en') {
  try {
    const formData = new FormData();
    formData.append('url', url);
    formData.append('target_lang', targetLang);
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
      return data;
    } else {
      throw new Error(data.error || 'Unknown error');
    }
  } catch (error) {
    console.error('Error generating summary:', error);
    throw error;
  }
}
