# Testing Guide - How to Know If It Works

## Step 1: Start the Flask Server

```bash
cd vhack2026-live-translator
python summarizer_web.py
```

**✅ Success indicators:**
- You see: "Server starting..."
- You see: "Open your browser and go to: http://localhost:5000"
- No error messages

**❌ If it fails:**
- Check if port 5000 is already in use
- Make sure you have all dependencies installed

---

## Step 2: Load Extension in Opera/Chrome

1. Open Opera and go to: `opera://extensions/`
   - Or Chrome: `chrome://extensions/`
   - Or Brave: `brave://extensions/`
   - Or Edge: `edge://extensions/`

2. Enable "Developer mode" (toggle in top right corner)

3. Click "Load unpacked"

4. Navigate to and select: `vhack2026-live-translator/browser-extension` folder

**✅ Success indicators:**
- Extension appears in the list
- No error messages
- You see "Bridge - Government Website Summarizer"
- Icon shows up in your toolbar

**❌ If it fails:**
- Check for error messages
- Make sure all icon files exist in `icons/` folder
- Try reloading the extension

---

## Step 3: Test on a Government Website

Visit any ASEAN government website, for example:
- Malaysia: https://www.gov.my
- Singapore: https://www.gov.sg
- Indonesia: https://www.go.id

**✅ Success indicators:**
1. **Floating button appears** in bottom-right corner saying "Summarize This Page"
2. **Button is purple/gradient colored**
3. **Button has a document icon 📄**

**❌ If button doesn't appear:**
- Open browser DevTools (F12)
- Check Console tab for errors
- Make sure the URL contains `.gov.my`, `.gov.sg`, `.go.id`, etc.

---

## Step 4: Generate a Summary

1. Click the "Summarize This Page" button

**✅ Success indicators:**
1. **Loading panel appears** with spinning animation
2. Shows message: "Generating summary..."
3. Shows: "Crawling 3 sublinks for comprehensive summary"

**After 10-30 seconds:**
4. **Summary panel appears** with:
   - Title: "Bridge Summary"
   - Word count stats (e.g., "5000 words → 150 words")
   - Bullet-point summary in simple language
   - "Copy" and "Read Aloud" buttons at bottom

**❌ If it fails:**
- Check if Flask server is still running
- Look for error message in the panel
- Check browser DevTools Console for errors
- Verify your API keys in `.env` file

---

## Step 5: Test Features

### Test Copy Button
1. Click "📋 Copy" button
2. Button should change to "✓ Copied!"
3. Paste somewhere (Ctrl+V) - you should see the summary text

### Test Read Aloud
1. Click "🔊 Read Aloud" button
2. You should hear the summary being read out loud
3. (Make sure your volume is on!)

### Test Close Button
1. Click the "×" button in top-right of panel
2. Panel should disappear

---

## Quick Visual Checklist

When everything works, you should see:

```
┌─────────────────────────────────────┐
│  Government Website (e.g. gov.my)  │
│                                     │
│  [Your normal webpage content]     │
│                                     │
│                                     │
│                          ┌─────────┐│
│                          │ 📄      ││
│                          │Summarize││
│                          │This Page││
│                          └─────────┘│
└─────────────────────────────────────┘
```

After clicking:

```
┌──────────────────────────┐
│ Bridge Summary        × │
│ 5000 → 150 words        │
├──────────────────────────┤
│                          │
│ • Point 1...             │
│ • Point 2...             │
│ • Point 3...             │
│                          │
├──────────────────────────┤
│ [📋 Copy] [🔊 Read Aloud]│
└──────────────────────────┘
```

---

## Troubleshooting

### Button doesn't appear
- **Check URL**: Must be a government domain (.gov.my, .gov.sg, etc.)
- **Check Console**: Press F12, look for JavaScript errors
- **Reload page**: Try refreshing the page

### "Server offline" error
- **Check Flask**: Make sure `python summarizer_web.py` is running
- **Check port**: Visit http://localhost:5000 in browser - should show web interface
- **Check firewall**: Make sure port 5000 isn't blocked

### Summary generation fails
- **Check API keys**: Open `.env` file, verify GEMINI_API_KEY and FIRECRAWL_API_KEY
- **Check internet**: Make sure you're connected
- **Check Flask logs**: Look at terminal where Flask is running for error messages

### Icons don't load
- **Check files exist**: Look in `browser-extension/icons/` folder
- **Should have**: icon16.png, icon48.png, icon128.png
- **Recreate**: Run `python create_icons.py` from vhack2026-live-translator folder

---

## Test Websites

Good test sites (ASEAN government websites):

1. **Malaysia**: https://www.gov.my
2. **Singapore**: https://www.gov.sg  
3. **Indonesia**: https://www.go.id
4. **Thailand**: https://www.go.th
5. **Philippines**: https://www.gov.ph

---

## Expected Behavior Summary

| Action | Expected Result | Time |
|--------|----------------|------|
| Visit gov website | Button appears | Instant |
| Click button | Loading panel shows | Instant |
| Wait | Summary generates | 10-30 sec |
| Summary appears | Clean panel with bullets | Instant |
| Click Copy | Text copied to clipboard | Instant |
| Click Read Aloud | Audio plays | Instant |
| Click × | Panel closes | Instant |

---

## Still Not Working?

1. Check Flask server terminal for errors
2. Check browser DevTools Console (F12)
3. Verify all files exist in browser-extension folder
4. Try reloading the extension
5. Try a different government website
6. Make sure your API keys are valid
