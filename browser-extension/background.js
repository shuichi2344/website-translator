// Background service worker — detects ASEAN government websites

const GOV_DOMAINS = [
  // Malaysia
  '.gov.my', '.mygov.my',
  // Singapore
  '.gov.sg',
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
  // Timor-Leste
  '.gov.tl',
  // Generic patterns
  'government.', 'ministry.', 'parliament.'
];

function isGovernmentWebsite(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase();
    return GOV_DOMAINS.some(d => hostname.includes(d));
  } catch {
    return false;
  }
}

// Notify content script when a gov page finishes loading
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    if (isGovernmentWebsite(tab.url)) {
      chrome.tabs.sendMessage(tabId, {
        action: 'showSummaryButton',
        url: tab.url
      }).catch(() => {});
    }
  }
});

// Handle messages from content script / popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'isGovWebsite') {
    sendResponse({ isGov: isGovernmentWebsite(request.url) });
    return;
  }

  if (request.action === 'generateSummary') {
    generateSummary(request.url, request.targetLang)
      .then(data => sendResponse({ success: true, data }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === 'askQuestion') {
    askQuestion(request.url, request.question, request.targetLang)
      .then(data => sendResponse({ success: true, data }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === 'speechToText') {
    speechToText(request.audioDataUrl)
      .then(text => sendResponse({ success: true, text }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

async function generateSummary(url, targetLang = 'en') {
  const formData = new FormData();
  formData.append('url', url);
  formData.append('target_lang', targetLang);
  formData.append('crawl_depth', '1');
  formData.append('max_sublinks', '3');

  const response = await fetch('http://localhost:5000/summarize/website', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) throw new Error(`Server error: ${response.status}`);

  const data = await response.json();
  if (!data.success) throw new Error(data.error || 'Unknown error');
  return data;
}

async function askQuestion(url, question, targetLang = 'en') {
  const formData = new FormData();
  formData.append('url', url);
  formData.append('question', question);
  formData.append('target_lang', targetLang);

  const response = await fetch('http://localhost:5000/qa/website', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  const data = await response.json();
  if (!data.success) throw new Error(data.error || 'Unknown error');
  return data;
}

async function speechToText(audioDataUrl) {
  const res = await fetch(audioDataUrl);
  const blob = await res.blob();

  const formData = new FormData();
  formData.append('audio', blob, 'recording.wav');

  const response = await fetch('http://localhost:5000/speech-to-text', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  const data = await response.json();
  if (!data.success) throw new Error(data.error || 'Unknown error');
  return data.text ?? data.question ?? '';
}
