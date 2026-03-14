# Bridge - Government Website Summarizer Extension

Chrome extension that automatically detects ASEAN government websites and provides simple summaries.

## Features

- 🔍 **Auto-detection**: Automatically detects when you visit government websites
- 📄 **One-click summarization**: Floating button appears on government sites
- 🕷️ **Smart crawling**: Automatically crawls 3 sublinks for comprehensive summaries
- 🌐 **Multilingual**: Supports 12 ASEAN languages
- 💬 **Simple language**: Summaries written in words a 10-year-old can understand
- 🔊 **Text-to-speech**: Read summaries aloud
- 📋 **Copy to clipboard**: Easy sharing

## Supported Government Domains

- Malaysia: `.gov.my`, `.mygov.my`
- Singapore: `.gov.sg`
- Indonesia: `.go.id`, `.gov.id`
- Thailand: `.go.th`, `.gov.th`
- Philippines: `.gov.ph`
- Vietnam: `.gov.vn`
- Myanmar: `.gov.mm`
- Cambodia: `.gov.kh`
- Laos: `.gov.la`
- Brunei: `.gov.bn`

## Browser Support

This extension works on:
- ✅ **Chrome** - Full support
- ✅ **Brave** - Full support  
- ✅ **Edge** - Full support
- ✅ **Opera** - Full support
- ✅ **Safari** - Use bookmarklet (see CROSS_BROWSER.md)
- ✅ **Firefox** - Use bookmarklet (see CROSS_BROWSER.md)

All Chromium-based browsers (Chrome, Brave, Edge, Opera) use the same extension. For Safari and Firefox, use the universal bookmarklet method.

## Installation

### 1. Start the Flask Server

```bash
cd vhack2026-live-translator
python summarizer_web.py
```

The server should be running at `http://localhost:5000`

### 2. Load Extension (Chrome/Brave/Edge/Opera)

1. Open your browser's extensions page:
   - Chrome: `chrome://extensions/`
   - Brave: `brave://extensions/`
   - Edge: `edge://extensions/`
   - Opera: `opera://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `browser-extension` folder
5. The Bridge extension icon should appear in your toolbar

### 3. Safari/Firefox Users

See `CROSS_BROWSER.md` for the universal bookmarklet that works on ANY browser without installation.

## Usage

### Automatic Detection

1. Visit any ASEAN government website (e.g., `https://www.gov.my`)
2. A floating "Summarize This Page" button will appear in the bottom-right
3. Click the button to generate a summary
4. The summary panel will show:
   - Simple bullet-point summary
   - Word count reduction stats
   - Copy and Read Aloud buttons

### Settings

Click the Bridge extension icon to:
- Change target language
- Check server status

## How It Works

1. **Detection**: Content script monitors all page loads
2. **Filtering**: Background script checks if URL matches government domains
3. **UI**: Floating button appears on government sites
4. **Summarization**: Sends URL to Flask backend
5. **Crawling**: Backend scrapes main page + 3 sublinks
6. **AI Processing**: Gemini generates simple summary
7. **Display**: Shows summary in clean panel

## Requirements

- Chrome browser (or Chromium-based browser)
- Flask server running on `localhost:5000`
- Internet connection for AI summarization

## Troubleshooting

### Button doesn't appear
- Check if the website domain is in the supported list
- Open DevTools Console to see detection logs

### "Server offline" error
- Make sure Flask server is running: `python summarizer_web.py`
- Check that it's accessible at `http://localhost:5000`

### Summary generation fails
- Ensure you have a valid Gemini API key in `.env`
- Check Flask server logs for errors
- Verify internet connection

## Privacy

- Extension only activates on government websites
- No data is collected or stored
- All processing happens locally or through your own API keys
- URLs are only sent to your local Flask server

## Development

### File Structure

```
browser-extension/
├── manifest.json       # Extension configuration
├── background.js       # Service worker (detection logic)
├── content.js         # Page script (UI injection)
├── popup.html         # Extension popup UI
├── popup.js           # Popup logic
└── icons/             # Extension icons
```

### Adding More Government Domains

Edit `background.js` and add domains to the `GOV_DOMAINS` array:

```javascript
const GOV_DOMAINS = [
  '.gov.my',
  '.your-domain.here',
  // ...
];
```

## License

MIT License - See main project LICENSE file
