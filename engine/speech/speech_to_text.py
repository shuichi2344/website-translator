from __future__ import annotations

import threading
import warnings

import numpy as np
import sounddevice as sd
import torch
from transformers import pipeline

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

country = "Malaysia"

# ==========================
# CONFIGURATION
# ==========================
ASR_MODEL = "openai/whisper-large-v3-turbo"
SAMPLING_RATE = 16000

# ==========================
# LAZY MODEL LOADING
# ==========================
_asr_pipe = None
_llm_instance = None


def get_asr_pipe():
    global _asr_pipe
    if _asr_pipe is not None:
        return _asr_pipe
    device = 0 if torch.cuda.is_available() else -1
    dtype = torch.float16 if device == 0 else torch.float32
    print(f"--- Loading ASR Model: {ASR_MODEL} ---")
    _asr_pipe = pipeline(
        "automatic-speech-recognition",
        model=ASR_MODEL,
        chunk_length_s=30,
        device=device,
        torch_dtype=dtype,
    )
    return _asr_pipe


def get_llm_instance():
    """Loads the CPU-optimized GGUF model."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance
    from llama_cpp import Llama  # type: ignore
    print("--- Loading Local LLM: Sailor2-8B-IQ2_M (GGUF) ---")
    _llm_instance = Llama.from_pretrained(
        repo_id="bartowski/Sailor2-8B-Chat-GGUF",
        filename="Sailor2-8B-Chat-IQ2_M.gguf",
        n_ctx=2048,
        n_threads=8,
        verbose=False,
    )
    return _llm_instance


# ==========================
# UTILITIES
# ==========================

def llm_process(text: str, task: str) -> dict:
    if not text or len(text) < 2:
        return {"dialect": "N/A", "question": "No input detected", "query": "N/A"}

    if task == "dialect":
        sys_msg = (
            "You are an ASEAN Linguistic Expert. Detect the dialect(s) from this list: "
            "Manglish, Singlish, Thai-English, Malay, Hokkien, Cantonese, Tagalog, Taglish, "
            "Indonesian, Thai, Lao, Burmese, Sundanese, Vietnamese, Khmer.\n"
            "RULE: If multiple dialects are used, combine them with a '+'.\n"
            "Output ONLY the names. No extra words or parentheses."
        )
    elif task == "question":
        sys_msg = (
            "You are an English Translator. Rewrite the input into ONE clear Standard English question.\n"
            "STRICT RULES:\n"
            "- The output MUST be in English ONLY.\n"
            "- Remove all slang and particles.\n"
            "- No bolding, no notes, no parentheses.\n"
            "Output ONLY the English question."
        )
    elif task == "query":
        sys_msg = (
            f"You are a Search Expert. The current user location is {country}.\n"
            "Convert the input into professional English keywords.\n"
            f"If the country is not specified, assume the context is {country}.\n"
            "Output ONLY the keywords."
        )
    else:
        return {"dialect": "N/A", "question": "N/A", "query": "N/A"}

    prompt = (
        f"<|im_start|>system\n{sys_msg}<|im_end|>\n"
        f"<|im_start|>user\nText: {text}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    try:
        llm = get_llm_instance()
        output = llm(prompt, max_tokens=100, stop=["<|im_end|>", "\n\n"], temperature=0.1)
        response = output["choices"][0]["text"].strip()
        results = {"dialect": "N/A", "question": "N/A", "query": "N/A"}
        if task == "dialect":
            results["dialect"] = response.replace("DIALECT:", "").strip()
        elif task == "question":
            results["question"] = response.replace("QUESTION:", "").strip()
        elif task == "query":
            results["query"] = response.replace("QUERY:", "").strip()
        return results
    except Exception as e:
        print(f"⚠️ LLM Error: {e}")
        return {"dialect": "N/A", "question": "N/A", "query": "N/A"}


# ==========================
# UI-DRIVEN PTT SESSION
# ==========================

class PTTSession:
    """
    Push-to-talk session driven by UI press/release events.

    Usage:
        session = PTTSession(on_result=my_callback, on_error=my_error_callback)
        session.start_recording()   # call on button press
        session.stop_recording()    # call on button release

    Callbacks:
        on_result(results: dict)  — called with {"dialect", "question", "query"}
        on_error(exc: Exception)  — called if recording or transcription fails
    """

    def __init__(
        self,
        on_result=None,
        on_error=None,
        on_status=None,
    ):
        self.on_result = on_result
        self.on_error = on_error
        self.on_status = on_status  # callable(str) for step-by-step progress
        self._recording = False
        self._audio_data: list = []
        self._stream = None

    # ------------------------------------------------------------------
    def _audio_callback(self, indata, frames, time, status):
        if self._recording:
            self._audio_data.append(indata.copy())

    # ------------------------------------------------------------------
    def start_recording(self):
        """Open the microphone stream and begin capturing audio."""
        if self._recording:
            return
        self._audio_data = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLING_RATE,
                channels=1,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._recording = False
            if self.on_error:
                self.on_error(exc)

    # ------------------------------------------------------------------
    def stop_recording(self):
        """Stop capturing and process the audio in a background thread."""
        if not self._recording:
            return
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # Process off the UI thread so we don't block Flet
        threading.Thread(target=self._process, daemon=True).start()

    # ------------------------------------------------------------------
    def _process(self):
        def status(msg):
            if self.on_status:
                self.on_status(msg)

        try:
            if not self._audio_data:
                status("No audio captured.")
                return

            status("Audio recorded ✓")
            audio_np = np.concatenate(self._audio_data, axis=0).flatten()

            # 1. Transcribe
            status("Transcribing audio...")
            asr = get_asr_pipe()
            res = asr(audio_np, generate_kwargs={"task": "transcribe", "do_sample": False})
            raw_text = res["text"].strip()
            if len(raw_text) < 2:
                status("Could not detect speech. Please try again.")
                return

            status(f'Heard: "{raw_text}"')

            # 2. Analyse
            status("Analysing dialect and normalising question...")
            results = {
                "dialect": llm_process(raw_text, "dialect").get("dialect"),
                "question": llm_process(raw_text, "question").get("question"),
                "query":    llm_process(raw_text, "query").get("query"),
                "raw":      raw_text,
            }
            if self.on_result:
                self.on_result(results)
        except Exception as exc:
            if self.on_error:
                self.on_error(exc)
