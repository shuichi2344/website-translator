# discovery.py
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

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
    return COUNTRY_SUFFIX_MAP.get(country_name, "my")


def find_specific_gov_links(query, country_suffix):
    """
    Returns a list of specific deep links from government sites using SerpAPI.
    """
    api_key = os.getenv("SERP_API_KEY")

    if not api_key:
        print("⚠️  SERP_API_KEY not found in .env file!")
        return []

    search_query = f"{query} site:.gov.{country_suffix}"

    try:
        # SerpAPI endpoint (not Serper.dev)
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "q": search_query,
                "api_key": api_key,
                "engine": "google",
                "gl": country_suffix,
                "hl": "en",
                "num": 10
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        organic = data.get("organic_results", [])
        if not organic:
            print("⚠️  No results found.")
            return []

        links = []

        # Grab sitelinks from top result if available
        if organic:
            top = organic[0]
            for sl in top.get("sitelinks", {}).get("inline", []):
                link = sl.get("link")
                if link:
                    links.append(link)

        # Add main organic links
        for res in organic[:5]:
            link = res.get("link")
            if link:
                links.append(link)

        # Deduplicate
        unique_links = list(dict.fromkeys(links))
        print(f"✅ Found {len(unique_links)} government links")
        return unique_links

    except Exception as e:
        print(f"⚠️  Search error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("=== Government Mapping Test ===\n")

    # Test country suffix mapping
    test_countries = ["Malaysia", "Singapore", "Indonesia", "Unknown"]
    print("Country suffix mapping:")
    for country in test_countries:
        suffix = get_country_suffix(country)
        print(f"  {country} -> {suffix}")

    print()

    # Test government link discovery
    test_cases = [
        ("MySTR housing assistance application", "my"),
        ("income tax filing", "my"),
    ]

    for query, suffix in test_cases:
        print(f"Query : {query}")
        print(f"Suffix: {suffix}")
        links = find_specific_gov_links(query, suffix)
        if links:
            for i, link in enumerate(links, 1):
                print(f"  {i}. {link}")
        else:
            print("  No links found.")
        print()
