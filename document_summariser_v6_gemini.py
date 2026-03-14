"""
Document & Website Summarizer using Docling + Google Gemini
Optimized for automatic mixed-language detection
Supports PDFs with complex tables and layout preservation
Uses Google Gemini Flash for AI summarization
"""

import os
import warnings
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from langdetect import detect_langs
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()


class DocumentSummarizer:
    def __init__(self, target_lang='en', use_ai=True, model='gemini-3-flash-preview'):
        self.target_lang = target_lang
        self.use_ai = use_ai
        self.model = model
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Initialize Docling with optimized settings
        print("🔄 Initializing Docling...")
        self._init_docling()
        
        if self.use_ai:
            self._check_gemini()
    
    def _init_docling(self):
        """Initialize Docling with optimized settings for mixed-language support"""
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableStructureOptions,
            )
            
            # Configure table structure options
            table_options = TableStructureOptions(
                do_cell_matching=True,
            )
            
            # Configure PDF pipeline with OCR and table structure recognition
            pipeline_options = PdfPipelineOptions(
                do_ocr=True,
                do_table_structure=True,
                table_structure_options=table_options,
            )
            
            # Create converter with optimized settings
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    ),
                }
            )
            
            print("✅ Docling initialized successfully")
            print("   • Automatic mixed-language detection enabled")
            print("   • Complex table recognition enabled")
            print("   • Layout preservation enabled")
            print("   • OCR enabled for all documents")
            
        except ImportError as e:
            print(f"❌ Docling not installed: {e}")
            print("   Install with: pip install docling")
            raise
        except Exception as e:
            print(f"❌ Failed to initialize Docling: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _check_gemini(self):
        """Check if Gemini API key is configured"""
        if not self.gemini_api_key:
            print("⚠️  Gemini API key not configured")
            print("   Add GEMINI_API_KEY to your .env file")
            print("   Get your API key from: https://aistudio.google.com/apikey")
            print("   Using extractive summarization instead")
            self.use_ai = False
            return False
        
        print(f"✅ Gemini API configured - using {self.model} for summarization")
        return True

    def extract_text_from_document(self, file_path):
        """Extract text from document using Docling VLM pipeline"""
        print(f"📄 Processing Document: {file_path}")
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext != '.pdf':
                print(f"⚠️  Docling works best with PDFs. File type: {file_ext}")
                print("   Converting to PDF or using direct processing...")
            
            print("   🔄 Processing with Docling (OCR + Table Recognition)...")
            print("   • Automatic language detection active")
            print("   • Complex table recognition active")
            print("   • Layout preservation active")
            
            # Convert document using Docling
            result = self.converter.convert(file_path)
            
            # Export to Markdown (preserves tables and layout)
            markdown_text = result.document.export_to_markdown()
            
            # Also get plain text for language detection
            plain_text = result.document.export_to_text()
            
            # Language Detection
            print("\n🌍 Detected Languages:")
            try:
                detections = detect_langs(plain_text[:3000])
                for lang in detections:
                    names = {
                        'en': 'English',
                        'ms': 'Malay',
                        'id': 'Indonesian', 
                        'vi': 'Vietnamese',
                        'th': 'Thai',
                        'zh-cn': 'Chinese (Simplified)',
                        'zh-tw': 'Chinese (Traditional)',
                        'ta': 'Tamil',
                        'my': 'Burmese/Myanmar',
                        'km': 'Khmer',
                        'lo': 'Lao',
                        'tl': 'Tagalog/Filipino'
                    }
                    full_name = names.get(lang.lang, lang.lang.upper())
                    print(f"   • {full_name}: {lang.prob*100:.1f}% confidence")
            except:
                print("   ⚠️ Could not determine specific languages.")
            
            # Show document statistics
            print(f"\n📊 Document Statistics:")
            print(f"   • Pages: {len(result.document.pages)}")
            print(f"   • Characters: {len(plain_text)}")
            print(f"   • Words: {len(plain_text.split())}")
            
            # Count tables if any
            table_count = markdown_text.count('|')
            if table_count > 10:
                print(f"   • Tables detected: Yes")
            
            print(f"✅ Document processed successfully\n")
            
            return markdown_text
            
        except Exception as e:
            print(f"❌ Error during document processing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_text_from_website(self, url, crawl_depth=0, max_sublinks=3):
        """Extract text from website using Firecrawl for better scraping"""
        print(f"🌐 Fetching website: {url}")
        
        try:
            # Try Firecrawl first if API key is available
            firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
            
            if firecrawl_key and firecrawl_key != 'your-firecrawl-api-key-here':
                print("   Using Firecrawl for enhanced web scraping...")
                try:
                    from firecrawl import Firecrawl
                    from firecrawl.v2.types import ScrapeOptions
                    
                    app = Firecrawl(api_key=firecrawl_key)
                    
                    # Firecrawl Fast Scraping: Up to 500% faster with cached data
                    # maxAge values: 1 hour = 3600000ms, 1 day = 86400000ms, 2 days = 172800000ms (default)
                    # Government websites change infrequently, so we use 1 day cache for optimal speed
                    cache_max_age = 86400000  # 1 day - government sites rarely change
                    
                    # If crawl_depth > 0, use crawl instead of scrape
                    if crawl_depth > 0:
                        print(f"   🕷️ Crawling with depth {crawl_depth}, max {max_sublinks} pages...")
                        print(f"   ⚡ Fast mode: Using cached data (up to 1 day old) for 500% faster scraping")
                        
                        result = app.crawl(
                            url,
                            limit=max_sublinks,
                            scrape_options=ScrapeOptions(
                                formats=['markdown'],
                                max_age=cache_max_age  # Fast scraping with 1-day cache
                            )
                        )
                        
                        if result and hasattr(result, 'data'):
                            all_text = []
                            for i, page in enumerate(result.data[:max_sublinks]):
                                page_url = page.metadata.source_url if hasattr(page.metadata, 'source_url') else f'Page {i+1}'
                                page_text = page.markdown if hasattr(page, 'markdown') else ''
                                if page_text:
                                    all_text.append(f"=== {page_url} ===\n{page_text}")
                                    print(f"   ✓ Scraped: {page_url}")
                            
                            if all_text:
                                combined_text = '\n\n'.join(all_text)
                                print(f"✅ Extracted {len(combined_text)} characters from {len(all_text)} pages via Firecrawl")
                                return combined_text
                    else:
                        # Single page scrape with caching
                        print(f"   ⚡ Fast mode: Using cached data (up to 1 day old) for 500% faster scraping")
                        
                        result = app.scrape(
                            url,
                            formats=['markdown'],
                            max_age=cache_max_age  # Fast scraping with 1-day cache
                        )
                        
                        if hasattr(result, 'markdown') and result.markdown:
                            text = result.markdown
                            print(f"✅ Extracted {len(text)} characters via Firecrawl")
                            return text
                    
                    print(f"   ⚠️  No markdown content in Firecrawl response")
                    print("   Falling back to BeautifulSoup...")
                    
                except ImportError as e:
                    print(f"   ⚠️  Firecrawl package not installed: {e}")
                    print("   Install with: pip install firecrawl-py")
                except Exception as e:
                    print(f"   ⚠️  Firecrawl failed: {e}")
                    print("   Falling back to BeautifulSoup...")
            
            # Fallback to BeautifulSoup with manual crawling
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Scrape main page
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main page text
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            main_text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in main_text.split('\n') if line.strip()]
            main_text = '\n'.join(lines)
            
            all_texts = [f"=== Main Page: {url} ===\n{main_text}"]
            print(f"✅ Extracted {len(main_text)} characters from main page")
            
            # If crawl_depth > 0, find and scrape sublinks
            if crawl_depth > 0:
                print(f"   🕷️ Finding relevant sublinks...")
                from urllib.parse import urljoin, urlparse
                
                base_domain = urlparse(url).netloc
                links = soup.find_all('a', href=True)
                
                # Filter relevant links (same domain, not anchors, not files)
                relevant_links = []
                for link in links:
                    href = link.get('href')
                    full_url = urljoin(url, href)
                    parsed = urlparse(full_url)
                    
                    # Only same domain, no anchors, no files
                    if (parsed.netloc == base_domain and 
                        not href.startswith('#') and
                        not any(full_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.doc'])):
                        
                        if full_url not in relevant_links and full_url != url:
                            relevant_links.append(full_url)
                
                # Scrape top N sublinks
                for i, sublink in enumerate(relevant_links[:max_sublinks]):
                    try:
                        print(f"   Scraping sublink {i+1}/{min(len(relevant_links), max_sublinks)}: {sublink}")
                        sub_response = requests.get(sublink, headers=headers, timeout=10)
                        sub_response.raise_for_status()
                        
                        sub_soup = BeautifulSoup(sub_response.content, 'html.parser')
                        for script in sub_soup(["script", "style", "nav", "footer", "header"]):
                            script.decompose()
                        
                        sub_text = sub_soup.get_text(separator='\n', strip=True)
                        sub_lines = [line.strip() for line in sub_text.split('\n') if line.strip()]
                        sub_text = '\n'.join(sub_lines)
                        
                        all_texts.append(f"=== Subpage: {sublink} ===\n{sub_text}")
                        print(f"   ✓ Extracted {len(sub_text)} characters")
                    except Exception as e:
                        print(f"   ⚠️  Failed to scrape {sublink}: {e}")
                        continue
            
            combined_text = '\n\n'.join(all_texts)
            print(f"✅ Total extracted: {len(combined_text)} characters from {len(all_texts)} pages")
            return combined_text
            
        except Exception as e:
            print(f"❌ Error fetching website: {e}")
            return None
    
    def summarize_text(self, text, num_sentences=5):
        """Summarize text using AI (Gemini)"""
        if self.use_ai:
            return self._summarize_with_ai(text, num_sentences)
        else:
            return self._summarize_extractive(text, num_sentences)
    
    def _summarize_with_ai(self, text, num_sentences=5):
        """Use Google Gemini for abstractive summarization"""
        print(f"\n🤖 Generating AI summary using {self.model}...")
        
        word_count = len(text.split())
        print(f"   Document length: {word_count} words")
        
        if word_count <= 5000:
            return self._summarize_chunk(text, num_sentences)
        
        print(f"   Long document detected - using chunking strategy")
        return self._summarize_long_document(text, num_sentences)
    
    def _summarize_chunk(self, text, num_sentences=5):
        """Summarize a single chunk of text using Gemini"""
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            prompt = f"""Read the following text and explain the main ideas in {num_sentences} simple bullet points.

IMPORTANT - Write like you're explaining to a 10-year-old child:
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences SHORT and SIMPLE (maximum 15-20 words per bullet)
- Explain what things DO, not what they're called
- If you must use a technical term, explain it in simple words right after
- Focus on the MAIN IDEAS only - skip minor details
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text (**) 
- Do NOT write intro text like "Here are the bullet points"
- Just write the bullet points directly

Example of GOOD simple language:
✓ "The project helps small factories know when their machines will break before it happens"
✗ "The project utilizes predictive maintenance algorithms for SME industrial equipment"

Text to summarize:
{text[:50000]}

Simple summary (write exactly {num_sentences} SHORT, SIMPLE bullet points):"""
            
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.95,
                    max_output_tokens=4096,
                )
            )
            
            if response and response.text:
                summary = response.text.strip()
                if summary:
                    summary = self._clean_bullet_format(summary)
                    return summary
            
            return None
                
        except ImportError:
            print("⚠️  google-genai package not installed")
            print("   Install with: pip install google-genai")
            print("   Falling back to Ollama (llama3.2)...")
            return self._summarize_with_ollama(text, num_sentences)
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            print("   Falling back to Ollama (llama3.2)...")
            return self._summarize_with_ollama(text, num_sentences)
    
    def _summarize_with_ollama(self, text, num_sentences=5):
        """Fallback to Ollama llama3.2 for summarization"""
        print(f"\n🦙 Using Ollama (llama3.2) for summarization...")
        
        try:
            prompt = f"""Read the following text and explain the main ideas in {num_sentences} simple bullet points.

IMPORTANT - Write like you're explaining to a 10-year-old child:
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences SHORT and SIMPLE (maximum 15-20 words per bullet)
- Explain what things DO, not what they're called
- If you must use a technical term, explain it in simple words right after
- Focus on the MAIN IDEAS only - skip minor details
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text (**) 
- Do NOT write intro text like "Here are the bullet points"
- Just write the bullet points directly

Example of GOOD simple language:
✓ "The project helps small factories know when their machines will break before it happens"
✗ "The project utilizes predictive maintenance algorithms for SME industrial equipment"

Text to summarize:
{text[:12000]}

Simple summary (write exactly {num_sentences} SHORT, SIMPLE bullet points):"""
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "top_p": 0.95,
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
                if summary:
                    summary = self._clean_bullet_format(summary)
                    print(f"✅ Ollama summary generated successfully")
                    return summary
            
            print("⚠️  Ollama failed, using extractive method...")
            return self._summarize_extractive(text, num_sentences)
                
        except Exception as e:
            print(f"⚠️  Ollama error: {e}")
            print("   Using extractive method...")
            return self._summarize_extractive(text, num_sentences)
    
    def _summarize_long_document(self, text, num_sentences=5):
        """Summarize long documents by chunking and combining"""
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
            print(f"   Split into {len(chunks)} chunks with overlap")
            
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"   Processing chunk {i+1}/{len(chunks)}...")
                summary = self._summarize_chunk(chunk, num_sentences=5)
                if summary:
                    chunk_summaries.append(summary)
            
            if not chunk_summaries:
                print("⚠️  No chunk summaries generated, falling back")
                return self._summarize_extractive(text, num_sentences)
            
            combined = "\n\n".join(chunk_summaries)
            print(f"   Combining {len(chunk_summaries)} chunk summaries...")
            
            final_prompt = f"""Read these summaries from different parts of a document and combine them into {num_sentences} simple bullet points.

IMPORTANT - Write like you're explaining to a 10-year-old child:
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences SHORT and SIMPLE (maximum 15-20 words per bullet)
- Explain what things DO, not what they're called
- If you must use a technical term, explain it in simple words right after
- Cover the MAIN IDEAS from all sections
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text (**)
- Do NOT write intro text
- Just write the bullet points directly

Example of GOOD simple language:
✓ "The project helps small factories know when their machines will break before it happens"
✗ "The project utilizes predictive maintenance algorithms for SME industrial equipment"

Section summaries:
{combined}

Simple final summary (write exactly {num_sentences} SHORT, SIMPLE bullet points):"""
            
            response = client.models.generate_content(
                model=self.model,
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.95,
                    max_output_tokens=4096,
                )
            )
            
            if response and response.text:
                summary = response.text.strip()
                if summary:
                    summary = self._clean_bullet_format(summary)
                    print(f"✅ AI summary generated successfully (from {len(chunks)} chunks)")
                    return summary
            
            print("⚠️  Final summarization failed, returning combined chunk summaries")
            return self._clean_bullet_format(combined)
                
        except Exception as e:
            print(f"⚠️  AI summarization failed: {e}")
            print("   Falling back to extractive method...")
            return self._summarize_extractive(text, num_sentences)
    
    def _clean_bullet_format(self, text):
        """Clean up bullet point formatting"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            skip_phrases = [
                'here are', 'here is', 'summarizing the text',
                'in simple words', '5th grader', 'bullet points',
                'summary:', 'following is', 'below are'
            ]
            
            line_lower = line.lower()
            if any(phrase in line_lower for phrase in skip_phrases) and len(line) < 150:
                continue
            
            line = line.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
            line = line.lstrip('•-*→·∙○●■□▪▫ ')
            line = line.lstrip('0123456789.) ')
            
            if line.isupper() and len(line) < 50:
                continue
            
            if line and not line.startswith('•'):
                line = '• ' + line
            elif line.startswith('•') and not line.startswith('• '):
                line = '• ' + line[1:].lstrip()
            
            cleaned_lines.append(line)
        
        if cleaned_lines:
            return 'Here is your summary:\n\n' + '\n'.join(cleaned_lines)
        return '\n'.join(cleaned_lines)
    
    def _split_into_chunks(self, text, max_words=2000, overlap=300):
        """Improved chunking with table protection and ASEAN language support"""
        
        char_count = len(text)
        word_list = text.split()
        
        if char_count > 0 and (len(word_list) / char_count) < 0.15:
            max_limit = max_words * 2
            overlap_limit = overlap * 2
            is_char_mode = True
            print(f"   Using character-based chunking (detected non-spaced language)")
        else:
            max_limit = max_words
            overlap_limit = overlap
            is_char_mode = False
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 2:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para) if is_char_mode else len(para.split())
            is_table = para.startswith('|') or '|' in para[:50]
            
            if current_size + para_size > max_limit and current_chunk:
                if is_table and para_size <= max_limit * 1.5:
                    if current_size < max_limit * 0.3:
                        current_chunk.append(para)
                        current_size += para_size
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                        continue
                
                chunks.append('\n\n'.join(current_chunk))
                
                overlap_paras = []
                overlap_size = 0
                for prev_para in reversed(current_chunk):
                    prev_size = len(prev_para) if is_char_mode else len(prev_para.split())
                    
                    if prev_para.startswith('|') or '|' in prev_para[:50]:
                        continue
                    
                    if overlap_size + prev_size <= overlap_limit:
                        overlap_paras.insert(0, prev_para)
                        overlap_size += prev_size
                    else:
                        break
                
                current_chunk = overlap_paras + [para]
                current_size = overlap_size + para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _summarize_extractive(self, text, num_sentences=5):
        """Simple extractive summarization (fallback)"""
        print(f"\n📝 Generating extractive summary...")
        
        sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
        
        if len(sentences) <= num_sentences:
            summary = '\n• '.join(sentences)
            print(f"✅ Document is already short ({len(sentences)} sentences)")
            return '• ' + summary
        
        print(f"   Processing {len(sentences)} sentences...")
        
        summary_sentences = []
        summary_sentences.append(sentences[0])
        
        if num_sentences > 2:
            step = len(sentences) // (num_sentences - 1)
            for i in range(1, num_sentences - 1):
                idx = min(i * step, len(sentences) - 2)
                summary_sentences.append(sentences[idx])
        
        summary_sentences.append(sentences[-1])
        summary = '\n• '.join(summary_sentences)
        
        print(f"✅ Extractive summary generated")
        print(f"   Reduced from {len(sentences)} to {len(summary_sentences)} sentences")
        return '• ' + summary
    
    def translate_text(self, text):
        """Translate text to target language using deep-translator"""
        if self.target_lang == 'en':
            return text
        
        print(f"🌐 Translating to {self.target_lang}...")
        
        try:
            lang_map = {
                'zh-cn': 'zh-CN',
                'zh-tw': 'zh-TW',
            }
            target = lang_map.get(self.target_lang, self.target_lang)
            
            max_length = 4500
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                translated_chunks = []
                for chunk in chunks:
                    translator = GoogleTranslator(source='auto', target=target)
                    translated = translator.translate(chunk)
                    translated_chunks.append(translated)
                translated_text = ' '.join(translated_chunks)
            else:
                translator = GoogleTranslator(source='auto', target=target)
                translated_text = translator.translate(text)
            
            print(f"✅ Translation complete")
            return translated_text
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text
    
    def process_document(self, file_path, summarize=True, translate=True):
        """Process document: extract, summarize, translate"""
        print("\n" + "=" * 60)
        print("📄 Document Summarizer (Docling + Gemini)")
        print("=" * 60)
        
        text = self.extract_text_from_document(file_path)
        if not text:
            return None
        
        if summarize:
            summary = self.summarize_text(text)
        else:
            summary = text
        
        if translate and self.target_lang != 'en':
            summary = self.translate_text(summary)
        
        return {
            'original_text': text,
            'summary': summary,
            'word_count': len(text.split()),
            'summary_word_count': len(summary.split()),
        }
    
    def process_website(self, url, summarize=True, translate=True, crawl_depth=0, max_sublinks=3):
        """Process website: extract, summarize, translate"""
        print("\n" + "=" * 60)
        print("🌐 Website Summarizer (Gemini)")
        if crawl_depth > 0:
            print(f"   Crawling enabled: depth={crawl_depth}, max_pages={max_sublinks}")
        print("=" * 60)
        
        text = self.extract_text_from_website(url, crawl_depth=crawl_depth, max_sublinks=max_sublinks)
        if not text:
            return None
        
        if summarize:
            summary = self.summarize_text(text)
        else:
            summary = text
        
        if translate and self.target_lang != 'en':
            summary = self.translate_text(summary)
        
        return {
            'original_text': text,
            'summary': summary,
            'word_count': len(text.split()),
            'summary_word_count': len(summary.split()),
            'url': url,
        }


def main():
    print("=" * 60)
    print("📄 Document & Website Summarizer")
    print("Docling + Google Gemini 2.0 Flash")
    print("=" * 60)
    print("\nFeatures:")
    print("  • Automatic mixed-language detection")
    print("  • Complex table recognition")
    print("  • Layout preservation")
    print("  • PDF processing (no image conversion needed!)")
    print("  • Google Gemini 2.0 Flash for AI summarization")
    print("  • Ollama llama3.2 fallback")
    
    print("\nWhat would you like to summarize?")
    print("  1 - Document (PDF)")
    print("  2 - Website (URL)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    print("\nASEAN Target Language Codes:")
    print("  en    - English (default)")
    print("  ms    - Malay (Malaysia, Brunei)")
    print("  id    - Indonesian")
    print("  vi    - Vietnamese")
    print("  th    - Thai")
    print("  zh-cn - Chinese (Simplified)")
    print("  zh-tw - Chinese (Traditional)")
    print("  ta    - Tamil")
    print("  my    - Burmese/Myanmar")
    print("  km    - Khmer (Cambodia)")
    print("  lo    - Lao")
    print("  tl    - Tagalog/Filipino")
    
    target_lang = input("\nEnter language code (default: en): ").strip() or 'en'
    
    summarizer = DocumentSummarizer(target_lang=target_lang)
    
    if choice == "1":
        file_path = input("\nEnter PDF path: ").strip().strip('"')
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        result = summarizer.process_document(file_path)
        
    elif choice == "2":
        url = input("\nEnter website URL: ").strip()
        # Automatically enable crawling with 3 sublinks
        result = summarizer.process_website(url, crawl_depth=1, max_sublinks=3)
        
    else:
        print("❌ Invalid choice")
        return
    
    if result:
        print("\n" + "=" * 60)
        print("✅ Summary Generated!")
        print("=" * 60)
        print(f"\nOriginal: {result['word_count']} words")
        print(f"Summary: {result['summary_word_count']} words")
        print(f"Reduction: {100 - (result['summary_word_count'] / result['word_count'] * 100):.1f}%")
        print("\n" + "-" * 60)
        print("SUMMARY:")
        print("-" * 60)
        print(result['summary'])
        print("-" * 60)
        
        save = input("\nSave summary to file? (y/n): ").strip().lower()
        if save == 'y':
            if choice == "1":
                output_file = Path(file_path).stem + "_summary.txt"
            else:
                output_file = "website_summary.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                f.write(result['summary'])
                f.write("\n\n" + "=" * 60 + "\n")
                f.write(f"Original: {result['word_count']} words\n")
                f.write(f"Summary: {result['summary_word_count']} words\n")
            
            print(f"✅ Saved to: {output_file}")
    else:
        print("\n❌ Failed to generate summary")


if __name__ == "__main__":
    main()
