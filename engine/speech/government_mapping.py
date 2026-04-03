# discovery.py
import os
import serpapi
from dotenv import load_dotenv

load_dotenv()

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
    """
    api_key = os.getenv("SERP_API_KEY")
    
    if not api_key:
        print("⚠️  SERP_API_KEY not found in .env file!")
        print("Please get your API key from https://serpapi.com/ and add it to .env")
        print("Free tier: 100 searches/month")
        return []
    
    try:
        client = serpapi.Client(api_key=api_key)
        
        # Advanced Query: Target specific sub-pages
        # We add 'inurl:en' to ensure we get English pages if applicable
        search_query = f"{query} site:{country_suffix}"
        
        results = client.search({
            "engine": "google",
            "q": search_query,
            "hl": "en",
            "gl": country_suffix.split('.')[-1] # Auto-detect country code (e.g., 'my')
        })

        organic_results = results.get("organic_results", [])
        if not organic_results:
            return []

        discovered_links = []
        
        # 1. Grab Sitelinks (These are high-intent deep links)
        top_result = organic_results[0]
        sitelinks = top_result.get("sitelinks", {})
        
        # Sitelinks can be 'inline' or 'expanded'
        for link_type in ["inline", "expanded"]:
            for item in sitelinks.get(link_type, []):
                discovered_links.append(item.get("link"))

        # 2. Add the main organic links as fallback
        for res in organic_results[:3]: # Take top 3 main results
            discovered_links.append(res.get("link"))

        # Remove duplicates while preserving order
        return list(dict.fromkeys(discovered_links))
    
    except Exception as e:
        print(f"⚠️  Error searching for government links: {e}")
        return []
