"""
Telegram Bot Server
Simple polling-based bot that works without webhooks
Much easier than WhatsApp - no ngrok needed!
Supports text and voice messages!
"""
import os
import asyncio
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode
from telegram_bot.message_handler import get_message_handler
from dotenv import load_dotenv

load_dotenv()

# Initialize message handler
message_handler = get_message_handler()

# ASEAN Countries
COUNTRIES = [
    "Malaysia", "Singapore", "Indonesia", "Thailand", "Vietnam",
    "Philippines", "Myanmar", "Cambodia", "Laos", "Brunei"
]

# Supported Languages
LANGUAGES = [
    "English", "Bahasa Melayu", "Bahasa Indonesia", "Thai",
    "Vietnamese", "Filipino/Tagalog", "Burmese", "Khmer", "Lao"
]

# Store user preferences temporarily (in production, use database)
user_preferences = {}


async def start_command(update: Update, context):
    """Handle /start command - show country selection"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "there"
    
    # Reset preferences
    user_preferences[user_id] = {}
    
    welcome_message = (
        f"👋 <b>Hi {user_name}! Welcome to Bridge AI Assistant!</b>\n\n"
        f"I'm your ASEAN government information assistant. I can help you with "
        f"questions about government services, passport renewal, "
        f"and official documents across Southeast Asia.\n\n"
        f"Before we proceed, I need to know:\n"
        f"📍 Your country\n"
        f"🗣️ Your preferred language\n\n"
        f"This helps me provide you with accurate information from the right "
        f"government sources in your language.\n\n"
        f"Let's get started! Please select your country:"
    )
    
    # Create inline keyboard with country buttons (2 per row)
    keyboard = []
    for i in range(0, len(COUNTRIES), 2):
        row = []
        row.append(InlineKeyboardButton(COUNTRIES[i], callback_data=f"country_{COUNTRIES[i]}"))
        if i + 1 < len(COUNTRIES):
            row.append(InlineKeyboardButton(COUNTRIES[i+1], callback_data=f"country_{COUNTRIES[i+1]}"))
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def button_callback(update: Update, context):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Initialize user preferences if not exists
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    
    # Handle country selection
    if data.startswith("country_"):
        country = data.replace("country_", "")
        user_preferences[user_id]['country'] = country
        
        # Update message and show language selection
        await query.edit_message_text(
            f"✅ Country: <b>{country}</b>\n\n"
            f"Now, please select your preferred language:",
            parse_mode=ParseMode.HTML
        )
        
        # Create inline keyboard with language buttons (2 per row)
        keyboard = []
        for i in range(0, len(LANGUAGES), 2):
            row = []
            row.append(InlineKeyboardButton(LANGUAGES[i], callback_data=f"lang_{LANGUAGES[i]}"))
            if i + 1 < len(LANGUAGES):
                row.append(InlineKeyboardButton(LANGUAGES[i+1], callback_data=f"lang_{LANGUAGES[i+1]}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "Select your language:",
            reply_markup=reply_markup
        )
    
    # Handle language selection
    elif data.startswith("lang_"):
        language = data.replace("lang_", "")
        user_preferences[user_id]['language'] = language
        
        country = user_preferences[user_id].get('country', 'Unknown')
        
        # Save to database
        telegram_user = update.effective_user
        user = message_handler.get_or_create_user(telegram_user)
        if user:
            # Update user preferences in database
            message_handler.mysql.ensure_connection()
            cursor = message_handler.mysql.connection.cursor()
            try:
                query_sql = "UPDATE users SET country = %s, language = %s WHERE user_id = %s"
                cursor.execute(query_sql, (country, language, user['user_id']))
                message_handler.mysql.connection.commit()
                print(f"✅ Updated preferences for user {user_id}: {country}, {language}")
            except Exception as e:
                print(f"❌ Error updating preferences: {e}")
            finally:
                cursor.close()
        
        # Update message handler's default country
        message_handler.default_country = country
        
        # Show completion message
        await query.edit_message_text(
            f"✅ Language: <b>{language}</b>",
            parse_mode=ParseMode.HTML
        )
        
        completion_message = (
            f"🎉 <b>Setup Complete!</b>\n\n"
            f"📍 Country: <b>{country}</b>\n"
            f"🌐 Language: <b>{language}</b>\n\n"
            f"I'm ready to help you with:\n"
            f"• Passport renewal\n"
            f"• Visa applications\n"
            f"• Government services\n"
            f"• Official documents\n"
            f"• And more!\n\n"
            f"Just send me your question!\n\n"
            f"<i>Example: How do I renew my passport?</i>\n\n"
            f"💡 Use /settings to change your preferences anytime."
        )
        
        await query.message.reply_text(
            completion_message,
            parse_mode=ParseMode.HTML
        )


async def settings_command(update: Update, context):
    """Handle /settings command - allow users to change preferences"""
    user_id = update.effective_user.id
    
    # Get current preferences
    current_country = user_preferences.get(user_id, {}).get('country', 'Not set')
    current_language = user_preferences.get(user_id, {}).get('language', 'Not set')
    
    message = (
        f"⚙️ <b>Your Current Settings:</b>\n\n"
        f"📍 Country: <b>{current_country}</b>\n"
        f"🌐 Language: <b>{current_language}</b>\n\n"
        f"What would you like to change?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌍 Change Country", callback_data="change_country")],
        [InlineKeyboardButton("🗣️ Change Language", callback_data="change_language")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def change_settings_callback(update: Update, context):
    """Handle settings change callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "change_country":
        # Show country selection
        keyboard = []
        for i in range(0, len(COUNTRIES), 2):
            row = []
            row.append(InlineKeyboardButton(COUNTRIES[i], callback_data=f"country_{COUNTRIES[i]}"))
            if i + 1 < len(COUNTRIES):
                row.append(InlineKeyboardButton(COUNTRIES[i+1], callback_data=f"country_{COUNTRIES[i+1]}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Select your country:",
            reply_markup=reply_markup
        )
    
    elif data == "change_language":
        # Show language selection
        keyboard = []
        for i in range(0, len(LANGUAGES), 2):
            row = []
            row.append(InlineKeyboardButton(LANGUAGES[i], callback_data=f"lang_{LANGUAGES[i]}"))
            if i + 1 < len(LANGUAGES):
                row.append(InlineKeyboardButton(LANGUAGES[i+1], callback_data=f"lang_{LANGUAGES[i+1]}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Select your language:",
            reply_markup=reply_markup
        )


async def help_command(update: Update, context):
    """Handle /help command"""
    help_message = (
        "🤖 <b>How to use Bridge:</b>\n\n"
        "Simply send me your question in plain text. I will:\n"
        "1. Search official government websites\n"
        "2. Extract relevant information\n"
        "3. Provide you with a clear answer\n"
        "4. Include reference links\n\n"
        "<b>Supported languages:</b>\n"
        "English, Bahasa Melayu, Bahasa Indonesia, Thai, Vietnamese, "
        "Filipino, and more!\n\n"
        "<b>Example questions:</b>\n"
        "• How to renew my passport?\n"
        "• What documents do I need for a visa?\n"
        "• How to replace my lost IC?\n"
        "• Where to apply for a work permit?"
    )
    await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)


async def handle_voice(update: Update, context):
    """Handle incoming voice messages using local Whisper model"""
    try:
        telegram_user = update.message.from_user
        user_id = telegram_user.id
        
        # Check if user has set preferences
        if user_id not in user_preferences or not user_preferences[user_id].get('country'):
            await update.message.reply_text(
                "👋 Welcome! Please use /start to set up your country and language preferences first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        print(f"\n{'='*50}")
        print(f"🎤 Incoming Voice Message")
        print(f"From: @{telegram_user.username or 'Unknown'} ({telegram_user.id})")
        print(f"{'='*50}\n")
        
        # Send "typing" indicator
        await update.message.chat.send_action("typing")
        
        # Download voice file
        voice = update.message.voice
        voice_file = await voice.get_file()
        
        # Show processing message
        await update.message.reply_text("🎤 Transcribing your voice message with local Whisper model...")
        
        # Use the message handler's voice processing method
        response = await message_handler.handle_voice(voice_file, telegram_user)
        
        # Send response
        MAX_LENGTH = 4096
        if len(response) > MAX_LENGTH:
            for i in range(0, len(response), MAX_LENGTH):
                chunk = response[i:i + MAX_LENGTH]
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        
        print(f"✅ Voice message processed for @{telegram_user.username or 'Unknown'}")
        
    except Exception as e:
        print(f"❌ Error handling voice message: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "Sorry, I encountered an error processing your voice message. "
            "Please try again or send your question as text."
        )


async def handle_document(update: Update, context):
    """Handle incoming document uploads"""
    try:
        telegram_user = update.message.from_user
        user_id = telegram_user.id
        
        # Check if user has set preferences
        if user_id not in user_preferences or not user_preferences[user_id].get('country'):
            await update.message.reply_text(
                "👋 Welcome! Please use /start to set up your country and language preferences first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        print(f"\n{'='*50}")
        print(f"📄 Incoming Document")
        print(f"From: @{telegram_user.username or 'Unknown'} ({telegram_user.id})")
        print(f"{'='*50}\n")
        
        # Send "typing" indicator
        await update.message.chat.send_action("typing")
        
        # Get document and caption
        document = update.message.document
        caption = update.message.caption
        
        # Show processing message
        await update.message.reply_text("📄 Processing your document...")
        
        # Use the message handler's document processing method
        response = await message_handler.handle_document(document, telegram_user, caption)
        
        # Send response
        MAX_LENGTH = 4096
        if len(response) > MAX_LENGTH:
            for i in range(0, len(response), MAX_LENGTH):
                chunk = response[i:i + MAX_LENGTH]
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        
        print(f"✅ Document processed for @{telegram_user.username or 'Unknown'}")
        
    except Exception as e:
        print(f"❌ Error handling document: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "Sorry, I encountered an error processing your document. "
            "Please try again."
        )


async def handle_photo(update: Update, context):
    """Handle incoming photo uploads"""
    try:
        telegram_user = update.message.from_user
        user_id = telegram_user.id
        
        # Check if user has set preferences
        if user_id not in user_preferences or not user_preferences[user_id].get('country'):
            await update.message.reply_text(
                "👋 Welcome! Please use /start to set up your country and language preferences first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        print(f"\n{'='*50}")
        print(f"🖼️ Incoming Photo")
        print(f"From: @{telegram_user.username or 'Unknown'} ({telegram_user.id})")
        print(f"{'='*50}\n")
        
        # Send "typing" indicator
        await update.message.chat.send_action("typing")
        
        # Get the largest photo (best quality)
        photo = update.message.photo[-1]
        caption = update.message.caption
        
        # Show processing message
        await update.message.reply_text("🖼️ Analyzing your image...")
        
        # Use the message handler's photo processing method
        response = await message_handler.handle_photo(photo, telegram_user, caption)
        
        # Send response
        MAX_LENGTH = 4096
        if len(response) > MAX_LENGTH:
            for i in range(0, len(response), MAX_LENGTH):
                chunk = response[i:i + MAX_LENGTH]
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        
        print(f"✅ Photo processed for @{telegram_user.username or 'Unknown'}")
        
    except Exception as e:
        print(f"❌ Error handling photo: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "Sorry, I encountered an error processing your photo. "
            "Please try again."
        )


async def handle_message(update: Update, context):
    """Handle incoming text messages"""
    try:
        # Get message text and user info
        message_text = update.message.text
        telegram_user = update.message.from_user
        user_id = telegram_user.id
        
        # Check if user has set preferences
        if user_id not in user_preferences or not user_preferences[user_id].get('country'):
            await update.message.reply_text(
                "👋 Welcome! Please use /start to set up your country and language preferences first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Get user preferences
        country = user_preferences[user_id].get('country', 'Malaysia')
        language = user_preferences[user_id].get('language', 'English')
        
        # Update message handler with user's country
        message_handler.default_country = country
        
        print(f"\n{'='*50}")
        print(f"📨 Incoming Telegram Message")
        print(f"From: @{telegram_user.username or 'Unknown'} ({telegram_user.id})")
        print(f"Country: {country}, Language: {language}")
        print(f"Content: {message_text}")
        print(f"{'='*50}\n")
        
        # Send "typing" indicator
        await update.message.chat.send_action("typing")
        
        # Process message using existing handler (pass language for URL summarization)
        response = await message_handler.handle_message(message_text, telegram_user, language)
        
        # Send response (Telegram supports HTML formatting and long messages!)
        # Split if longer than 4096 characters (Telegram's limit)
        MAX_LENGTH = 4096
        if len(response) > MAX_LENGTH:
            # Send in chunks
            for i in range(0, len(response), MAX_LENGTH):
                chunk = response[i:i + MAX_LENGTH]
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.5)  # Small delay between messages
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        
        print(f"✅ Response sent to @{telegram_user.username or 'Unknown'}")
        
    except Exception as e:
        print(f"❌ Error handling message: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again later."
        )


async def error_handler(update: Update, context):
    """Handle errors"""
    print(f"❌ Error: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "Sorry, something went wrong. Please try again."
        )


def main():
    """Start the bot"""
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file!")
        print("\nTo create a bot:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the token and add to .env:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    print("\n" + "="*60)
    print("🚀 Bridge Telegram Bot Starting...")
    print("="*60)
    print(f"🤖 Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    print("📡 Mode: Polling (no webhook needed!)")
    print("="*60 + "\n")
    
    # Create application
    app = Application.builder().token(bot_token).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(country_|lang_)"))
    app.add_handler(CallbackQueryHandler(change_settings_callback, pattern="^change_"))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))  # Voice messages
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # Documents (PDF, DOCX, etc.)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Photos/Images
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Text messages
    app.add_error_handler(error_handler)
    
    # Start polling
    print("✅ Bot is running! Press Ctrl+C to stop.\n")
    print("📱 To test:")
    print("1. Open Telegram")
    print("2. Search for your bot by username")
    print("3. Send /start")
    print("4. Ask a question!\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
