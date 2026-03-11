from speech_to_text import speech_to_text
from web_scraping import search_web

query = speech_to_text()

if query:
    print("Sending query to web scraping:", query)
    search_web(query)