# discovery.py
import os
from dotenv import load_dotenv

load_dotenv()

# Try to import serpapi - support both old and new versions
try:
    import serpapi
    HAS_NEW_SERPAPI = hasattr(serpapi, 'Client')
except ImportError:
    serpapi = None
    HAS_NEW_SERPAPI = False

# Fallback to google-search-results if serpapi not available
if not HAS_NEW_SERPAPI:
    try:
        from serpapi import GoogleSearch
    except ImportError:
        GoogleSearch = None

# Country to domain suffix mapping
COUNTRY_SUFFIX_MAP = {
    "Malaysia": "my",
    "Indonesia": "id",
    "Thailand": "th",
    "Vietnam": "vn",
    "Philippines": "ph",
    "Myanmar": "mm",
    "Cambodia": "kh",
    "Laos": "la",
    "Singapore": "sg",
    "Brunei": "bn",
    "Timor-Leste": "tl",
}

def get_country_suffix(country_name):
    """Get the domain suffix for a country name"""
    return COUNTRY_SUFFIX_MAP.get(country_name, "my")  # Default to Malaysia

def find_specific_gov_links(query, country_suffix):
    """
    Returns a list of specific deep links from government sites.
    Compatible with both old and new serpapi versions.
    """
    api_key = os.getenv("SERP_API_KEY")
    
    if not api_key or api_key == "your_serpapi_key_here":
        print("⚠️  SERP_API_KEY not found or not configured in .env file!")
        print("Please get your API key from https://serpapi.com/ and add it to .env")
        print("Free tier: 100 searches/month")
        return []
    
    try:
        # Advanced Query: Target specific sub-pages
        search_query = f"{query} site:{country_suffix}"
        
        # Use new serpapi.Client if available
        if HAS_NEW_SERPAPI:
            client = serpapi.Client(api_key=api_key)
            results = client.search({
                "engine": "google",
                "q": search_query,
                "hl": "en",
                "gl": country_suffix.split('.')[-1]
            })
        # Otherwise use old GoogleSearch
        elif GoogleSearch:
            params = {
                "engine": "google",
                "q": search_query,
                "hl": "en",
                "gl": country_suffix.split('.')[-1],
                "api_key": api_key
            }
            search = GoogleSearch(params)
            results = search.get_dict()
        else:
            print("⚠️  serpapi package not installed correctly")
            return []
        
        # Check if results is valid
        if not results or not isinstance(results, dict):
            print("⚠️  SerpAPI returned empty or invalid response")
            print("     This usually means:")
            print("     - API key is invalid")
            print("     - Monthly quota exceeded (100 free searches)")
            print("     - Network/API issue")
            return []

        organic_results = results.get("organic_results", [])
        if not organic_results:
            print("⚠️  No organic results found")
            return []

        discovered_links = []
        
        # 1. Grab Sitelinks (These are high-intent deep links)
        top_result = organic_results[0]
        sitelinks = top_result.get("sitelinks", {})
        
        # Sitelinks can be 'inline' or 'expanded'
        for link_type in ["inline", "expanded"]:
            for item in sitelinks.get(link_type, []):
                link = item.get("link")
                if link:
                    discovered_links.append(link)

        # 2. Add the main organic links as fallback
        for res in organic_results[:3]: # Take top 3 main results
            link = res.get("link")
            if link:
                discovered_links.append(link)

        # Remove duplicates while preserving order
        unique_links = list(dict.fromkeys(discovered_links))
        print(f"✅ Found {len(unique_links)} unique government links")
        return unique_links
    
    except Exception as e:
        print(f"⚠️  Error searching for government links: {e}")
        print("     Check your SERP_API_KEY in .env file")
        print("     Verify you haven't exceeded the monthly quota")
        import traceback
        traceback.print_exc()
        return []
