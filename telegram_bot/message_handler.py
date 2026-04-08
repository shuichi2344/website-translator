"""
Telegram Message Handler
Processes incoming messages and generates responses using existing Bridge engine
Reuses the same logic as WhatsApp bot
"""
import re
import os
import time
import tempfile
import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from engine.database.mysql_handler import MySQLHandler
from engine.database.rag_integration import RAGIntegration
from engine.speech.response_gen import generate_final_response, get_dialect_from_language
from engine.speech.government_mapping import find_specific_gov_links, get_country_suffix
from engine.speech.web_scraping import get_chunks_from_list
from engine.search.speech_to_text import transcribe_audio
from engine.search.document_summariser_v6_gemini import DocumentSummarizer


class TelegramMessageHandler:
    def __init__(self):
        self.mysql = MySQLHandler()
        self.rag = RAGIntegration()
        
        # Default country for government searches
        self.default_country = "Malaysia"
        
        # Store uploaded documents per user (in-memory cache)
        # Structure: {user_id: {'file_path': str, 'file_type': str, 'timestamp': float, 'extracted_text': str, 'processing': bool}}
        self.user_documents = {}
        
        # Thread pool for background processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache for document extractions (avoid re-processing)
        self.extraction_cache = {}  # {file_path: {'text': str, 'timestamp': float}}
        
        # Language detection keywords for common ASEAN languages
        self.language_keywords = {
            "Bahasa Melayu": ["saya", "apa", "bagaimana", "boleh", "terima kasih"],
            "Bahasa Indonesia": ["saya", "apa", "bagaimana", "bisa", "terima kasih"],
            "Thai": ["สวัสดี", "ขอบคุณ", "อะไร", "ที่ไหน"],
            "Vietnamese": ["xin chào", "cảm ơn", "gì", "ở đâu"],
            "Filipino/Tagalog": ["salamat", "ano", "saan", "paano"],
        }
    
    def extract_user_id(self, telegram_user) -> str:
        """Extract user ID from Telegram user object"""
        return str(telegram_user.id)
    
    def detect_language(self, text: str) -> str:
        """Simple language detection based on keywords"""
        text_lower = text.lower()
        
        for language, keywords in self.language_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return language
        
        # Default to English
        return "English"
    
    def extract_urls(self, text: str) -> list:
        """Extract URLs from text"""
        # Regex pattern for URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def _extract_document_text_sync(self, file_path: str, lang_code: str = "en") -> Optional[str]:
        """Synchronous document text extraction (runs in thread pool)"""
        try:
            # Check cache first
            if file_path in self.extraction_cache:
                cached = self.extraction_cache[file_path]
                # Cache valid for 30 minutes
                if time.time() - cached['timestamp'] < 1800:
                    print(f"✅ Using cached extraction for {file_path}")
                    return cached['text']
            
            print(f"📄 Extracting text from document...")
            summarizer = DocumentSummarizer(target_lang=lang_code)
            text = summarizer.extract_text_from_document(file_path)
            
            if text:
                # Cache the extraction
                self.extraction_cache[file_path] = {
                    'text': text,
                    'timestamp': time.time()
                }
                print(f"✅ Text extracted: {len(text)} characters")
                return text
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting document text: {e}")
            return None
    
    async def _extract_document_background(self, user_id: str, file_path: str, lang_code: str = "en"):
        """Extract document text in background (non-blocking)"""
        try:
            if user_id not in self.user_documents:
                return
            
            # Mark as processing
            self.user_documents[user_id]['processing'] = True
            
            # Run extraction in thread pool (non-blocking)
            loop = asyncio.get_event_loop()
            extracted_text = await loop.run_in_executor(
                self.executor,
                self._extract_document_text_sync,
                file_path,
                lang_code
            )
            
            # Store extracted text
            if user_id in self.user_documents and extracted_text:
                self.user_documents[user_id]['extracted_text'] = extracted_text
                self.user_documents[user_id]['processing'] = False
                print(f"✅ Background extraction complete for user {user_id}")
            
        except Exception as e:
            print(f"❌ Error in background extraction: {e}")
            if user_id in self.user_documents:
                self.user_documents[user_id]['processing'] = False
    
    def summarize_url(self, url: str, language: str = "English") -> Dict[str, Any]:
        """
        Summarize a website URL
        
        Args:
            url: Website URL to summarize
            language: Target language for summary
        
        Returns:
            Dictionary with summary and metadata
        """
        try:
            print(f"🌐 Summarizing URL: {url}")
            
            # Map language to code
            lang_map = {
                "English": "en",
                "Bahasa Melayu": "ms",
                "Bahasa Indonesia": "id",
                "Thai": "th",
                "Vietnamese": "vi",
                "Filipino/Tagalog": "tl",
                "Burmese": "my",
                "Khmer": "km",
                "Lao": "lo"
            }
            lang_code = lang_map.get(language, "en")
            
            # Use DocumentSummarizer to process the website
            summarizer = DocumentSummarizer(target_lang=lang_code)
            result = summarizer.process_website(url, crawl_depth=0, max_sublinks=3)
            
            if result and result.get('summary'):
                print(f"✅ URL summarized successfully")
                return {
                    'success': True,
                    'summary': result['summary'],
                    'word_count': result.get('word_count', 0),
                    'summary_word_count': result.get('summary_word_count', 0),
                    'url': url
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not extract content from URL'
                }
                
        except Exception as e:
            print(f"❌ Error summarizing URL: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_or_create_user(self, telegram_user) -> Dict[str, Any]:
        """Get existing user or create new one"""
        telegram_id = str(telegram_user.id)
        email = f"telegram_{telegram_id}@bridge.local"
        
        # Check if user exists
        user = self.mysql.get_user_by_email(email)
        
        if user:
            return user
        
        # Create new user
        username = telegram_user.username or f"User{telegram_id[-4:]}"
        full_name = f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip()
        
        user_id = self.mysql.create_user(
            name=full_name or f"Telegram User {telegram_id[-4:]}",
            email=email,
            password_hash="telegram_auth",  # Not used for Telegram users
            country="Unknown",
            language="en"
        )
        
        if user_id:
            print(f"✅ New Telegram user created: {username} ({telegram_id})")
            return self.mysql.get_user_by_email(email)
        
        return None
    
    def get_or_create_conversation(self, user_id: str) -> str:
        """Get active conversation or create new one"""
        # Get user's conversations
        conversations = self.mysql.get_user_conversations(user_id)
        
        if conversations:
            # Return most recent conversation
            return conversations[0]['conversation_id']
        
        # Create new conversation
        conversation_id = self.mysql.create_conversation(
            user_id=user_id,
            title="Telegram Chat"
        )
        
        return conversation_id
    
    def fetch_government_data(self, query: str, country: str = None) -> dict:
        """
        Fetch fresh government data for a query (same as WhatsApp bot)
        
        Args:
            query: User's question
            country: Country name (defaults to Malaysia)
        
        Returns:
            Dictionary with 'chunks' and 'sources' keys
        """
        try:
            country = country or self.default_country
            country_suffix = get_country_suffix(country)
            
            print(f"🔍 Searching government websites for: {query}")
            
            # Find relevant government links using SerpAPI
            gov_links = find_specific_gov_links(query, country_suffix)
            
            if not gov_links:
                print("⚠️ No government links found")
                return {"chunks": [], "sources": []}
            
            print(f"✅ Found {len(gov_links)} government links")
            
            # Scrape content from government websites using Firecrawl
            chunks = get_chunks_from_list(gov_links)
            
            print(f"✅ Extracted {len(chunks)} chunks from government websites")
            return {"chunks": chunks, "sources": gov_links}
            
        except Exception as e:
            print(f"❌ Error fetching government data: {e}")
            return {"chunks": [], "sources": []}
    
    def _generate_simple_response(self, user_question: str, relevant_chunks: list, dialect: str) -> str:
        """
        Generate a simple, child-friendly response for Telegram bot
        Uses the same style as document summarizer (explain like to a 10-year-old)
        """
        try:
            from google import genai
            from google.genai import types
            
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                # Fallback to original method
                return generate_final_response(user_question, relevant_chunks, dialect)
            
            client = genai.Client(api_key=api_key)
            
            # Combine chunks into context
            context = "\n---\n".join(relevant_chunks)
            
            prompt = f"""You are Bridge, the ASEAN government information assistant.
Answer the user's question based ONLY on the provided government information.

TARGET LANGUAGE: {dialect}
USER QUESTION: {user_question}

GOVERNMENT INFORMATION:
{context}

IMPORTANT - Write like you're explaining to a 10-year-old child:
- YES/NO FIRST: If the user is asking a closed-ended question, start the response with a clear "Yes" or "No" in the target language.
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences SHORT and SIMPLE (maximum 15-20 words per sentence)
- Explain what things DO, not what they're called
- If you must use a technical term, explain it in simple words right after
- Focus on the MAIN IDEAS only - skip minor details
- You can use bullet points (•) for lists
- Do NOT include titles, headers, or bold text (**)
- Do NOT write intro text like "Here are the bullet points"
- LANGUAGE: Respond ENTIRELY in {dialect}. Do not mix languages.
- NO WEBSITES OR URLS: Do not mention any URLs
- STOP when done - no polite closings like "hope this helps"

Answer (in simple, clear {dialect}):"""
            
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )
            
            if response and response.text:
                # Clean up any markdown formatting
                clean_text = response.text.replace('**', '').replace('*', '').replace('__', '').replace('#', '').strip()
                return clean_text
            
            # Fallback to original method
            return generate_final_response(user_question, relevant_chunks, dialect)
            
        except Exception as e:
            print(f"⚠️ Error in simple response generation: {e}")
            # Fallback to original method
            return generate_final_response(user_question, relevant_chunks, dialect)
    
    async def handle_message(self, message_text: str, telegram_user, user_language: str = "English") -> str:
        """
        Main handler for incoming Telegram messages
        Supports:
        - Regular questions (searches government data)
        - URL only (summarizes the URL)
        - URL + question (answers question based on URL content)
        
        Args:
            message_text: The text message from user
            telegram_user: Telegram user object
            user_language: User's preferred language
        
        Returns:
            Response text to send back
        """
        try:
            # Extract user info
            telegram_id = str(telegram_user.id)
            username = telegram_user.username or "Unknown"
            print(f"📱 Message from: {username} ({telegram_id})")
            
            # Check if user has an uploaded document/image and this is a follow-up question
            if telegram_id in self.user_documents:
                doc_info = self.user_documents[telegram_id]
                # Check if document is recent (within last 30 minutes)
                if time.time() - doc_info['timestamp'] < 1800:
                    print(f"📎 User has uploaded {doc_info['file_type']}: {doc_info['file_name']}")
                    
                    # Check if this message is a question (not a URL)
                    urls = self.extract_urls(message_text)
                    if not urls and len(message_text.strip()) > 3:
                        print(f"💬 Processing as follow-up question about uploaded {doc_info['file_type']}")
                        
                        if doc_info['file_type'] == 'document':
                            return await self._process_document_qa(telegram_id, message_text, telegram_user)
                        elif doc_info['file_type'] == 'image':
                            return await self._process_image_analysis(telegram_id, message_text, telegram_user)
                else:
                    # Document expired, remove it
                    print(f"🗑️ Removing expired document for user {telegram_id}")
                    try:
                        if os.path.exists(doc_info['file_path']):
                            os.remove(doc_info['file_path'])
                    except:
                        pass
                    del self.user_documents[telegram_id]
            
            # Check if message contains URLs
            urls = self.extract_urls(message_text)
            
            if urls:
                # Remove URLs from the message to get the question
                question_text = message_text
                for url in urls:
                    question_text = question_text.replace(url, "").strip()
                
                # Clean up extra whitespace
                question_text = " ".join(question_text.split())
                
                print(f"🔗 Detected {len(urls)} URL(s) in message")
                
                # If there's a question along with the URL, do Q&A
                if question_text and len(question_text) > 3:
                    print(f"❓ Question detected: {question_text}")
                    return self._handle_url_qa(urls, question_text, user_language)
                else:
                    # No question, just summarize the URLs
                    print(f"📄 No question detected, summarizing URLs")
                    return self._handle_url_summary(urls, user_language)
            
            # Regular message handling (no URLs)
            # Get or create user
            user = self.get_or_create_user(telegram_user)
            if not user:
                return "Sorry, there was an error processing your request. Please try again."
            
            user_id = user['user_id']
            
            # Get or create conversation
            conversation_id = self.get_or_create_conversation(user_id)
            
            # Save user message to database
            self.rag.save_user_message(conversation_id, message_text)
            
            # Detect language
            detected_language = self.detect_language(message_text)
            dialect = get_dialect_from_language(detected_language)
            
            # Get relevant context using RAG
            context = self.rag.get_context_for_response(
                query=message_text,
                conversation_id=conversation_id,
                include_history=True
            )
            
            # Extract relevant chunks for response generation
            relevant_chunks = []
            if context['relevant_messages']:
                for msg in context['relevant_messages']:
                    if msg['sender'] == 'bot':
                        relevant_chunks.append(msg['message_text'])
            
            # If no relevant context, fetch fresh data from government websites
            sources = []
            fetched_fresh_data = False  # Track if we fetched new data
            
            if not relevant_chunks:
                print("📡 No cached context found, fetching fresh government data...")
                gov_data = self.fetch_government_data(message_text, self.default_country)
                relevant_chunks = gov_data["chunks"]
                sources = gov_data["sources"]
                fetched_fresh_data = bool(sources)  # Only true if we got sources
                
                # If still no data, use fallback message
                if not relevant_chunks:
                    relevant_chunks = [
                        "I'm Bridge, your ASEAN government information assistant. "
                        "I can help you with questions about government services, documents, and procedures. "
                        "However, I couldn't find specific information about your question. "
                        "Please try rephrasing or ask about common topics like passport renewal, visa applications, or government services."
                    ]
            
            # Generate response using simple, child-friendly style
            response = self._generate_simple_response(
                user_question=message_text,
                relevant_chunks=relevant_chunks,
                dialect=dialect
            )
            
            # Only add sources if we actually fetched fresh government data
            # Don't add for greetings, casual chat, or cached responses
            if sources and fetched_fresh_data:
                response += "\n\n📚 <b>References:</b>"
                for i, source in enumerate(sources, 1):
                    response += f"\n{i}. {source}"
            
            # Save bot response
            self.rag.save_bot_message(conversation_id, response)
            
            print(f"✅ Response generated for {username}")
            return response
            
        except Exception as e:
            print(f"❌ Error handling message: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I encountered an error. Please try again later."
    
    def _handle_url_summary(self, urls: list, language: str) -> str:
        """Handle URL-only messages (no question) - summarize the URLs"""
        summaries = []
        for url in urls[:3]:  # Limit to 3 URLs
            result = self.summarize_url(url, language)
            if result['success']:
                reduction = 0
                if result['word_count'] > 0:
                    reduction = int(100 - (result['summary_word_count'] / result['word_count'] * 100))
                
                summary_text = (
                    f"🌐 <b>Summary of {url}</b>\n\n"
                    f"📊 {result['word_count']} words → {result['summary_word_count']} words ({reduction}% shorter)\n\n"
                    f"{result['summary']}"
                )
                summaries.append(summary_text)
            else:
                summaries.append(f"⚠️ Could not summarize {url}: {result.get('error', 'Unknown error')}")
        
        if summaries:
            return "\n\n" + "─" * 30 + "\n\n".join(summaries)
        else:
            return "Sorry, I couldn't summarize any of the URLs you provided."
    
    def _handle_url_qa(self, urls: list, question: str, language: str) -> str:
        """Handle URL + question messages - answer question based on URL content"""
        try:
            print(f"💬 Answering question based on URL content")
            
            # Map language to code
            lang_map = {
                "English": "en",
                "Bahasa Melayu": "ms",
                "Bahasa Indonesia": "id",
                "Thai": "th",
                "Vietnamese": "vi",
                "Filipino/Tagalog": "tl",
                "Burmese": "my",
                "Khmer": "km",
                "Lao": "lo"
            }
            lang_code = lang_map.get(language, "en")
            
            answers = []
            for url in urls[:3]:  # Limit to 3 URLs
                print(f"🔍 Processing Q&A for: {url}")
                
                # Use DocumentSummarizer's RAG Q&A function
                summarizer = DocumentSummarizer(target_lang=lang_code)
                result = summarizer.rag_qa_website(url, question)
                
                if result and result.get('answer'):
                    answer_text = (
                        f"🌐 <b>Answer from {url}</b>\n\n"
                        f"❓ <i>{question}</i>\n\n"
                        f"{result['answer']}"
                    )
                    
                    # Add sources if available
                    if result.get('sources'):
                        answer_text += "\n\n📚 <b>Relevant sections:</b>"
                        for i, source in enumerate(result['sources'][:3], 1):
                            # Truncate long sources
                            source_preview = source[:150] + "..." if len(source) > 150 else source
                            answer_text += f"\n{i}. {source_preview}"
                    
                    answers.append(answer_text)
                else:
                    answers.append(f"⚠️ Could not answer question based on {url}")
            
            if answers:
                return "\n\n" + "─" * 30 + "\n\n".join(answers)
            else:
                return f"Sorry, I couldn't find an answer to your question in the provided URLs."
                
        except Exception as e:
            print(f"❌ Error in URL Q&A: {e}")
            import traceback
            traceback.print_exc()
            return f"Sorry, I encountered an error while processing your question about the URL."
    
    async def handle_voice(self, voice_file, telegram_user) -> str:
        """
        Handle voice messages by transcribing them using local Whisper model
        
        Args:
            voice_file: Telegram voice file object
            telegram_user: Telegram user object
        
        Returns:
            Response text to send back
        """
        temp_path = None
        try:
            telegram_id = str(telegram_user.id)
            username = telegram_user.username or "Unknown"
            print(f"🎤 Voice message from: {username} ({telegram_id})")
            
            # Download voice file to temporary location
            temp_path = os.path.join(tempfile.gettempdir(), f"telegram_voice_{telegram_id}.ogg")
            await voice_file.download_to_drive(temp_path)
            print(f"✅ Voice file downloaded: {temp_path}")
            
            # Transcribe using local Whisper model
            print("🔄 Transcribing audio with local Whisper model...")
            transcribed_text = transcribe_audio(temp_path, normalize_to_question=False)
            
            if not transcribed_text:
                return "Sorry, I couldn't understand the audio. Please try again or send a text message."
            
            print(f"✅ Transcribed: {transcribed_text}")
            
            # Process the transcribed text as a regular message
            response = await self.handle_message(transcribed_text, telegram_user)
            
            # Add transcription note to response
            return f"🎤 <i>You said: \"{transcribed_text}\"</i>\n\n{response}"
            
        except Exception as e:
            print(f"❌ Error handling voice message: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I couldn't process your voice message. Please try sending a text message instead."
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"🗑️ Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    print(f"⚠️ Could not delete temp file: {e}")
    
    async def handle_document(self, document_file, telegram_user, caption: str = None) -> str:
        """
        Handle document uploads (PDF, DOCX, etc.)
        Stores the document immediately and starts background extraction
        
        Args:
            document_file: Telegram document file object
            telegram_user: Telegram user object
            caption: Optional caption/question with the document
        
        Returns:
            Response text to send back
        """
        temp_path = None
        try:
            telegram_id = str(telegram_user.id)
            username = telegram_user.username or "Unknown"
            file_name = document_file.file_name or "document"
            
            print(f"📄 Document from: {username} ({telegram_id})")
            print(f"📎 File: {file_name}")
            
            # Check file extension
            ext = os.path.splitext(file_name)[1].lower()
            supported_exts = ['.pdf', '.docx', '.doc', '.txt']
            
            if ext not in supported_exts:
                return f"⚠️ Sorry, I only support PDF, DOCX, DOC, and TXT files. Your file: {ext}"
            
            # Download document to temporary location
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"telegram_doc_{telegram_id}_{int(time.time())}{ext}")
            
            file_obj = await document_file.get_file()
            await file_obj.download_to_drive(temp_path)
            print(f"✅ Document downloaded: {temp_path}")
            
            # Store document info for this user
            self.user_documents[telegram_id] = {
                'file_path': temp_path,
                'file_name': file_name,
                'file_type': 'document',
                'timestamp': time.time(),
                'extracted_text': None,
                'processing': False
            }
            
            # Start background extraction immediately (non-blocking)
            asyncio.create_task(self._extract_document_background(telegram_id, temp_path))
            
            # If there's a caption with a question, process it immediately
            if caption and len(caption.strip()) > 5:
                print(f"❓ Question with document: {caption}")
                return await self._process_document_qa(telegram_id, caption, telegram_user)
            else:
                # No question yet - just acknowledge receipt
                return (
                    f"✅ <b>Document received: {file_name}</b>\n\n"
                    f"📄 Processing your document in the background...\n"
                    f"You can ask questions right away!\n\n"
                    f"<i>Examples:</i>\n"
                    f"• What is this document about?\n"
                    f"• Summarize the main points\n"
                    f"• What are the requirements?\n\n"
                    f"💡 Available for 30 minutes."
                )
                
        except Exception as e:
            print(f"❌ Error handling document: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I couldn't process your document. Please try again."
    
    async def handle_photo(self, photo_file, telegram_user, caption: str = None) -> str:
        """
        Handle photo uploads
        Stores the image immediately and waits for user's question
        
        Args:
            photo_file: Telegram photo file object
            telegram_user: Telegram user object
            caption: Optional caption/question with the photo
        
        Returns:
            Response text to send back
        """
        temp_path = None
        try:
            telegram_id = str(telegram_user.id)
            username = telegram_user.username or "Unknown"
            
            print(f"🖼️ Photo from: {username} ({telegram_id})")
            
            # Download photo to temporary location
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"telegram_photo_{telegram_id}_{int(time.time())}.jpg")
            
            file_obj = await photo_file.get_file()
            await file_obj.download_to_drive(temp_path)
            print(f"✅ Photo downloaded: {temp_path}")
            
            # Store photo info for this user
            self.user_documents[telegram_id] = {
                'file_path': temp_path,
                'file_name': 'photo.jpg',
                'file_type': 'image',
                'timestamp': time.time()
            }
            
            # If there's a caption with a question, process it immediately
            if caption and len(caption.strip()) > 5:
                print(f"❓ Question with photo: {caption}")
                return await self._process_image_analysis(telegram_id, caption, telegram_user)
            else:
                # No question yet - just acknowledge receipt and wait for user's question
                return (
                    f"✅ <b>Image received!</b>\n\n"
                    f"🖼️ I've saved your image. Now you can ask me questions about it!\n\n"
                    f"<i>Examples:</i>\n"
                    f"• What is in this image?\n"
                    f"• Describe what you see\n"
                    f"• Can you read the text?\n"
                    f"• Is this document valid?\n"
                    f"• Translate the text in the image\n\n"
                    f"💡 Your image will be available for the next 30 minutes."
                )
                
        except Exception as e:
            print(f"❌ Error handling photo: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I couldn't process your photo. Please try again."
    
    async def _process_document_summary(self, user_id: str, telegram_user) -> str:
        """Summarize a document"""
        try:
            doc_info = self.user_documents.get(user_id)
            if not doc_info:
                return "⚠️ No document found. Please upload a document first."
            
            file_path = doc_info['file_path']
            file_name = doc_info['file_name']
            
            # Get user language preference (default to English)
            user = self.get_or_create_user(telegram_user)
            lang_code = "en"  # Default
            
            print(f"📄 Summarizing document: {file_name}")
            
            # Use DocumentSummarizer
            summarizer = DocumentSummarizer(target_lang=lang_code)
            result = summarizer.process_document(file_path)
            
            if result and result.get('summary'):
                reduction = 0
                if result.get('word_count', 0) > 0:
                    reduction = int(100 - (result.get('summary_word_count', 0) / result['word_count'] * 100))
                
                response = (
                    f"📄 <b>Summary of {file_name}</b>\n\n"
                    f"📊 {result.get('word_count', 0)} words → {result.get('summary_word_count', 0)} words ({reduction}% shorter)\n\n"
                    f"{result['summary']}\n\n"
                    f"💡 <i>You can now ask me questions about this document!</i>"
                )
                return response
            else:
                return f"⚠️ Could not extract text from {file_name}. Please make sure it's a valid document."
                
        except Exception as e:
            print(f"❌ Error summarizing document: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I encountered an error while summarizing the document."
    
    async def _process_document_qa(self, user_id: str, question: str, telegram_user) -> str:
        """Answer a question about a document (optimized with background extraction)"""
        try:
            doc_info = self.user_documents.get(user_id)
            if not doc_info:
                return "⚠️ No document found. Please upload a document first, then ask your question."
            
            file_path = doc_info['file_path']
            file_name = doc_info['file_name']
            
            # Get user language preference
            user = self.get_or_create_user(telegram_user)
            lang_code = "en"  # Default
            
            print(f"💬 Answering question about document: {file_name}")
            print(f"❓ Question: {question}")
            
            # Check if text is already extracted
            extracted_text = doc_info.get('extracted_text')
            
            if not extracted_text:
                # Check if still processing
                if doc_info.get('processing'):
                    print(f"⏳ Document still processing, waiting...")
                    # Wait a bit for background extraction (max 5 seconds)
                    for _ in range(10):
                        await asyncio.sleep(0.5)
                        if doc_info.get('extracted_text'):
                            extracted_text = doc_info['extracted_text']
                            break
                
                # If still no text, extract now (blocking)
                if not extracted_text:
                    print(f"📄 Extracting text now (not ready from background)...")
                    loop = asyncio.get_event_loop()
                    extracted_text = await loop.run_in_executor(
                        self.executor,
                        self._extract_document_text_sync,
                        file_path,
                        lang_code
                    )
                    
                    if extracted_text and user_id in self.user_documents:
                        self.user_documents[user_id]['extracted_text'] = extracted_text
            
            if not extracted_text:
                return f"⚠️ Could not extract text from {file_name}. Please try uploading again."
            
            print(f"✅ Using extracted text ({len(extracted_text)} chars)")
            
            # Use RAG Q&A with pre-extracted text (much faster!)
            summarizer = DocumentSummarizer(target_lang=lang_code)
            result = summarizer.rag_qa(
                extracted_text,
                question,
                source_type="document",
                source_path=file_path
            )
            
            if result and result.get('answer'):
                response = (
                    f"📄 <b>Answer from {file_name}</b>\n\n"
                    f"❓ <i>{question}</i>\n\n"
                    f"{result['answer']}"
                )
                
                # Add relevant sections if available
                if result.get('sources'):
                    response += "\n\n📚 <b>Relevant sections:</b>"
                    for i, source in enumerate(result['sources'][:3], 1):
                        source_preview = source[:150] + "..." if len(source) > 150 else source
                        response += f"\n{i}. {source_preview}"
                
                return response
            else:
                return f"⚠️ Could not find an answer to your question in {file_name}."
                
        except Exception as e:
            print(f"❌ Error in document Q&A: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I encountered an error while processing your question."
    
    async def _process_image_analysis(self, user_id: str, question: str, telegram_user) -> str:
        """Analyze an image using Gemini Vision"""
        try:
            doc_info = self.user_documents.get(user_id)
            if not doc_info:
                return "⚠️ No image found. Please upload an image first."
            
            file_path = doc_info['file_path']
            
            print(f"🔍 Analyzing image with Gemini Vision")
            print(f"❓ Question: {question}")
            
            # Use new Google GenAI library (same as document summarizer)
            from google import genai
            from google.genai import types
            from PIL import Image
            
            # Configure Gemini
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return "⚠️ Gemini API key not configured. Cannot analyze images."
            
            client = genai.Client(api_key=api_key)
            
            # Load image
            img = Image.open(file_path)
            
            # Use the same prompt style as document summarizer
            prompt = f"""{question}

IMPORTANT - Write like you're explaining to a 10-year-old child:
- YES/NO FIRST: If the user is asking a closed-ended question, start the response with a clear "Yes" or "No" in the target language.
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences SHORT and SIMPLE (maximum 15-20 words per bullet)
- Explain what things DO, not what they're called
- If you must use a technical term, explain it in simple words right after
- Focus on the MAIN IDEAS only - skip minor details
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text (**) 
- Do NOT write intro text like "Here are the bullet points"
"""
            
            # Generate response using new API
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )
            
            if response and response.text:
                answer = response.text.strip()
                # Clean up any markdown formatting
                answer = answer.replace('**', '').replace('*', '').replace('__', '')
                
                return (
                    f"🖼️ <b>Image Analysis</b>\n\n"
                    f"❓ <i>{question}</i>\n\n"
                    f"{answer}\n\n"
                    f"💡 <i>You can ask me more questions about this image!</i>"
                )
            else:
                return "⚠️ Could not analyze the image. Please try again."
                
        except Exception as e:
            print(f"❌ Error analyzing image: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I encountered an error while analyzing the image. Make sure Gemini API is configured."


# Singleton instance
_handler = None

def get_message_handler() -> TelegramMessageHandler:
    """Get or create message handler singleton"""
    global _handler
    if _handler is None:
        _handler = TelegramMessageHandler()
    return _handler
