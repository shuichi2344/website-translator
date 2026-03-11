"""
Document & Website Summarizer using OCR and AI
Supports PDFs, images, and websites
Uses Docling for document processing and Ollama for intelligent summarization
"""

import os
from pathlib import Path
from docling.document_converter import DocumentConverter
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
import warnings
warnings.filterwarnings('ignore')


class DocumentSummarizer:
    def __init__(self, target_lang='en', use_ai=True, model='llama3.2'):
        self.target_lang = target_lang
        self.translator = Translator()
        self.use_ai = use_ai
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        
        # Initialize Docling converter (simplified initialization)
        self.converter = DocumentConverter()
        
        # Check if Ollama is available
        if self.use_ai:
            self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"✅ Ollama is running - using {self.model} for AI summarization")
                return True
        except:
            pass
        
        print("⚠️  Ollama not detected - using extractive summarization")
        print("   To use AI summarization:")
        print("   1. Install Ollama: https://ollama.ai")
        print("   2. Run: ollama pull llama3.2")
        print("   3. Start Ollama service")
        self.use_ai = False
        return False
    
    def extract_text_from_document(self, file_path):
        """Extract text from document using Docling OCR"""
        print(f"📄 Processing document: {file_path}")
        
        try:
            # Convert document
            result = self.converter.convert(file_path)
            
            # Extract text
            text = result.document.export_to_markdown()
            
            print(f"✅ Extracted {len(text)} characters")
            return text
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            return None
    
    def extract_text_from_website(self, url):
        """Extract text from website"""
        print(f"🌐 Fetching website: {url}")
        
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch website
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            print(f"✅ Extracted {len(text)} characters")
            return text
        except Exception as e:
            print(f"❌ Error fetching website: {e}")
            return None
    
    def summarize_text(self, text, num_sentences=5):
        """
        Summarize text using AI (Ollama) or extractive method
        """
        if self.use_ai:
            return self._summarize_with_ai(text, num_sentences)
        else:
            return self._summarize_extractive(text, num_sentences)
    
    def _summarize_with_ai(self, text, num_sentences=5):
        """Use Ollama AI for abstractive summarization with chunking for long documents"""
        print(f"\n🤖 Generating AI summary using {self.model}...")
        
        # Check document length
        word_count = len(text.split())
        print(f"   Document length: {word_count} words")
        
        # For short documents, summarize directly
        if word_count <= 3000:
            return self._summarize_chunk(text, num_sentences)
        
        # For long documents, use chunking strategy
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
                    # Clean up formatting
                    summary = self._clean_bullet_format(summary)
                    return summary
            
            return None
                
        except Exception as e:
            print(f"⚠️  Error summarizing chunk: {e}")
            return None
    
    def _summarize_long_document(self, text, num_sentences=5):
        """Summarize long documents by chunking and combining"""
        try:
            # Split into chunks with overlap to avoid missing content
            chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
            print(f"   Split into {len(chunks)} chunks with overlap")
            
            # Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"   Processing chunk {i+1}/{len(chunks)}...")
                summary = self._summarize_chunk(chunk, num_sentences=4)
                if summary:
                    chunk_summaries.append(summary)
            
            if not chunk_summaries:
                print("⚠️  No chunk summaries generated, falling back")
                return self._summarize_extractive(text, num_sentences)
            
            # Combine chunk summaries
            combined = "\n\n".join(chunk_summaries)
            print(f"   Combining {len(chunk_summaries)} chunk summaries...")
            
            # Final summarization of combined summaries
            final_prompt = f"""The following are summaries from different parts of a document. 
Create a final summary as {num_sentences} clean bullet points that covers ALL the main ideas from ALL sections.

RULES:
- Use simple words that a 5th grader can understand
- Keep the original meaning but explain it simply
- Each bullet point should be ONE complete sentence
- Start each line with just a bullet symbol: •
- Do NOT include titles, headers, or bold text
- Do NOT use ** or other formatting symbols
- Do NOT write intro text like "Here are the bullet points"
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
                    # Clean up formatting
                    summary = self._clean_bullet_format(summary)
                    print(f"✅ AI summary generated successfully (from {len(chunks)} chunks)")
                    return summary
            
            # Fallback: return combined chunk summaries
            print("⚠️  Final summarization failed, returning combined chunk summaries")
            return self._clean_bullet_format(combined)
                
        except Exception as e:
            print(f"⚠️  AI summarization failed: {e}")
            print("   Falling back to extractive method...")
            return self._summarize_extractive(text, num_sentences)
    
    def _clean_bullet_format(self, text):
        """Clean up bullet point formatting and add header"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip common intro phrases
            skip_phrases = [
                'here are',
                'here is',
                'summarizing the text',
                'in simple words',
                '5th grader',
                'bullet points',
                'summary:',
                'following is',
                'below are'
            ]
            
            line_lower = line.lower()
            if any(phrase in line_lower for phrase in skip_phrases) and len(line) < 150:
                continue
            
            # Remove markdown bold/italic
            line = line.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
            
            # Remove common prefixes
            line = line.lstrip('•-*→·∙○●■□▪▫ ')
            line = line.lstrip('0123456789.) ')
            
            # Skip lines that look like headers (all caps or very short)
            if line.isupper() and len(line) < 50:
                continue
            
            # Add bullet if not present
            if line and not line.startswith('•'):
                line = '• ' + line
            elif line.startswith('•') and not line.startswith('• '):
                line = '• ' + line[1:].lstrip()
            
            cleaned_lines.append(line)
        
        # Add header and return
        if cleaned_lines:
            return 'Here is your summary:\n\n' + '\n'.join(cleaned_lines)
        return '\n'.join(cleaned_lines)
    
    def _split_into_chunks(self, text, max_words=2000, overlap=300):
        """Split text into chunks by paragraphs with overlap to avoid missing content"""
        """Clean up bullet point formatting - remove ALL intro text and formatting"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip common intro phrases (more aggressive)
            skip_phrases = [
                'here are',
                'here is',
                'summarizing',
                'summary',
                'simple words',
                '5th grader',
                'bullet points',
                'following',
                'below',
                'understand:',
                'understand',
                'can understand'
            ]
            
            line_lower = line.lower()
            # Skip if line contains any skip phrase and is relatively short (likely intro)
            if any(phrase in line_lower for phrase in skip_phrases):
                if len(line) < 200 or line_lower.startswith(('here', 'following', 'below', 'summary')):
                    continue
            
            # Remove ALL markdown formatting
            line = line.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
            
            # Remove colons after titles (like "Predictive Maintenance:")
            if ':' in line and len(line.split(':')[0]) < 80:
                # This looks like a title, extract content after colon
                parts = line.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    line = parts[1].strip()
                else:
                    continue  # Skip title-only lines
            
            # Remove common prefixes
            line = line.lstrip('•-*→·∙○●■□▪▫ ')
            line = line.lstrip('0123456789.) ')
            
            # Skip very short lines (likely fragments)
            if len(line) < 20:
                continue
            
            # Skip lines that look like headers (all caps or very short)
            if line.isupper() and len(line) < 50:
                continue
            
            # Add bullet if not present
            if line and not line.startswith('•'):
                line = '• ' + line
            elif line.startswith('•') and not line.startswith('• '):
                line = '• ' + line[1:].lstrip()
            
            cleaned_lines.append(line)
        
        # Return without any header - just the bullet points
        return '\n'.join(cleaned_lines)

    
    def _split_into_chunks(self, text, max_words=2000, overlap=300):
        """Split text into chunks by paragraphs with overlap to avoid missing content"""
        # Split by double newlines (paragraphs) or single newlines
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for i, para in enumerate(paragraphs):
            para_words = len(para.split())
            
            if current_words + para_words > max_words and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Start new chunk with overlap (include last few paragraphs)
                overlap_paras = []
                overlap_words = 0
                for prev_para in reversed(current_chunk):
                    prev_words = len(prev_para.split())
                    if overlap_words + prev_words <= overlap:
                        overlap_paras.insert(0, prev_para)
                        overlap_words += prev_words
                    else:
                        break
                
                current_chunk = overlap_paras + [para]
                current_words = overlap_words + para_words
            else:
                current_chunk.append(para)
                current_words += para_words
        
        # Add last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _summarize_extractive(self, text, num_sentences=5):
        """Simple extractive summarization (fallback) - returns bullet points"""
        print(f"\n📝 Generating extractive summary...")
        
        # Split into sentences (simple approach)
        sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
        
        if len(sentences) <= num_sentences:
            summary = '\n• '.join(sentences)
            print(f"✅ Document is already short ({len(sentences)} sentences)")
            return '• ' + summary
        
        print(f"   Processing {len(sentences)} sentences...")
        
        # Take first, evenly distributed middle, and last sentences
        summary_sentences = []
        summary_sentences.append(sentences[0])
        
        if num_sentences > 2:
            step = len(sentences) // (num_sentences - 1)
            for i in range(1, num_sentences - 1):
                idx = min(i * step, len(sentences) - 2)
                summary_sentences.append(sentences[idx])
        
        summary_sentences.append(sentences[-1])
        
        # Format as bullet points
        summary = '\n• '.join(summary_sentences)
        
        print(f"✅ Extractive summary generated")
        print(f"   Reduced from {len(sentences)} to {len(summary_sentences)} sentences")
        return '• ' + summary
    
    def translate_text(self, text):
        """Translate text to target language"""
        if self.target_lang == 'en':
            return text
        
        print(f"🌐 Translating to {self.target_lang}...")
        
        try:
            # Split into chunks if too long
            max_length = 4500
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                translated_chunks = []
                for chunk in chunks:
                    result = self.translator.translate(chunk, dest=self.target_lang)
                    translated_chunks.append(result.text)
                translated_text = ' '.join(translated_chunks)
            else:
                result = self.translator.translate(text, dest=self.target_lang)
                translated_text = result.text
            
            print(f"✅ Translation complete")
            return translated_text
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text
    
    def process_document(self, file_path, summarize=True, translate=True):
        """Process document: extract, summarize, translate"""
        print("\n" + "=" * 60)
        print("📄 Document Summarizer")
        print("=" * 60)
        
        # Extract text
        text = self.extract_text_from_document(file_path)
        if not text:
            return None
        
        # Summarize
        if summarize:
            summary = self.summarize_text(text)
        else:
            summary = text
        
        # Translate
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
        
        # Extract text
        text = self.extract_text_from_website(url)
        if not text:
            return None
        
        # Summarize
        if summarize:
            summary = self.summarize_text(text)
        else:
            summary = text
        
        # Translate
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
    print("=" * 60)
    print("\nSupported formats:")
    print("  • PDF documents (with OCR)")
    print("  • Images (PNG, JPG)")
    print("  • Word documents (DOCX)")
    print("  • PowerPoint (PPTX)")
    print("  • Excel (XLSX)")
    print("  • Websites (URLs)")
    
    # Choose input type
    print("\nWhat would you like to summarize?")
    print("  1 - Document (PDF, Image, DOCX, etc.)")
    print("  2 - Website (URL)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    # Get target language
    print("\nTarget language codes:")
    print("  en - English (default)")
    print("  ms - Malay")
    print("  zh-cn - Chinese")
    print("  ta - Tamil")
    print("  hi - Hindi")
    
    target_lang = input("\nEnter language code (default: en): ").strip() or 'en'
    
    # Initialize summarizer
    summarizer = DocumentSummarizer(target_lang=target_lang)
    
    if choice == "1":
        # Document
        file_path = input("\nEnter document path: ").strip().strip('"')
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        result = summarizer.process_document(file_path)
        
    elif choice == "2":
        # Website
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
        
        # Save to file
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
