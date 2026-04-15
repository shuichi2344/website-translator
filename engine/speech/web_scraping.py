import os
from pathlib import Path
from dotenv import load_dotenv
# Try the modern import first
try:
    from firecrawl import Firecrawl as FirecrawlApp
except ImportError:
    from firecrawl import FirecrawlApp

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

# Initialize with your key
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk.strip())
        if i + chunk_size >= len(text):
            break
    return chunks

def scrape_with_firecrawl(url):
    """
    Updated for latest Firecrawl SDK:
    Passes options as direct keyword arguments.
    """
    try:
        # Pass options directly as keyword arguments, NOT in a 'params' dict
        # The first argument is the URL (positional), the rest are keywords.
        result = app.scrape(
            url, 
            formats=['markdown'], 
            only_main_content=True
        )
        
        # Check if result is a dictionary or an object
        if isinstance(result, dict):
            markdown_content = result.get('markdown', '')
        else:
            markdown_content = getattr(result, 'markdown', '')

        if markdown_content:
            print(f"✓ Successfully scraped {len(markdown_content)} chars from {url}")
            return chunk_text(markdown_content)
        else:
            print(f"⚠ Warning: No content found for {url}")
            return []

    except Exception as e:
        print(f"❌ Firecrawl error on {url}: {e}")
        return []

def get_chunks_from_list(url_list):
    """
    Scrape multiple URLs and return chunks with source URL metadata
    
    Returns:
        tuple: (chunks, chunk_to_url_map)
        - chunks: list of text chunks
        - chunk_to_url_map: dict mapping chunk index to source URL
    """
    final_chunks = []
    chunk_to_url_map = {}  # Maps chunk index to source URL
    
    for url in url_list:
        print(f"Processing: {url}")
        page_chunks = scrape_with_firecrawl(url)
        
        # Track which URL each chunk came from
        for chunk in page_chunks:
            chunk_to_url_map[len(final_chunks)] = url
            final_chunks.append(chunk)
    
    # Remove duplicates while preserving URL mapping
    unique_chunks = []
    unique_chunk_to_url = {}
    seen = set()
    
    for i, chunk in enumerate(final_chunks):
        if chunk not in seen:
            seen.add(chunk)
            unique_chunk_to_url[len(unique_chunks)] = chunk_to_url_map[i]
            unique_chunks.append(chunk)
    
    return unique_chunks, unique_chunk_to_url

# # Test run
# if __name__ == "__main__":
#     test_urls = [
#         "https://www.imi.gov.my/index.php/en/main-services/passport/malaysian-international-passport/",
#         "https://www.malaysia.gov.my/portal/content/27671"
#     ]
#     all_chunks = get_chunks_from_list(test_urls)
#     print(f"\nTotal unique chunks gathered: {len(all_chunks)}")