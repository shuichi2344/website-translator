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
from dotenv import load_dotenv
from engine.gpu_accelerator import load_sentence_transformer, get_optimal_batch_size, is_gpu_available

warnings.filterwarnings('ignore')
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)


class DocumentSummarizer:
    def __init__(self, target_lang='en', use_ai=True, model='gemini-3-flash-preview', use_embeddings=True, use_vector_db=True):
        self.target_lang = target_lang
        self.use_ai = use_ai
        self.model = model
        self.use_embeddings = use_embeddings
        self.use_vector_db = use_vector_db
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Initialize embedding model for RAG
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        
        if self.use_embeddings:
            print("🔄 Initializing EmbeddingGemma-300M...")
            self._init_embeddings()
            
            if self.use_vector_db:
                print("🔄 Initializing ChromaDB vector database...")
                self._init_vector_db()
        
        # Initialize Docling with optimized settings
        print("🔄 Initializing Docling...")
        self._init_docling()
        
        if self.use_ai:
            self._check_gemini()
    
    def _init_vector_db(self):
        """Initialize ChromaDB for persistent vector storage"""
        try:
            import chromadb
            from chromadb.config import Settings
            import hashlib
            
            # Create persistent ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path="./chroma_db",
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collection for document chunks
            self.collection = self.chroma_client.get_or_create_collection(
                name="document_chunks",
                metadata={"description": "Document chunks with EmbeddingGemma embeddings"}
            )
            
            print("✅ ChromaDB initialized successfully")
            print(f"   • Database path: ./chroma_db")
            print(f"   • Collection: document_chunks")
            print(f"   • Stored embeddings: {self.collection.count()}")
            
        except ImportError:
            print("⚠️  chromadb not installed")
            print("   Install with: pip install chromadb")
            print("   Continuing without vector database...")
            self.use_vector_db = False
        except Exception as e:
            print(f"⚠️  Failed to initialize ChromaDB: {e}")
            print("   Continuing without vector database...")
            self.use_vector_db = False
    
    def _check_existing_embeddings(self, doc_id):
        """Check if embeddings for this document already exist in ChromaDB"""
        if not self.use_vector_db or not self.collection:
            return False
        
        try:
            # Query for any chunks with this doc_id
            results = self.collection.get(
                where={"doc_id": doc_id},
                limit=1
            )
            
            if results and results['ids']:
                print(f"   ✅ Found existing embeddings for doc_id: {doc_id[:8]}...")
                print(f"   💾 Skipping re-embedding (using cached embeddings)")
                return True
            
        except Exception as e:
            print(f"   ⚠️  Error checking existing embeddings: {e}")
        
        return False
    
    def _get_chunks_from_db(self, doc_id):
        """Retrieve all chunks for a document from ChromaDB"""
        if not self.use_vector_db or not self.collection:
            return None
        
        try:
            results = self.collection.get(
                where={"doc_id": doc_id},
                include=["documents", "embeddings", "metadatas"]
            )
            
            if results and results['documents']:
                # Sort by chunk_index to maintain order
                sorted_data = sorted(
                    zip(results['documents'], results['embeddings'], results['metadatas']),
                    key=lambda x: x[2]['chunk_index']
                )
                
                chunks = [item[0] for item in sorted_data]
                embeddings = [item[1] for item in sorted_data]
                
                print(f"   📥 Retrieved {len(chunks)} chunks from ChromaDB")
                return chunks, embeddings
            
        except Exception as e:
            print(f"   ⚠️  Error retrieving chunks from DB: {e}")
        
        return None
    
    def _get_document_id(self, text):
        """Generate unique document ID using MD5 hash"""
        import hashlib
        # Use first 10000 chars to generate ID (enough to be unique)
        sample = text[:10000] if len(text) > 10000 else text
        return hashlib.md5(sample.encode('utf-8')).hexdigest()
    
    def _store_chunks_in_db(self, chunks, embeddings, doc_id, full_text=None):
        """Store chunks, embeddings, and optionally full extracted text in ChromaDB"""
        if not self.use_vector_db or not self.collection:
            return
        
        try:
            # Prepare data for ChromaDB
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"chunk_index": i, "doc_id": doc_id} for i in range(len(chunks))]
            
            # Add full text to first chunk's metadata if provided
            if full_text and len(metadatas) > 0:
                metadatas[0]["full_text"] = full_text
                metadatas[0]["has_full_text"] = True
                print(f"   💾 Caching full extracted text ({len(full_text)} chars)")
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            print(f"   💾 Stored {len(chunks)} chunks in ChromaDB")
            
        except Exception as e:
            print(f"   ⚠️  Failed to store in ChromaDB: {e}")
    
    def _get_full_text_from_db(self, doc_id):
        """Retrieve cached full text from ChromaDB"""
        if not self.use_vector_db or not self.collection:
            return None
        
        try:
            # Query for first chunk which contains full text
            # Use $and operator for multiple conditions
            results = self.collection.get(
                where={
                    "$and": [
                        {"doc_id": doc_id},
                        {"chunk_index": 0}
                    ]
                },
                include=["metadatas"]
            )
            
            if results and results['metadatas'] and len(results['metadatas']) > 0:
                metadata = results['metadatas'][0]
                if metadata.get('has_full_text') and 'full_text' in metadata:
                    full_text = metadata['full_text']
                    print(f"   ✅ Retrieved cached full text ({len(full_text)} chars)")
                    return full_text
            
        except Exception as e:
            print(f"   ⚠️  Error retrieving full text from DB: {e}")
        
        return None
    
    def _query_vector_db(self, query_embedding, n_results=10):
        """Query ChromaDB for most similar chunks"""
        if not self.use_vector_db or not self.collection:
            return None
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding],
                n_results=min(n_results, self.collection.count())
            )
            
            if results and results['documents']:
                print(f"   🔍 Retrieved {len(results['documents'][0])} chunks from ChromaDB")
                return {
                    'documents': results['documents'][0],
                    'distances': results['distances'][0],
                    'metadatas': results['metadatas'][0]
                }
            
        except Exception as e:
            print(f"   ⚠️  ChromaDB query failed: {e}")
        
        return None
    
    def _init_embeddings(self):
        """Initialize EmbeddingGemma-300M for semantic search and RAG with GPU acceleration"""
        try:
            import os
            
            # Get Hugging Face token from environment
            hf_token = os.getenv('HUGGINGFACE_TOKEN') or os.getenv('HF_TOKEN')
            
            if hf_token and hf_token != 'your-huggingface-token-here':
                # Login to Hugging Face
                try:
                    from huggingface_hub import login
                    login(token=hf_token, add_to_git_credential=False)
                    print("✅ Logged in to Hugging Face")
                except:
                    pass
            
            # Load model with GPU acceleration
            self.embedding_model = load_sentence_transformer("google/embeddinggemma-300m")
            self.batch_size = get_optimal_batch_size(default_cpu=8, default_gpu=32)
            
            print("✅ EmbeddingGemma-300M initialized successfully")
            print("   • 300M parameters, 768-dimensional embeddings")
            print("   • Optimized for semantic search and retrieval")
            print("   • Supports 100+ languages including all ASEAN languages")
            print(f"   • Batch size: {self.batch_size}")
            if is_gpu_available():
                print("   • 🚀 GPU acceleration enabled")
            else:
                print("   • 💻 Running on CPU")
            
        except ImportError:
            print("⚠️  sentence-transformers not installed")
            print("   Install with: pip install sentence-transformers")
            print("   Continuing without embedding-based RAG...")
            self.use_embeddings = False
        except Exception as e:
            print(f"⚠️  Error initializing embeddings: {e}")
            print("   Continuing without embedding-based RAG...")
            self.use_embeddings = False
        except Exception as e:
            error_msg = str(e)
            if "gated repo" in error_msg or "401" in error_msg:
                print(f"⚠️  EmbeddingGemma requires Hugging Face authentication")
                print("   1. Go to: https://huggingface.co/google/embeddinggemma-300m")
                print("   2. Click 'Agree and access repository'")
                print("   3. Get token from: https://huggingface.co/settings/tokens")
                print("   4. Add to .env: HUGGINGFACE_TOKEN='your-token-here'")
                print("   Continuing without embedding-based RAG...")
            else:
                print(f"⚠️  Failed to load EmbeddingGemma: {e}")
                print("   Continuing without embedding-based RAG...")
            self.use_embeddings = False
    
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
        """Extract text from document using Docling VLM pipeline or Gemini Vision for images"""
        print(f"📄 Processing Document: {file_path}")
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Check if it's an image file - use Gemini Vision instead of Docling
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
            if file_ext in image_extensions:
                print(f"🖼️ Image detected: {file_ext}")
                print("   Using Gemini Vision for image analysis (OCR + visual understanding)...")
                return self._extract_text_from_image_with_vision(file_path)
            
            # Check cache first (before expensive Docling processing)
            if self.use_vector_db:
                # Generate doc_id from file path + modification time for file-based caching
                import os
                import hashlib
                file_stat = os.stat(file_path)
                cache_key = f"{file_path}_{file_stat.st_mtime}_{file_stat.st_size}"
                doc_id = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
                
                # Try to get cached full text
                cached_text = self._get_full_text_from_db(doc_id)
                if cached_text:
                    print(f"   ♻️  Using cached extracted text (skipping Docling)")
                    return cached_text
            
            if file_ext != '.pdf':
                print(f"⚠️  Docling works best with PDFs. File type: {file_ext}")
                print("   Converting to PDF or using direct processing...")
            
            print("   🔄 Processing with Docling (OCR + Table Recognition)...")
            print("   • Automatic language detection active")
            print("   • Complex table recognition active")
            print("   • Layout preservation active")
            
            # Convert document using Docling with retry logic
            max_retries = 3
            result = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"   🔄 Retry attempt {attempt + 1}/{max_retries}...")
                        # Add a small delay between retries
                        import time
                        time.sleep(1)
                    
                    result = self.converter.convert(file_path)
                    
                    # Check if conversion was successful
                    if result and result.document:
                        # Check for failed pages
                        failed_pages = []
                        if hasattr(result, 'errors') and result.errors:
                            for error in result.errors:
                                if 'page' in str(error).lower():
                                    failed_pages.append(str(error))
                        
                        if failed_pages and attempt < max_retries - 1:
                            print(f"   ⚠️  Some pages failed preprocessing: {len(failed_pages)} errors")
                            print(f"   Retrying to recover failed pages...")
                            continue  # Retry
                        elif failed_pages:
                            print(f"   ⚠️  {len(failed_pages)} pages had preprocessing issues (continuing with available content)")
                        
                        break  # Success
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a memory error
                    if 'bad_alloc' in error_msg or 'memory' in error_msg:
                        print(f"   ⚠️  Memory allocation error on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            print(f"   Retrying with reduced memory footprint...")
                            # Force garbage collection to free memory
                            import gc
                            gc.collect()
                            continue
                    else:
                        print(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
                        if attempt < max_retries - 1:
                            continue
                    
                    # If last attempt, raise the error
                    if attempt == max_retries - 1:
                        raise
            
            if not result or not result.document:
                raise Exception("Failed to convert document after all retry attempts")
            
            # Export to Markdown (preserves tables and layout)
            markdown_text = result.document.export_to_markdown()
            
            # Also get plain text for language detection
            plain_text = result.document.export_to_text()
            
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
            
            # Cache the extracted text if vector DB is enabled
            if self.use_vector_db and markdown_text:
                try:
                    import os
                    import hashlib
                    file_stat = os.stat(file_path)
                    cache_key = f"{file_path}_{file_stat.st_mtime}_{file_stat.st_size}"
                    doc_id = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
                    
                    # Create minimal chunks and embeddings just for caching
                    chunks = self._split_into_chunks(markdown_text, max_words=2000, overlap=300)
                    self._embed_chunks(chunks, doc_id=doc_id, full_text=markdown_text)
                except Exception as cache_error:
                    print(f"   ⚠️  Failed to cache extracted text: {cache_error}")
            
            return markdown_text
            
        except Exception as e:
            print(f"❌ Error during document processing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_text_from_image_with_vision(self, image_path):
        """Extract text from image using Gemini Vision (OCR + visual understanding)"""
        try:
            from google import genai
            from google.genai import types
            from PIL import Image
            
            if not self.gemini_api_key:
                print("⚠️  Gemini API key not configured")
                print("   Cannot use Gemini Vision for image processing")
                return None
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            # Load image
            img = Image.open(image_path)
            print(f"   📐 Image size: {img.size[0]}x{img.size[1]} pixels")
            
            # Prompt for comprehensive text extraction
            prompt = """Extract ALL text from this image in a structured format.

INSTRUCTIONS:
1. Extract every piece of text you can see, including:
   - Main content and body text
   - Headers, titles, and subtitles
   - Labels, captions, and annotations
   - Tables (preserve table structure using markdown format)
   - Forms and fields
   - Small text, footnotes, and fine print
   - Any text in different languages

2. Preserve the layout and structure:
   - Use markdown headers (# ## ###) for titles
   - Use markdown tables (| | |) for tabular data
   - Use bullet points (•) for lists
   - Maintain paragraph breaks

3. If the image contains visual elements (photos, diagrams, charts):
   - Briefly describe them in [brackets]
   - Example: [Photo of a person signing a document]
   - Example: [Bar chart showing sales data]

4. Output ONLY the extracted text and descriptions. Do not add commentary or explanations.

Extract all text now:"""
            
            # Generate response using Gemini Vision
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for accurate extraction
                    top_p=0.95,
                    max_output_tokens=4096,
                )
            )
            
            if response and response.text:
                extracted_text = response.text.strip()
                
                # Show statistics
                print(f"\n📊 Extraction Statistics:")
                print(f"   • Characters: {len(extracted_text)}")
                print(f"   • Words: {len(extracted_text.split())}")
                print(f"✅ Image processed successfully with Gemini Vision\n")
                
                return extracted_text
            else:
                print("⚠️  Gemini Vision returned empty response")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting text from image with Gemini Vision: {e}")
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
        
        # Always create embeddings if enabled (for caching and Q&A)
        if self.use_embeddings and self.use_vector_db:
            doc_id = self._get_document_id(text)
            
            # Check if embeddings already exist
            if not self._check_existing_embeddings(doc_id):
                # Create and store embeddings even for short documents
                chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
                print(f"   📦 Creating embeddings for {len(chunks)} chunk(s) (for caching)...")
                self._embed_chunks(chunks, doc_id=doc_id, full_text=text)
        
        if word_count <= 5000:
            return self._summarize_chunk(text, num_sentences)
        
        print(f"   Long document detected - using chunking strategy")
        return self._summarize_long_document(text, num_sentences)
    
    def _lang_instruction(self):
        """Returns a language instruction string for Gemini prompts."""
        lang_map = {
            'en': 'English',
            'ms': 'Malay (Bahasa Melayu)', 'id': 'Indonesian (Bahasa Indonesia)',
            'vi': 'Vietnamese', 'th': 'Thai', 'zh-cn': 'Simplified Chinese',
            'zh-tw': 'Traditional Chinese', 'ta': 'Tamil', 'tl': 'Tagalog/Filipino',
            'my': 'Burmese/Myanmar', 'km': 'Khmer', 'lo': 'Lao',
        }
        lang_name = lang_map.get(self.target_lang, 'English')
        return f"\n- IMPORTANT: You MUST write your entire response in {lang_name}, regardless of the language of the source text."

    def _summarize_chunk(self, text, num_sentences=5):
        """Summarize a single chunk of text using Gemini"""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)

            lang_instruction = self._lang_instruction()

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
- Just write the bullet points directly{lang_instruction}

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
    
    def _embed_chunks(self, chunks, doc_id=None, full_text=None):
        """Create embeddings for text chunks using EmbeddingGemma and store in ChromaDB"""
        if not self.use_embeddings or not self.embedding_model:
            return None
        
        try:
            print(f"   🔮 Creating embeddings for {len(chunks)} chunks...")
            # Use document prompt for better retrieval
            embeddings = self.embedding_model.encode(
                chunks,
                prompt_name="Retrieval-document",
                show_progress_bar=False
            )
            print(f"   ✅ Generated {len(embeddings)} embeddings (768-dim)")
            
            # Store in ChromaDB if enabled (with full text)
            if self.use_vector_db and doc_id:
                self._store_chunks_in_db(chunks, embeddings, doc_id, full_text=full_text)
            
            return embeddings
        except Exception as e:
            print(f"   ⚠️  Embedding generation failed: {e}")
            return None
    
    def _rank_chunks_by_relevance(self, chunks, embeddings, query="summarize this document", use_db=True):
        """Rank chunks by semantic relevance using ChromaDB or in-memory similarity"""
        if not self.use_embeddings or not self.embedding_model:
            return list(range(len(chunks)))  # Return original order
        
        try:
            print(f"   🔍 Ranking chunks by relevance to: '{query}'")
            
            # Create query embedding
            query_embedding = self.embedding_model.encode(
                query,
                prompt_name="Retrieval-query",
                show_progress_bar=False
            )
            
            # Try ChromaDB first if enabled
            if use_db and self.use_vector_db and self.collection and self.collection.count() > 0:
                results = self._query_vector_db(query_embedding, n_results=len(chunks))
                if results:
                    # Map retrieved documents back to original chunk indices
                    retrieved_docs = results['documents']
                    ranked_indices = []
                    for doc in retrieved_docs:
                        try:
                            idx = chunks.index(doc)
                            if idx not in ranked_indices:
                                ranked_indices.append(idx)
                        except ValueError:
                            continue
                    
                    # Add any missing indices at the end
                    for i in range(len(chunks)):
                        if i not in ranked_indices:
                            ranked_indices.append(i)
                    
                    print(f"   ✅ Chunks ranked using ChromaDB")
                    return ranked_indices
            
            # Fallback to in-memory similarity calculation
            if embeddings is not None:
                similarities = self.embedding_model.similarity(query_embedding, embeddings)
                ranked_indices = similarities[0].argsort(descending=True).tolist()
                print(f"   ✅ Chunks ranked by semantic similarity (in-memory)")
                return ranked_indices
            
        except Exception as e:
            print(f"   ⚠️  Ranking failed: {e}")
        
        return list(range(len(chunks)))
    
    def _summarize_long_document(self, text, num_sentences=5):
        """Summarize long documents using Map-Reduce: summarize all chunks, then combine"""
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            # Generate document ID
            doc_id = self._get_document_id(text)
            
            # Check if we already have embeddings for this document
            if self._check_existing_embeddings(doc_id):
                # Retrieve cached chunks and embeddings
                cached_data = self._get_chunks_from_db(doc_id)
                if cached_data:
                    chunks, embeddings = cached_data
                    print(f"   ♻️  Using {len(chunks)} cached chunks (no re-processing needed)")
                else:
                    # Fallback: create new chunks
                    chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
                    embeddings = self._embed_chunks(chunks, doc_id=doc_id, full_text=text)
            else:
                # New document: create chunks and embeddings
                chunks = self._split_into_chunks(text, max_words=2000, overlap=300)
                print(f"   Split into {len(chunks)} chunks with overlap")
                embeddings = self._embed_chunks(chunks, doc_id=doc_id, full_text=text)
                embeddings = self._embed_chunks(chunks, doc_id=doc_id)
            
            # MAP PHASE: Summarize ALL chunks (not just top 10)
            print(f"   📊 MAP PHASE: Summarizing all {len(chunks)} chunks...")
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                print(f"   Processing chunk {i+1}/{len(chunks)}...")
                summary = self._summarize_chunk(chunk, num_sentences=3)  # Shorter summaries per chunk
                if summary:
                    chunk_summaries.append(summary)
            
            if not chunk_summaries:
                print("⚠️  No chunk summaries generated, falling back")
                return self._summarize_extractive(text, num_sentences)
            
            # REDUCE PHASE: Combine all chunk summaries into final summary
            print(f"   🔄 REDUCE PHASE: Combining {len(chunk_summaries)} summaries...")
            combined = "\n\n".join(chunk_summaries)
            
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
- Just write the bullet points directly{self._lang_instruction()}

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
            print("   Falling back to Ollama (llama3.2)...")
            return self._summarize_with_ollama(text, num_sentences)
    
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
        print("🌐 Website Summarizer (ChromaDB + Gemini + EmbeddingGemma)")
        if crawl_depth > 0:
            print(f"   Crawling enabled: depth={crawl_depth}, max_pages={max_sublinks}")
        if self.use_embeddings:
            print(f"   RAG enabled: Using semantic search for better summaries")
        if self.use_vector_db:
            print(f"   Vector DB: ChromaDB for persistent embeddings")
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
    
    def rag_qa(self, text, question, source_type="text", source_path=None):
        """
        Universal RAG Q&A function for documents, websites, or raw text
        
        Args:
            text: The text content to query
            question: The question to answer
            source_type: "document", "website", or "text"
            source_path: Original file path or URL (optional)
        """
        print("\n" + "=" * 60)
        print("❓ RAG Q&A (ChromaDB + EmbeddingGemma + Gemini)")
        print(f"   Source: {source_type}")
        if source_path:
            print(f"   Path: {source_path}")
        print(f"   Question: {question}")
        print("=" * 60)
        
        if not text:
            return None
        
        # Generate document ID
        doc_id = self._get_document_id(text)
        
        # Check if we already have embeddings
        if self._check_existing_embeddings(doc_id):
            cached_data = self._get_chunks_from_db(doc_id)
            if cached_data:
                chunks, embeddings = cached_data
                print(f"   ♻️  Using {len(chunks)} cached chunks")
            else:
                chunks = self._split_into_chunks(text, max_words=1000, overlap=200)
                embeddings = self._embed_chunks(chunks, doc_id=doc_id, full_text=text)
        else:
            # Split into chunks
            chunks = self._split_into_chunks(text, max_words=1000, overlap=200)
            print(f"   Split into {len(chunks)} chunks")
            embeddings = self._embed_chunks(chunks, doc_id=doc_id, full_text=text)
        
        # Rank by relevance to question (uses ChromaDB if available)
        # For Q&A, we DO want to use semantic ranking to find relevant chunks
        ranked_indices = self._rank_chunks_by_relevance(
            chunks, 
            embeddings, 
            query=question,
            use_db=True
        )
        
        # Get top 3 most relevant chunks
        top_chunks = [chunks[i] for i in ranked_indices[:3]]
        context = "\n\n".join(top_chunks)
        
        print(f"   Using top 3 most relevant chunks as context")
        
        # Generate answer using Gemini, fall back to Ollama
        answer = None
        lang_instruction = self._lang_instruction()
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)

            prompt = f"""Answer the following question based on the provided context. Use simple language that a 10-year-old can understand.{lang_instruction}

                    Question: {question}

                    Context:
                    {context[:8000]}

                    Answer (in simple, clear language, - Do NOT include titles, headers, or bold text (**) ):"""

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )

            if response and response.text:
                answer = response.text.strip()
                print(f"✅ Answer generated successfully")

        except Exception as e:
            print(f"⚠️  Gemini Q&A error: {e}")
            print("   Falling back to Ollama (llama3.2)...")

        if not answer:
            answer = self._rag_qa_with_ollama(context, question)

        if not answer:
            return None

        # Translate answer if target language is not English (safety net in case Gemini ignored the instruction)
        if self.target_lang != 'en':
            answer = self.translate_text(answer)

        result = {
            'original_text': text,
            'summary': answer,
            'word_count': len(text.split()),
            'summary_word_count': len(answer.split()),
            'question': question,
            'source_type': source_type,
        }
        if source_path:
            result['source_path'] = source_path
        return result

    def _rag_qa_with_ollama(self, context, question):
        """Fallback Q&A using Ollama llama3.2"""
        print(f"\n🦙 Using Ollama (llama3.2) for Q&A...")
        try:
            prompt = f"""Answer the following question based on the provided context. Use simple language that a 10-year-old can understand.

Question: {question}

Context:
{context[:8000]}

Answer (in simple, clear language):"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "top_p": 0.95}
                },
                timeout=120
            )

            if response.status_code == 200:
                answer = response.json().get('response', '').strip()
                if answer:
                    print(f"✅ Ollama Q&A answer generated successfully")
                    return answer

            print("⚠️  Ollama Q&A failed")
            return None
        except Exception as e:
            print(f"⚠️  Ollama Q&A error: {e}")
            return None

    def rag_qa_document(self, file_path, question):
        """Answer questions about a document using RAG with ChromaDB"""
        print(f"📄 Processing Document: {file_path}")
        
        # Extract text from document
        text = self.extract_text_from_document(file_path)
        if not text:
            return None
        
        # Use unified RAG Q&A function
        return self.rag_qa(text, question, source_type="document", source_path=file_path)
    
    def rag_qa_website(self, url, question):
        """Answer questions about a website using RAG with ChromaDB (uses semantic ranking)"""
        print(f"🌐 Fetching website: {url}")
        
        # Extract website content
        text = self.extract_text_from_website(url, crawl_depth=1, max_sublinks=3)
        if not text:
            return None
        
        # Use unified RAG Q&A function
        return self.rag_qa(text, question, source_type="website", source_path=url)


def main():
    print("=" * 60)
    print("📄 Document & Website Summarizer")
    print("Docling + Google Gemini 3.0 Flash")
    print("=" * 60)
    print("\nFeatures:")
    print("  • Automatic mixed-language detection")
    print("  • Complex table recognition")
    print("  • Layout preservation")
    print("  • PDF processing (no image conversion needed!)")
    print("  • Google Gemini 3.0 Flash for AI summarization")
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
