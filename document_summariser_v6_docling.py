"""
Document & Website Summarizer using Docling
Optimized for automatic mixed-language detection
Supports PDFs with complex tables and layout preservation
100% FREE - No API keys needed!
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
    def __init__(self, target_lang='en', use_ai=True, model='llama3.2'):
        self.target_lang = target_lang
        self.use_ai = use_ai
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        
        # Initialize Docling with optimized settings
        print("🔄 Initializing Docling...")
        self._init_docling()
        
        if self.use_ai:
            self._check_ollama()
    
    def _init_docling(self):
        """Initialize Docling with optimized settings for mixed-language support"""
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.pipeline.simple_pipeline import SimplePipeline
            from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
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
                do_ocr=True,  # Enable OCR for text extraction
                do_table_structure=True,  # Enable table structure recognition
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
    
    def _check_ollama(self):
        """Check if Ollama is running for summarization"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"✅ Ollama is running - using {self.model} for summarization")
                return True
        except:
            pass
        print("⚠️  Ollama not detected - using extractive summarization")
        self.use_ai = False
        return False

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
            table_count = markdown_text.count('|')  # Simple table detection
            if table_count > 10:  # Likely has tables
                print(f"   • Tables detected: Yes")
            
            print(f"✅ Document processed successfully\n")
            
            # Return markdown for better structure preservation
            return markdown_text
            
        except Exception as e:
            print(f"❌ Error during document processing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_text_from_website(self, url):
        """Extract text from website using Firecrawl for better scraping"""
        print(f"🌐 Fetching website: {url}")
        
        try:
            # Try Firecrawl first if API key is available
            firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
            
            if firecrawl_key and firecrawl_key != 'your-firecrawl-api-key-here':
                print("   Using Firecrawl for enhanced web scraping...")
                try:
                    from firecrawl import Firecrawl
                    
                    app = Firecrawl(api_key=firecrawl_key)
                    
                    # Scrape with markdown format for clean content
                    result = app.scrape(
                        url,
                        formats=['markdown']
                    )
                    
                    # Firecrawl returns a Document object with markdown attribute
                    if hasattr(result, 'markdown') and result.markdown:
                        text = result.markdown
                        print(f"✅ Extracted {len(text)} characters via Firecrawl")
                        return text
                    elif isinstance(result, dict) and 'markdown' in result:
                        text = result['markdown']
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
            elif firecrawl_key == 'your-firecrawl-api-key-here':
                print("   ⚠️  Firecrawl API key not configured (using placeholder)")
                print("   Add your API key to .env file")
            
            # Fallback to BeautifulSoup
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            print(f"✅ Extracted {len(text)} characters via BeautifulSoup")
            return text
            
        except Exception as e:
            print(f"❌ Error fetching website: {e}")
            return None
    
    def summarize_text(self, text, num_sentences=5):
        """Summarize text using AI (Ollama)"""
        if self.use_ai:
            return self._summarize_with_ai(text, num_sentences)
        else:
            return self._summarize_extractive(text, num_sentences)
    
    def _summarize_with_ai(self, text, num_sentences=5):
        """Use Ollama AI for abstractive summarization"""
        print(f"\n🤖 Generating AI summary using {self.model}...")
        
        word_count = len(text.split())
        print(f"   Document length: {word_count} words")
        
        if word_count <= 3000:
            return self._summarize_chunk(text, num_sentences)
        
        print(f"   Long document detected - using chunking strategy")
        return self._summarize_long_document(text, num_sentences)
    
    def _summarize_chunk(self, text, num_sentences=5):
        """Summarize a single chunk of text"""
        try:
            prompt = f"""Summarize the following text as {num_sentences} clean bullet points.

RULES:
- Use simple words that a 5th grader can understand
- Keep the original meaning but explain it simply
- Each bullet point should be ONE complete sentence
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text
- Do NOT use ** or other formatting symbols
- Do NOT write intro text like "Here are the bullet points"
- Just write the bullet points directly

Text to summarize:
{text[:12000]}

Summary (write {num_sentences} bullet points, one per line):"""
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
                if summary:
                    summary = self._clean_bullet_format(summary)
                    return summary
            
            return None
                
        except Exception as e:
            print(f"⚠️  Error summarizing chunk: {e}")
            return None
    
    def _summarize_long_document(self, text, num_sentences=5):
        """Summarize long documents by chunking and combining"""
        try:
            chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
            print(f"   Split into {len(chunks)} chunks with overlap")
            
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"   Processing chunk {i+1}/{len(chunks)}...")
                summary = self._summarize_chunk(chunk, num_sentences=4)
                if summary:
                    chunk_summaries.append(summary)
            
            if not chunk_summaries:
                print("⚠️  No chunk summaries generated, falling back")
                return self._summarize_extractive(text, num_sentences)
            
            combined = "\n\n".join(chunk_summaries)
            print(f"   Combining {len(chunk_summaries)} chunk summaries...")
            
            final_prompt = f"""The following are summaries from different parts of a document. 
Create a final summary as {num_sentences} clean bullet points that covers ALL the main ideas from ALL sections.

RULES:
- Use simple words that a 5th grader can understand
- Keep the original meaning but explain it simply
- Each bullet point should be ONE complete sentence
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text
- Do NOT use ** or other formatting symbols
- Do NOT write intro text
- Just write the bullet points directly
- Make sure to include points from the beginning, middle, AND end of the document
- Cover all major topics mentioned

Section summaries:
{combined}

Final summary (write exactly {num_sentences} bullet points, one per line):"""
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": final_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
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
        
        # Detect if text uses non-space-separated language (Chinese, Thai, Khmer, Lao, etc.)
        char_count = len(text)
        word_list = text.split()
        
        # If word density is very low, likely a non-spaced language
        if char_count > 0 and (len(word_list) / char_count) < 0.15:
            # Character-based chunking for Asian languages
            # Approximate: 1 word ≈ 2-3 characters in these languages
            max_limit = max_words * 2
            overlap_limit = overlap * 2
            is_char_mode = True
            print(f"   Using character-based chunking (detected non-spaced language)")
        else:
            max_limit = max_words
            overlap_limit = overlap
            is_char_mode = False
        
        # Split by double newlines to preserve paragraph/table structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Fallback to single newlines if no double newlines found
        if len(paragraphs) < 2:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            # Measure size based on mode
            para_size = len(para) if is_char_mode else len(para.split())
            
            # TABLE PROTECTION: Detect markdown tables
            is_table = para.startswith('|') or '|' in para[:50]
            
            # If adding this paragraph exceeds limit AND we have content
            if current_size + para_size > max_limit and current_chunk:
                # Special handling for tables
                if is_table and para_size <= max_limit * 1.5:
                    # If table fits in 1.5x limit, keep it whole in current chunk
                    # This prevents breaking tables across chunks
                    if current_size < max_limit * 0.3:  # Current chunk is small
                        current_chunk.append(para)
                        current_size += para_size
                        # Force chunk end after table
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                        continue
                
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Create overlap: grab last few paragraphs within overlap budget
                overlap_paras = []
                overlap_size = 0
                for prev_para in reversed(current_chunk):
                    prev_size = len(prev_para) if is_char_mode else len(prev_para.split())
                    
                    # Don't include tables in overlap (they're usually complete units)
                    if prev_para.startswith('|') or '|' in prev_para[:50]:
                        continue
                    
                    if overlap_size + prev_size <= overlap_limit:
                        overlap_paras.insert(0, prev_para)
                        overlap_size += prev_size
                    else:
                        break
                
                # Start new chunk with overlap + current paragraph
                current_chunk = overlap_paras + [para]
                current_size = overlap_size + para_size
            else:
                # Add paragraph to current chunk
                current_chunk.append(para)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # Fallback: if no chunks created, return whole text
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
        print("📄 Document Summarizer (Docling)")
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
    
    def process_website(self, url, summarize=True, translate=True):
        """Process website: extract, summarize, translate"""
        print("\n" + "=" * 60)
        print("🌐 Website Summarizer")
        print("=" * 60)
        
        text = self.extract_text_from_website(url)
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
    print("Docling - Advanced Document Processing")
    print("=" * 60)
    print("\nFeatures:")
    print("  • Automatic mixed-language detection")
    print("  • Complex table recognition")
    print("  • Layout preservation")
    print("  • PDF processing (no image conversion needed!)")
    
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
        result = summarizer.process_website(url)
        
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
