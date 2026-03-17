"""
engine/speech/main.py — UI-integrated pipeline.

run_pipeline_with_stt_result() and _pipeline_with_result() are both
importable so home.py can call either the threaded wrapper or the raw
function directly.
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Callable


def run_pipeline_with_stt_result(
    stt_result: dict,
    on_status: Callable[[str], None],
    on_result: Callable[[str, list, str, str], None],
    on_error: Callable[[Exception], None],
    country_suffix: str = "my",
) -> None:
    """Spawn a background thread that runs the full pipeline."""
    threading.Thread(
        target=_pipeline_with_result,
        args=(stt_result, on_status, on_result, on_error, country_suffix),
        daemon=True,
    ).start()


def _pipeline_with_result(
    stt_result: dict,
    on_status: Callable[[str], None],
    on_result: Callable[[str, list, str, str], None],
    on_error: Callable[[Exception], None],
    country_suffix: str = "my",
) -> None:
    """Full pipeline: gov-link search → scrape → RAG → answer → TTS."""
    try:
        from engine.speech.web_scraping import get_chunks_from_list
        from engine.speech.text_to_speech import speak_answer
        from engine.speech.government_mapping import find_specific_gov_links
        from engine.speech.embedding import ingest_to_chroma, query_from_chroma
        from engine.speech.response_gen import generate_final_response

        dialect  = stt_result.get("dialect") or ""
        question = stt_result.get("question") or stt_result.get("raw") or ""
        query    = stt_result.get("query") or question

        if question:
            on_status(f'🗣 "{question}"')
        if dialect:
            on_status(f"Detected dialect: {dialect}")

        # 1. Find government links
        on_status("Searching official government sources...")
        links = find_specific_gov_links(query, country_suffix)
        if not links:
            on_status("No official links found.")
            return

        on_status(f"Found {len(links)} source(s). Extracting content...")

        # 2. Scrape & chunk
        all_chunks = get_chunks_from_list(links)
        if not all_chunks:
            on_status("Could not extract text from pages.")
            return

        on_status(f"Extracted {len(all_chunks)} content chunks.")

        # 3. Ingest to ChromaDB
        on_status("Indexing information...")
        doc_id = f"gov_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ingest_to_chroma(doc_id, all_chunks)

        # 4. RAG query
        on_status("Finding most relevant information...")
        relevant_info = query_from_chroma(question, top_k=5)

        # 5. Generate answer
        on_status("Drafting answer...")
        final_answer = generate_final_response(question, relevant_info, dialect)

        sources_text = "\n".join(f"• {link}" for link in links)
        on_status(f"Sources:\n{sources_text}")

        # Deliver final answer
        on_result(final_answer, links, dialect, question)

        # 6. TTS
        on_status("Speaking the answer...")
        asyncio.run(speak_answer(final_answer))

    except Exception as exc:
        on_error(exc)
