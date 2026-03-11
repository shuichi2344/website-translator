import sounddevice as sd
import numpy as np
from pynput import keyboard
from transformers import pipeline
import torch
import warnings
from datetime import datetime
from ddgs import DDGS
import trafilatura
import requests
import spacy
from sentence_transformers import SentenceTransformer, util

# Load the small English model
nlp = spacy.load("en_core_web_sm")

# 1. Suppress the annoying transformers warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# --- Configuration ---
MODEL_NAME = "mesolitica/malaysian-whisper-small-v2"
QUERY_CLEANER_MODEL = "meta-llama/Llama-3.2-1B-Instruct"
SAMPLING_RATE = 16000
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading model '{MODEL_NAME}' onto {device}...")
pipe = pipeline(
    "automatic-speech-recognition",
    model=MODEL_NAME,
    chunk_length_s=30,
    device=device
)

class PTTSession:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        if not self.recording:
            print("\n🔴 Listening... (Release SPACE to stop)")
            self.audio_data = []
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.recording = False
            print("⏹️  Processing...")
            self.process_audio()

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

    def refine_query(self, raw_text):
        doc = nlp(raw_text.lower())

        keywords = []

        for token in doc:

            # keep important grammatical roles
            if token.dep_ in ["nsubj", "dobj", "pobj", "attr", "ROOT"]:
                keywords.append(token.lemma_)

            # keep numbers (age, dates, quantities)
            if token.pos_ == "NUM":
                keywords.append(token.text)

            # keep named entities
            if token.ent_type_:
                keywords.append(token.text)

        # remove duplicates but preserve order
        seen = set()
        compressed = []

        for word in keywords:
            if word not in seen:
                seen.add(word)
                compressed.append(word)

        return " ".join(compressed)

    def process_audio(self):
        if not self.audio_data:
            return
        
        audio_np = np.concatenate(self.audio_data, axis=0).flatten()
        result = pipe(audio_np, generate_kwargs={"task": "transcribe"})
        raw_text = result['text'].strip()
        
        print(f"📝 You asked: {raw_text}")

        # Basic filter to ensure we aren't searching for "junk" input
        if len(raw_text) > 4:
            refined = self.refine_query(raw_text)
            print(f"🧹 Cleaned query: {refined}")
            self.get_answer_from_web(refined)
        else:
            print("⚠️ Input too short to search.")

session = PTTSession()

def on_press(key):
    if key == keyboard.Key.space:
        session.start_recording()

def on_release(key):
    if key == keyboard.Key.space:
        session.stop_recording()
    if key == keyboard.Key.esc:
        return False

stream = sd.InputStream(samplerate=SAMPLING_RATE, channels=1, callback=session.callback)

print(f"\n✅ READY! (Today is {datetime.now().strftime('%A, %d %B %Y')})")
print("Hold SPACE to ask a question. Press ESC to quit.")

with stream:
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()