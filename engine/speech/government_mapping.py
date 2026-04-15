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
    Returns a list of specific deep links from government sites using Serper.dev.
    """
    api_key = os.getenv("serper")

    if not api_key:
        print("⚠️  serper key not found in .env file!")
        return []

    search_query = f"{query} site:.gov.{country_suffix}"

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": search_query, "gl": country_suffix, "hl": "en"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        organic = data.get("organic", [])
        if not organic:
            print("⚠️  No results found.")
            return []

        links = []

        # Grab sitelinks from top result if available
        top = organic[0]
        for sl in top.get("sitelinks", []):
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
