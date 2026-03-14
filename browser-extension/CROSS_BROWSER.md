# Cross-Browser Support

## Browser Compatibility

### ✅ Chrome, Brave, Edge, Opera (Chromium-based)
**Status:** Fully supported with extension

**Installation:**
1. Go to browser extensions page:
   - Chrome: `chrome://extensions/`
   - Brave: `brave://extensions/`
   - Edge: `edge://extensions/`
   - Opera: `opera://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `browser-extension` folder

---

### 🦊 Firefox
**Status:** Requires manifest v2 conversion

**Installation:**
1. Use the Firefox version in `browser-extension-firefox/` folder
2. Go to `about:debugging#/runtime/this-firefox`
3. Click "Load Temporary Add-on"
4. Select `manifest.json` from the Firefox folder

---

### 🧭 Safari
**Status:** Requires Xcode conversion

**Installation:**
1. Use the Safari version in `browser-extension-safari/` folder
2. Open with Xcode
3. Build and run
4. Enable in Safari Extensions preferences

---

### 🌐 Universal Bookmarklet (ALL BROWSERS)
**Status:** Works on ANY browser without installation!

**What is a bookmarklet?**
A bookmarklet is a bookmark that runs JavaScript code. It works on Safari, Firefox, Chrome, and any other browser.

**Installation:**

1. **Create a new bookmark** in your browser
2. **Name it:** "📄 Summarize Page"
3. **Copy and paste this as the URL/Location:**

```javascript
javascript:(function(){if(window.location.hostname.match(/\.gov\.(my|sg|id|th|ph|vn|mm|kh|la|bn)|\.go\.(id|th)/)){var s=document.createElement('script');s.src='http://localhost:5000/static/bookmarklet.js';document.body.appendChild(s);}else{alert('This only works on government websites!');}})();
```

**How to use:**
1. Visit any ASEAN government website
2. Click the "📄 Summarize Page" bookmark
3. A floating button will appear
4. Click it to generate a summary

**Browser-specific instructions:**

**Safari:**
- Bookmarks → Add Bookmark → Edit → Paste the code in the URL field

**Firefox:**
- Bookmarks → Show All Bookmarks → New Bookmark → Paste the code in Location field

**Chrome/Brave/Edge:**
- Bookmarks → Bookmark Manager → Add new bookmark → Paste the code in URL field

**How it works:**
- Checks if you're on a government website
- Loads the summarizer script from your Flask server
- Shows the same floating button and summary panel
- Works on desktop and mobile browsers

---

## Recommended Setup by Browser

| Browser | Best Option | Alternative |
|---------|-------------|-------------|
| Chrome | Extension | Bookmarklet |
| Brave | Extension | Bookmarklet |
| Edge | Extension | Bookmarklet |
| Opera | Extension | Bookmarklet |
| Firefox | Firefox Extension | Bookmarklet |
| Safari | Bookmarklet | Safari Extension |
| Mobile | Bookmarklet | - |

---

## Mobile Support

### iOS Safari
1. Add bookmarklet to favorites
2. Visit government website
3. Tap bookmarklet from favorites

### Android Chrome
1. Add bookmarklet to bookmarks
2. Visit government website
3. Tap bookmarklet from bookmarks

---

## Which Should I Use?

**Use Extension if:**
- You use Chrome, Brave, Edge, or Opera
- You want automatic detection
- You want the best experience

**Use Bookmarklet if:**
- You use Safari or Firefox
- You can't install extensions
- You want it to work on mobile
- You want a universal solution

Both provide the same features:
- ✅ Government website detection
- ✅ Auto-crawl 3 sublinks
- ✅ Simple summaries
- ✅ Multilingual support
- ✅ Copy & Read Aloud
