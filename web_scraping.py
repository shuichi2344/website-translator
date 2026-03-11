from datetime import datetime
from ddgs import DDGS
import trafilatura
import requests
import spacy
from sentence_transformers import SentenceTransformer, util

nlp = spacy.load("en_core_web_sm")

class PTTSession:
    def __init__(self):
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_full_page_content(self, url):
        """Fetch URL and extract main text with trafilatura (ignores ads/menus)."""
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        return trafilatura.extract(downloaded)

    def chunk_text(self, text, chunk_size=500, overlap=50):
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def retrieve_best_chunks(self, query, text):
        chunks = self.chunk_text(text)
        query_emb = self.embed_model.encode(query, convert_to_tensor=True)
        chunk_emb = self.embed_model.encode(chunks, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, chunk_emb)[0]
        ranked = sorted(zip(scores, chunks), reverse=True)
        return [chunk for _, chunk in ranked[:3]]

    def rank_results(self, query, results):
        texts = [r["title"] + " " + r["body"] for r in results]
        query_emb = self.embed_model.encode(query, convert_to_tensor=True)
        doc_emb = self.embed_model.encode(texts, convert_to_tensor=True)

        scores = util.cos_sim(query_emb, doc_emb)[0]

        ranked = sorted(zip(scores, results), reverse=True)

        return [r for _, r in ranked[:3]]

    def get_answer_from_web(self, query):
        """Fetches the actual answer from official .gov.my or Bernama sources."""
        
        # 2. Automatically detect today's Month and Year
        now = datetime.now()
        current_month_year = now.strftime("%B %Y")  # e.g., "March 2026"
        
        # Create a targeted search for official sources
        # official_tlds = "site:gov OR site:gov.* OR site:go.* OR site:bernama.com OR site:reuters.com OR site:apnews.com"
        search_query = f"(site:gov.my OR site:go.jp OR site:gov.sg) {query} {current_month_year}"
        
        print(f"🔍 ANALYZING ({current_month_year}): '{query}'...")
        
        try:
            with DDGS() as ddgs:
                # 3. Pulling results only from official government/news domains
                results = list(ddgs.text(search_query, max_results=10))
                results = self.rank_results(query, results)
                
                if results:
                    extracted_sources = []
                    combined_context_parts = []

                    for i, r in enumerate(results[:3], start=1):
                        url = r.get("href", "") or ""
                        snippet = r.get("body", "") or ""
                        full_text = self.get_full_page_content(url) if url else None
                        context = (full_text and full_text.strip()) or snippet
                        if context:
                            best_chunks = self.retrieve_best_chunks(query, context)
                            context = "\n".join(best_chunks)

                        extracted_sources.append(url)
                        if context:
                            combined_context_parts.append(f"[SOURCE {i}] {url}\n{context}")

                    combined_context = "\n\n".join(combined_context_parts).strip()
                    print("\n" + "═"*60)
                    print("🏛️  OFFICIAL SOURCE FOUND")
                    print("─"*60)
                    print("Sources:")
                    for i, url in enumerate(extracted_sources, start=1):
                        print(f"  {i}. {url}")
                    print("\nRAW EXTRACT (combined):")
                    print(f"{combined_context[:2000]}{'...' if len(combined_context) > 2000 else ''}")
                    print("═"*60)

                    # Optionally ask local Ollama to synthesize a nicer answer
                    if combined_context:
                        ollama_answer = self.get_answer_from_ollama(query, combined_context)
                        if ollama_answer:
                            print("\n🧠 OLLAMA SUMMARY")
                            print("─" * 60)
                            print(ollama_answer.strip())
                            print("─" * 60)
                else:
                    print(f"❌ No official data found for '{query}' in {current_month_year}.")
        except Exception as e:
            print(f"❌ Search Error: {e}")

    def get_answer_from_ollama(self, question, context):
        # Get the most relevant chunks
        best_chunks = self.retrieve_best_chunks(question, context)

        if not best_chunks:
            return "No relevant information found."

        context_for_llm = "\n\n".join(best_chunks)

        prompt = f"""
            You are a factual government assistant.

            Task:
            Answer the user's question using ONLY the provided sources.

            Rules:
            - Interpret synonyms (e.g., "withdraw", "take money out").
            - Answer ONLY using the provided sources
            - Maximum 60 words
            - If the text truly contains no answer, say: "Specific data not found in source."

            Question:
            {question}

            Sources:
            {context_for_llm}

            Answer:
        """

        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )

            resp.raise_for_status()
            data = resp.json()

            return data.get("response", "").strip()

        except Exception as e:
            print(f"❌ Ollama Error: {e}")
            return None

session = PTTSession()


def search_web(query: str) -> None:
    """
    Entry point used by main.py.
    Takes a text query (e.g. from speech_to_text) and runs the web-scraping flow.
    """
    if not query or not query.strip():
        print("⚠️ Empty query, skipping web search.")
        return
    print(f"🔎 Searching web for: {query}")
    session.get_answer_from_web(query.strip())