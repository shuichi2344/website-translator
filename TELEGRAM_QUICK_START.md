# Telegram Bot - Quick Start Guide

## ⚡ 5-Minute Setup (Much Easier Than WhatsApp!)

### 1️⃣ Create Your Bot

1. Open Telegram on your phone/computer
2. Search for **@BotFather**
3. Send `/newbot`
4. Choose a name: `Bridge AI Assistant`
5. Choose a username: `your_bridge_bot` (must end with 'bot')
6. Copy the token you receive (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2️⃣ Install Dependencies

```bash
pip install python-telegram-bot==21.0
```

### 3️⃣ Configure Token

Add to your `.env` file:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 4️⃣ Start Bot

```bash
python telegram_bot_server.py
```

You should see:
```
🚀 Bridge Telegram Bot Starting...
🤖 Bot Token: 123456789:...
📡 Mode: Polling (no webhook needed!)
✅ Bot is running!
```

### 5️⃣ Test It!

1. Open Telegram
2. Search for your bot username (e.g., `@your_bridge_bot`)
3. Click **Start**
4. Send: `How do I renew my passport?`
5. Get instant response with reference links!

---

## 🎉 That's It!

No webhook needed! No ngrok! No Cloudflare tunnel! Just works!

---

## 🎯 What You Get

✅ **Real Government Data** - Fetches fresh info from official websites  
✅ **Reference Links** - Clickable URLs in responses  
✅ **Multi-language** - Automatic language detection  
✅ **Voice Messages** - Send voice, get text response (local Whisper model)  
✅ **URL Summarization** - Send any website URL, get instant summary  
✅ **Document Q&A** - Upload PDF/DOCX, ask questions about it  
✅ **Image Analysis** - Send photos, get AI-powered descriptions (Gemini Vision)  
✅ **Message History** - Stored in MySQL  
✅ **HTML Formatting** - Bold, italic, links work!  
✅ **Long Messages** - Up to 4096 characters (vs WhatsApp's 1600)  
✅ **Completely Free** - No costs, no limits  
✅ **No Sandbox** - Works immediately for everyone  

---

## 📊 How It Works

```
User sends message
    ↓
Telegram delivers to your bot
    ↓
Bot checks ChromaDB for cached data
    ↓
If no cache: Fetch from government websites
    ├─ Search with SerpAPI
    ├─ Scrape with Firecrawl
    └─ Generate answer with Gemini
    ↓
Add clickable reference links
    ↓
Send response to user
```

---

## 🔧 Commands

- `/start` - Welcome message with country/language selection
- `/help` - How to use the bot
- `/settings` - Change your country and language preferences
- Just send any question - Get answer with sources!
- 🎤 Send voice message - Transcribed using local Whisper model
- 🔗 Send website URL - Get instant summary in your language
- 🔗 Send URL + question - Get answer based on URL content
- 📄 Send document (PDF/DOCX) - Get summary or ask questions
- 🖼️ Send photo/image - Get AI analysis with Gemini Vision

---

## 💡 Advantages Over WhatsApp

| Feature | Telegram | WhatsApp |
|---------|----------|----------|
| Setup Time | 5 minutes | 30+ minutes |
| Webhook Needed | ❌ No | ✅ Yes |
| ngrok/Tunnel | ❌ No | ✅ Yes |
| Sandbox | ❌ No | ✅ Yes |
| User Limit | ♾️ Unlimited | Limited |
| Message Length | 4096 chars | 1600 chars |
| HTML Formatting | ✅ Yes | ❌ No |
| Clickable Links | ✅ Yes | ✅ Yes |
| Voice Messages | ✅ Yes (local) | ✅ Yes (local) |
| URL Summarization | ✅ Yes | ❌ No |
| Cost | 💰 Free | 💰 Paid after 1000 |
| Approval Needed | ❌ No | ✅ Yes (production) |

---

## 🐛 Troubleshooting

### Bot not responding?
- Check if `telegram_bot_server.py` is running
- Verify token in `.env` is correct
- Make sure you clicked "Start" in Telegram

### "Token not found" error?
- Add `TELEGRAM_BOT_TOKEN` to `.env`
- Get token from @BotFather
- Restart the server

### No government data?
- Check `SERP_API_KEY` is set
- Check `FIRECRAWL_API_KEY` is set
- Check `GEMINI_API_KEY` is set

---

## 🚀 Production Deployment

Telegram bot can run anywhere:

**Option 1: Your Computer**
- Just keep `telegram_bot_server.py` running
- No public URL needed!

**Option 2: Cloud Server**
- Deploy to any VPS
- Run with `nohup python telegram_bot_server.py &`
- Or use systemd service

**Option 3: Heroku/Railway**
- Add `Procfile`: `worker: python telegram_bot_server.py`
- Deploy and forget!

---

## 📝 Example Conversation

```
You: /start
Bot: 👋 Hi [Your Name]! Welcome to Bridge AI Assistant!
     Before we proceed, I need to know:
     📍 Your country
     🗣️ Your preferred language
     [Shows country selection buttons]

You: [Select Malaysia]
Bot: ✅ Country: Malaysia
     [Shows language selection buttons]

You: [Select English]
Bot: 🎉 Setup Complete!
     📍 Country: Malaysia
     🌐 Language: English
     Just send me your question!

You: How do I renew my passport?
Bot: To renew your passport, visit the nearest 
     immigration office with your current passport...
     
     📚 References:
     1. https://www.imi.gov.my/...
     2. https://www.kln.gov.my/...

You: 🎤 [Voice message: "What documents do I need?"]
Bot: 🎤 You said: "What documents do I need?"
     
     You need:
     • Current passport
     • Identity card
     • Two passport photos
     • RM200 fee
     
     📚 References:
     1. https://www.imi.gov.my/...

You: https://www.imi.gov.my/passport-renewal
Bot: 🌐 Summary of https://www.imi.gov.my/passport-renewal
     
     📊 2,450 words → 245 words (90% shorter)
     
     [Detailed summary of the webpage in your language]

You: https://www.imi.gov.my/passport-renewal
     What is the processing time?
Bot: 🌐 Answer from https://www.imi.gov.my/passport-renewal
     
     ❓ What is the processing time?
     
     The processing time for passport renewal is typically
     7-14 working days for normal processing. Express service
     is available for urgent cases with 2-3 working days
     processing time at an additional fee.
     
     📚 Relevant sections:
     1. Processing times vary depending on the type...
     2. Express service is available at selected...

You: [Upload passport_form.pdf]
Bot: 📄 Summary of passport_form.pdf
     
     📊 1,200 words → 120 words (90% shorter)
     
     [Summary of the document]
     
     💡 You can now ask me questions about this document!

You: What documents are required?
Bot: 📄 Answer from passport_form.pdf
     
     ❓ What documents are required?
     
     According to the form, you need:
     • Original passport
     • MyKad (IC)
     • Two passport-sized photos
     • Payment receipt
     
     📚 Relevant sections:
     1. Section 3: Required Documents...

You: [Upload photo of IC]
Bot: 🖼️ Image Analysis
     
     ❓ What is in this image?
     
     This is a Malaysian Identity Card (MyKad). It shows
     personal information including name, IC number, address,
     and photo. The card appears to be valid and in good
     condition.
     
     💡 You can ask me more questions about this image!
```

---

## 🎨 Customization

Edit `telegram_bot_server.py` to:
- Change welcome message
- Add more commands
- Customize response format
- Add inline buttons
- Send photos/documents

---

## 📚 Full Documentation

- **Quick start**: `TELEGRAM_QUICK_START.md` (this file)
- **WhatsApp comparison**: `WHATSAPP_QUICK_START.md`
- **Architecture**: `WHATSAPP_ARCHITECTURE.md` (same backend)

---

**Ready? Just follow steps 1-5 above!** 🚀

*Much easier than WhatsApp, right?* 😊
