import os
import numpy as np
try:
    from pynput import keyboard
except ImportError:
    keyboard = None  # pynput not required for web/API usage
from transformers import pipeline
import warnings
import torch
from llama_cpp import Llama
import soundfile as sf
from typing import Tuple

# Prevent torch._dynamo from registering noisy/slow atexit handlers (Windows often looks "hung" on exit).
# This app does not rely on torch.compile, so disabling Dynamo is safe here.
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

country = "Malaysia"

# ==========================
# CONFIGURATION
# ==========================
ASR_MODEL = "openai/whisper-large-v3-turbo"
# No longer a string path for transformers, but a local GGUF file
SAMPLING_RATE = 16000

# ==========================
# LAZY MODEL LOADING
# ==========================
_asr_pipe = None
_llm_instance = None  # <--- Renamed for clarity

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

    print(f"--- Loading Local LLM: Sailor2-8B-IQ2_M (GGUF) ---")
    # This automatically downloads the file from HF to your cache if not present
    _llm_instance = Llama.from_pretrained(
        repo_id="bartowski/Sailor2-8B-Chat-GGUF",
        filename="Sailor2-8B-Chat-IQ2_M.gguf",
        n_ctx=2048,    # Context window
        n_threads=8,   # Adjust based on your physical CPU cores
        verbose=False  # Keeps the console clean
    )
    return _llm_instance

# ==========================
# UTILITIES
# ==========================

def llm_process(text, task):
    if not text or len(text) < 2:
        return {"dialect": "N/A", "question": "No input detected", "query": "N/A"}

    if task == "dialect":
        sys_msg = (
        "You are an ASEAN Linguistic Expert. Detect the dialect(s) from this list: "
        "Manglish, Singlish, Thai-English, Malay, Hokkien, Cantonese, Tagalog, Taglish, Indonesian, Thai, Lao, Burmese, Sundanese, Vietnamese, Khmer.\n"
        "RULE: If multiple dialects are used, combine them with a '+'.\n"
        "Example: 'Sawadika, where is the shop?' -> Thai+English\n"
        "Output ONLY the names. No extra words or parentheses."
    )
    elif task == "question":
        sys_msg = (
            "You are a Translator. Rewrite the input into ONE clear question.\n"
            "STRICT RULES:\n"
            "- Remove all slang and particles.\n"
            "- No bolding, no notes, no parentheses.\n"
            "Output ONLY the English question."
        )
    elif task == "query":
        sys_msg = (
            f"You are a Search Expert. The current user location is {country}.\n"
            "Convert the input into professional English keywords.\n"
            "RULES:\n"
            f"1. If the country is not specified, assume the context is {country}.\n"
            "2. Output must be 100 percent English. Translate all dialect words.\n"
            f"Example: 'renew license' -> {country} driving license renewal requirements online\n"
            "Output ONLY the keywords."
        )

    prompt = f"<|im_start|>system\n{sys_msg}<|im_end|>\n<|im_start|>user\nText: {text}<|im_end|>\n<|im_start|>assistant\n"
    
    try:
        llm = get_llm_instance()
        output = llm(prompt, max_tokens=100, stop=["<|im_end|>", "\n\n"], temperature=0.1)
        response = output["choices"][0]["text"].strip()
        
        # FIX: If the task is 'question' or 'query', the small model won't output the label
        # So we force the result into the dictionary even if the label is missing
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

def transcribe_audio(filepath: str, *, normalize_to_question: bool = False) -> str:
    """
    Transcribe audio for the web app without requiring ffmpeg.
    The web UI will upload WAV (PCM) so we can decode via libsndfile (soundfile).
    """
    samples, sr = _load_audio_soundfile(filepath)
    if samples.size == 0:
        return ""

    # Ensure mono float32
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = samples.astype(np.float32, copy=False)

    # Resample to Whisper's expected rate (16k)
    if sr != SAMPLING_RATE:
        samples = _resample_linear(samples, sr, SAMPLING_RATE)
        sr = SAMPLING_RATE

    # Add a tiny bit of silence (0.5s) at the start/end to avoid clipped words
    pad = int(0.5 * sr)
    if pad > 0:
        samples = np.concatenate([np.zeros(pad, dtype=np.float32), samples, np.zeros(pad, dtype=np.float32)])

    asr = get_asr_pipe()
    res = asr(samples, generate_kwargs={"task": "transcribe"}, chunk_length_s=30, stride_length_s=5)
    raw_text = (res.get("text") or "").strip()
    if not raw_text:
        return ""

    # By default, return the raw transcription (what the user spoke).
    # Normalization into a "clean question" is optional and should be explicitly requested.
    if normalize_to_question:
        normalized = llm_process(raw_text, "question").get("question")
        if isinstance(normalized, str) and normalized.strip():
            return normalized.strip()

    # Fallback / default
    return raw_text


def _load_audio_soundfile(path: str) -> Tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    return data, int(sr)


def _resample_linear(x: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return x
    if x.size == 0:
        return x.astype(np.float32, copy=False)
    duration = x.shape[0] / float(src_sr)
    dst_len = max(1, int(round(duration * dst_sr)))
    src_idx = np.linspace(0.0, x.shape[0] - 1, num=x.shape[0], dtype=np.float32)
    dst_idx = np.linspace(0.0, x.shape[0] - 1, num=dst_len, dtype=np.float32)
    return np.interp(dst_idx, src_idx, x.astype(np.float32, copy=False)).astype(np.float32, copy=False)

# ==========================
# PUSH TO TALK SESSION
# ==========================
class PTTSession:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.results = {"dialect": None, "question": None, "query": None}

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        if not self.recording:
            print("\nRecording... (Release SPACE to stop)")
            self.audio_data = []
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.recording = False
            print("Processing...")
            self.process_audio()

    # ... (inside PTTSession class) ...

    def process_audio(self):
        if not self.audio_data: return
        audio_np = np.concatenate(self.audio_data, axis=0).flatten()

        # 1. TRANSCRIBE
        asr = get_asr_pipe()
        res = asr(audio_np, generate_kwargs={"task": "transcribe", "do_sample": False})
        raw_text = res["text"].strip()
        
        print(f"Raw Transcription: {raw_text}")
        if len(raw_text) < 2: return

        # 2. ANALYZE (Three separate focused passes)
        print("Normalizing and Generating Query...")
        
        # We extract the string result from the dictionary returned by llm_process
        self.dialect_data = llm_process(raw_text, "dialect").get("dialect")
        self.question_data = llm_process(raw_text, "question").get("question")
        self.query_data = llm_process(raw_text, "query").get("query")

        # Update the dictionary that run_assistant() actually returns
        self.results = {
            "dialect": self.dialect_data,
            "question": self.question_data,
            "query": self.query_data
        }

# if __name__ == "__main__":
#     try:
#         # Pre-load to ensure models are ready
#         get_asr_pipe()
#         llm = get_llm_instance()

#         final_results = run_assistant()

#         print("\n" + "="*30)
#         print(f"DETECTED: {final_results.get('dialect')}")
#         print(f"ENGLISH : {final_results.get('question')}")
#         print(f"QUERY   : {final_results.get('query')}")
#         print("="*30)

#     except KeyboardInterrupt:
#         print("\nStopping assistant...")
#     finally:
#         # MANUALLY CLOSE THE LLM
#         # This prevents the TypeError you saw in the traceback
#         if _llm_instance is not None:
#             print("Cleaning up models...")
#             _llm_instance.close()
#             _llm_instance = None