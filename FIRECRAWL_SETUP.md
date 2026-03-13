# Firecrawl Setup Guide

Firecrawl provides enhanced web scraping capabilities with better handling of dynamic content, JavaScript-rendered sites, and complex layouts.

## Why Use Firecrawl?

- **Better Content Extraction**: Handles dynamic websites and JavaScript-rendered content
- **Clean Markdown Output**: Returns clean, LLM-ready markdown format
- **Proxy Management**: Automatically handles proxies, rate limits, and caching
- **Main Content Focus**: Extracts only the main content, filtering out navigation, ads, etc.

## Installation

### 1. Install Firecrawl Python Package

```bash
pip install firecrawl-py
```

### 2. Get API Key

1. Go to [https://firecrawl.dev](https://firecrawl.dev)
2. Click "Sign Up" or "Get Started"
3. Create an account (free tier available)
4. Go to your dashboard
5. Copy your API key (starts with `fc-`)

### 3. Configure API Key

Open your `.env` file and replace the placeholder:

```env
# Before:
FIRECRAWL_API_KEY="your-firecrawl-api-key-here"

# After (example):
FIRECRAWL_API_KEY="fc-1234567890abcdef1234567890abcdef"
```

**Important**: 
- Your API key should start with `fc-`
- Keep it secret - don't commit to Git
- The `.env` file is already in `.gitignore`

## Testing

### Test with Command Line

```bash
python document_summariser_v6_docling.py
```

Choose option 2 (Website) and enter a URL like:
```
https://www.jpj.gov.my/myjpj/
```

You should see:
```
🌐 Fetching website: https://www.jpj.gov.my/myjpj/
   Using Firecrawl for enhanced web scraping...
✅ Extracted 2419 characters via Firecrawl
```

### Test with Web Interface

```bash
python summarizer_web.py
```

Open http://localhost:5000 and try the Website tab.

## Configuration Options

### Basic Usage (Current Implementation)

```python
from firecrawl import Firecrawl

app = Firecrawl(api_key="fc-YOUR-API-KEY")
result = app.scrape(url, formats=['markdown'])
text = result.markdown
```

### Advanced Options

You can customize the scraping behavior:

```python
result = app.scrape(
    url,
    formats=['markdown', 'html'],  # Multiple formats
    only_main_content=True,         # Filter out navigation/ads
    wait_for='networkidle',         # Wait for page to load
    timeout=30000,                  # 30 second timeout
)
```

### Available Formats

- `markdown` - Clean markdown (recommended)
- `html` - Cleaned HTML
- `raw_html` - Original HTML
- `links` - Extract all links
- `screenshot` - Page screenshot
- `metadata` - Page metadata

## Pricing

### Free Tier
- **500 credits/month**
- 1 credit = 1 page scraped
- Perfect for testing and small projects

### Paid Plans
- **Starter**: $20/month - 5,000 credits
- **Standard**: $100/month - 30,000 credits
- **Scale**: Custom pricing

## Troubleshooting

### Common Errors and Solutions

#### 1. Error: "'Firecrawl' object has no attribute 'scrape_url'"

**Cause**: Using old API method names

**Solution**: The API changed. Use `scrape()` instead of `scrape_url()`:

```python
# ❌ Old (doesn't work)
result = app.scrape_url(url, params={'formats': ['markdown']})

# ✅ New (correct)
result = app.scrape(url, formats=['markdown'])
```

#### 2. Error: "API key not configured" or "using placeholder"

**Cause**: API key not set or still using placeholder value

**Solution**: 
1. Open `.env` file
2. Replace `your-firecrawl-api-key-here` with your actual key
3. Make sure it starts with `fc-`
4. Restart your Python script

```env
# ❌ Wrong
FIRECRAWL_API_KEY="your-firecrawl-api-key-here"

# ✅ Correct
FIRECRAWL_API_KEY="fc-1234567890abcdef1234567890abcdef"
```

#### 3. Error: "Firecrawl package not installed"

**Solution**:
```bash
pip install firecrawl-py
```

If that fails, try:
```bash
pip install --upgrade pip
pip install firecrawl-py --no-cache-dir
```

#### 4. Error: "401 Unauthorized" or "Invalid API key"

**Causes**:
- API key is incorrect
- API key has expired
- Extra spaces in the key

**Solution**:
1. Go to https://firecrawl.dev/dashboard
2. Generate a new API key
3. Copy it carefully (no extra spaces)
4. Update `.env` file
5. Restart your script

#### 5. Error: "429 Too Many Requests"

**Cause**: Exceeded rate limit (500 requests/month on free tier)

**Solutions**:
- Wait for your monthly quota to reset
- Upgrade to a paid plan
- Use BeautifulSoup fallback (automatic)

#### 6. Error: "Response format is not a dict" or "Unexpected response format"

**Cause**: Firecrawl returns a `Document` object, not a dictionary

**Solution**: Already fixed in the code! Access markdown as an attribute:

```python
# ✅ Correct (current implementation)
if hasattr(result, 'markdown'):
    text = result.markdown
```

#### 7. Error: "Module 'firecrawl' has no attribute 'FirecrawlApp'"

**Cause**: Using old class name

**Solution**: Use `Firecrawl` instead of `FirecrawlApp`:

```python
# ❌ Old
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=key)

# ✅ New
from firecrawl import Firecrawl
app = Firecrawl(api_key=key)
```

#### 8. Error: "Connection timeout" or "Request failed"

**Causes**:
- Slow internet connection
- Firecrawl API is down
- Firewall blocking requests

**Solutions**:
1. Check your internet connection
2. Check Firecrawl status: https://status.firecrawl.dev
3. Try again in a few minutes
4. System will automatically fall back to BeautifulSoup

#### 9. Error: "No markdown content in response"

**Causes**:
- Website blocked Firecrawl
- Page failed to load
- Invalid URL

**Solutions**:
1. Verify the URL is correct and accessible
2. Try a different website
3. System will fall back to BeautifulSoup automatically

#### 10. Error: "ImportError: cannot import name 'Firecrawl'"

**Cause**: Wrong package version or corrupted installation

**Solution**:
```bash
pip uninstall firecrawl-py
pip install firecrawl-py --upgrade
```

#### 11. Environment Variable Not Loading

**Cause**: `.env` file not being read

**Solution**:
1. Make sure `.env` is in the same directory as your script
2. Check that `python-dotenv` is installed:
   ```bash
   pip install python-dotenv
   ```
3. Verify the code loads it:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

#### 12. Error: "SSL Certificate Verification Failed"

**Cause**: SSL/TLS issues

**Solution**:
```bash
pip install --upgrade certifi
```

Or temporarily (not recommended for production):
```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### Debugging Tips

#### Enable Verbose Logging

The current implementation already shows detailed logs:
```
🌐 Fetching website: https://example.com
   Using Firecrawl for enhanced web scraping...
✅ Extracted 2419 characters via Firecrawl
```

#### Check API Key is Loaded

Add this to test:
```python
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('FIRECRAWL_API_KEY')
print(f"API Key loaded: {key[:10]}..." if key else "No API key found")
```

#### Test Firecrawl Directly

Create a test script `test_firecrawl.py`:
```python
from firecrawl import Firecrawl
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('FIRECRAWL_API_KEY')

if not api_key or api_key == 'your-firecrawl-api-key-here':
    print("❌ API key not configured")
    exit(1)

print(f"✅ API key found: {api_key[:10]}...")

try:
    app = Firecrawl(api_key=api_key)
    print("✅ Firecrawl initialized")
    
    result = app.scrape('https://example.com', formats=['markdown'])
    print(f"✅ Scrape successful")
    print(f"   Type: {type(result)}")
    print(f"   Has markdown: {hasattr(result, 'markdown')}")
    
    if hasattr(result, 'markdown'):
        print(f"   Length: {len(result.markdown)} characters")
        print(f"   Preview: {result.markdown[:100]}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
```

Run it:
```bash
python test_firecrawl.py
```

### Falls back to BeautifulSoup

If you see this message, it means Firecrawl failed but the system is still working:
```
⚠️  Firecrawl failed: [error message]
   Falling back to BeautifulSoup...
✅ Extracted 2419 characters via BeautifulSoup
```

This is **normal behavior** and ensures your application always works!

### When to Use BeautifulSoup Instead

Consider skipping Firecrawl if:
- You're scraping simple static websites
- You want to avoid API costs
- You're doing high-volume scraping (>500 pages/month)
- The website doesn't use JavaScript

Just leave the API key as placeholder or remove it from `.env`.

## Fallback Behavior

The system automatically falls back to BeautifulSoup if:
- Firecrawl API key is not configured
- Firecrawl package is not installed
- API request fails
- No credits remaining

This ensures your application always works, even without Firecrawl.

## Benefits Over BeautifulSoup

| Feature | Firecrawl | BeautifulSoup |
|---------|-----------|---------------|
| JavaScript rendering | ✅ Yes | ❌ No |
| Dynamic content | ✅ Yes | ❌ No |
| Clean markdown | ✅ Yes | ⚠️ Manual |
| Main content extraction | ✅ Automatic | ⚠️ Manual |
| Proxy handling | ✅ Automatic | ❌ No |
| Rate limiting | ✅ Handled | ⚠️ Manual |
| Cost | 💰 Paid | ✅ Free |

## Documentation

- Official Docs: https://docs.firecrawl.dev
- Python SDK: https://docs.firecrawl.dev/sdks/python
- API Reference: https://docs.firecrawl.dev/features/scrape

## Example Output

When Firecrawl is working correctly, you'll see:

```
🌐 Fetching website: https://example.com
   Using Firecrawl for enhanced web scraping...
✅ Extracted 5432 characters via Firecrawl

🤖 Generating AI summary using llama3.2...
   Document length: 1234 words
```

The markdown will be clean and well-formatted, perfect for AI summarization!

