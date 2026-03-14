# What to Expect - Visual Guide

## ✅ How to Know If It Works

### Step 1: Run the Test Script

```bash
cd vhack2026-live-translator
python test_extension.py
```

**You should see:**
- ✅ All green checkmarks
- ✅ "ALL CHECKS PASSED!"
- ✅ Flask server is running

---

### Step 2: Load Extension in Opera

1. Open Opera
2. Type in address bar: `opera://extensions/`
3. Turn ON "Developer mode" (top right)
4. Click "Load unpacked" button
5. Select folder: `vhack2026-live-translator/browser-extension`

**You should see:**
- Extension card appears with name "Bridge - Government Website Summarizer"
- Purple document icon
- Version 1.0.0
- NO error messages

---

### Step 3: Visit a Government Website

Open any of these in Opera:
- https://www.gov.my
- https://www.gov.sg
- https://www.go.id

**Within 1-2 seconds, you should see:**

A purple floating button in the BOTTOM-RIGHT corner that says:
```
┌─────────────────────┐
│ 📄 Summarize This   │
│    Page             │
└─────────────────────┘
```

**If you DON'T see the button:**
- The website might not be recognized as a government site
- Check browser console (F12) for errors
- Try refreshing the page

---

### Step 4: Click the Button

**Immediately after clicking, you should see:**

A panel appears in the TOP-RIGHT with:
```
┌──────────────────────────────┐
│ Bridge Summary            × │
├──────────────────────────────┤
│                              │
│    [Spinning animation]      │
│                              │
│  Generating summary...       │
│  Crawling 3 sublinks for     │
│  comprehensive summary       │
│                              │
└──────────────────────────────┘
```

**This means:**
- ✅ Extension is working
- ✅ Communicating with Flask server
- ✅ Processing the website

---

### Step 5: Wait 10-30 Seconds

**After processing, you should see:**

```
┌──────────────────────────────────┐
│ Bridge Summary                × │
│ 5000 words → 150 words           │
├──────────────────────────────────┤
│                                  │
│ • This website talks about...    │
│ • The main services include...   │
│ • You can find information...    │
│ • Important links are...         │
│ • Contact details are...         │
│                                  │
├──────────────────────────────────┤
│  [📋 Copy]    [🔊 Read Aloud]    │
└──────────────────────────────────┘
```

**This means:**
- ✅ Summary generated successfully!
- ✅ AI processed the content
- ✅ Everything is working!

---

### Step 6: Test the Buttons

**Click "📋 Copy":**
- Button changes to "✓ Copied!"
- Open Notepad and press Ctrl+V
- You should see the summary text

**Click "🔊 Read Aloud":**
- You should HEAR the summary being read
- (Make sure your volume is on!)

**Click "×" (close button):**
- Panel disappears
- Button remains in bottom-right

---

## 🎯 Success Checklist

You know it's working when:

- [ ] Test script shows all green checkmarks
- [ ] Extension loads without errors in Opera
- [ ] Purple button appears on government websites
- [ ] Clicking button shows loading animation
- [ ] Summary appears after 10-30 seconds
- [ ] Summary has 5 bullet points in simple language
- [ ] Copy button works
- [ ] Read Aloud button works
- [ ] Close button works

---

## ❌ Common Issues

### Button doesn't appear
**Cause:** Not a government website
**Fix:** Make sure URL contains `.gov.my`, `.gov.sg`, `.go.id`, etc.

### "Server offline" error
**Cause:** Flask not running
**Fix:** Run `python summarizer_web.py` in terminal

### Summary takes forever
**Cause:** Slow internet or API rate limits
**Fix:** Wait up to 60 seconds, or check API keys

### Extension won't load
**Cause:** Missing files or icon errors
**Fix:** Run `python test_extension.py` to check setup

---

## 📸 Screenshots Reference

### What the button looks like:
- Position: Bottom-right corner
- Color: Purple gradient
- Icon: 📄 document emoji
- Text: "Summarize This Page"
- Shape: Rounded pill shape
- Hover: Slightly grows when you hover over it

### What the summary panel looks like:
- Position: Top-right corner
- Size: About 450px wide
- Header: Purple gradient with "Bridge Summary"
- Content: White background with bullet points
- Footer: Two buttons (Copy and Read Aloud)
- Close: × button in top-right of panel

---

## 🚀 Quick Test Command

Run this to verify everything:

```bash
cd vhack2026-live-translator
python test_extension.py
```

If you see "ALL CHECKS PASSED!" - you're ready to test in the browser!
